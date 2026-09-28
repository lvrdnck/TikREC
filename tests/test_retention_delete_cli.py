"""Offline exact-session Windows deletion consent and result reporting."""

import argparse
import json
import os
import uuid
from dataclasses import replace
from io import StringIO
from pathlib import Path

import pytest

from tests.test_retention_execute import events, fixture
from tests.test_retention_plan import NOW, inspect
from tikrec.cli import main
from tikrec.configuration import Configuration
from tikrec.job_state import JobState, JobStateStore
from tikrec.lifecycle_lock import acquire_lifecycle
from tikrec.retention_cli import run_retention_command


class Terminal(StringIO):
    """One interactive answer with an optional change made after display."""

    def __init__(self, value: str, before=None):
        super().__init__(value)
        self.before = before

    def isatty(self):
        return True

    def readline(self, *args):
        if self.before is not None:
            before, self.before = self.before, None
            before()
        return super().readline(*args)


def call(case, *, target=None, root=None, confirm=None, stdin=None):
    """Run the real local command against one disposable synthetic session."""
    actual_root, parts, session_id, config, jobs, audit, _ = case
    arguments = argparse.Namespace(
        config_path=str(config.path), retention_action="delete",
        session_id=target or session_id, root=str(root) if root is not None else str(actual_root),
        confirm=confirm)
    stdout, stderr = StringIO(), StringIO()
    result = run_retention_command(
        arguments, stdout, stderr, stdin or StringIO(),
        clock=lambda: NOW, media_inspector=inspect, job_paths=jobs, audit_path=audit)
    return result, stdout.getvalue(), stderr.getvalue()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_complete_exact_noninteractive_deletion_and_audit(tmp_path):
    case = fixture(tmp_path)
    root, parts, session_id, config, _, audit, _ = case
    config.save(Configuration(output_directory=root, retention_max_age_days=1))
    code, out, err = call(case, root=root, confirm=session_id)
    assert code == 0 and not err
    assert "Retention deletion preview" in out
    assert f"Root: {root}" in out and f"Session: {session_id}" in out
    assert "State: eligible" in out and "not protected" in out
    assert f"Final MP4: {root / 'alpha.mp4'}" in out
    assert f"Retained parts: {parts}" in out
    assert "final MP4 last" in out and "Deletion is permanent" in out
    assert "COMPLETE" in out and f"Audit: {audit}" in out
    operation = events(audit)[0]["operation_id"]
    assert f"Operation ID: {operation}" in out
    assert events(audit)[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
@pytest.mark.parametrize("line", ["COMPLETE:", "Operation ID:", "Audit:", "flush"])
def test_completed_output_fault_stays_complete(tmp_path, failure, line):
    case = fixture(tmp_path)
    root, parts, session_id, config, jobs, audit, _ = case

    class FailingOutput(StringIO):
        def write(self, value):
            if value.startswith(line):
                raise failure("synthetic completed output fault")
            return super().write(value)

        def flush(self):
            if line == "flush":
                raise failure("synthetic completed output fault")
            return super().flush()

    arguments = argparse.Namespace(
        config_path=str(config.path), retention_action="delete",
        session_id=session_id, root=str(root), confirm=session_id)
    stdout, stderr = FailingOutput(), StringIO()
    code = run_retention_command(
        arguments, stdout, stderr, StringIO(), clock=lambda: NOW,
        media_inspector=inspect, job_paths=jobs, audit_path=audit)
    records = events(audit)
    assert code == 0 and records[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    assert "COMPLETE" in stderr.getvalue()
    assert f"Output error: {failure.__name__}: synthetic completed output fault" in stderr.getvalue()
    assert f"Operation ID: {records[0]['operation_id']}" in stderr.getvalue()
    assert f"Audit: {audit}" in stderr.getvalue()
    assert "PARTIAL" not in stderr.getvalue() and "FAILED" not in stderr.getvalue()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_completed_output_and_diagnostic_failure_keep_exit_zero(tmp_path):
    case = fixture(tmp_path)
    root, parts, session_id, config, jobs, audit, _ = case

    class FailingSuccessOutput(StringIO):
        def write(self, value):
            if value.startswith("COMPLETE:"):
                raise OSError("synthetic output failure")
            return super().write(value)

    class FailingDiagnostic(StringIO):
        def write(self, _value):
            raise OSError("synthetic diagnostic failure")

    arguments = argparse.Namespace(
        config_path=str(config.path), retention_action="delete",
        session_id=session_id, root=str(root), confirm=session_id)
    code = run_retention_command(
        arguments, FailingSuccessOutput(), FailingDiagnostic(), StringIO(),
        clock=lambda: NOW, media_inspector=inspect, job_paths=jobs, audit_path=audit)
    assert code == 0 and events(audit)[-1]["event"] == "completed"
    assert not parts.exists() and not (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_configured_root_and_interactive_exact_uuid(tmp_path):
    case = fixture(tmp_path)
    root, parts, session_id, config, _, audit, _ = case
    config.save(Configuration(output_directory=root, retention_max_age_days=1))
    arguments = argparse.Namespace(config_path=str(config.path),
                                   retention_action="delete", session_id=session_id,
                                   root=None, confirm=None)
    out, err = StringIO(), StringIO()
    code = run_retention_command(arguments, out, err, Terminal(session_id + "\r\n"),
                                 clock=lambda: NOW, media_inspector=inspect,
                                 job_paths=case[4], audit_path=audit)
    assert code == 0 and f"Root: {root}" in out.getvalue() and not err.getvalue()
    assert not parts.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_main_parser_routes_exact_confirm_to_private_executor(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    root, parts, session_id, config, jobs, audit, _ = case
    config.save(Configuration(output_directory=root, retention_max_age_days=1))
    import tikrec.cli as entry
    actual = entry.run_retention_command
    monkeypatch.setattr(entry, "run_retention_command", lambda args, out, err, stdin: actual(
        args, out, err, stdin, clock=lambda: NOW, media_inspector=inspect,
        job_paths=jobs, audit_path=audit))
    out, err = StringIO(), StringIO()
    code = main(["--config", str(config.path), "retention", "delete", session_id,
                 "--confirm", session_id], stdout=out, stderr=err, stdin=StringIO())
    assert code == 0 and not err.getvalue()
    assert "COMPLETE" in out.getvalue() and not parts.exists()
    assert events(audit)[-1]["event"] == "completed"


@pytest.mark.skipif(os.name != "nt", reason="Windows preview tests")
@pytest.mark.parametrize("answer", ["yes\n", "123e4567\n", " {uuid}\n",
                                      "{uuid} \n", "{upper}\n", ""])
def test_wrong_or_missing_interactive_confirmation_refuses(tmp_path, answer):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, audit, _ = case
    answer = answer.replace("{uuid}", session_id).replace("{upper}", session_id.upper())
    code, out, err = call(case, stdin=Terminal(answer))
    assert code == 1 and "REFUSED" in err and "No deletion operation" in err
    assert "Retention deletion preview" in out
    assert parts.exists() and (root / "alpha.mp4").exists() and not audit.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows preview tests")
def test_noninteractive_without_exact_confirm_refuses(tmp_path):
    case = fixture(tmp_path)
    session_id = case[2]
    for supplied in (None, session_id.upper(), "yes", session_id + " "):
        code, _, err = call(case, confirm=supplied)
        assert code == 1 and "REFUSED" in err and not case[5].exists()
    assert case[1].exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows preview tests")
@pytest.mark.parametrize("state", ["absent", "retained", "protected", "ineligible",
                                       "active", "recoverable", "needs_attention",
                                       "unsafe_root"])
def test_preflight_states_refuse_before_confirmation(tmp_path, state):
    case = fixture(tmp_path)
    root, parts, session_id, config, _, audit, _ = case
    target, selected_root = session_id, root
    if state == "absent":
        target = str(uuid.uuid4())
    elif state == "retained":
        config.save(Configuration())
    elif state == "protected":
        config.save(Configuration(retention_max_age_days=1,
                                  retention_protected_creators=("alpha",)))
    elif state in {"ineligible", "active", "recoverable"}:
        manifest = parts / "session.json"
        value = json.loads(manifest.read_text())
        value["status"] = {"ineligible": "failed", "active": "recording",
                           "recoverable": "interrupted"}[state]
        manifest.write_text(json.dumps(value))
    elif state == "needs_attention":
        (parts / "unexpected.txt").write_text("preserve")
    else:
        selected_root = parts / "session.json"
    code, out, err = call(case, target=target, root=selected_root,
                          stdin=Terminal(session_id + "\n"))
    assert code == 1 and "REFUSED" in err and "No deletion operation" in err
    assert "Type the exact session UUID" not in out
    assert parts.exists() and (root / "alpha.mp4").exists() and not audit.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows preview tests")
def test_policy_and_artifact_changes_after_display_veto(tmp_path):
    for change in ("still_eligible_rule", "protection", "output_bytes"):
        parent = tmp_path / change
        parent.mkdir()
        case = fixture(parent)
        root, parts, session_id, config, _, audit, _ = case
        def mutate():
            if change == "still_eligible_rule":
                config.save(replace(config.load(), retention_max_age_days=2))
            elif change == "protection":
                config.save(replace(config.load(),
                                    retention_protected_creators=("alpha",)))
            else:
                output = root / "alpha.mp4"
                original = output.read_bytes()
                output.write_bytes(b"X" + original[1:])
        code, out, err = call(case, stdin=Terminal(session_id + "\n", mutate))
        assert code == 1 and "REFUSED" in err and "No deletion operation" in err
        assert "Deletion is permanent" in out
        assert parts.exists() and (root / "alpha.mp4").exists() and not audit.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows preview tests")
def test_job_audit_and_lifecycle_refusals(tmp_path):
    for failure in ("job", "audit", "lifecycle"):
        parent = tmp_path / failure
        parent.mkdir()
        case = fixture(parent)
        root, parts, session_id, _, jobs, audit, _ = case
        if failure == "job":
            JobStateStore(jobs[1]).save(JobState(
                session_id=session_id, source_url="https://www.tiktok.com/@alpha/live",
                output_path=str(root / "alpha.mp4"), parts_directory=str(parts),
                started_at=1000, state="completed", ended_at=1010))
        if failure == "audit":
            audit.parent.mkdir()
            audit.write_bytes(b'{"schema_version":1')
        if failure == "lifecycle":
            with acquire_lifecycle(root, "writer"):
                code, _, err = call(case, confirm=session_id)
        else:
            code, _, err = call(case, confirm=session_id)
        assert code == 1 and "REFUSED" in err and "No deletion operation" in err
        assert parts.exists() and (root / "alpha.mp4").exists()
        if failure != "audit":
            assert not audit.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
@pytest.mark.parametrize("fail_at,state", [(0, "FAILED"), (1, "PARTIAL")])
def test_after_intent_failure_reports_original_context(tmp_path, monkeypatch,
                                                       fail_at, state):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, audit, _ = case
    import tikrec.retention_delete_cli as cli
    original = cli.execute_retention
    seen = []
    def injected(*args, **kwargs):
        def before(path):
            if len(seen) == fail_at:
                raise OSError("synthetic stop")
            seen.append(path)
        return original(*args, before_mutation=before, **kwargs)
    monkeypatch.setattr(cli, "execute_retention", injected)
    code, out, err = call(case, confirm=session_id)
    assert code == 3 and state in err and "synthetic stop" in err
    assert "Operation ID: " in err and f"Audit: {audit}" in err
    assert "will not retry or resume" in err and "COMPLETE" not in out
    assert [record["event"] for record in events(audit)][-1] == "failed"
    assert parts.exists() and (root / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_uncertain_first_removal_reports_partial(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    import tikrec.retention_execute as executor
    def uncertain(*_args, **_kwargs):
        raise OSError("synthetic disposition uncertainty")
    monkeypatch.setattr(executor, "remove_authorized", uncertain)
    code, _, err = call(case, confirm=case[2])
    assert code == 3 and "PARTIAL" in err and "synthetic disposition" in err
    assert case[1].exists() and (case[0] / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_failed_intent_is_refusal_before_any_artifact_attempt(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    from tikrec.retention_audit import RetentionAudit
    original = RetentionAudit.append
    def reject_intent(self, event, operation_id, **fields):
        if event == "intent":
            raise OSError("synthetic intent sync failure")
        return original(self, event, operation_id, **fields)
    monkeypatch.setattr(RetentionAudit, "append", reject_intent)
    code, _, err = call(case, confirm=case[2])
    assert code == 1 and "REFUSED" in err
    assert "Audit intent durability was not confirmed" in err
    assert "No deletion operation was started" in err
    assert case[1].exists() and (case[0] / "alpha.mp4").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows exact-object deletion only")
def test_interrupt_after_intent_reports_failed_with_code_3(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    import tikrec.retention_delete_cli as cli
    original = cli.execute_retention
    def injected(*args, **kwargs):
        def interrupt(_path):
            raise KeyboardInterrupt()
        return original(*args, before_mutation=interrupt, **kwargs)
    monkeypatch.setattr(cli, "execute_retention", injected)
    code, _, err = call(case, confirm=case[2])
    assert code == 3 and "FAILED" in err and "Operation ID:" in err
    assert case[1].exists() and events(case[5])[-1]["event"] == "failed"


@pytest.mark.skipif(os.name == "nt", reason="native POSIX refusal")
def test_posix_refuses_before_preview_lock_or_audit(tmp_path):
    case = fixture(tmp_path)
    root, parts, session_id, _, _, audit, _ = case
    before = {str(path.relative_to(root)): path.read_bytes()
              for path in root.rglob("*") if path.is_file()}
    code, out, err = call(case, confirm=session_id)
    assert code == 1 and not out
    assert "v0.11 destructive retention is Windows-only" in err
    assert "retention plan remains available" in err
    assert not audit.exists() and not (root / ".tikrec-lifecycle.lock").exists()
    assert before == {str(path.relative_to(root)): path.read_bytes()
                      for path in root.rglob("*") if path.is_file()}
    assert parts.exists()
