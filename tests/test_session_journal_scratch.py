"""Durable scratch intent survives reopen without granting filesystem adoption."""

from dataclasses import asdict

import pytest

from tests.session_journal_helpers import journal, queued, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import ArtifactIdentity, JournalError


def owned(store):
    """Create an isolated running task with original H and attempt input binding."""
    selected, _ = queued(store)
    token, owner = uid(), uid()
    claim = store.claim_owned(uid(), token, owner)
    bound = store.bind_owned_inputs(uid(), token, owner, claim["revision"], "a" * 64)
    return selected, token, owner, bound


def reservation(store, selected, token, owner, revision):
    """Bind synthetic fixture data to the actual accepted H record."""
    row = store.owned_attempt(token)
    parent = asdict(selected.root)
    workspace = ArtifactIdentity(selected.root.volume,
        selected.root.components + (f".tikrec-attempt-{token}",))
    evidence = {"catalog_id": store.catalog_id, "session_id": selected.session_id,
                "h_operation": row["h_operation"],
                "h_revision": row["h_revision"], "seal_hash": row["seal_hash"],
                "marker_hash": row["marker_hash"],
                "workspace_path": rf"C:\capture\.tikrec-attempt-{token}",
                "parent": parent, "workspace": asdict(workspace),
                "artifacts": [{"name": "candidate.mp4", "role": "candidate", "required": True},
                              {"name": "concat.txt", "role": "helper", "required": False}]}
    return store.reserve_scratch(uid(), token, owner, revision, evidence)


def test_reservation_intent_is_inspectable_after_reopen_but_cannot_be_adopted(tmp_path):
    store = journal(tmp_path)
    selected, token, owner, bound = owned(store)
    receipt = reservation(store, selected, token, owner, bound["revision"])
    assert receipt["state"] == "reserved"
    reopened = SessionJournal(store.path, store.catalog_id)
    row = reopened.owned_attempt(token)
    assert row["scratch"]["state"] == "reserved"
    assert row["scratch"]["workspace_identity"] is None
    assert row["scratch"]["candidate"] is None
    assert reopened.status()["units"] and reopened.status()["tasks"][0]["state"] == "running"
    with pytest.raises(JournalError, match="stale owned attempt"):
        reopened.reserve_scratch(uid(), token, owner, bound["revision"], row["scratch"]["intent"])


def test_arbitrary_scope_and_collision_retarget_are_refused(tmp_path):
    store = journal(tmp_path)
    selected, token, owner, bound = owned(store)
    row = store.owned_attempt(token)
    parent = asdict(selected.root)
    workspace = ArtifactIdentity(selected.root.volume,
        selected.root.components + (f".tikrec-attempt-{token}",))
    evidence = {"catalog_id": store.catalog_id, "session_id": selected.session_id,
                "h_operation": row["h_operation"],
                "h_revision": row["h_revision"], "seal_hash": row["seal_hash"],
                "marker_hash": row["marker_hash"], "workspace_path": rf"C:\capture\other",
                "parent": parent, "workspace": asdict(workspace),
                "artifacts": [{"name": "candidate.mp4", "role": "candidate", "required": True}]}
    with pytest.raises(JournalError, match="caller-selected scratch path"):
        store.reserve_scratch(uid(), token, owner, bound["revision"], evidence)
    assert store.scratch(token) is None


def test_held_failure_is_permanent_and_keeps_running_unit(tmp_path):
    store = journal(tmp_path)
    selected, token, owner, bound = owned(store)
    receipt = reservation(store, selected, token, owner, bound["revision"])
    held = store.hold_scratch(uid(), token, owner, receipt["revision"],
                              {"first": "injected unknown create outcome", "secondary": []})
    reopened = SessionJournal(store.path, store.catalog_id)
    row = reopened.owned_attempt(token)
    assert row["scratch"]["state"] == "held"
    assert row["scratch"]["hold_reason"]["first"] == "injected unknown create outcome"
    assert row["scratch"]["candidate"] is None
    assert reopened.status()["tasks"][0]["state"] == "running"
    assert len(reopened.status()["units"]) == 1
    with pytest.raises(JournalError):
        reopened.hold_scratch(uid(), token, owner, held["revision"],
                              {"first": "second owner", "secondary": []})
