"""Strict typed input validation and explicit evidence-proof limits."""

from dataclasses import replace

import pytest

from tests.session_journal_helpers import capture, intent, journal, rows, seal, uid
from tikrec.session_journal_types import ArtifactIdentity, JournalError, ReservationReleaseProof


@pytest.mark.parametrize("changes", [{"session_id": "bad"}, {"raw_copy": 1},
                                    {"expected_room": "001"}, {"creator": "Gracie"},
                                    {"automatic_claim": "bad"}, {"started_at": float('nan')},
                                    {"output_path": "relative.mp4"}, {"parts_path": r"C:\x.parts"},
                                    {"root": None}, {"creator": "signed?secret"}])
def test_invalid_intent_rejected_before_any_state_change(tmp_path, changes):
    store = journal(tmp_path)
    before = rows(store)
    with pytest.raises((JournalError, ValueError)):
        store.reserve(uid(), replace(intent(), **changes))
    assert rows(store) == before


@pytest.mark.parametrize("components", [(), ("..",), ("Upper",), ("a/b",), ("a\\b",), ("",)])
def test_native_identity_requires_canonical_nonempty_components(components):
    with pytest.raises(JournalError):
        ArtifactIdentity("volume", components)


def test_room_admission_mismatch_and_revision_do_not_mutate(tmp_path):
    store = journal(tmp_path)
    selected = intent()
    accepted = store.reserve(uid(), selected)
    before = rows(store)
    with pytest.raises(JournalError):
        store.admit(uid(), selected.session_id, accepted["generation"], 1, "456")
    with pytest.raises(JournalError):
        store.admit(uid(), selected.session_id, accepted["generation"], 99, "123")
    assert rows(store) == before
    store.admit(uid(), selected.session_id, accepted["generation"], 1, "123")
    before = rows(store)
    with pytest.raises(JournalError):
        store.settle_reservation(uid(), selected.session_id, 1, 2,
                                 ReservationReleaseProof(selected.session_id, 1, "thread-absent"))
    assert rows(store) == before


def test_seal_must_bind_owned_inventory_and_hashes(tmp_path):
    store = journal(tmp_path)
    selected, binding = capture(store)
    binding = store.capture_intent(uid(), selected.session_id, binding["generation"],
                                   binding["revision"], closing=True)
    original = seal(selected, binding)
    outside = replace(original.artifacts[0], identity=ArtifactIdentity("other-volume", ("part-0001.flv",)))
    before = rows(store)
    with pytest.raises(JournalError):
        store.handoff(uid(), selected.session_id, binding["generation"], binding["revision"],
                      replace(original, artifacts=(outside,) + original.artifacts[1:]))
    with pytest.raises(JournalError):
        replace(original.artifacts[1], control_hash=None)
    with pytest.raises(JournalError):
        replace(original, artifacts=original.artifacts + original.artifacts[:1])
    assert rows(store) == before
