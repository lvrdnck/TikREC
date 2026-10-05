"""Connected native writers never turn partial/error evidence into candidate success."""

import os
import sys
from pathlib import Path

import pytest

from tests.journal_assembly_helpers import connected, managed_process
from tikrec.assembly_types import AssemblyError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="actual connected Windows faults")


def writer_code(monkeypatch, code):
    """Substitute only disposable writer work, keeping durable intent/helper containment."""
    import tikrec.journal_assembly as module
    monkeypatch.setattr(module, "_build_ffmpeg_command", lambda *_, **__: [str(Path(sys._base_executable)), "-c", code])


@pytest.mark.parametrize("point,name", [
    ("before_assembly_writer", "concat.ffconcat"), ("before_assembly_writer", "candidate.mp4"),
    ("after_identity", "concat.ffconcat"), ("before_resume_fence", "candidate.mp4"),
    ("after_artifact_bind", "unexpected.txt"), ("before_candidate_ready", "unexpected.txt")])
def test_connected_collisions_and_changed_inventory_are_retained(connected, point, name):
    adapter, _, _, _ = connected
    runner = adapter.coordinator
    def change(boundary):
        if boundary == point:
            (runner.scratch.path / name).write_bytes(b"preserve unexplained artifact")
    runner._fault = change
    with pytest.raises(AssemblyError):
        adapter.run()
    assert (runner.scratch.path / name).read_bytes() == b"preserve unexplained artifact"
    assert runner.journal.scratch(runner.token)["candidate"] is None
    assert not adapter.close() and runner.scratch.workspace.handle is not None


@pytest.mark.parametrize("diagnostic", [
    b"Error opening output file: occupied -n destination", b"Conversion failed!",
    b"x" * 70000, b"incomplete unicode \xc3"], ids=["occupied", "explicit", "oversized", "utf8"])
def test_zero_exit_final_tail_cannot_bypass_semantic_diagnostics(connected, monkeypatch, diagnostic):
    adapter, _, _, _ = connected
    # Generate oversized stderr inside the child; embedding 70 KiB in argv
    # would test the Windows command-line limit before any writer could run.
    expression = "b'x' * 70000" if len(diagnostic) == 70000 else repr(diagnostic)
    writer_code(monkeypatch, "from pathlib import Path;import sys;"
        "Path('candidate.mp4').write_bytes(b'partial');sys.stderr.buffer.write(" + expression + ")")
    with pytest.raises(AssemblyError) as caught:
        adapter.run()
    runner = adapter.coordinator
    child = runner.journal.owned_attempt(runner.token)["child"]
    assert child["exit"]["code"] == 0 and child["cleanup"] == 1
    assert child["diagnostics"]["counts"]["stderr"] == len(diagnostic)
    assert runner.scratch.failure is caught.value.original
    assert runner.journal.scratch(runner.token)["candidate"] is None
    assert not adapter.close()


@pytest.mark.parametrize("code", ["import sys;sys.exit(7)", "pass"])
def test_descendant_failure_or_missing_candidate_retains_helper(connected, monkeypatch, code):
    adapter, _, _, _ = connected
    writer_code(monkeypatch, code)
    with pytest.raises(AssemblyError):
        adapter.run()
    runner = adapter.coordinator
    assert (runner.scratch.path / "concat.ffconcat").is_file()
    assert runner.journal.owned_attempt(runner.token)["child"]["exit"]["code"] in {0, 7}
    assert runner.journal.scratch(runner.token)["candidate"] is None
    assert not adapter.close()


@pytest.mark.parametrize("failure", ["observer", "eof", "native_cleanup", "artifact_close"])
def test_integrated_diagnostics_and_native_cleanup_remain_independent(connected, monkeypatch, failure):
    adapter, _, _, _ = connected
    runner = adapter.coordinator
    def unavailable(*_):
        raise OSError("injected " + failure)
    def fault(point):
        if point == "native_after_resume" and failure in {"eof", "native_cleanup"}:
            native = runner.children[-1]["process"].native
            if failure == "native_cleanup":
                monkeypatch.setattr(native, "close", unavailable)
            else:
                status = native.status
                def exited():
                    value = status()
                    if value[0] is not None and value[1] == 0:
                        native.streams.eof.clear()
                        monkeypatch.setattr(native.streams, "read", unavailable)
                    return value
                monkeypatch.setattr(native, "status", exited)
    runner._fault = fault
    if failure == "observer":
        adapter.progress = unavailable
    if failure == "artifact_close":
        adapter.run()
        held = runner.scratch.artifacts["candidate.mp4"]
        monkeypatch.setattr(held, "close", unavailable)
        assert not adapter.close() and held.handle is not None
        assert runner.cleanup_evidence()["execution_revoked"]
        assert not runner.cleanup_evidence()["cleanup_complete"]
        return
    with pytest.raises(AssemblyError):
        adapter.run()
    child = runner.journal.owned_attempt(runner.token)["child"]
    assert child["exit"]["state"] == "confirmed_exited"
    assert not child["diagnostics"]["complete"]
    assert runner.journal.scratch(runner.token)["candidate"] is None
    assert not adapter.close()
    if failure == "native_cleanup":
        assert child["cleanup"] == 0 and not runner.guard.closed


@pytest.mark.parametrize("unavailable", [False, True])
def test_candidate_acknowledgement_is_reconciled_once_or_retained(connected, monkeypatch, unavailable):
    adapter, _, _, _ = connected
    runner = adapter.coordinator
    lookups = []
    operation = runner.journal.operation
    def lookup(identity):
        lookups.append(identity)
        if unavailable:
            raise OSError("receipt unavailable")
        return operation(identity)
    def fault(kind, boundary):
        if kind == "seal_candidate" and boundary == "after_commit":
            raise OSError("candidate acknowledgement lost")
    runner.journal._fault = fault
    monkeypatch.setattr(runner.journal, "operation", lookup)
    if unavailable:
        with pytest.raises(AssemblyError):
            adapter.run()
        assert not runner.scratch.candidate_ready and adapter.receipt is None
        assert not adapter.close() and runner.scratch.artifacts["candidate.mp4"].handle is not None
    else:
        assert adapter.run().state == "candidate_ready"
    assert len(lookups) == 1
    record = runner.journal.scratch(runner.token)
    assert record["candidate"]["publication"] == "unpublished"
    assert record["candidate"]["validation"] == "not_checked"
    assert len(runner.journal.status()["units"]) == 1


def test_actual_ffmpeg_zero_exit_occupied_output_is_not_sealed(connected, monkeypatch):
    import tikrec.journal_assembly as module
    adapter, _, _, _ = connected
    build = module._build_ffmpeg_command
    def occupied(*args, **kwargs):
        command = build(*args, **kwargs)
        code = "from pathlib import Path;import subprocess,sys;" \
            "Path('candidate.mp4').write_bytes(b'foreign occupant');" \
            "sys.exit(subprocess.call(" + repr(command) + "))"
        return [str(Path(sys._base_executable)), "-c", code]
    monkeypatch.setattr(module, "_build_ffmpeg_command", occupied)
    with pytest.raises(AssemblyError) as caught:
        adapter.run()
    runner = adapter.coordinator
    child = runner.journal.owned_attempt(runner.token)["child"]
    assert child["exit"]["code"] == 0
    assert "FFmpeg reported execution failure" in str(caught.value.original)
    assert (runner.scratch.path / "candidate.mp4").read_bytes() == b"foreign occupant"
    assert runner.journal.scratch(runner.token)["candidate"] is None


def test_exclusive_helper_production_refuses_late_collision(connected, monkeypatch):
    import tikrec.assembly_launcher as launcher
    adapter, _, _, _ = connected
    marker = "    with open(spec['manifest'], 'x'"
    code = launcher.CONCAT_LAUNCHER.replace(marker,
        "    Path(spec['manifest']).write_bytes(b'late foreign helper')\n" + marker)
    assert code != launcher.CONCAT_LAUNCHER
    monkeypatch.setattr(launcher, "CONCAT_LAUNCHER", code)
    with pytest.raises(AssemblyError):
        adapter.run()
    runner = adapter.coordinator
    assert (runner.scratch.path / "concat.ffconcat").read_bytes() == b"late foreign helper"
    assert not (runner.scratch.path / "candidate.mp4").exists()
    assert runner.journal.owned_attempt(runner.token)["child"]["exit"]["code"] == 1


def test_integrated_first_failure_survives_secondary_hold_lookup(connected, monkeypatch):
    adapter, _, _, _ = connected
    runner = adapter.coordinator
    writer_code(monkeypatch, "import sys;sys.stderr.write('first writer failure');sys.exit(9)")
    def unavailable(_):
        raise OSError("secondary scratch journal lookup unavailable")
    def fault(point):
        if point == "native_after_resume":
            monkeypatch.setattr(runner.journal, "scratch", unavailable)
    runner._fault = fault
    with pytest.raises(AssemblyError) as caught:
        adapter.run()
    assert runner.scratch.failure is caught.value.original
    assert "first writer failure" in str(caught.value.original)
    assert runner.errors and any("secondary scratch" in str(e) for e in runner.errors)
    assert not adapter.close() and runner.scratch.workspace.handle is not None


@pytest.mark.parametrize("connected", [True], indirect=True)
def test_failed_durable_probe_never_allocates_writer_or_scratch(connected):
    adapter, _, _, _ = connected
    runner = adapter.coordinator
    original = ValueError("probe authorization revoked")
    def fault(point):
        if point == "after_identity":
            raise original
    runner._fault = fault
    with pytest.raises(AssemblyError):
        adapter.run()
    assert runner.scratch is None and len(runner.children) == 1
    child = runner.journal.owned_attempt(runner.token)["child"]
    assert child["intent"]["phase"] == "frame_rate" and "access" not in child["intent"]
    assert child["exit"]["state"] == "confirmed_exited"
    assert len(runner.journal.status()["units"]) == 1
