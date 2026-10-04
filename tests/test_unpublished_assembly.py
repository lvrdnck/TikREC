"""Assembly ownership regressions added before the new boundary implementation."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.assembly_helpers import assembly_fixture
from tests.test_finalize import write_part


def test_copy_is_unpublished_preserves_source_controls_and_siblings(assembly_fixture, tmp_path):
    build, controls, parts = assembly_fixture
    for name in ("session.json", "connections.jsonl", "connection.raw", "arrival.jsonl"):
        (parts[0].parent / name).write_bytes(name.encode())
    before = {p: p.read_bytes() for p in parts[0].parent.iterdir()}
    sibling = tmp_path / "old-attempt.mp4"
    sibling.write_bytes(b"keep")
    attempt = build(inputs=parts[::-1])
    result = attempt.run()
    assert result.state == "candidate_ready" and result.candidate.is_file()
    assert result.input_decode["status"] == "not_checked"
    assert result.diagnostics_complete and len(result.children) == 1
    assert result.children[0].owner.closed
    assert result.children[0].evidence.state == "confirmed_exited"
    assert not (tmp_path / "final.mp4").exists()
    assert all(p.read_bytes() == value for p, value in before.items())
    assert sibling.read_bytes() == b"keep"
    manifest = next(attempt.work_scope.glob("*.ffconcat")).read_text()
    assert manifest.index(str(parts[0])) < manifest.index(str(parts[1]))


def test_reencode_probes_sequentially_preserves_degraded_tail(assembly_fixture):
    build, controls, parts = assembly_fixture
    write_part(parts[1], b"different")
    controls["chunks"] = [b"ignored\n" * 5000, b"[h264 @ 0x1] error while decoding ", b"MB 1 2"]
    with patch("tikrec.finalize_plan.avc_configuration_dimensions", return_value=(64, 64)):
        result = build().run()
    assert result.state == "candidate_ready" and len(result.children) == 3
    assert all(c.evidence.stream_status == ("complete", "complete") for c in result.children)
    assert all(c.owner.closed for c in result.children)
    assert result.input_decode["status"] == "degraded"
    assert result.input_decode["diagnostic_codes"] == ["h264_macroblock"]
    assert result.children[-1].evidence.truncated[1] > 0
    assert "libx264" in result.children[-1].command


@pytest.mark.parametrize("collision", ["scope", "candidate"])
def test_existing_scope_or_candidate_refused_without_changes(assembly_fixture, tmp_path, collision):
    build, controls, _ = assembly_fixture
    attempt = build()
    attempt.work_scope.mkdir()
    occupied = attempt.candidate if collision == "candidate" else attempt.work_scope / "sibling"
    occupied.write_bytes(b"previous attempt")
    with pytest.raises(Exception) as caught:
        attempt.run()
    assert isinstance(caught.value.original, FileExistsError)
    assert occupied.read_bytes() == b"previous attempt" and not controls["owners"]


def test_failed_partial_and_first_error_survive_cleanup_failure(assembly_fixture):
    build, controls, _ = assembly_fixture
    controls["code"] = 9
    controls["cleanup_error"] = OSError("secondary native cleanup")
    attempt = build()
    with pytest.raises(Exception) as caught:
        attempt.run()
    result = caught.value.result
    assert result.candidate.is_file() and result.state == "failed"
    assert "exited with code 9" in str(caught.value.original)
    assert any("secondary native cleanup" in str(e) for e in result.diagnostics)
    assert result.children[0].owner is controls["owners"][0]


@pytest.mark.parametrize("when", ["before_run", "authorization", "after_resume"])
def test_irreversible_cancellation_retains_partial_when_created(assembly_fixture, when):
    build, controls, _ = assembly_fixture
    attempt = build()
    if when == "before_run":
        attempt.cancel()
    elif when == "authorization":
        attempt.before_resume = lambda identity: attempt.cancel() or identity
    else:
        controls["fault"] = lambda boundary: attempt.cancel() if boundary == "after_resume" else None
    with pytest.raises(Exception) as caught:
        attempt.run()
    assert caught.value.result.state == "cancelled"
    assert attempt.candidate.exists() == (when == "after_resume")
    with pytest.raises(ValueError, match="single-use"):
        attempt.run()


def test_authorization_mismatch_never_executes_payload(assembly_fixture):
    build, controls, _ = assembly_fixture
    attempt = build(before_resume=lambda _: None)
    with pytest.raises(Exception):
        attempt.run()
    assert not attempt.candidate.exists()
    assert controls["owners"][0].native.resumes == 0


def test_unknown_owner_reachable_and_no_successor(assembly_fixture, monkeypatch):
    build, controls, parts = assembly_fixture
    write_part(parts[1], b"different")
    import tests.owned_process_state_helpers as doubles
    original = doubles.Native.status
    monkeypatch.setattr(doubles.Native, "status", lambda _: (_ for _ in ()).throw(OSError("unknown lifetime")))
    attempt = build()
    with patch("tikrec.finalize_plan.avc_configuration_dimensions", return_value=(64, 64)):
        with pytest.raises(Exception) as caught:
            attempt.run()
    result = caught.value.result
    assert result.state == "exit_unknown" and len(result.children) == 1
    assert result.children[0].owner.native.process is not None
    assert caught.value.attempt is attempt
    assert attempt.work_scope.is_dir()
    monkeypatch.setattr(doubles.Native, "status", original)


def test_incomplete_parser_cannot_report_clean_candidate(assembly_fixture):
    build, controls, parts = assembly_fixture
    write_part(parts[1], b"different")
    controls["chunks"] = [b"x" * 200000]
    attempt = build()
    with patch("tikrec.finalize_plan.avc_configuration_dimensions", return_value=(64, 64)):
        with pytest.raises(Exception) as caught:
            attempt.run()
    assert not caught.value.result.diagnostics_complete
    assert caught.value.result.input_decode["status"] == "unknown"
    assert attempt.candidate.exists()


def test_progress_error_is_primary_and_partial_remains(assembly_fixture):
    build, controls, _ = assembly_fixture
    controls["chunks"] = [b"out_time=00:00:01.000000\n"]
    error = RuntimeError("observer rejected")
    def progress(_):
        raise error
    attempt = build(progress=progress)
    with pytest.raises(Exception) as caught:
        attempt.run()
    assert caught.value.original is error
    assert attempt.candidate.is_file()
    assert caught.value.result.children[0].evidence.state == "confirmed_exited"
    assert not caught.value.result.diagnostics_complete


def test_cancellation_between_planning_probes_prevents_next_child(assembly_fixture):
    build, controls, parts = assembly_fixture
    write_part(parts[1], b"different")
    attempt = build()
    probe = attempt._probe
    def first_probe(part):
        rate = probe(part)
        attempt.cancel()
        return rate
    attempt._probe = first_probe
    with patch("tikrec.finalize_plan.avc_configuration_dimensions", return_value=(64, 64)):
        with pytest.raises(Exception) as caught:
            attempt.run()
    assert caught.value.result.state == "cancelled" and len(controls["owners"]) == 1
    assert controls["owners"][0].closed and not attempt.candidate.exists()


def test_running_assembly_has_no_thirty_second_deadline(assembly_fixture, monkeypatch):
    build, controls, _ = assembly_fixture
    import tests.owned_process_state_helpers as doubles
    original, elapsed, polls = doubles.Native.status, [], []
    def status(native):
        polls.append(True)
        return (None, 1) if len(polls) <= 8 else original(native)
    monkeypatch.setattr(doubles.Native, "status", status)
    import tikrec.assembly_process as execution
    monkeypatch.setattr(execution, "time", SimpleNamespace(sleep=lambda _: elapsed.append(5)))
    result = build().run()
    assert result.state == "candidate_ready" and sum(elapsed) == 40
    assert result.children[0].evidence.error is None


@pytest.mark.parametrize("invalid", ["relative-input", "duplicate", "source-scratch", "relative-exe", "candidate-outside"])
def test_explicit_scope_validation_launches_nothing(assembly_fixture, tmp_path, invalid):
    build, controls, parts = assembly_fixture
    options = {
        "relative-input": dict(inputs=[parts[0].relative_to(tmp_path)]),
        "duplicate": dict(inputs=[parts[0], parts[0]]),
        "source-scratch": dict(work_scope=parts[0].parent / "attempt", candidate=parts[0].parent / "attempt/candidate.mp4"),
        "relative-exe": dict(ffmpeg="ffmpeg.exe"),
        "candidate-outside": dict(candidate=tmp_path / "final.mp4"),
    }
    attempt = build(**options[invalid])
    with pytest.raises(Exception):
        attempt.run()
    assert not controls["owners"] and not attempt.work_scope.exists()


def test_final_drain_failure_preserves_exit_and_unknown_health(assembly_fixture, monkeypatch):
    build, controls, parts = assembly_fixture
    write_part(parts[1], b"different")
    original_factory = build().process_factory
    def factory(session, token):
        owner = original_factory(session, token)
        if len(controls["owners"]) == 3:
            def fault(boundary):
                if boundary == "after_resume":
                    owner.native.streams.no_eof = True
            owner._fault = fault
            wait = owner.wait
            owner.wait = lambda timeout, **options: wait(0.01, **options)
        return owner
    attempt = build(process_factory=factory)
    with patch("tikrec.finalize_plan.avc_configuration_dimensions", return_value=(64, 64)):
        with pytest.raises(Exception) as caught:
            attempt.run()
    result = caught.value.result
    assert result.children[-1].evidence.state == "confirmed_exited"
    assert result.children[-1].evidence.stream_status == ("incomplete", "incomplete")
    assert not result.diagnostics_complete and result.input_decode["status"] == "unknown"
    assert attempt.candidate.exists()


@pytest.mark.parametrize("output", [b"not JSON", b"x" * 70000], ids=["malformed", "oversized"])
def test_required_probe_failure_has_no_uncontrolled_fallback_or_successor(assembly_fixture, output):
    build, controls, parts = assembly_fixture
    write_part(parts[1], b"different")
    controls["probe_output"] = output
    attempt = build()
    with patch("tikrec.finalize_plan.avc_configuration_dimensions", return_value=(64, 64)):
        with patch("tikrec.frame_rate.subprocess.run", side_effect=AssertionError("uncontrolled fallback")):
            with pytest.raises(Exception) as caught:
                attempt.run()
    assert len(controls["owners"]) == 1 and controls["owners"][0].closed
    assert not attempt.candidate.exists() and caught.value.result.state == "failed"


def test_missing_candidate_never_means_ready(assembly_fixture):
    build, controls, _ = assembly_fixture
    attempt = build()
    def fault(boundary):
        if boundary == "after_resume":
            attempt.candidate.unlink()
    controls["fault"] = fault
    with pytest.raises(Exception) as caught:
        attempt.run()
    assert caught.value.result.state == "failed"
    assert "nonempty candidate" in str(caught.value.original)


def test_candidate_created_during_authorization_never_resumes(assembly_fixture):
    build, controls, _ = assembly_fixture
    attempt = build()
    def authorize(identity):
        attempt.candidate.write_bytes(b"occupied")
        return identity
    attempt.before_resume = authorize
    with pytest.raises(Exception) as caught:
        attempt.run()
    assert isinstance(caught.value.original, FileExistsError)
    assert attempt.candidate.read_bytes() == b"occupied"
    assert controls["owners"][0].native.resumes == 0


@pytest.mark.parametrize("cleanup_error", [False, True])
def test_zero_exit_with_explicit_output_error_is_not_ready(assembly_fixture, cleanup_error):
    build, controls, _ = assembly_fixture
    controls["chunks"] = [b"Error opening output file candidate.mp4."]
    if cleanup_error:
        controls["cleanup_error"] = OSError("secondary cleanup")
    attempt = build()
    with pytest.raises(Exception) as caught:
        attempt.run()
    assert caught.value.result.state == "failed" and caught.value.result.diagnostics_complete
    assert caught.value.result.children[0].evidence.root_exit_code == 0
    assert "execution failure" in str(caught.value.original)
    if cleanup_error:
        assert any("secondary cleanup" in str(e) for e in caught.value.result.diagnostics)
