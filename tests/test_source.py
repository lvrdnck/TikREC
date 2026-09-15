from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from threading import Event
import unittest

from tikrec.flv import FlvFormatError, FlvTag
from tikrec.capture_control import CaptureControl, CaptureStopped
from tikrec.source import (
    DEFAULT_READ_TIMEOUT, RawCopy, SourceStallError,
    iter_tags, iter_url_chunks, iter_url_tags,
)


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
    def test_stop_while_waiting_for_incomplete_tag_closes_http_response(self) -> None:
        event = Event()
        closed = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                closed.append(True)

            def read(self, count):
                event.set()
                return b"FLV"

        control = CaptureControl(event, lambda _: None)
        with patch("tikrec.source.urlopen", return_value=Response()):
            with self.assertRaises(CaptureStopped):
                list(iter_url_tags("url", check_stop=control.check))
        self.assertEqual(closed, [True])

    def test_closing_parser_generator_closes_its_http_response(self) -> None:
        closed = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                closed.append(True)

            def read(self, count):
                return make_stream(video(120, b"\x17\x01keyframe"))

        with patch("tikrec.source.urlopen", return_value=Response()):
            tags = iter_url_tags("url")
            next(tags)
            self.assertEqual(closed, [])
            tags.close()
        self.assertEqual(closed, [True])

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

        open_url.assert_called_once_with(
            "https://example.test/live", timeout=DEFAULT_READ_TIMEOUT
        )

    def test_url_chunks_turns_a_socket_read_timeout_into_a_stall(self) -> None:
        response = _StalledResponse()

        with patch("tikrec.source.urlopen", return_value=response) as open_url:
            with self.assertRaisesRegex(SourceStallError, "stalled after 2.5s"):
                list(iter_url_chunks("https://example.test/live", timeout=2.5))

        open_url.assert_called_once_with("https://example.test/live", timeout=2.5)

    def test_url_chunks_rejects_a_nonpositive_timeout(self) -> None:
        with self.assertRaisesRegex(ValueError, "timeout must be positive"):
            list(iter_url_chunks("https://example.test/live", timeout=0))

    def test_url_tags_uses_the_same_parser_with_a_mocked_response(self) -> None:
        tags = [video(100, b"\x17\x01keyframe")]
        response = _Response(split(make_stream(*tags), [5, 12]))

        with patch("tikrec.source.urlopen", return_value=response):
            self.assertEqual(list(iter_url_tags("https://example.test/live")), tags)

    def test_raw_copy_receives_exact_chunks_before_parsing(self) -> None:
        response = _Response([b"first", b"second", b""])

        with TemporaryDirectory() as directory:
            path = Path(directory) / "connection-0001.raw"
            with patch("tikrec.source.urlopen", return_value=response):
                self.assertEqual(
                    list(iter_url_chunks("https://example.test/live", raw_copy=RawCopy(path))),
                    [b"first", b"second"],
                )
            self.assertEqual(path.read_bytes(), b"firstsecond")
            records = [json.loads(line) for line in path.with_suffix(".arrivals.jsonl").read_text().splitlines()]
            self.assertEqual([record["event"] for record in records],
                             ["clock_reference", "byte_arrival", "byte_arrival", "read_end"])
            self.assertEqual([(record["offset"], record["count"]) for record in records[1:3]],
                             [(0, 5), (5, 6)])
            self.assertEqual(records[-1]["reason"], "eof")

    def test_arrival_log_open_failure_keeps_raw_copy_and_capture(self) -> None:
        response = _Response([b"first", b""])
        warnings: list[str] = []

        with TemporaryDirectory() as directory:
            path = Path(directory) / "connection-0001.raw"
            path.with_suffix(".arrivals.jsonl").write_text("existing evidence\n")
            raw_copy = RawCopy(path, warnings.append)
            with patch("tikrec.source.urlopen", return_value=response):
                self.assertEqual(list(iter_url_chunks("url", raw_copy=raw_copy)), [b"first"])
            self.assertEqual(path.read_bytes(), b"first")

        self.assertEqual(raw_copy.saved_path, path)
        self.assertIsNone(raw_copy.saved_arrivals_path)
        self.assertIn("could not open raw arrival log", warnings[0])

    def test_read1_preserves_partial_bytes_and_times_stall_or_disconnect(self) -> None:
        for failure, reason in ((TimeoutError("timed out"), "timeout"),
                                (ConnectionResetError("reset"), "error")):
            with self.subTest(reason=reason), TemporaryDirectory() as directory:
                path = Path(directory) / "connection-0007.raw"
                readings = iter((10.0, 11.0, 14.0, 20.0))
                raw_copy = RawCopy(path, connection_number=7, wall_clock=lambda: 2000.0,
                                   monotonic_clock=lambda: next(readings))
                chunks = iter_url_chunks("https://example.test/live", raw_copy=raw_copy)
                with patch("tikrec.source.urlopen", return_value=_Read1Response(failure)):
                    self.assertEqual(next(chunks), b"first")
                    self.assertEqual(next(chunks), b"tail")
                    with self.assertRaises((SourceStallError, ConnectionResetError)):
                        next(chunks)
                records = [json.loads(line) for line in raw_copy.arrivals_path.read_text().splitlines()]

                self.assertEqual(path.read_bytes(), b"firsttail")
                self.assertEqual([(item["offset"], item["count"]) for item in records[1:3]],
                                 [(0, 5), (5, 4)])
                self.assertEqual(records[0]["connection"], 7)
                self.assertEqual(records[0]["wall_time"], 2000.0)
                self.assertEqual(records[2]["elapsed_seconds"], 4.0)
                self.assertEqual(records[3]["reason"], reason)
                self.assertEqual(records[3]["elapsed_seconds"], 10.0)

    def test_raw_copy_open_failure_warns_without_stopping_the_stream(self) -> None:
        response = _Response([b"first", b""])
        warnings: list[str] = []

        with TemporaryDirectory() as directory:
            blocked = Path(directory) / "blocked"
            blocked.write_bytes(b"not a directory")
            raw_copy = RawCopy(blocked / "connection-0001.raw", warnings.append)
            with patch("tikrec.source.urlopen", return_value=response):
                self.assertEqual(list(iter_url_chunks("https://example.test/live", raw_copy=raw_copy)), [b"first"])

        self.assertIsNone(raw_copy.saved_path)
        self.assertIn("could not open raw copy", warnings[0])

    def test_raw_copy_write_failure_warns_without_stopping_the_stream(self) -> None:
        response = _Response([b"first", b"second", b""])
        warnings: list[str] = []

        with TemporaryDirectory() as directory:
            with patch("tikrec.source.Path.open", return_value=_WriteFailingHandle()):
                raw_copy = RawCopy(Path(directory) / "connection-0001.raw", warnings.append)
                with patch("tikrec.source.urlopen", return_value=response):
                    self.assertEqual(
                        list(iter_url_chunks("https://example.test/live", raw_copy=raw_copy)),
                        [b"first", b"second"],
                    )

        self.assertIsNone(raw_copy.saved_path)
        self.assertTrue(any("could not write raw copy" in message for message in warnings))


class _Response:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = iter(chunks)

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self, _: int) -> bytes:
        return next(self._chunks, b"")


class _StalledResponse(_Response):
    def __init__(self) -> None:
        super().__init__([])

    def read(self, _: int) -> bytes:
        raise TimeoutError("timed out")


class _Read1Response(_Response):
    def __init__(self, failure: Exception) -> None:
        super().__init__([])
        self._results = iter((b"first", b"tail", failure))

    def read1(self, _: int) -> bytes:
        result = next(self._results)
        if isinstance(result, Exception):
            raise result
        return result

    def read(self, _: int) -> bytes:
        raise AssertionError("read1 must avoid full-buffer response.read")


class _WriteFailingHandle:
    def write(self, _: bytes) -> None:
        raise OSError("disk full")

    def close(self) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
