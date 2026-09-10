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


def audio_configuration(timestamp: int, value: bytes = b"\x12\x10") -> FlvTag:
    return FlvTag(8, timestamp, b"\x00\x00\x00", b"\xaf\x00" + value)


def read_part(path: Path) -> list[FlvTag]:
    with path.open("rb") as handle:
        assert handle.read(13) == b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00"
        tags: list[FlvTag] = []
        while tag := read_tag(handle):
            tags.append(tag)
    return tags


class WriterTests(unittest.TestCase):
    def test_prepends_audio_configuration_seen_before_avc_configuration(self) -> None:
        tags = [
            audio_configuration(50),
            avc_configuration(100, b"first"),
            audio(110),
            video(120, frame_type=1),
            audio(125),
        ]

        with TemporaryDirectory() as directory:
            paths = write_parts(tags, Path(directory))
            written_tags = read_part(paths[0])

        self.assertEqual([tag.payload for tag in written_tags], [
            avc_configuration(0, b"first").payload,
            audio_configuration(0).payload,
            video(0, frame_type=1).payload,
            audio(0).payload,
        ])
        self.assertEqual([tag.timestamp for tag in written_tags], [0, 0, 0, 5])

    def test_prepends_audio_configuration_seen_while_waiting_for_keyframe(self) -> None:
        tags = [
            avc_configuration(100, b"first"),
            audio_configuration(110, b"\x11\x90"),
            audio(115),
            video(120, frame_type=1),
        ]

        with TemporaryDirectory() as directory:
            paths = write_parts(tags, Path(directory))
            written_tags = read_part(paths[0])

        self.assertEqual([tag.payload for tag in written_tags], [
            avc_configuration(0, b"first").payload,
            audio_configuration(0, b"\x11\x90").payload,
            video(0, frame_type=1).payload,
        ])

    def test_writes_later_audio_configuration_at_its_stream_position(self) -> None:
        tags = [
            avc_configuration(100, b"first"),
            video(120, frame_type=1),
            audio_configuration(130, b"\x11\x90"),
            audio(135),
        ]

        with TemporaryDirectory() as directory:
            paths = write_parts(tags, Path(directory))
            written_tags = read_part(paths[0])

        self.assertEqual([tag.timestamp for tag in written_tags], [0, 0, 10, 15])
        self.assertEqual(written_tags[2].payload, audio_configuration(0, b"\x11\x90").payload)

    def test_stream_without_audio_configuration_still_writes_video(self) -> None:
        tags = [avc_configuration(100, b"first"), video(120, frame_type=1)]

        with TemporaryDirectory() as directory:
            paths = write_parts(tags, Path(directory))
            written_tags = read_part(paths[0])

        self.assertEqual([tag.payload for tag in written_tags], [
            avc_configuration(0, b"first").payload,
            video(0, frame_type=1).payload,
        ])

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
            timings = []
            paths = write_parts(iter(tags), Path(directory), on_part_closed=timings.append)
            parts = [read_part(path) for path in paths]

        self.assertEqual([path.name for path in paths], ["part-0001.flv", "part-0002.flv"])
        self.assertEqual(
            [[tag.timestamp for tag in part] for part in parts],
            [[0, 0, 10], [0, 0, 15]],
        )
        self.assertEqual(parts[0][0].payload[-5:], b"first")
        self.assertEqual(parts[1][0].payload[-6:], b"second")
        self.assertEqual(
            [(timing.configuration_timestamp, timing.first_media_timestamp, timing.first_keyframe_timestamp,
              timing.last_tag_timestamp, timing.keyframe_gate_duration) for timing in timings],
            [(100, 120, 120, 130, 0), (1000, 1025, 1025, 1040, 0)],
        )

    def test_measures_the_gate_from_media_not_a_zero_timestamp_configuration(self) -> None:
        tags = [
            avc_configuration(0, b"first"),
            video(3_427_480, frame_type=2),
            video(3_427_493, frame_type=1),
        ]

        with TemporaryDirectory() as directory:
            timings = []
            write_parts(tags, Path(directory), on_part_closed=timings.append)

        self.assertEqual(timings[0].configuration_timestamp, 0)
        self.assertEqual(timings[0].first_media_timestamp, 3_427_480)
        self.assertEqual(timings[0].first_keyframe_timestamp, 3_427_493)
        self.assertEqual(timings[0].keyframe_gate_duration, 13)

    def test_records_a_timestamp_replay_without_discarding_tags(self) -> None:
        tags = [
            avc_configuration(100, b"first"),
            video(120, frame_type=1),
            video(130, frame_type=2),
            FlvTag(18, 0, b"\x00\x00\x00", b"script"),
            video(110, frame_type=2),
            video(120, frame_type=2),
            video(131, frame_type=2),
        ]
        timings = []
        replays = []

        with TemporaryDirectory() as directory:
            paths = write_parts(
                tags,
                Path(directory),
                on_part_closed=timings.append,
                on_timestamp_replay=replays.append,
            )
            written_tags = read_part(paths[0])

        self.assertEqual([tag.payload for tag in written_tags][-4:], [
            b"script",
            video(0, frame_type=2).payload,
            video(0, frame_type=2).payload,
            video(0, frame_type=2).payload,
        ])
        self.assertEqual(len(replays), 1)
        self.assertEqual(replays[0].position, 4)
        self.assertEqual(replays[0].magnitude, 130)
        self.assertEqual(replays[0].replayed_tag_count, 3)
        self.assertTrue(replays[0].recovered)
        self.assertEqual(timings[0].timestamp_replays, tuple(replays))

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

    def test_uses_explicit_start_index_for_part_names(self) -> None:
        tags = [avc_configuration(100, b"first"), video(120, frame_type=1)]

        with TemporaryDirectory() as directory:
            paths = write_parts(tags, Path(directory), start_index=7)

        self.assertEqual([path.name for path in paths], ["part-0007.flv"])

    def test_reports_a_part_start_only_after_its_first_keyframe(self) -> None:
        tags = [
            avc_configuration(100, b"first"),
            video(110, frame_type=2),
            video(120, frame_type=1),
        ]
        started: list[Path] = []

        with TemporaryDirectory() as directory:
            paths = write_parts(tags, Path(directory), on_part_started=started.append)

        self.assertEqual(started, list(paths))

    def test_reports_written_bytes_for_an_active_part(self) -> None:
        reported: list[tuple[Path, int]] = []
        tags = [
            avc_configuration(100, b"first"),
            video(120, frame_type=1),
            video(130, frame_type=2),
        ]

        with TemporaryDirectory() as directory:
            paths = write_parts(
                tags, Path(directory), on_progress=lambda path, size: reported.append((path, size)),
            )

        self.assertEqual([path for path, _ in reported], [paths[0], paths[0]])
        self.assertGreater(reported[0][1], 13)
        self.assertLess(reported[0][1], reported[1][1])


if __name__ == "__main__":
    unittest.main()
