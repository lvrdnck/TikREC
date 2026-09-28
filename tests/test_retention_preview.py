"""An exact-target preview is read-only and only vetoes fresh authority."""

import os
from dataclasses import replace

import pytest

from tests.test_retention_execute import fixture
from tests.test_retention_plan import NOW, inspect
from tikrec.retention_execute import execute_retention
from tikrec.retention_preview import prepare_preview


@pytest.mark.skipif(os.name != "nt", reason="Windows preview for destructive retention")
def test_preview_binds_bytes_without_creating_lock_or_audit(tmp_path):
    root, parts, session_id, config, jobs, audit, _ = fixture(tmp_path)
    before = {path: path.read_bytes() for path in (root / "alpha.mp4", *parts.iterdir())}
    preview = prepare_preview(root, session_id, config, job_paths=jobs,
                              clock=lambda: NOW, media_inspector=inspect)
    assert preview.session_id == session_id and preview.creator == "alpha"
    assert preview.file_count == len(before)
    assert preview.total_file_bytes == sum(len(content) for content in before.values())
    assert {path: path.read_bytes() for path in before} == before
    assert not audit.exists() and not (root / ".tikrec-lifecycle.lock").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows preview for destructive retention")
def test_preview_guard_cannot_authorize_a_changed_still_eligible_rule(tmp_path):
    root, parts, session_id, config, jobs, audit, _ = fixture(tmp_path)
    preview = prepare_preview(root, session_id, config, job_paths=jobs,
                              clock=lambda: NOW, media_inspector=inspect)
    config.save(replace(config.load(), retention_max_age_days=2))
    with pytest.raises(ValueError, match="changed after deletion preview"):
        execute_retention(root, session_id, config, audit_path=audit, job_paths=jobs,
                          clock=lambda: NOW, media_inspector=inspect,
                          preview_guard=preview.guard)
    assert parts.exists() and (root / "alpha.mp4").exists() and not audit.exists()


@pytest.mark.skipif(os.name == "nt", reason="native POSIX preview refusal")
def test_posix_preview_refuses_before_lock_or_audit(tmp_path):
    root, parts, session_id, config, jobs, audit, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="POSIX retention is read-only"):
        prepare_preview(root, session_id, config, job_paths=jobs,
                        clock=lambda: NOW, media_inspector=inspect)
    assert parts.exists() and not audit.exists()
    assert not (root / ".tikrec-lifecycle.lock").exists()
