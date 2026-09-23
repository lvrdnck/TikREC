"""Current public LIVE owner cache behavior under partial controller reads."""

from types import SimpleNamespace

from tikrec.recording_ownership import OwnerCache, page_identity


SESSION_ONE = "00000000-0000-0000-0000-000000000001"
SESSION_TWO = "00000000-0000-0000-0000-000000000002"
PAGE_ONE = "https://www.tiktok.com/@Alpha/live"
PAGE_TWO = "https://www.tiktok.com/@beta/live"


def test_partial_snapshot_cannot_erase_same_session_proven_room():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123")
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
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123")
    current = {"current": True, "session_id": SESSION_TWO,
               "source_url": PAGE_TWO, "room_id": "456"}
    controller = SimpleNamespace(ownership=lambda: current)
    assert cache.refresh("slot-1", controller,
                         {"state": "unavailable"},
                         {"active": True, "available": False}, True) is False
    assert cache.get("slot-1").session_id == SESSION_TWO
    assert cache.get("slot-1").page == PAGE_TWO
    assert cache.get("slot-1").room_id == "456"
    controller.ownership = lambda: {"current": False}
    assert cache.refresh("slot-1", controller,
                         {"state": "completed", "active": False},
                         {"active": False, "available": True}, False) is False
    assert cache.get("slot-1") is None


def test_partial_new_session_cannot_inherit_old_room_claim():
    cache = OwnerCache()
    cache.claim("slot-1", SESSION_ONE, page_identity(PAGE_ONE), "123")
    controller = SimpleNamespace(ownership=lambda: {
        "current": True, "session_id": SESSION_TWO, "room_id": None,
    })
    assert cache.refresh("slot-1", controller,
                         {"state": "unavailable"},
                         {"active": True, "available": False}, True) is True
    assert cache.get("slot-1").session_id == SESSION_ONE
