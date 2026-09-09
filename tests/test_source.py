from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch
import unittest

from tikrec.flv import FlvFormatError, FlvTag
from tikrec.source import iter_tags, iter_url_chunks, iter_url_tags


def make_stream(*tags: FlvTag) -> bytes:
    header = b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00"
    return header + b"".join(tag.encoded() for tag in tags)


def split(data: bytes, sizes: list[int]) -> list[bytes]:
    chunks = []
    position = 0
    for size in sizes:
        chunks.append(data[position : position + size])
        position += size
    if position < len(data):
        chunks.append(data[position:])
    return chunks


def video(timestamp: int, payload: bytes) -> FlvTag:
    return FlvTag(9, timestamp, b"\x00\x00\x00", payload)


class TagIterationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tags = [
            video(100, b"\x17\x00config"),
            video(120, b"\x17\x01keyframe"),
            video(140, b"\x27\x01interframe"),
        ]
        self.stream = make_stream(*self.tags)

    def test_normal_stream_split_across_several_chunks(self) -> None:
        self.assertEqual(list(iter_tags(split(self.stream, [20, 17, 23]))), self.tags)

    def test_one_byte_chunks_are_parsed_incrementally(self) -> None:
        self.assertEqual(list(iter_tags([bytes([byte]) for byte in self.stream])), self.tags)

    def test_multiple_tags_in_one_chunk_are_all_yielded(self) -> None:
        self.assertEqual(list(iter_tags([self.stream])), self.tags)

    def test_split_flv_header_is_buffered(self) -> None:
        chunks = [self.stream[:4], self.stream[4:9], self.stream[9:13], self.stream[13:]]

        self.assertEqual(list(iter_tags(chunks)), self.tags)

    def test_split_tag_header_is_buffered(self) -> None:
        tag_start = 13
        chunks = [self.stream[: tag_start + 5], self.stream[tag_start + 5 :]]

        self.assertEqual(list(iter_tags(chunks)), self.tags)

    def test_split_tag_payload_is_buffered(self) -> None:
        payload_start = 13 + 11
        chunks = [self.stream[: payload_start + 3], self.stream[payload_start + 3 :]]

        self.assertEqual(list(iter_tags(chunks)), self.tags)

    def test_split_previous_tag_size_is_buffered(self) -> None:
        first_tag_end = 13 + 11 + len(self.tags[0].payload)
        chunks = [self.stream[: first_tag_end + 2], self.stream[first_tag_end + 2 :]]

        self.assertEqual(list(iter_tags(chunks)), self.tags)

    def test_clean_eof_stops_iteration(self) -> None:
        self.assertEqual(list(iter_tags([make_stream()])), [])

    def test_returns_a_lazy_iterator(self) -> None:
        iterator = iter_tags([self.stream])

        self.assertIsInstance(iterator, Iterator)
        self.assertEqual(next(iterator), self.tags[0])
        self.assertEqual(list(iterator), self.tags[1:])

    def test_truncated_tag_raises_eof_error(self) -> None:
        with self.assertRaises(EOFError):
            list(iter_tags([self.stream[:-1]]))

    def test_malformed_header_raises_format_error(self) -> None:
        with self.assertRaisesRegex(FlvFormatError, "did not return an FLV stream"):
            list(iter_tags([b"not-a-stream"]))


class UrlChunkTests(unittest.TestCase):
    def test_url_chunks_reads_a_mocked_response_without_network(self) -> None:
        response = _Response([b"first", b"second", b""])

        with patch("tikrec.source.urlopen", return_value=response) as open_url:
            self.assertEqual(list(iter_url_chunks("https://example.test/live", chunk_size=6)), [b"first", b"second"])

        open_url.assert_called_once_with("https://example.test/live", timeout=None)

    def test_url_tags_uses_the_same_parser_with_a_mocked_response(self) -> None:
        tags = [video(100, b"\x17\x01keyframe")]
        response = _Response(split(make_stream(*tags), [5, 12]))

        with patch("tikrec.source.urlopen", return_value=response):
            self.assertEqual(list(iter_url_tags("https://example.test/live")), tags)


class _Response:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = iter(chunks)

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self, _: int) -> bytes:
        return next(self._chunks, b"")


if __name__ == "__main__":
    unittest.main()
