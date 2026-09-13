"""Turn a direct FLV byte stream into an iterator of parsed FLV tags."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import BinaryIO
from urllib.request import urlopen

from .flv import FlvFormatError, FlvTag, read_tag


DEFAULT_READ_TIMEOUT = 30.0


class SourceStallError(TimeoutError):
    """Raised when an open source connection stops delivering bytes."""


class RawCopy:
    """Best-effort byte-for-byte copy of one source connection.

    The copy is deliberately independent of parsing: write failures disable
    only the copy, so capture retains the received source bytes when possible.
    """

    def __init__(self, path: Path, warning: Callable[[str], None] | None = None) -> None:
        self.path = Path(path)
        self._warning = warning
        self._handle: BinaryIO | None = None
        self._saved_path: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("xb")
            self._saved_path = self.path
        except OSError as error:
            self._warn(f"could not open raw copy {self.path}: {error}")

    @property
    def saved_path(self) -> Path | None:
        """Return the completed raw path, or ``None`` after a copy failure."""
        return self._saved_path

    def write(self, chunk: bytes) -> None:
        """Copy a received chunk without allowing disk errors to stop capture."""
        if self._handle is None:
            return
        try:
            if self._handle.write(chunk) != len(chunk):
                raise OSError("short write")
        except OSError as error:
            self._saved_path = None
            self._warn(f"could not write raw copy {self.path}: {error}")
            self._close_handle()

    def close(self) -> None:
        """Finish the copy and turn a close error into a non-fatal warning."""
        if self._handle is None:
            return
        try:
            self._handle.close()
        except OSError as error:
            self._saved_path = None
            self._warn(f"could not close raw copy {self.path}: {error}")
        finally:
            self._handle = None

    def _close_handle(self) -> None:
        assert self._handle is not None
        try:
            self._handle.close()
        except OSError:
            pass
        self._handle = None

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
                    chunk = response.read(chunk_size)
                except TimeoutError as error:
                    duration = "" if timeout is None else f" after {timeout:g}s"
                    raise SourceStallError(
                        f"source connection stalled{duration} without data"
                    ) from error
                # Stop between chunks even if the parser is waiting for one large tag.
                if check_stop is not None:
                    check_stop()
                if not chunk:
                    break
                # Tee the received bytes before their first parser read.
                if raw_copy is not None:
                    raw_copy.write(chunk)
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
