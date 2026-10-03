"""Disposable journal fixtures with synthetic native proofs, never real media."""

import sqlite3
import uuid

from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import (ArtifactIdentity, ClosedArtifact, ClosureSeal,
                                        SessionIntent, SettlementProof)


def uid():
    """Create an independent operation/catalog/session/claim identity."""
    return str(uuid.uuid4())


def journal(tmp_path):
    """Initialize a real disposable file-backed catalog under explicit basetemp."""
    return SessionJournal.initialize(tmp_path / "sessions.sqlite3", uid())


def intent(creator="gracie.kf", room="123", name=None, *, raw=True, automatic=True):
    """Use Windows display paths and synthetic canonical keys, not a filesystem proof."""
    sid = uid()
    name = name or sid
    return SessionIntent(sid, creator, room, rf"C:\capture\{name}.mp4",
                         rf"C:\capture\{name}.parts",
                         ArtifactIdentity("volume-1", ("capture",)),
                         ArtifactIdentity("volume-1", ("capture", name + ".mp4")),
                         ArtifactIdentity("volume-1", ("capture", name + ".parts")),
                         raw, 100.0, uid() if automatic else None)


def capture(store, selected=None, *, slot=None):
    """Reserve and admit one caller-proven synthetic room."""
    selected = selected or intent()
    accepted = store.reserve(uid(), selected, slot=slot)
    return selected, store.admit(uid(), selected.session_id, accepted["generation"],
                                 accepted["revision"], selected.expected_room or "999")


def seal(selected, binding):
    """Synthetic closure evidence preserves raw/arrival/control inventory."""
    names = [("part-0001.flv", "flv", None), ("session.json", "manifest", "1" * 64),
             ("connections.jsonl", "connections", "2" * 64)]
    if selected.raw_copy:
        names += [("connection-0001.raw", "raw", None),
                  ("connection-0001.arrivals.jsonl", "arrivals", None)]
    return ClosureSeal(selected.session_id, binding["generation"], selected.expected_room or "999",
                       selected.raw_copy, 150.0, tuple(ClosedArtifact(
                           ArtifactIdentity(selected.parts.volume, selected.parts.components + (name,)),
                           role, 100, "native-stamp", control_hash) for name, role, control_hash in names))


def closing(store, selected=None):
    """Record ordinary closing intent without touching any media."""
    selected, binding = capture(store, selected)
    return selected, store.capture_intent(uid(), selected.session_id, binding["generation"],
                                          binding["revision"], closing=True)


def queued(store, selected=None):
    """Hand off one synthetic closed source to a durable task."""
    selected, binding = closing(store, selected)
    receipt = store.handoff(uid(), selected.session_id, binding["generation"],
                            binding["revision"], seal(selected, binding))
    return selected, receipt


def proof(store, selected, claim):
    """Synthetic publication/exit proof; never create an MP4 or a process."""
    return SettlementProof(selected.session_id, claim["token"],
                           store.session(selected.session_id)["seal_hash"], "proven-child-exit",
                           selected.output, 1000, "3" * 64, "4" * 64)


def rows(store):
    """Compare every durable row across failures, including permanent receipts."""
    with sqlite3.connect(store.path) as connection:
        names = [x[0] for x in connection.execute("SELECT name FROM sqlite_master "
                                                 "WHERE type='table' ORDER BY name")]
        return {name: connection.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
                for name in names}
