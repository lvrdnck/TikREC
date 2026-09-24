"""Offline one-session destructive retention over synthetic eligible evidence."""

import json
import uuid
from pathlib import Path

import pytest

from tests.test_retention_plan import NOW, inspect, session
from tikrec.configuration import Configuration, ConfigurationStore
from tikrec.job_state import JobState, JobStateStore
from tikrec.retention_execute import execute_retention
from tikrec.retention_plan import plan_retention


def fixture(tmp_path):
    """Keep audit and durable job stores outside the selected recording root."""
    root = tmp_path / "recordings"
    root.mkdir()
    parts = session(root, "alpha")
    session_id = json.loads((parts / "session.json").read_text())["session_id"]
    config = ConfigurationStore(tmp_path / "configuration.json")
    config.save(Configuration(retention_max_age_days=1))
    jobs = (tmp_path / "job.json", tmp_path / "job-2.json")
    audit = tmp_path / "audit" / "root.jsonl"
    def run(**overrides):
        args = dict(audit_path=audit, job_paths=jobs, clock=lambda: NOW,
                    media_inspector=inspect)
        args.update(overrides)
        return execute_retention(root, session_id, config, **args)
    return root, parts, session_id, config, jobs, audit, run


def events(path):
    """Read only complete durable JSONL records for assertions."""
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_exact_one_session_order_and_external_audit(tmp_path):
    root, parts, session_id, _, _, audit, run = fixture(tmp_path)
    other = session(root, "beta", creator="beta")
    unrelated = root / "notes.txt"
    unrelated.write_text("keep")
    order = []
    run(before_mutation=lambda path: order.append(path))
    assert not parts.exists() and not (root / "alpha.mp4").exists()
    assert other.exists() and (root / "beta.mp4").exists()
    assert unrelated.read_text() == "keep"
    assert [path.name for path in order][-3:] == ["session.json", "alpha.parts", "alpha.mp4"]
    records = events(audit)
    assert records[0]["event"] == "intent" and records[-1]["event"] == "completed"
    assert records[0]["session_id"] == session_id
    assert [record["event"] for record in records[1:-1]] == [
        event for _ in order for event in ("attempt", "deleted")]
    assert [record["path"] for record in records if record["event"] == "deleted"] == [
        str(path.relative_to(root)) for path in order]
    assert "https://" not in audit.read_text() and "signed" not in audit.read_text()


@pytest.mark.parametrize("change", ["disabled", "protected", "young", "wrong", "ambiguous"])
def test_fresh_eligibility_refuses_without_deletion(tmp_path, change):
    root, parts, session_id, config, _, audit, run = fixture(tmp_path)
    # An earlier eligible plan is informational and never passed to the executor.
    assert plan_retention(root, config.load(), clock=lambda: NOW,
                          media_inspector=inspect)["sessions"][0]["classification"] == "eligible"
    if change == "disabled":
        config.save(Configuration())
    elif change == "protected":
        config.save(Configuration(retention_max_age_days=1,
                                  retention_protected_creators=("alpha",)))
    elif change == "young":
        config.save(Configuration(retention_max_age_days=100))
    elif change == "ambiguous":
        (root / "conflict.parts").mkdir()
    with pytest.raises(ValueError):
        if change == "wrong":
            execute_retention(root, str(uuid.uuid4()), config, audit_path=audit,
                              job_paths=(tmp_path / "job.json", tmp_path / "job-2.json"),
                              clock=lambda: NOW, media_inspector=inspect)
        else:
            run()
    assert parts.exists() and (root / "alpha.mp4").exists()
    assert not audit.exists()


@pytest.mark.parametrize("slot,state", [(0, "recording"), (1, "recording"),
                                         (0, "completed")])
def test_any_service_job_reference_blocks(tmp_path, slot, state):
    root, parts, session_id, _, jobs, audit, run = fixture(tmp_path)
    job = JobState(session_id=session_id, source_url="https://www.tiktok.com/@alpha/live",
                   output_path=str(root / "alpha.mp4"), parts_directory=str(parts),
                   started_at=1000, state=state, ended_at=1010 if state == "completed" else None)
    JobStateStore(jobs[slot]).save(job)
    with pytest.raises(ValueError, match="durable service job"):
        run()
    assert parts.exists() and not audit.exists()


def test_malformed_job_blocks_and_unrelated_settled_job_does_not(tmp_path):
    root, parts, _, _, jobs, audit, run = fixture(tmp_path)
    jobs[1].write_text("{")
    with pytest.raises(ValueError):
        run()
    assert parts.exists() and not audit.exists()
    jobs[1].unlink()
    unrelated = JobState(session_id=str(uuid.uuid4()),
                         source_url="https://www.tiktok.com/@beta/live",
                         output_path=str(root / "beta.mp4"),
                         parts_directory=str(root / "beta.parts"),
                         started_at=1000, state="completed", ended_at=1010)
    JobStateStore(jobs[1]).save(unrelated)
    run()
    assert not parts.exists()


def test_service_job_path_reference_blocks_even_with_another_uuid(tmp_path):
    root, parts, _, _, jobs, audit, run = fixture(tmp_path)
    job = JobState(session_id=str(uuid.uuid4()),
                   source_url="https://www.tiktok.com/@beta/live",
                   output_path=str(root / "alpha.mp4"),
                   parts_directory=str(parts),
                   started_at=1000, state="completed", ended_at=1010)
    JobStateStore(jobs[0]).save(job)
    with pytest.raises(ValueError, match="durable service job"):
        run()
    assert parts.exists() and not audit.exists()


def test_audit_intent_failure_and_inside_root_preserve_all(tmp_path, monkeypatch):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    from tikrec.retention_audit import RetentionAudit
    def fail(*_args, **_kwargs):
        raise OSError("injected audit failure")
    monkeypatch.setattr(RetentionAudit, "append", fail)
    with pytest.raises(OSError):
        run()
    assert parts.exists() and (root / "alpha.mp4").exists()
    with pytest.raises(ValueError, match="outside recording root"):
        run(audit_path=root / "audit.jsonl")
    assert parts.exists()


def test_durable_intent_precedes_first_mutation(tmp_path):
    root, _, _, _, _, audit, run = fixture(tmp_path)
    observed = []
    def witness(path):
        if not observed:
            assert path.exists()
            records = events(audit)
            assert len(records) == 1 and records[0]["event"] == "intent"
            observed.append(True)
    run(before_mutation=witness)
    assert observed


def test_policy_change_during_audit_attempt_stops_before_unlink(tmp_path, monkeypatch):
    root, parts, _, config, _, audit, run = fixture(tmp_path)
    from tikrec.retention_audit import RetentionAudit
    original = RetentionAudit.append
    def change_after_attempt(self, event, operation_id, **fields):
        original(self, event, operation_id, **fields)
        if event == "attempt":
            config.save(Configuration(retention_max_age_days=1,
                                      retention_protected_creators=("alpha",)))
    monkeypatch.setattr(RetentionAudit, "append", change_after_attempt)
    with pytest.raises(ValueError, match="policy"):
        run()
    assert parts.exists() and (root / "alpha.mp4").exists()
    assert [record["event"] for record in events(audit)] == ["intent", "attempt", "failed"]


def test_invalid_clock_after_intent_stops_before_unlink(tmp_path):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    calls = 0
    def changing_clock():
        nonlocal calls
        calls += 1
        return float("nan") if calls >= 4 else NOW
    with pytest.raises(ValueError, match="clock"):
        run(clock=changing_clock)
    assert parts.exists() and (root / "alpha.mp4").exists()
    assert events(audit)[-1]["event"] == "failed"


def test_partial_failure_preserves_mp4_and_refuses_blind_resume(tmp_path):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    observed = []
    def fail_second(path):
        observed.append(path)
        if len(observed) == 2:
            raise OSError("injected deletion failure")
    with pytest.raises(OSError):
        run(before_mutation=fail_second)
    assert not observed[0].exists() and observed[1].exists()
    assert (root / "alpha.mp4").exists()
    assert events(audit)[-1]["event"] == "failed"
    with pytest.raises(ValueError):
        run()
    assert (root / "alpha.mp4").exists()


@pytest.mark.parametrize("change", ["new_file", "replacement", "new_claimant",
                                     "protected", "rule", "hardlink"])
def test_revalidation_stops_on_change(tmp_path, change):
    root, parts, _, config, _, audit, run = fixture(tmp_path)
    target = next(parts.glob("part-*.flv"))
    def alter(path):
        if change == "new_file":
            (parts / "surprise.bin").write_bytes(b"new")
        elif change == "replacement":
            target.unlink()
            target.write_bytes(b"replacement")
        elif change == "new_claimant":
            session(root, "late")
        elif change == "protected":
            config.save(Configuration(retention_max_age_days=1,
                                      retention_protected_creators=("alpha",)))
        elif change == "rule":
            config.save(Configuration(retention_max_age_days=2))
        elif change == "hardlink":
            (parts / "other.flv").hardlink_to(target)
    with pytest.raises((ValueError, FileExistsError)):
        run(before_mutation=alter)
    assert (root / "alpha.mp4").exists()
    assert events(audit)[-1]["event"] == "failed"


def test_changed_volume_and_reparse_evidence_stop_before_delete(tmp_path, monkeypatch):
    root, parts, _, _, _, audit, run = fixture(tmp_path)
    import tikrec.retention_authorization as authorization
    original_volume = authorization.local_volume
    media = next(parts.glob("part-*.flv"))
    def move_volume(path):
        monkeypatch.setattr(authorization, "local_volume", lambda candidate:
                            None if candidate == media else original_volume(candidate))
    with pytest.raises(ValueError):
        run(before_mutation=move_volume)
    assert media.exists() and (root / "alpha.mp4").exists()
    monkeypatch.undo()
    from types import SimpleNamespace
    original_lstat = Path.lstat
    def redirect(path):
        details = original_lstat(path)
        if path != media:
            return details
        values = {name: getattr(details, name) for name in
                  ("st_mode", "st_size", "st_dev", "st_ino", "st_nlink",
                   "st_mtime_ns", "st_ctime_ns")}
        values["st_file_attributes"] = 0x400
        return SimpleNamespace(**values)
    with pytest.raises(ValueError):
        run(before_mutation=lambda _path: monkeypatch.setattr(Path, "lstat", redirect))
    assert media.exists() and (root / "alpha.mp4").exists()
