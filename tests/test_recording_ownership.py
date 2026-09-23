"""Current public LIVE owner cache behavior under partial controller reads."""

from pathlib import Path
from types import SimpleNamespace

from tikrec.recording_ownership import OwnerCache, page_identity


SESSION_ONE = "00000000-0000-0000-0000-000000000001"
SESSION_TWO = "00000000-0000-0000-0000-000000000002"
PAGE_ONE = "https://www.tiktok.com/@Alpha/live"
PAGE_TWO = "https://www.tiktok.com/@beta/live"
OUTPUT_ONE = str(Path.cwd() / "one.mp4")
PARTS_ONE = str(Path.cwd() / "one.parts")
OUTPUT_TWO = str(Path.cwd() / "two.mp4")
PARTS_TWO = str(Path.cwd() / "two.parts")


def test_partial_snapshot_cannot_erase_same_session_proven_room():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123",
                OUTPUT_ONE, PARTS_ONE)
    controller = SimpleNamespace(ownership=lambda: {
        "current": True, "session_id": SESSION_ONE,
        "source_url": PAGE_ONE, "room_id": None,
    })
    uncertain = cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": True, "available": False}, True,
    )
    assert uncertain is False
    assert cache.get("slot-1").room_id == "123"


def test_current_session_replacement_and_settlement_drop_prior_claim():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123",
                OUTPUT_ONE, PARTS_ONE)
    current = {"current": True, "session_id": SESSION_TWO,
               "source_url": PAGE_TWO, "room_id": "456",
               "output_path": OUTPUT_TWO, "parts_directory": PARTS_TWO}
    controller = SimpleNamespace(ownership=lambda: current)
    assert cache.refresh("slot-1", controller,
                         {"state": "unavailable"},
                         {"active": True, "available": False}, True) is False
    assert cache.get("slot-1").session_id == SESSION_TWO
    assert cache.get("slot-1").page == PAGE_TWO
    assert cache.get("slot-1").room_id == "456"
    assert cache.get("slot-1").output_path == OUTPUT_TWO
    assert cache.get("slot-1").parts_directory == PARTS_TWO
    controller.ownership = lambda: {"current": False}
    assert cache.refresh("slot-1", controller,
                         {"state": "completed", "active": False},
                         {"active": False, "available": True}, False) is False
    assert cache.get("slot-1") is None


def test_partial_new_session_cannot_inherit_old_room_claim():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123",
                OUTPUT_ONE, PARTS_ONE)
    controller = SimpleNamespace(ownership=lambda: {
        "current": True, "session_id": SESSION_TWO, "room_id": None,
    })
    assert cache.refresh("slot-1", controller,
                         {"state": "unavailable"},
                         {"active": True, "available": False}, True) is True
    assert cache.get("slot-1").session_id == SESSION_ONE


def test_first_unreadable_ambiguous_slot_has_unknown_ownership():
    cache = OwnerCache()
    for snapshot in (None, {"current": "unknown"}, {"current": True}):
        controller = SimpleNamespace(ownership=lambda value=snapshot: value)
        assert cache.refresh(
            "slot-1", controller, {"state": "unavailable"},
            {"active": False, "available": False,
             "recovery_reason": "ambiguous_state"}, True,
        ) is True
        assert cache.get("slot-1") is None


def test_explicitly_empty_ambiguous_slot_is_not_an_unknown_owner():
    cache = OwnerCache()
    controller = SimpleNamespace(ownership=lambda: {"current": False})
    assert cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": False, "available": False,
         "recovery_reason": "ambiguous_state"}, True,
    ) is False


def test_invalid_current_snapshot_overrides_earlier_available_health():
    cache = OwnerCache()
    controller = SimpleNamespace(ownership=lambda: {
        "current": True, "session_id": "invalid", "source_url": PAGE_ONE,
        "room_id": "123",
    })
    assert cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": False, "available": True}, False,
    ) is True


def test_invalid_current_snapshot_cannot_clear_or_reuse_prior_owner():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123",
                OUTPUT_ONE, PARTS_ONE)
    controller = SimpleNamespace(ownership=lambda: {
        "current": True, "session_id": None, "source_url": "invalid",
        "room_id": None,
    })
    assert cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": True, "available": False}, True,
    ) is True
    assert cache.get("slot-1").session_id == SESSION_ONE
    assert cache.refresh(
        "slot-1", controller, {"state": "idle", "active": False},
        {"active": False, "available": True}, False,
    ) is True
    assert cache.get("slot-1").session_id == SESSION_ONE


def test_partial_same_session_paths_preserve_accepted_claim():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123",
                OUTPUT_ONE, PARTS_ONE)
    controller = SimpleNamespace(ownership=lambda: {
        "current": True, "session_id": SESSION_ONE,
        "source_url": PAGE_ONE, "room_id": None,
        "output_path": "relative.mp4", "parts_directory": None,
    })
    assert cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": True, "available": False}, True,
    ) is False
    assert cache.get("slot-1").room_id == "123"
    assert cache.get("slot-1").output_path == OUTPUT_ONE
    assert cache.get("slot-1").parts_directory == PARTS_ONE


def test_uncached_current_missing_paths_fails_closed_until_complete_read():
    cache = OwnerCache()
    current = {"current": True, "session_id": SESSION_ONE,
               "source_url": PAGE_ONE, "room_id": "123",
               "output_path": None, "parts_directory": PARTS_ONE}
    controller = SimpleNamespace(ownership=lambda: current)
    assert cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": True, "available": False}, True,
    ) is True
    assert cache.get("slot-1").output_path is None
    current["output_path"] = OUTPUT_ONE
    assert cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": True, "available": False}, True,
    ) is False
    assert cache.get("slot-1").output_path == OUTPUT_ONE


def test_new_session_cannot_inherit_prior_local_paths():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123",
                OUTPUT_ONE, PARTS_ONE)
    controller = SimpleNamespace(ownership=lambda: {
        "current": True, "session_id": SESSION_TWO,
        "source_url": PAGE_TWO, "room_id": "456",
        "output_path": None, "parts_directory": None,
    })
    assert cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": True, "available": False}, True,
    ) is True
    assert cache.get("slot-1").session_id == SESSION_TWO
    assert cache.get("slot-1").output_path is None
    assert cache.get("slot-1").parts_directory is None


def test_same_session_path_disagreement_keeps_prior_and_fails_closed():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123",
                OUTPUT_ONE, PARTS_ONE)
    controller = SimpleNamespace(ownership=lambda: {
        "current": True, "session_id": SESSION_ONE,
        "source_url": PAGE_ONE, "room_id": "123",
        "output_path": OUTPUT_TWO, "parts_directory": PARTS_TWO,
    })
    assert cache.refresh(
        "slot-1", controller, {"state": "unavailable"},
        {"active": True, "available": False}, True,
    ) is True
    assert cache.get("slot-1").output_path == OUTPUT_ONE
    assert cache.get("slot-1").parts_directory == PARTS_ONE


def test_newer_empty_ownership_releases_after_worker_settles_between_reads():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123",
                OUTPUT_ONE, PARTS_ONE)
    controller = SimpleNamespace(
        ownership=lambda: {"current": False},
        health=lambda: {"active": False, "available": True},
    )
    assert cache.refresh(
        "slot-1", controller, {"state": "failed", "active": True},
        {"active": True, "available": False}, True,
    ) is False
    assert cache.get("slot-1") is None
