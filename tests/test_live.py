from __future__ import annotations

import json
from http.client import IncompleteRead
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tikrec.capture import CaptureError, CaptureResult
from tikrec.cli import main
from tikrec.flv import FlvFormatError, FlvTag
from tikrec.live import capture_live
from tikrec.source import SourceStallError
from tikrec.tiktok import (
    TikTokOfflineError,
    TikTokResolutionError,
    TikTokResolutionTransientError,
)


def stream() -> list[FlvTag]:
    return [
        FlvTag(9, 100, b"\x00\x00\x00", b"\x17\x00\x00\x00\x00config"),
        FlvTag(9, 120, b"\x00\x00\x00", b"\x17\x01\x00\x00\x00key"),
    ]


class LiveCaptureTests(unittest.TestCase):
    def test_mixed_case_public_page_persists_canonical_creator(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            actions = iter(("https://cdn.test/live.flv", TikTokOfflineError("offline")))
            def resolver(_):
                item = next(actions)
                if isinstance(item, Exception):
                    raise item
                return item
            capture_live("https://www.tiktok.com/@Alpha/live?share=1",
                         parts_directory=root / "alpha.parts", output_path=root / "alpha.mp4",
                         resolver=resolver, tag_source=lambda _: iter(stream()),
                         finalizer=_finalizer, sleeper=lambda _: None,
                         offline_confirmation_checks=1)
            values = json.loads((root / "alpha.parts/session.json").read_text())
            self.assertEqual(values["creator"], "alpha")
            self.assertNotIn("share", str(values))

    def test_reports_the_live_lifecycle_without_a_signed_cdn_url(self) -> None:
        actions: list[object] = [
            "https://cdn.test/live.flv?token=secret",
            TikTokOfflineError("offline"),
        ]
        progress: list[str] = []

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "final.mp4"
            capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                output_path=output,
                resolver=resolver,
                tag_source=lambda _: iter(stream()),
                finalizer=_finalizer,
                sleeper=lambda _: None,
                progress=progress.append,
                offline_confirmation_checks=1,
            )

        self.assertEqual(progress, [
            "resolving room",
            "connection 1 opened",
            "part started: part-0001.flv",
            "connection lost: connection closed; reconnecting in 0s",
            "resolving room",
            "room ended",
            "capture ended; finalizing 1 retained part(s)",
            f"output written: {output} (5 bytes)",
        ])
        self.assertNotIn("token=secret", "\n".join(progress))

    def test_reports_active_part_bytes_to_the_heartbeat(self) -> None:
        actions: list[object] = [
            "https://cdn.test/live.flv",
            TikTokOfflineError("offline"),
        ]
        heartbeat: list[tuple[Path, int]] = []

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=Path(directory) / "parts",
                resolver=resolver,
                tag_source=lambda _: iter(stream()),
                sleeper=lambda _: None,
                heartbeat=lambda path, size: heartbeat.append((path, size)),
                offline_confirmation_checks=1,
            )

        self.assertEqual([path.name for path, _ in heartbeat], ["part-0001.flv"])
        self.assertGreater(heartbeat[0][1], 13)
        self.assertEqual(len(result.parts), 1)

    def test_warns_for_media_replay_but_ignores_zero_timestamp_script_tag(self) -> None:
        tags = [
            FlvTag(9, 100, b"\x00\x00\x00", b"\x17\x00\x00\x00\x00config"),
            FlvTag(9, 120, b"\x00\x00\x00", b"\x17\x01\x00\x00\x00key"),
            FlvTag(9, 130, b"\x00\x00\x00", b"\x27\x01\x00\x00\x00frame"),
            FlvTag(18, 0, b"\x00\x00\x00", b"script"),
            FlvTag(9, 110, b"\x00\x00\x00", b"\x27\x01\x00\x00\x00replay"),
            FlvTag(9, 131, b"\x00\x00\x00", b"\x27\x01\x00\x00\x00recovered"),
        ]
        progress: list[str] = []
        actions: list[object] = ["https://cdn.test/live.flv", TikTokOfflineError("offline")]

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                resolver=resolver,
                tag_source=lambda _: iter(tags),
                progress=progress.append,
                sleeper=lambda _: None,
                offline_confirmation_checks=1,
            )
            record = json.loads((root / "parts" / "connections.jsonl").read_text().splitlines()[0])

        self.assertEqual(len(record["part_timings"][0]["timestamp_replays"]), 1)
        self.assertIn(
            "warning: timestamp replay detected; part-0001.flv tag 5 jumped back "
            "20ms; 1 tags replayed before recovery; this part may not validate",
            progress,
        )

    def test_live_raw_copy_maps_each_connection_to_its_manifest_record(self) -> None:
        actions: list[object] = ["https://cdn.test/live.flv", TikTokOfflineError("offline")]

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        def raw_source(_: str, raw_copy) -> object:
            raw_copy.write(b"unmodified connection bytes")
            return iter(stream())

        with TemporaryDirectory() as directory:
            root = Path(directory)
            capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                resolver=resolver,
                raw_copy_dir=root / "raw",
                raw_tag_source=raw_source,
                sleeper=lambda _: None,
                offline_confirmation_checks=1,
            )
            records = [
                json.loads(line)
                for line in (root / "parts" / "connections.jsonl").read_text().splitlines()
                if "\"connection\"" in line
            ]

            self.assertEqual((root / "raw" / "connection-0001.raw").read_bytes(), b"unmodified connection bytes")
            arrival = json.loads((root / "raw" / "connection-0001.arrivals.jsonl").read_text().splitlines()[1])
            self.assertEqual((arrival["connection"], arrival["count"]), (1, 27))

        self.assertEqual(records[0]["raw_copy"], "connection-0001.raw")
        self.assertEqual(records[0]["raw_arrivals"], "connection-0001.arrivals.jsonl")
        self.assertIsNone(records[1]["raw_copy"])
        self.assertIsNone(records[1]["raw_arrivals"])

    def test_redacts_a_signed_url_from_a_connection_loss_reason(self) -> None:
        progress: list[str] = []

        def failing_stream():
            raise OSError("read failed: https://cdn.test/live.flv?token=secret")
            yield

        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CaptureError, "consecutive connection failures"):
                capture_live(
                    "https://www.tiktok.com/@creator/live",
                    parts_directory=Path(directory) / "parts",
                    resolver=lambda _: "https://cdn.test/live.flv?token=secret",
                    tag_source=lambda _: failing_stream(),
                    max_consecutive_failures=2,
                    progress=progress.append,
                    sleeper=lambda _: None,
                )

        self.assertIn("[URL redacted]", "\n".join(progress))
        self.assertNotIn("token=secret", "\n".join(progress))
    def test_reconnects_into_new_parts_and_appends_records_as_connections_close(self) -> None:
        actions: list[object] = ["https://cdn.test/one.flv", "https://cdn.test/two.flv", TikTokOfflineError("offline")]
        sleeps: list[tuple[float, int]] = []

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "parts" / "connections.jsonl"

            def sleeper(delay: float) -> None:
                sleeps.append((delay, len(log_path.read_text().splitlines())))

            times = iter((100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0))
            output = root / "final.mp4"
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                output_path=output,
                resolver=resolver,
                tag_source=lambda _: iter(stream()),
                finalizer=_finalizer,
                sleeper=sleeper,
                clock=lambda: next(times),
                offline_confirmation_checks=1,
            )
            records = [
                json.loads(line)
                for line in log_path.read_text().splitlines()
                if "\"connection\"" in line
            ]
            manifest = json.loads((root / "parts" / "session.json").read_text())

        self.assertEqual([part.name for part in result.parts], ["part-0001.flv", "part-0002.flv"])
        self.assertEqual(result.output_path, output)
        self.assertEqual(sleeps, [(0.0, 1), (0.0, 2)])
        self.assertEqual([record["outcome"] for record in records], ["closed", "closed", "offline"])
        self.assertEqual(records[0]["part_start"], "part-0001.flv")
        self.assertEqual(records[1]["part_end"], "part-0002.flv")
        self.assertEqual(records[0]["part_timings"], [{
            "name": "part-0001.flv",
            "configuration_timestamp": 100,
            "first_media_timestamp": 120,
            "first_keyframe_timestamp": 120,
            "keyframe_gate_duration": 0,
            "last_tag_timestamp": 120,
            "timestamp_replays": [], "width": None, "height": None, "nominal_frame_rate": None, "nominal_frame_rate_source": None,
        }])
        self.assertEqual(result.connections[0].part_timings[0].keyframe_gate_duration, 0)
        self.assertEqual(result.connections[1].gap_before, 10.0)
        self.assertEqual(manifest["source_type"], "tiktok_live")
        self.assertEqual(manifest["part_count"], 2)
        self.assertEqual(manifest["connection_count"], 3)
        self.assertEqual(manifest["reconnect_count"], 2)
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["finalization"]["status"], "completed")

    def test_retries_transient_resolver_failure_with_backoff(self) -> None:
        actions: list[object] = [TikTokResolutionTransientError("timeout"), "https://cdn.test/live.flv", TikTokOfflineError("offline")]
        delays: list[float] = []

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                resolver=resolver,
                tag_source=lambda _: iter(stream()),
                sleeper=delays.append,
                offline_confirmation_checks=1,
            )

        self.assertEqual(len(result.parts), 1)
        # The transient attempt keeps its wait; only the later healthy close is immediate.
        self.assertEqual(delays, [1.0, 0.0])
        self.assertEqual(result.connections[0].outcome, "resolver_error")

    def test_initial_offline_room_leaves_no_directory_and_same_path_can_retry(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts_directory = root / "parts"
            with self.assertRaisesRegex(CaptureError, "not live"):
                capture_live(
                    "https://www.tiktok.com/@creator/live",
                    parts_directory=parts_directory,
                    resolver=lambda _: (_ for _ in ()).throw(TikTokOfflineError("offline", 4)),
                )

            self.assertFalse(parts_directory.exists())
            actions: list[object] = [
                "https://cdn.test/live.flv",
                TikTokOfflineError("offline", 4),
            ]

            def resolver(_: str) -> str:
                action = actions.pop(0)
                if isinstance(action, Exception):
                    raise action
                return str(action)

            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=parts_directory,
                resolver=resolver,
                tag_source=lambda _: iter(stream()),
                sleeper=lambda _: None,
                offline_confirmation_checks=1,
            )

        self.assertEqual([part.name for part in result.parts], ["part-0001.flv"])

    def test_initial_transient_failures_leave_no_session_directory(self) -> None:
        with TemporaryDirectory() as directory:
            parts_directory = Path(directory) / "parts"
            with self.assertRaisesRegex(CaptureError, "consecutive connection failures"):
                capture_live(
                    "https://www.tiktok.com/@creator/live",
                    parts_directory=parts_directory,
                    resolver=lambda _: (_ for _ in ()).throw(
                        TikTokResolutionTransientError("temporary failure")
                    ),
                    max_consecutive_failures=2,
                    sleeper=lambda _: None,
                )

            self.assertFalse(parts_directory.exists())

    def test_initial_permanent_resolution_error_leaves_no_session_directory(self) -> None:
        with TemporaryDirectory() as directory:
            parts_directory = Path(directory) / "parts"
            with self.assertRaisesRegex(CaptureError, "resolution failed"):
                capture_live(
                    "invalid live URL",
                    parts_directory=parts_directory,
                    resolver=lambda _: (_ for _ in ()).throw(
                        TikTokResolutionError("unsupported URL")
                    ),
                )

            self.assertFalse(parts_directory.exists())

    def test_existing_session_with_retained_parts_is_still_refused(self) -> None:
        with TemporaryDirectory() as directory:
            parts_directory = Path(directory) / "parts"
            parts_directory.mkdir()
            (parts_directory / "part-0001.flv").write_bytes(b"retained")

            with self.assertRaisesRegex(FileExistsError, "refusing to reuse"):
                capture_live(
                    "https://www.tiktok.com/@creator/live",
                    parts_directory=parts_directory,
                    resolver=lambda _: "https://cdn.test/live.flv",
                    tag_source=lambda _: iter(stream()),
                )

            self.assertEqual((parts_directory / "part-0001.flv").read_bytes(), b"retained")

    def test_confirms_three_non_live_responses_over_ten_seconds_by_default(self) -> None:
        actions: list[object] = [
            "https://cdn.test/live.flv",
            TikTokOfflineError("offline", 4),
            TikTokOfflineError("offline", "4"),
            TikTokOfflineError("offline", 3),
        ]
        delays: list[float] = []

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                resolver=resolver,
                tag_source=lambda _: iter(stream()),
                sleeper=delays.append,
                clock=lambda: 123.0,
            )
            records = [
                json.loads(line)
                for line in (root / "parts" / "connections.jsonl").read_text().splitlines()
            ]

        statuses = [record for record in records if record.get("event") == "room_status"]
        self.assertEqual(delays, [0.0, 5.0, 5.0])
        self.assertEqual([record["timestamp"] for record in statuses], [123.0] * 3)
        self.assertEqual([record["status"] for record in statuses], [4, "4", 3])
        self.assertEqual(
            [record["confirmation_reached"] for record in statuses],
            [False, False, True],
        )

    def test_live_response_during_confirmation_is_logged_and_capture_resumes(self) -> None:
        actions: list[object] = [
            "https://cdn.test/one.flv",
            TikTokOfflineError("offline", 4),
            "https://cdn.test/two.flv",
            TikTokOfflineError("offline", 4),
            TikTokOfflineError("offline", 4),
        ]
        delays: list[float] = []

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                resolver=resolver,
                tag_source=lambda _: iter(stream()),
                sleeper=delays.append,
                offline_confirmation_checks=2,
                offline_confirmation_interval=2.5,
            )
            records = [
                json.loads(line)
                for line in (root / "parts" / "connections.jsonl").read_text().splitlines()
            ]

        statuses = [record for record in records if record.get("event") == "room_status"]
        self.assertEqual([part.name for part in result.parts], ["part-0001.flv", "part-0002.flv"])
        self.assertEqual(delays, [0.0, 2.5, 0.0, 2.5])
        self.assertEqual([record["status"] for record in statuses], [4, 2, 4, 4])
        self.assertEqual(
            [record["confirmation_reached"] for record in statuses],
            [False, False, False, True],
        )

    def test_stops_after_the_injectable_failure_limit(self) -> None:
        calls = 0

        def resolver(_: str) -> str:
            nonlocal calls
            calls += 1
            raise TikTokResolutionTransientError("temporary failure")

        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CaptureError, "consecutive connection failures"):
                capture_live(
                    "https://www.tiktok.com/@creator/live",
                    parts_directory=Path(directory) / "parts",
                    resolver=resolver,
                    max_consecutive_failures=2,
                    sleeper=lambda _: None,
                )

        self.assertEqual(calls, 2)

    def test_retained_media_resets_failure_and_empty_connection_streaks(self) -> None:
        resolve_count = 0
        source_count = 0
        no_media = [
            FlvTag(9, 100, b"\x00\x00\x00", b"\x17\x00\x00\x00\x00config"),
            FlvTag(9, 110, b"\x00\x00\x00", b"\x27\x01\x00\x00\x00inter"),
        ]

        def resolver(_: str) -> str:
            nonlocal resolve_count
            resolve_count += 1
            if resolve_count == 7:
                raise TikTokOfflineError("offline")
            return f"https://cdn.test/{resolve_count}.flv"

        def failed_stream():
            raise OSError("transient read failure")
            yield

        def media_then_failure():
            yield from stream()
            raise IncompleteRead(b"partial FLV response", 59_998)

        def source(_: str):
            nonlocal source_count
            source_count += 1
            if source_count in (2, 3, 5):
                return failed_stream()
            if source_count == 4:
                return media_then_failure()
            return iter(no_media)

        with TemporaryDirectory() as directory:
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=Path(directory) / "parts",
                resolver=resolver,
                tag_source=source,
                max_consecutive_failures=3,
                max_consecutive_empty_connections=2,
                sleeper=lambda _: None,
                offline_confirmation_checks=1,
            )

        self.assertEqual(source_count, 6)
        self.assertEqual([part.name for part in result.parts], ["part-0001.flv"])
        self.assertEqual(
            [record.outcome for record in result.connections],
            ["closed", "connection_error", "connection_error", "connection_error",
             "connection_error", "closed", "offline"],
        )
        self.assertEqual(
            [part.name for part in result.connections[3].parts], ["part-0001.flv"])

    def test_stops_after_connections_that_retain_no_media(self) -> None:
        actions: list[object] = ["https://cdn.test/one.flv", "https://cdn.test/two.flv"]
        no_keyframe = [
            FlvTag(9, 100, b"\x00\x00\x00", b"\x17\x00\x00\x00\x00config"),
            FlvTag(9, 110, b"\x00\x00\x00", b"\x27\x01\x00\x00\x00inter"),
        ]

        def resolver(_: str) -> str:
            return str(actions.pop(0))

        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CaptureError, "no media"):
                capture_live(
                    "https://www.tiktok.com/@creator/live",
                    parts_directory=Path(directory) / "parts",
                    resolver=resolver,
                    tag_source=lambda _: iter(no_keyframe),
                    max_consecutive_empty_connections=2,
                    sleeper=lambda _: None,
                )

    def test_retries_incomplete_http_read_and_keeps_its_completed_part(self) -> None:
        actions: list[object] = [
            "https://cdn.test/one.flv",
            "https://cdn.test/two.flv",
            TikTokOfflineError("offline"),
        ]
        finalizer_parts: list[tuple[Path, ...]] = []
        delays: list[float] = []

        def incomplete_stream():
            yield from stream()
            raise IncompleteRead(b"partial FLV response", 51_069)

        def finalizer(parts, output: Path) -> Path:
            finalizer_parts.append(tuple(parts))
            output.write_bytes(b"final")
            return output

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                output_path=root / "final.mp4",
                resolver=resolver,
                tag_source=lambda url: incomplete_stream() if url.endswith("one.flv") else iter(stream()),
                finalizer=finalizer,
                sleeper=delays.append,
                offline_confirmation_checks=1,
            )

        self.assertEqual([part.name for part in result.parts], ["part-0001.flv", "part-0002.flv"])
        self.assertEqual([part.name for part in finalizer_parts[0]], ["part-0001.flv", "part-0002.flv"])
        self.assertEqual(result.connections[0].outcome, "connection_error")
        self.assertEqual(delays, [1.0, 0.0])

    def test_retries_a_stalled_read_and_records_a_distinct_outcome(self) -> None:
        actions: list[object] = [
            "https://cdn.test/one.flv",
            "https://cdn.test/two.flv",
            TikTokOfflineError("offline"),
        ]

        def stalled_stream():
            yield from stream()
            raise SourceStallError("source connection stalled after 30s without data")

        def resolver(_: str) -> str:
            action = actions.pop(0)
            if isinstance(action, Exception):
                raise action
            return str(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                resolver=resolver,
                tag_source=lambda url: stalled_stream() if url.endswith("one.flv") else iter(stream()),
                sleeper=lambda _: None,
                offline_confirmation_checks=1,
            )
            records = [
                json.loads(line)
                for line in (root / "parts" / "connections.jsonl").read_text().splitlines()
                if "connection" in json.loads(line)
            ]

        self.assertEqual(result.connections[0].outcome, "stalled")
        self.assertIn("stalled after 30s", result.connections[0].error or "")
        self.assertEqual(records[0]["outcome"], "stalled")
        self.assertEqual([part.name for part in result.parts], [
            "part-0001.flv", "part-0002.flv",
        ])

    def test_keyboard_interrupt_finalizes_retained_parts_and_stays_interrupted(self) -> None:
        finalizer_calls: list[tuple[Path, ...]] = []
        progress: list[str] = []

        def interrupted_stream():
            yield from stream()
            raise KeyboardInterrupt

        def finalizer(parts, output: Path) -> Path:
            finalizer_calls.append(tuple(parts))
            output.write_bytes(b"final")
            return output

        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "final.mp4"
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                output_path=output,
                resolver=lambda _: "https://cdn.test/live.flv",
                tag_source=lambda _: interrupted_stream(),
                finalizer=finalizer,
                progress=progress.append,
            )
            record = json.loads((root / "parts" / "connections.jsonl").read_text())

        self.assertTrue(result.interrupted)
        self.assertEqual([part.name for part in result.parts], ["part-0001.flv"])
        self.assertEqual(record["outcome"], "interrupted")
        self.assertEqual(result.output_path, output)
        self.assertEqual([part.name for part in finalizer_calls[0]], ["part-0001.flv"])
        self.assertIn(
            "capture stopped by interrupt; finalizing 1 retained part(s)", progress
        )

    def test_second_keyboard_interrupt_abandons_finalization_but_keeps_parts(self) -> None:
        def interrupted_stream():
            yield from stream()
            raise KeyboardInterrupt

        def interrupted_finalizer(*_: object) -> Path:
            raise KeyboardInterrupt

        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture_live(
                "https://www.tiktok.com/@creator/live",
                parts_directory=root / "parts",
                output_path=root / "final.mp4",
                resolver=lambda _: "https://cdn.test/live.flv",
                tag_source=lambda _: interrupted_stream(),
                finalizer=interrupted_finalizer,
            )

        self.assertTrue(result.interrupted)
        self.assertIsNone(result.output_path)
        self.assertEqual([part.name for part in result.parts], ["part-0001.flv"])

    def test_malformed_flv_is_not_retried(self) -> None:
        calls = 0

        def resolver(_: str) -> str:
            nonlocal calls
            calls += 1
            return "https://cdn.test/live.flv"

        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(CaptureError, "malformed"):
                capture_live(
                    "https://www.tiktok.com/@creator/live",
                    parts_directory=Path(directory) / "parts",
                    resolver=resolver,
                    tag_source=lambda _: (_ for _ in ()).throw(FlvFormatError("malformed")),
                    sleeper=lambda _: None,
                )

        self.assertEqual(calls, 1)


class LiveCliTests(unittest.TestCase):
    def test_live_command_uses_the_injected_live_capture(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        def live_capture(url: str, **kwargs: object) -> CaptureResult:
            calls.append((url, kwargs))
            return CaptureResult((), Path(kwargs["output_path"]), False)

        stdout = StringIO()
        with TemporaryDirectory() as directory:
            output = Path(directory) / "final media.mp4"
            code = main(
                ["live", "https://www.tiktok.com/@creator/live", "--output", str(output)],
                live_capture=live_capture,
                stdout=stdout,
            )

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][0], "https://www.tiktok.com/@creator/live")
        self.assertEqual(calls[0][1]["parts_directory"], output.with_name("final media.parts"))
        self.assertIn("progress", calls[0][1])
        self.assertIn("heartbeat", calls[0][1])
        self.assertIn("recorded", stdout.getvalue())

    def test_live_command_passes_the_optional_raw_copy_directory(self) -> None:
        calls: list[dict[str, object]] = []

        def live_capture(_: str, **kwargs: object) -> CaptureResult:
            calls.append(kwargs)
            return CaptureResult((), Path(kwargs["output_path"]), False)

        code = main(
            ["live", "https://www.tiktok.com/@creator/live", "--output", "final.mp4", "--raw-copy", "raw"],
            live_capture=live_capture,
        )

        self.assertEqual(code, 0)
        self.assertEqual(calls[0]["raw_copy_dir"], Path("raw"))

    def test_interrupted_live_clears_a_visible_heartbeat_before_stderr(self) -> None:
        class TtyStringIO(StringIO):
            def isatty(self) -> bool:
                return True

        def interrupted_live_capture(_: str, **kwargs: object) -> CaptureResult:
            heartbeat = kwargs["heartbeat"]
            assert callable(heartbeat)
            heartbeat(Path("part-0001.flv"), 96_400_000)
            return CaptureResult((), None, True)

        stdout = TtyStringIO()
        stderr = StringIO()
        code = main(
            ["live", "https://www.tiktok.com/@creator/live", "--output", "final.mp4"],
            live_capture=interrupted_live_capture,
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(code, 130)
        self.assertTrue(stdout.getvalue().endswith("\r\x1b[2K"))
        self.assertEqual(stderr.getvalue(), "tikrec: interrupted; retained parts in final.parts\n")

    def test_failed_live_clears_a_visible_heartbeat_before_stderr(self) -> None:
        class TtyStringIO(StringIO):
            def isatty(self) -> bool:
                return True

        def failed_live_capture(_: str, **kwargs: object) -> CaptureResult:
            heartbeat = kwargs["heartbeat"]
            assert callable(heartbeat)
            heartbeat(Path("part-0002.flv"), 17_400_000)
            raise CaptureError("live capture stopped after consecutive connection failures")

        stdout = TtyStringIO()
        stderr = StringIO()
        code = main(
            ["live", "https://www.tiktok.com/@creator/live", "--output", "final.mp4"],
            live_capture=failed_live_capture,
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(code, 1)
        self.assertTrue(stdout.getvalue().endswith("\r\x1b[2K"))
        self.assertEqual(
            stderr.getvalue(),
            "tikrec: live capture stopped after consecutive connection failures\n",
        )

    def test_interrupted_live_with_output_still_exits_130(self) -> None:
        stderr = StringIO()

        code = main(
            ["live", "https://www.tiktok.com/@creator/live", "--output", "final.mp4"],
            live_capture=lambda *_args, **_kwargs: CaptureResult((), Path("final.mp4"), True),
            stderr=stderr,
        )

        self.assertEqual(code, 130)
        self.assertEqual(
            stderr.getvalue(),
            "tikrec: interrupted; output written to final.mp4; retained parts in final.parts\n",
        )


def _finalizer(parts, output: Path) -> Path:
    assert list(parts)
    output.write_bytes(b"final")
    return output


if __name__ == "__main__":
    unittest.main()
