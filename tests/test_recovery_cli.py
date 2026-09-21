"""User-facing and structured output for read-only recovery discovery."""

import json
from dataclasses import replace
from io import StringIO
from pathlib import Path

from tikrec.cli import main
from tikrec.recovery_cli import render_recovery_report
from tikrec.recovery_discovery import RecoveryCandidate


BASE = RecoveryCandidate(
    parts_directory="/recordings/creator.parts",
    session_id="a738109c-a387-423f-a20b-969ecf656c4b",
    source_type="tiktok_live",
    room_id="7687950152400816913",
    output_path="/recordings/creator.mp4",
    lifecycle_state="interrupted",
    retained_parts=3,
    final_output="missing",
    finalization_state="incomplete",
    evidence_consistent=True,
    classification="recoverable",
    safe_next_action=True,
    summary="Recording ended before finalization — parts appear available for recovery.",
    next_action="Use tikrec finalize with this parts directory and the declared output path.",
    untouched_reason=None,
)


def test_recover_prints_plain_language_session_facts() -> None:
    stdout = StringIO()

    code = main(
        ["recover", "/recordings"],
        recovery_discoverer=lambda _: (BASE,), stdout=stdout,
    )

    assert code == 0
    report = stdout.getvalue()
    assert f"Recovery candidates in {Path('/recordings')}: 1" in report
    assert "Session: a738109c-a387-423f-a20b-969ecf656c4b" in report
    assert "Source: TikTok LIVE (room 7687950152400816913)" in report
    assert "Retained parts: 3" in report
    assert "parts appear available for recovery" in report


def test_recover_json_is_machine_readable() -> None:
    stdout = StringIO()

    code = main(
        ["recover", "recordings", "--json"],
        recovery_discoverer=lambda _: (BASE,), stdout=stdout,
    )

    document = json.loads(stdout.getvalue())
    assert code == 0
    assert document["scope"] == "recordings"
    assert document["candidate_count"] == 1
    assert document["candidates"][0]["classification"] == "recoverable"


def test_recover_reports_empty_scope_plainly() -> None:
    stdout = StringIO()
    code = main(
        ["recover", "empty"], recovery_discoverer=lambda _: (), stdout=stdout
    )
    assert code == 0
    assert stdout.getvalue() == "No TikREC recovery candidates found in empty.\n"


def test_recover_errors_use_existing_cli_error_contract() -> None:
    def fail(_: Path):
        raise ValueError("recovery scope must be a regular directory")

    stderr = StringIO()
    code = main(["recover", "missing"], recovery_discoverer=fail, stderr=stderr)
    assert code == 1
    assert stderr.getvalue() == "tikrec: recovery scope must be a regular directory\n"


def test_render_preserves_windows_and_posix_paths() -> None:
    windows = replace(
        BASE,
        parts_directory=r"C:\Videos\creator.parts",
        output_path=r"C:\Videos\creator.mp4",
    )
    report = render_recovery_report(Path("."), (windows, BASE))
    assert r"C:\Videos\creator.parts" in report
    assert r"C:\Videos\creator.mp4" in report
    assert "/recordings/creator.parts" in report
