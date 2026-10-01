"""Mediated preview consent, policy conflicts and authoritative state paths."""

import pytest

from tests.managed_fixture import managed_fixture, service_action, inspect, NOW
from tikrec.managed_retention import preview, delete, promote_policy


def test_preview_veto_and_exact_confirmation(managed_fixture):
    def run(authority, _):
        options = dict(clock=lambda: NOW, media_inspector=inspect)
        session_id = managed_fixture[5]
        body = preview(authority, dict(session_id=session_id), **options)
        with pytest.raises(ValueError, match="confirmation"):
            delete(authority, dict(session_id=session_id, confirm="other",
                                   preview_digest=body["preview_digest"]), **options)
        result = delete(authority, dict(session_id=session_id, confirm=session_id,
                                       preview_digest="0" * 64), **options)
        assert result["code"] == 1 and "after owner preview" in result["stderr"]
        assert not (authority.state / "retention-audit").exists()
        result = delete(authority, dict(session_id=session_id, confirm=session_id,
                                       preview_digest=body["preview_digest"]), **options)
        assert result["code"] == 0 and "COMPLETE" in result["stdout"]
    service_action(managed_fixture, run)


def test_policy_promotion_is_bounded_and_blocked_during_retention(managed_fixture):
    def run(authority, _):
        assert promote_policy(authority, dict(action="protect", value="alpha"))[
            "retention_protected_creators"] == ["alpha"]
        assert promote_policy(authority, dict(action="unprotect", value="alpha"))[
            "retention_protected_creators"] == []
        assert promote_policy(authority, dict(action="age", value=None))["retention_max_age_days"] is None
        assert promote_policy(authority, dict(action="age", value=2))["retention_max_age_days"] == 2
        with authority.retention_scope(authority.root):
            with pytest.raises(ValueError, match="busy"):
                promote_policy(authority, dict(action="age", value=1))
        for body in [dict(action="root", value="/tmp"), dict(action="age", value=True),
                     dict(action="age", value=0), dict(action="age", value=1, root="/tmp")]:
            with pytest.raises(ValueError):
                promote_policy(authority, body)
    service_action(managed_fixture, run)


def test_authoritative_job_policy_and_audit_paths_cannot_be_overridden(managed_fixture):
    def run(authority, _):
        for config, jobs, audit in [(authority.state / "other.json", None, None),
                                   (authority.config_path, (), None),
                                   (authority.config_path, None, authority.state / "other-audit")]:
            with pytest.raises(ValueError, match="authoritative"):
                authority.check_retention_inputs(config, jobs, audit)
    service_action(managed_fixture, run)
