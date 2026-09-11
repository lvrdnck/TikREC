from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tikrec.capture import CaptureError, CaptureResult, capture_tags, capture_url
from tikrec.cli import main
from tikrec.finalize import finalize_parts
from tikrec.flv import FlvTag, read_tag
from tikrec.manifest import SessionManifest
from tikrec.media import MediaInfo
from tikrec.tiktok import TikTokResolutionTransientError
from tikrec.writer import write_parts


def tags() -> list[FlvTag]:
    return [
        FlvTag(9, 100, b"\x00\x00\x00", b"\x17\x00\x00\x00\x00config"),
        FlvTag(9, 120, b"\x00\x00\x00", b"\x17\x01\x00\x00\x00key"),
        FlvTag(8, 125, b"\x00\x00\x00", b"\xaf\x01audio"),
        FlvTag(9, 130, b"\x00\x00\x00", b"\x27\x01\x00\x00\x00inter"),
    ]


def part_tags(path: Path) -> list[FlvTag]:
    with path.open("rb") as handle:
        handle.read(13)
        result = []
        while tag := read_tag(handle):
            result.append(tag)
    return result


class CaptureTests(unittest.TestCase):
    def test_successful_synthetic_capture_writes_all_retained_tags(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)

            result = capture_tags(tags(), parts_directory=root / "session")

            self.assertFalse(result.interrupted)
            self.assertEqual(len(result.parts), 1)
            self.assertEqual([tag.payload for tag in part_tags(result.parts[0])], [
                tags()[0].payload, tags()[1].payload, tags()[2].payload, tags()[3].payload,
            ])

    def test_clean_eof_returns_completed_parts(self) -> None:
        with TemporaryDirectory() as directory:
            parts_directory = Path(directory) / "session"
            result = capture_tags(iter(tags()), parts_directory=parts_directory)
            manifest = json.loads((parts_directory / "session.json").read_text())

            self.assertEqual([part.name for part in result.parts], ["part-0001.flv"])
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["part_count"], 1)
            self.assertEqual(manifest["finalization"]["status"], "not_requested")

    def test_finalized_capture_records_output_and_media_in_its_manifest(self) -> None:
        def finalizer(parts, output: Path) -> Path:
            self.assertEqual(len(tuple(parts)), 1)
            output.write_bytes(b"final")
            return output

        times = iter((10.0, 14.0))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture_tags(
                tags(), parts_directory=root / "session", output_path=root / "final.mp4",
                finalizer=finalizer, clock=lambda: next(times),
                media_inspector=lambda _: MediaInfo("h264", "aac", 720, 1280),
            )
            manifest = json.loads((root / "session" / "session.json").read_text())

        self.assertEqual(result.output_path, root / "final.mp4")
        self.assertEqual(manifest["elapsed_seconds"], 4.0)
        self.assertEqual(manifest["finalization"]["status"], "completed")
        self.assertEqual(manifest["media"]["video_codec"], "h264")

    def test_finalizer_failure_is_preserved_in_the_manifest(self) -> None:
        def failing_finalizer(*_: object) -> Path:
            raise RuntimeError("muxer failed")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(CaptureError, "finalization failed"):
                capture_tags(
                    tags(), parts_directory=root / "session", output_path=root / "final.mp4",
                    finalizer=failing_finalizer,
                )
            manifest = json.loads((root / "session" / "session.json").read_text())

        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["finalization"]["status"], "failed")
        self.assertIn("muxer failed", manifest["finalization"]["error"])

    def test_capture_url_uses_an_injected_tag_source(self) -> None:
        seen_urls: list[str] = []

        def source(url: str):
            seen_urls.append(url)
            return iter(tags())

        with TemporaryDirectory() as directory:
            result = capture_url(
                "https://example.test/direct.flv",
                parts_directory=Path(directory) / "session",
                tag_source=source,
            )

        self.assertEqual(seen_urls, ["https://example.test/direct.flv"])
        self.assertEqual(len(result.parts), 1)

    def test_capture_url_writes_a_raw_copy_and_connection_mapping(self) -> None:
        def raw_source(_: str, raw_copy) -> object:
            raw_copy.write(b"unmodified source bytes")
            return iter(tags())

        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture_url(
                "https://example.test/direct.flv",
                parts_directory=root / "session",
                raw_copy_dir=root / "raw",
                raw_tag_source=raw_source,
            )
            record = json.loads((root / "session" / "connections.jsonl").read_text())
            manifest = json.loads((root / "session" / "session.json").read_text())

            self.assertEqual((root / "raw" / "connection-0001.raw").read_bytes(), b"unmodified source bytes")

        self.assertEqual(len(result.parts), 1)
        self.assertEqual(record["connection"], 1)
        self.assertEqual(record["raw_copy"], "connection-0001.raw")
        self.assertEqual(manifest["source_type"], "direct_flv")
        self.assertEqual(manifest["connection_count"], 1)
        self.assertEqual(manifest["reconnect_count"], 0)

    def test_injected_writer_receives_the_complete_stream(self) -> None:
        received: list[FlvTag] = []

        def writer(stream, _: Path):
            received.extend(stream)
            return ()

        with TemporaryDirectory() as directory:
            capture_tags(tags(), parts_directory=Path(directory) / "session", writer=writer)

        self.assertEqual(received, tags())

    def test_failure_preserves_completed_parts_and_skips_finalizer(self) -> None:
        finalizer_calls = []

        def failing_tags():
            yield from tags()[:2]
            raise RuntimeError("source dropped")

        def finalizer(*_: object) -> Path:
            finalizer_calls.append(True)
            raise AssertionError("finalizer must not run")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(CaptureError, "source dropped") as error:
                capture_tags(
                    failing_tags(),
                    parts_directory=root / "session",
                    output_path=root / "final.mp4",
                    finalizer=finalizer,
                )

            self.assertEqual([part.name for part in error.exception.parts], ["part-0001.flv"])
            manifest = json.loads((root / "session" / "session.json").read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["part_count"], 1)
            self.assertEqual(manifest["finalization"]["status"], "not_started")

        self.assertEqual(finalizer_calls, [])

    def test_keyboard_interrupt_closes_and_finalizes_completed_parts(self) -> None:
        finalizer_calls: list[tuple[Path, ...]] = []

        def interrupted_tags():
            yield from tags()[:2]
            raise KeyboardInterrupt

        def finalizer(parts, output: Path) -> Path:
            finalizer_calls.append(tuple(parts))
            output.write_bytes(b"final")
            return output

        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture_tags(
                interrupted_tags(),
                parts_directory=root / "session",
                output_path=root / "final.mp4",
                finalizer=finalizer,
            )
            manifest = json.loads((root / "session" / "session.json").read_text())

            self.assertTrue(result.interrupted)
            self.assertTrue((root / "final.mp4").is_file())
            self.assertEqual([part.name for part in finalizer_calls[0]], ["part-0001.flv"])
            self.assertEqual(manifest["status"], "interrupted")
            self.assertTrue(manifest["interrupted"])
            self.assertEqual(manifest["finalization"]["status"], "completed")

    def test_finalizer_runs_after_successful_capture(self) -> None:
        calls: list[tuple[Path, ...]] = []

        def finalizer(parts, output: Path) -> Path:
            calls.append(tuple(parts))
            output.write_bytes(b"final")
            return output

        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts_directory = root / "parts with spaces"
            output = root / "final media.mp4"
            result = capture_tags(
                tags(),
                parts_directory=parts_directory,
                output_path=output,
                finalizer=finalizer,
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(result.output_path.name, "final media.mp4")


class CliTests(unittest.TestCase):
    def test_version_reports_the_installed_tikrec_version(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            code = main(["--version"])

        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), "tikrec 0.3.1\n")

    def test_success_returns_zero_and_uses_deterministic_session_directory(self) -> None:
        calls = []

        def capture(url: str, **kwargs: object) -> CaptureResult:
            calls.append((url, kwargs))
            return CaptureResult((), Path(kwargs["output_path"]), False)

        stdout = StringIO()
        with TemporaryDirectory() as directory:
            output = Path(directory) / "recording.mp4"
            code = main(["record", "https://example.test/live", "--output", str(output)], capture=capture, stdout=stdout)

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][0], "https://example.test/live")
        self.assertEqual(calls[0][1]["parts_directory"], output.with_name("recording.parts"))
        self.assertIn("recorded", stdout.getvalue())

    def test_record_passes_the_optional_raw_copy_directory(self) -> None:
        calls = []

        def capture(url: str, **kwargs: object) -> CaptureResult:
            calls.append((url, kwargs))
            return CaptureResult((), Path(kwargs["output_path"]), False)

        code = main(
            ["record", "https://example.test/live", "--output", "recording.mp4", "--raw-copy", "raw"],
            capture=capture,
        )

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][1]["raw_copy_dir"], Path("raw"))

    def test_invalid_arguments_return_argparse_error_code(self) -> None:
        self.assertEqual(main(["record", "https://example.test/live"]), 2)

    def test_capture_error_returns_nonzero_without_a_traceback(self) -> None:
        stderr = StringIO()

        def failing_capture(*_: object, **__: object) -> CaptureResult:
            raise CaptureError("stream failed")

        code = main(
            ["record", "https://example.test/live", "--output", "folder with spaces/final.mp4"],
            capture=failing_capture,
            stderr=stderr,
        )

        self.assertEqual(code, 1)
        self.assertIn("stream failed", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_interrupted_capture_returns_conventional_interrupt_code(self) -> None:
        def interrupted_capture(*_: object, **__: object) -> CaptureResult:
            return CaptureResult((), None, True)

        self.assertEqual(
            main(
                ["record", "https://example.test/live", "--output", "final.mp4"],
                capture=interrupted_capture,
                stderr=StringIO(),
            ),
            130,
        )

    def test_resolve_command_returns_a_direct_url(self) -> None:
        stdout = StringIO()

        code = main(
            ["resolve", "https://www.tiktok.com/@creator/live"],
            resolver=lambda _: "https://cdn.test/live.flv?token=x",
            stdout=stdout,
        )

        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "https://cdn.test/live.flv?token=x\n")

    def test_resolve_reports_a_known_error_without_a_traceback(self) -> None:
        stderr = StringIO()

        code = main(
            ["resolve", "https://www.tiktok.com/@creator/live"],
            resolver=lambda _: (_ for _ in ()).throw(TikTokResolutionTransientError("short read")),
            stderr=stderr,
        )

        self.assertEqual(code, 1)
        self.assertEqual(stderr.getvalue(), "tikrec: short read\n")

    def test_finalize_command_stitches_retained_parts_without_deleting_them(self) -> None:
        calls: list[tuple[Path, ...]] = []

        def finalizer(parts, output: Path) -> Path:
            calls.append(tuple(parts))
            output.write_bytes(b"final")
            return output

        stdout = StringIO()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts_directory = root / "interrupted.parts"
            parts = write_parts(tags(), parts_directory)
            output = root / "recording.mp4"
            manifest = SessionManifest(parts_directory, output, "tiktok_live", clock=lambda: 1.0)
            manifest.start(connection_count=1)
            manifest.complete(
                parts, interrupted=True, finalization_status="not_started"
            )

            code = main(
                ["finalize", str(parts_directory), "--output", str(output)],
                finalizer=finalizer,
                stdout=stdout,
            )

            self.assertEqual(code, 0)
            self.assertEqual(calls, [parts])
            self.assertTrue(parts[0].is_file())
            self.assertEqual(output.read_bytes(), b"final")
            manifest_values = json.loads((parts_directory / "session.json").read_text())
            self.assertTrue(manifest_values["recovery_performed"])
            self.assertEqual(manifest_values["finalization"]["status"], "completed")

        self.assertIn("finalizing", stdout.getvalue())
        self.assertIn("output written:", stdout.getvalue())

    def test_finalize_command_refuses_an_existing_output_and_keeps_parts(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts_directory = root / "recording.parts"
            parts = write_parts(tags(), parts_directory)
            output = root / "recording.mp4"
            output.write_bytes(b"keep")

            code = main(
                ["finalize", str(parts_directory), "--output", str(output)],
                finalizer=finalize_parts,
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(code, 1)
            self.assertEqual(output.read_bytes(), b"keep")
            self.assertTrue(parts[0].is_file())

        self.assertIn("refusing to overwrite", stderr.getvalue())

    def test_unexpected_resolve_error_is_short_without_debug(self) -> None:
        stderr = StringIO()

        code = main(
            ["resolve", "https://www.tiktok.com/@creator/live"],
            resolver=lambda _: (_ for _ in ()).throw(RuntimeError("broken resolver")),
            stderr=stderr,
        )

        self.assertEqual(code, 1)
        self.assertEqual(stderr.getvalue(), "tikrec: unexpected RuntimeError: broken resolver\n")

    def test_debug_prints_an_unexpected_error_traceback(self) -> None:
        stderr = StringIO()

        with patch("tikrec.cli.traceback.print_exc") as print_exc:
            code = main(
                ["resolve", "https://www.tiktok.com/@creator/live", "--debug"],
                resolver=lambda _: (_ for _ in ()).throw(RuntimeError("broken resolver")),
                stderr=stderr,
            )

        self.assertEqual(code, 1)
        print_exc.assert_called_once_with(file=stderr)

    def test_keyboard_interrupt_returns_130_without_a_traceback(self) -> None:
        stderr = StringIO()

        code = main(
            ["resolve", "https://www.tiktok.com/@creator/live"],
            resolver=lambda _: (_ for _ in ()).throw(KeyboardInterrupt),
            stderr=stderr,
        )

        self.assertEqual(code, 130)
        self.assertEqual(stderr.getvalue(), "tikrec: interrupted\n")


if __name__ == "__main__":
    unittest.main()
