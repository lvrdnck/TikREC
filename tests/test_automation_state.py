"""Strict atomic persistence tests for automatic recording state."""

from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tikrec.automation_state import (
    AutomationState,
    AutomationStateError,
    AutomationStateStore,
    PendingAutomaticStart,
)


def _claim(tmp_path: Path) -> PendingAutomaticStart:
    output = tmp_path / "creator-20260922-120000.mp4"
    return PendingAutomaticStart(
        "creator", "123", str(output), str(tmp_path / "creator-20260922-120000.parts")
    )


def test_absent_state_is_empty_and_complete_state_round_trips(tmp_path: Path):
    store = AutomationStateStore(tmp_path / "automation.json")
    assert store.load() == AutomationState()
    state = AutomationState((("creator", "123"),), _claim(tmp_path))
    store.save(state)
    assert store.load() == state
    document = json.loads(store.path.read_text(encoding="utf-8"))
    assert document == {
        "schema_version": 1,
        "consumed_rooms": {"creator": "123"},
        "pending_claim": {
            "creator": "creator",
            "room_id": "123",
            "output_path": str(tmp_path / "creator-20260922-120000.mp4"),
            "parts_directory": str(tmp_path / "creator-20260922-120000.parts"),
            "previous_session_id": None,
        },
    }


@pytest.mark.parametrize("document", [
    [],
    {"schema_version": 2, "consumed_rooms": {}, "pending_claim": None},
    {"schema_version": 1, "consumed_rooms": [] , "pending_claim": None},
    {"schema_version": 1, "consumed_rooms": {"Creator": "123"}, "pending_claim": None},
    {"schema_version": 1, "consumed_rooms": {"creator": "00123"}, "pending_claim": None},
    {"schema_version": 1, "consumed_rooms": {}, "pending_claim": {}},
    {"schema_version": 1, "consumed_rooms": {}, "pending_claim": {
        "creator": "creator", "room_id": "123", "output_path": "relative.mp4",
        "parts_directory": "relative.parts",
    }},
    {"schema_version": 1, "consumed_rooms": {}, "pending_claim": None,
     "signed_url": "https://cdn.test/live.flv?secret=hidden"},
])
def test_invalid_or_unknown_state_is_preserved_with_fixed_error(
    tmp_path: Path, document
):
    path = tmp_path / "automation.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    original = path.read_bytes()
    with pytest.raises(AutomationStateError) as failure:
        AutomationStateStore(path).load()
    assert path.read_bytes() == original
    assert "secret" not in str(failure.value)


@pytest.mark.parametrize("body", [
    "{",
    '{"schema_version":1,"schema_version":1,"consumed_rooms":{},"pending_claim":null}',
    '{"schema_version":1,"consumed_rooms":{"creator":"1","creator":"2"},"pending_claim":null}',
    "\udcff",
])
def test_malformed_duplicate_or_invalid_text_is_rejected(tmp_path: Path, body: str):
    path = tmp_path / "automation.json"
    path.write_text(body, encoding="utf-8", errors="surrogatepass")
    with pytest.raises(AutomationStateError):
        AutomationStateStore(path).load()


def test_failed_atomic_replace_keeps_previous_committed_state(tmp_path: Path):
    store = AutomationStateStore(tmp_path / "automation.json")
    original = AutomationState((("creator", "123"),))
    store.save(original)
    with patch("tikrec.automation_state.os.replace", side_effect=OSError("secret")):
        with pytest.raises(OSError):
            store.save(AutomationState((("creator", "456"),)))
    assert store.load() == original
    assert list(tmp_path.glob("*.partial")) == []


def test_pending_claim_rejects_noncanonical_previous_job_identity(tmp_path: Path):
    invalid = replace(_claim(tmp_path), previous_session_id="not-a-uuid")
    with pytest.raises(AutomationStateError):
        AutomationStateStore(tmp_path / "automation.json").save(
            AutomationState(pending_claim=invalid)
        )


def test_state_never_serializes_transport_or_credentials(tmp_path: Path):
    store = AutomationStateStore(tmp_path / "automation.json")
    store.save(AutomationState((("creator", "123"),), _claim(tmp_path)))
    text = store.path.read_text(encoding="utf-8")
    assert all(word not in text for word in ("cdn", "signed", "cookie", "token"))
