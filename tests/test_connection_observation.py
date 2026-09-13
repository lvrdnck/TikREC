"""Offline connection milestones and writer evidence integration."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tikrec.connection_observation import ConnectionObservation
from tikrec.capture import capture_url
from tikrec.flv import FlvTag
from tikrec.live import capture_live
from tikrec.tiktok import TikTokOfflineError, _ResolvedLiveUrl
from tikrec.writer import write_parts
from tests.test_flv import make_avc_configuration, make_sps
from tests.test_flv_metadata import metadata
from tests.test_writer import audio, avc_configuration, video


class ObservationTests(unittest.TestCase):
    def test_plain_resolver_and_media_free_stream_leave_unknowns(self):
        observer = ConnectionObservation(lambda: 1.0)
        observer.resolved("https://cdn.test/live.flv")
        self.assertIsNone(observer.rendition_label)
        tags = [avc_configuration(0, b"config")]
        self.assertEqual(list(observer.tags(tags)), tags)
        self.assertIsNone(observer.first_media_tag_at)
        self.assertIsNone(observer.first_retained_media_at)

    def test_stall_records_distinct_setup_gate_and_tail_milestones(self):
        now = [0.0]
        config = make_avc_configuration(make_sps(720, 1280))
        chunks = iter([
            (3.5, b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00"),
            (4.0, FlvTag(18, 0, b"\0\0\0", metadata(15)).encoded()),
            (4.5, avc_configuration(0, config).encoded()),
            (5.0, video(100, 2).encoded()),
            (7.0, video(120, 1).encoded()),
            (8.0, audio(140).encoded()),
            (9.0, avc_configuration(150, config).encoded()),
        ])

        class Response:
            def __enter__(self):
                now[0] = 3.0
                return self

            def __exit__(self, *args):
                pass

            def read(self, size):
                item = next(chunks, None)
                if item is None:
                    now[0] = 38.0
                    raise TimeoutError("silent socket")
                now[0], data = item
                return data

        resolves = [0]

        def resolver(url):
            resolves[0] += 1
            if resolves[0] == 1:
                now[0] = 2.0
                return _ResolvedLiveUrl("https://cdn.test/live.flv?secret=x", 2,
                                        "hd1", "flv_pull_url")
            now[0] = 40.0
            raise TikTokOfflineError("offline", 4)

        with TemporaryDirectory() as directory, patch("tikrec.source.urlopen", return_value=Response()):
            root = Path(directory)
            result = capture_live("https://www.tiktok.com/@creator/live", parts_directory=root / "parts",
                                  resolver=resolver, clock=lambda: now[0],
                                  observation_clock=lambda: now[0], sleeper=lambda _: None,
                                  offline_confirmation_checks=1, raw_copy_dir=root / "raw")
            records = [json.loads(line) for line in (root / "parts/connections.jsonl").read_text().splitlines()]
            records = [r for r in records if "connection" in r]
        record = records[0]
        self.assertEqual(record["outcome"], "stalled")
        self.assertEqual([record[key] for key in ("resolved_at", "http_opened_at", "first_media_tag_at",
                                                  "first_retained_media_at", "last_retained_media_at")],
                         [2.0, 3.0, 5.0, 7.0, 8.0])
        self.assertEqual(record["ended_at"] - record["last_retained_media_at"], 30.0)
        self.assertEqual((record["rendition_label"], record["rendition_source"]), ("hd1", "flv_pull_url"))
        self.assertNotIn("secret", json.dumps(record))
        self.assertEqual((record["part_timings"][0]["width"], record["part_timings"][0]["height"]),
                         (720, 1280))
        self.assertEqual(record["part_timings"][0]["nominal_frame_rate"], "15/1")
        self.assertEqual(record["part_timings"][0]["nominal_frame_rate_source"], "onMetaData")
        self.assertIsNone(records[1]["first_retained_media_at"])
        self.assertIsNone(records[1]["rendition_label"])
        self.assertEqual(result.connections[0].last_retained_media_at, 8.0)

    def test_writer_observes_only_written_media_including_replays(self):
        retained = []
        tags = [audio(0), avc_configuration(0, b"config"), video(10, 2),
                video(20, 1), audio(30), video(5, 2), avc_configuration(40, b"config")]
        with TemporaryDirectory() as directory:
            observed = write_parts(tags, Path(directory) / "observed", on_media_retained=lambda: retained.append(True))
            plain = write_parts(tags, Path(directory) / "plain")
            self.assertEqual(observed[0].read_bytes(), plain[0].read_bytes())
        self.assertEqual(len(retained), 3)

    def test_interrupted_part_preserves_timing_and_metadata(self):
        timings = []
        observer = ConnectionObservation(lambda: 123.0)

        def tags():
            yield FlvTag(18, 0, b"\0\0\0", metadata(25))
            yield avc_configuration(0, make_avc_configuration(make_sps(640, 1280)))
            yield video(100, 1)
            raise KeyboardInterrupt

        with TemporaryDirectory() as directory:
            with self.assertRaises(KeyboardInterrupt):
                write_parts(observer.tags(tags()), Path(directory), on_media_retained=observer.retained,
                            on_part_closed=timings.append)
        self.assertEqual(observer.first_retained_media_at, 123.0)
        self.assertEqual((timings[0].width, timings[0].height, timings[0].nominal_frame_rate),
                         (640, 1280, "25/1"))

    def test_gated_empty_connection_has_no_retained_media_times(self):
        observer = ConnectionObservation(lambda: 5.0)
        with TemporaryDirectory() as directory:
            parts = write_parts(observer.tags([avc_configuration(0, b"config"), video(100, 2)]),
                                Path(directory), on_media_retained=observer.retained)
        self.assertEqual(parts, ())
        self.assertEqual(observer.first_media_tag_at, 5.0)
        self.assertIsNone(observer.first_retained_media_at)
        self.assertIsNone(observer.last_retained_media_at)

    def test_each_rolled_part_uses_its_own_config_and_metadata_rate(self):
        timings = []
        tags = [FlvTag(18, 0, b"\0\0\0", metadata(15)),
                avc_configuration(0, make_avc_configuration(make_sps(720, 1280))), video(100, 1),
                avc_configuration(200, make_avc_configuration(make_sps(640, 1280))),
                FlvTag(18, 200, b"\0\0\0", metadata(25)), video(220, 1)]
        with TemporaryDirectory() as directory:
            write_parts(tags, Path(directory), on_part_closed=timings.append)
        self.assertEqual([(t.width, t.height, t.nominal_frame_rate) for t in timings],
                         [(720, 1280, "15/1"), (640, 1280, "25/1")])

    def test_direct_raw_capture_also_records_observations(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)

            def tags(url, raw):
                raw.write(b"raw evidence")
                yield avc_configuration(0, b"config")
                yield video(100, 1)

            capture_url("https://cdn.test/live.flv", parts_directory=root / "parts",
                        raw_copy_dir=root / "raw", raw_tag_source=tags, observation_clock=lambda: 7.0)
            record = json.loads((root / "parts/connections.jsonl").read_text())
        self.assertEqual(record["first_retained_media_at"], 7.0)
        self.assertIsNone(record["http_opened_at"])
        self.assertIsNone(record["rendition_source"])

    def test_announced_next_rate_does_not_relabel_previous_part(self):
        timings = []
        tags = [FlvTag(18, 0, b"\0\0\0", metadata(15)),
                avc_configuration(0, make_avc_configuration(make_sps(720, 1280))), video(100, 1),
                FlvTag(18, 200, b"\0\0\0", metadata(25)),
                avc_configuration(200, make_avc_configuration(make_sps(640, 1280))), video(220, 1)]
        with TemporaryDirectory() as directory:
            write_parts(tags, Path(directory), on_part_closed=timings.append)
        self.assertEqual([t.nominal_frame_rate for t in timings], ["15/1", "25/1"])


if __name__ == "__main__":
    unittest.main()
