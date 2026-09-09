"""Turn a direct FLV byte stream into an iterator of parsed FLV tags."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from urllib.request import urlopen

from .flv import FlvFormatError, FlvTag, read_tag


def iter_tags(chunks: Iterable[bytes]) -> Iterator[FlvTag]:
    """Yield tags from incremental FLV byte chunks.

    The iterable may be backed by an HTTP response, a local file, or a test.
    """
    stream = _ChunkStream(chunks)
    _read_flv_header(stream)
    while tag := read_tag(stream):
        yield tag


def iter_url_chunks(
    url: str, *, chunk_size: int = 64 * 1024, timeout: float | None = None
) -> Iterator[bytes]:
    """Yield byte chunks from one direct HTTP FLV URL without retrying."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    with urlopen(url, timeout=timeout) as response:
        while chunk := response.read(chunk_size):
            yield chunk


def iter_url_tags(
    url: str, *, chunk_size: int = 64 * 1024, timeout: float | None = None
) -> Iterator[FlvTag]:
    """Yield parsed tags from one direct HTTP FLV URL without retrying."""
    yield from iter_tags(iter_url_chunks(url, chunk_size=chunk_size, timeout=timeout))


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
