from __future__ import annotations

from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tikrec.capture import CaptureError, CaptureResult, capture_tags, capture_url
from tikrec.cli import main
from tikrec.flv import FlvTag, read_tag


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
            result = capture_tags(iter(tags()), parts_directory=Path(directory) / "session")

            self.assertEqual([part.name for part in result.parts], ["part-0001.flv"])

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

            self.assertTrue(result.interrupted)
            self.assertTrue((root / "final.mp4").is_file())
            self.assertEqual([part.name for part in finalizer_calls[0]], ["part-0001.flv"])

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


if __name__ == "__main__":
    unittest.main()
