from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tikrec.flv import FlvTag, read_tag
from tikrec.writer import write_parts


def avc_configuration(timestamp: int, value: bytes) -> FlvTag:
    return FlvTag(9, timestamp, b"\x00\x00\x00", b"\x17\x00\x00\x00\x00" + value)


def video(timestamp: int, frame_type: int) -> FlvTag:
    payload = bytes([frame_type << 4 | 7, 1, 0, 0, 0]) + b"video"
    return FlvTag(9, timestamp, b"\x00\x00\x00", payload)


def audio(timestamp: int) -> FlvTag:
    return FlvTag(8, timestamp, b"\x00\x00\x00", b"\xaf\x01audio")


def read_part(path: Path) -> list[FlvTag]:
    with path.open("rb") as handle:
        assert handle.read(13) == b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00"
        tags: list[FlvTag] = []
        while tag := read_tag(handle):
            tags.append(tag)
    return tags


class WriterTests(unittest.TestCase):
    def test_waits_for_keyframe_and_rebases_the_retained_tags(self) -> None:
        tags = [
            avc_configuration(1000, b"first"),
            audio(1005),
            video(1010, frame_type=2),
            video(1020, frame_type=1),
            audio(1025),
            video(1030, frame_type=2),
        ]

        with TemporaryDirectory() as directory:
            paths = write_parts(tags, Path(directory))
            written_tags = read_part(paths[0])

        self.assertEqual([path.name for path in paths], ["part-0001.flv"])
        self.assertEqual([tag.timestamp for tag in written_tags], [0, 0, 5, 10])
        self.assertEqual([tag.payload for tag in written_tags], [
            avc_configuration(0, b"first").payload,
            video(0, frame_type=1).payload,
            audio(0).payload,
            video(0, frame_type=2).payload,
        ])

    def test_configuration_change_creates_two_rebased_parts(self) -> None:
        tags = [
            avc_configuration(100, b"first"),
            video(120, frame_type=1),
            audio(130),
            avc_configuration(1000, b"second"),
            video(1025, frame_type=1),
            video(1040, frame_type=2),
        ]

        with TemporaryDirectory() as directory:
            paths = write_parts(iter(tags), Path(directory))
            parts = [read_part(path) for path in paths]

        self.assertEqual([path.name for path in paths], ["part-0001.flv", "part-0002.flv"])
        self.assertEqual(
            [[tag.timestamp for tag in part] for part in parts],
            [[0, 0, 10], [0, 0, 15]],
        )
        self.assertEqual(parts[0][0].payload[-5:], b"first")
        self.assertEqual(parts[1][0].payload[-6:], b"second")

    def test_deletes_part_when_no_keyframe_produced_media(self) -> None:
        tags = [
            avc_configuration(100, b"first"),
            audio(105),
            video(110, frame_type=2),
        ]

        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            paths = write_parts(tags, output_dir)

            self.assertEqual(paths, ())
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_reuses_index_after_deleting_a_pre_keyframe_part(self) -> None:
        tags = [
            avc_configuration(100, b"first"),
            video(110, frame_type=2),
            avc_configuration(200, b"second"),
            video(220, frame_type=1),
        ]

        with TemporaryDirectory() as directory:
            paths = write_parts(tags, Path(directory))
            written_tags = read_part(paths[0])

        self.assertEqual([path.name for path in paths], ["part-0001.flv"])
        self.assertEqual(written_tags[0].payload[-6:], b"second")

    def test_promotes_the_hidden_partial_file_only_after_clean_close(self) -> None:
        tags = [avc_configuration(100, b"first"), video(120, frame_type=1)]

        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            paths = write_parts(tags, output_dir)

            self.assertTrue(paths[0].is_file())
            self.assertEqual(list(output_dir.glob(".*.partial")), [])


if __name__ == "__main__":
    unittest.main()
