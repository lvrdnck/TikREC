"""Turn a direct FLV byte stream into an iterator of parsed FLV tags."""

from __future__ import annotations

import json
import time
import warnings
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import BinaryIO, TextIO
from urllib.request import urlopen

from .flv import FlvFormatError, FlvTag, read_tag


DEFAULT_READ_TIMEOUT = 30.0


class SourceStallError(TimeoutError):
    """Raised when an open source connection stops delivering bytes."""


class RawCopy:
    """Copy one source connection without letting diagnostic failures stop capture."""

    def __init__(self, path: Path, warning: Callable[[str], None] | None = None, *,
                 connection_number: int = 1,
                 wall_clock: Callable[[], float] = time.time,
                 monotonic_clock: Callable[[], float] = time.monotonic) -> None:
        if type(connection_number) is not int or connection_number < 1:
            raise ValueError("connection_number must be a positive integer")
        self.path = Path(path)
        self.arrivals_path = self.path.with_suffix(".arrivals.jsonl")
        self._warning = warning
        self._connection_number = connection_number
        self._monotonic_clock = monotonic_clock
        self._handle: BinaryIO | None = None
        self._arrivals_handle: TextIO | None = None
        self._saved_path: Path | None = None
        self._saved_arrivals_path: Path | None = None
        self._offset = 0
        self._monotonic_reference = 0.0
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("xb")
            self._saved_path = self.path
        except OSError as error:
            self._warn(f"could not open raw copy {self.path}: {error}")
            return
        try:
            # Pair wall and monotonic clocks once so arrival elapsed times can be
            # correlated with wall-clock connection events without trusting clock changes.
            wall_reference = wall_clock()
            self._monotonic_reference = monotonic_clock()
            self._arrivals_handle = self.arrivals_path.open("x", encoding="utf-8")
            self._saved_arrivals_path = self.arrivals_path
            self._write_arrival_record({
                "event": "clock_reference", "connection": connection_number,
                "wall_time": wall_reference, "monotonic_time": self._monotonic_reference,
                "boundary": "raw_copy_write",
            })
        # Clock/serialization faults belong to optional diagnostics, not capture.
        except Exception as error:
            self._saved_arrivals_path = None
            self._warn(f"could not open raw arrival log {self.arrivals_path}: {error}")
            self._close_arrivals_handle()

    @property
    def saved_path(self) -> Path | None:
        """Return the completed raw path, or ``None`` after a copy failure."""
        return self._saved_path

    @property
    def saved_arrivals_path(self) -> Path | None:
        """Return the completed arrival-log path, or ``None`` after its failure."""
        return self._saved_arrivals_path

    def write(self, chunk: bytes) -> None:
        """Copy a received chunk without allowing disk errors to stop capture."""
        if self._handle is None:
            return
        observed_at = self._monotonic_clock()
        try:
            if self._handle.write(chunk) != len(chunk):
                raise OSError("short write")
        except OSError as error:
            self._saved_path = None
            self._saved_arrivals_path = None
            self._warn(f"could not write raw copy {self.path}: {error}")
            self._close_handle()
            self._close_arrivals_handle()
            return
        self._write_arrival_record({
            "event": "byte_arrival", "connection": self._connection_number,
            "offset": self._offset, "count": len(chunk), "monotonic_time": observed_at,
            "elapsed_seconds": observed_at - self._monotonic_reference,
        })
        self._offset += len(chunk)

    def observe_read_end(self, reason: str) -> None:
        """Record EOF or a read failure at the same boundary as byte observations."""
        observed_at = self._monotonic_clock()
        self._write_arrival_record({
            "event": "read_end", "connection": self._connection_number, "reason": reason,
            "monotonic_time": observed_at,
            "elapsed_seconds": observed_at - self._monotonic_reference,
        })

    def close(self) -> None:
        """Finish the copy and turn a close error into a non-fatal warning."""
        if self._handle is None:
            return
        try:
            self._handle.close()
        except OSError as error:
            self._saved_path = None
            self._saved_arrivals_path = None
            self._warn(f"could not close raw copy {self.path}: {error}")
        finally:
            self._handle = None
        if self._arrivals_handle is not None:
            try:
                self._arrivals_handle.close()
            except Exception as error:
                # The raw media copy can remain valid when only its sidecar cannot close.
                self._saved_arrivals_path = None
                self._warn(f"could not close raw arrival log {self.arrivals_path}: {error}")
            finally:
                self._arrivals_handle = None

    def _close_handle(self) -> None:
        assert self._handle is not None
        try:
            self._handle.close()
        except OSError:
            pass
        self._handle = None

    def _write_arrival_record(self, values: dict[str, object]) -> None:
        if self._arrivals_handle is None:
            return
        try:
            self._arrivals_handle.write(json.dumps(values, sort_keys=True) + "\n")
            # Line buffering is not guaranteed for regular files, so flush each
            # observation while avoiding an fsync on every network-sized chunk.
            self._arrivals_handle.flush()
        except Exception as error:
            # Optional diagnostic serialization and I/O must never stop recording.
            self._saved_arrivals_path = None
            self._warn(f"could not write raw arrival log {self.arrivals_path}: {error}")
            self._close_arrivals_handle()

    def _close_arrivals_handle(self) -> None:
        if self._arrivals_handle is None:
            return
        try:
            self._arrivals_handle.close()
        except Exception:
            pass
        self._arrivals_handle = None

    def _warn(self, message: str) -> None:
        if self._warning is not None:
            self._warning(message)
        else:
            warnings.warn(message, RuntimeWarning, stacklevel=2)


def iter_tags(chunks: Iterable[bytes]) -> Iterator[FlvTag]:
    """Yield tags from incremental FLV byte chunks.

    The iterable may be backed by an HTTP response, a local file, or a test.
    """
    stream = _ChunkStream(chunks)
    _read_flv_header(stream)
    while tag := read_tag(stream):
        yield tag


def iter_url_chunks(
    url: str,
    *,
    chunk_size: int = 64 * 1024,
    timeout: float | None = DEFAULT_READ_TIMEOUT,
    raw_copy: RawCopy | None = None,
    on_open: Callable[[], None] | None = None,
    check_stop: Callable[[], None] | None = None,
) -> Iterator[bytes]:
    """Yield byte chunks from one direct HTTP FLV URL without retrying."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if timeout is not None and timeout <= 0:
        raise ValueError("timeout must be positive or None")
    try:
        if check_stop is not None:
            check_stop()
        with urlopen(url, timeout=timeout) as response:
            if on_open is not None:
                on_open()
            while True:
                if check_stop is not None:
                    check_stop()
                try:
                    # HTTPResponse.read1 performs at most one underlying buffered
                    # read, so bytes already available are returned before a later stall.
                    read1 = getattr(response, "read1", None)
                    chunk = read1(chunk_size) if callable(read1) else response.read(chunk_size)
                except TimeoutError as error:
                    if raw_copy is not None:
                        raw_copy.observe_read_end("timeout")
                    duration = "" if timeout is None else f" after {timeout:g}s"
                    raise SourceStallError(
                        f"source connection stalled{duration} at the HTTP read boundary"
                    ) from error
                except Exception:
                    if raw_copy is not None:
                        raw_copy.observe_read_end("error")
                    raise
                if not chunk:
                    if raw_copy is not None:
                        raw_copy.observe_read_end("eof")
                    break
                # Timestamp and preserve bytes immediately after read1 returns,
                # even if a concurrent stop prevents the parser from consuming them.
                if raw_copy is not None:
                    raw_copy.write(chunk)
                # Stop between chunks even if the parser is waiting for one large tag.
                if check_stop is not None:
                    check_stop()
                yield chunk
    finally:
        if raw_copy is not None:
            raw_copy.close()


def iter_url_tags(
    url: str,
    *,
    chunk_size: int = 64 * 1024,
    timeout: float | None = DEFAULT_READ_TIMEOUT,
    raw_copy: RawCopy | None = None,
    on_open: Callable[[], None] | None = None,
    check_stop: Callable[[], None] | None = None,
) -> Iterator[FlvTag]:
    """Yield parsed tags from one direct HTTP FLV URL without retrying."""
    chunks = iter_url_chunks(url, chunk_size=chunk_size, timeout=timeout,
                             raw_copy=raw_copy, on_open=on_open, check_stop=check_stop)
    try:
        yield from iter_tags(chunks)
    finally:
        # Closing a parser generator must also release its still-open HTTP response.
        chunks.close()


class _ChunkStream:
    """A file-like view over a chunk iterator for ``flv.read_tag``."""

    def __init__(self, chunks: Iterable[bytes]) -> None:
        self._chunks = iter(chunks)
        self._buffer = bytearray()
        self._exhausted = False

    def read(self, count: int) -> bytes:
        """Return up to ``count`` bytes, blocking on chunks only as needed."""
        if count < 0:
            raise ValueError("unbounded reads are not supported for a live stream")
        while len(self._buffer) < count and not self._exhausted:
            try:
                chunk = next(self._chunks)
            except StopIteration:
                self._exhausted = True
                break
            if not isinstance(chunk, bytes):
                raise TypeError("FLV chunks must be bytes")
            # Keep only bytes not yet consumed; no complete stream is collected.
            self._buffer.extend(chunk)

        data = bytes(self._buffer[:count])
        del self._buffer[:count]
        return data


def _read_flv_header(stream: _ChunkStream) -> None:
    header = stream.read(9)
    if len(header) != 9:
        raise FlvFormatError("truncated FLV header")
    if header[:3] != b"FLV":
        raise FlvFormatError("source did not return an FLV stream")

    data_offset = int.from_bytes(header[5:9], "big")
    if data_offset < 9:
        raise FlvFormatError("invalid FLV data offset")
    if len(stream.read(data_offset - 9)) != data_offset - 9:
        raise FlvFormatError("truncated FLV header extension")

    # FLV places a zero PreviousTagSize before the first tag, after any header
    # extension. Checking it catches shifted or otherwise malformed streams.
    if stream.read(4) != b"\x00\x00\x00\x00":
        raise FlvFormatError("invalid initial FLV PreviousTagSize")
