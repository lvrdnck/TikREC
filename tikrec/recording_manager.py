"""Bounded service ownership for independent recording controllers."""

from __future__ import annotations

from pathlib import Path
from threading import Lock, Thread
from uuid import UUID

from .recording import RecordingBusy
from .recording_ownership import OwnerCache, page_identity, same_page, same_room
from .recording_safety import normalize_live_url
from .tiktok_identity import canonical_room_id


RECORDING_CAPACITY = 2


class RecordingAmbiguous(ValueError):
    """A legacy singular operation cannot safely choose one recording."""


class RecordingNotFound(ValueError):
    """A requested session is not active in any service slot."""


class RecordingDuplicate(RecordingBusy):
    """Another current slot already owns this public LIVE page or room."""


class RecordingManager:
    """Atomically allocate and control a fixed set of independent controllers."""

    def __init__(self, controllers: tuple[object, ...]) -> None:
        if not controllers or len(controllers) > RECORDING_CAPACITY:
            raise ValueError("recording manager requires one or two controllers")
        self._controllers = tuple(controllers)
        self._lock = Lock()
        self._closed = False
        # Keep page/expected-room claims while a worker may not publish status yet.
        self._owners = OwnerCache()

    @property
    def controllers(self) -> tuple[object, ...]:
        """Expose immutable controller ownership for wiring and deterministic tests."""
        return self._controllers

    def health(self) -> dict:
        """Report capacity without flattening independent recovery/error state."""
        from . import __version__

        with self._lock:
            entries = self._entries()
            slot_health = [self._health(entry[0], entry[2]) for entry in entries]
            available = 0 if self._closed else sum(
                item.get("available") is True for item in slot_health
            )
            active = sum(item.get("active") is True for item in slot_health)
            return {
                "service": "tikrec", "version": __version__,
                "capacity": len(self._controllers), "active_count": active,
                "available_slots": available, "available": available > 0,
                "active": active > 0, "shutting_down": self._closed,
                "slots": slot_health,
            }

    def recordings(self) -> dict:
        """Return one sanitized snapshot per stable service slot."""
        with self._lock:
            entries = self._entries()
            slots = [_with_slot(entry[0], entry[1]) for entry in entries]
            available = 0 if self._closed else sum(
                entry[2].get("available") is True for entry in entries
            )
            return {
                "capacity": len(self._controllers),
                "active_count": sum(item.get("active") is True for item in slots),
                "available_slots": available,
                "slots": slots,
            }

    def jobs(self) -> tuple[dict, ...]:
        """Return all current job snapshots for automation reconciliation."""
        with self._lock:
            return tuple(dict(controller.status()) for controller in self._controllers)

    def prior_session_id_for_start(self) -> str | None:
        """Fingerprint the slot a new atomic claim would currently select."""
        with self._lock:
            selected = next(
                (entry for entry in self._entries()
                 if entry[2].get("available") is True), None
            )
            if selected is None:
                raise RecordingBusy("recording capacity is unavailable")
            status = selected[1]
            return None if status.get("state") == "idle" else _session_id(
                status.get("session_id")
            )

    def status(self) -> dict:
        """Preserve singular status only when one current owner is unambiguous."""
        with self._lock:
            entries = self._entries()
            owned = [entry for entry in entries if _owns_current_work(entry[1], entry[2])]
            if len(owned) > 1:
                raise RecordingAmbiguous("multiple recordings require aggregate status")
            if owned:
                return _with_slot(owned[0][0], owned[0][1])
            non_idle = [entry for entry in entries if entry[1].get("state") != "idle"]
            if not non_idle:
                return _with_slot(entries[0][0], entries[0][1])
            latest = max(non_idle, key=lambda entry: _started_at(entry[1]))
            return _with_slot(latest[0], latest[1])

    def start(self, url: str, output: str, **options) -> dict:
        """Atomically claim one free slot without duplicating a current LIVE."""
        page = normalize_live_url(url)
        canonical_page = page_identity(page)
        expected_room = options.get("expected_room_id")
        if expected_room is not None:
            expected_room = canonical_room_id(expected_room)
            options["expected_room_id"] = expected_room
        output_path = Path(output)
        parts_path = output_path.with_name(f"{output_path.stem}.parts")
        with self._lock:
            if self._closed:
                raise RecordingBusy("service is shutting down")
            entries = self._entries()
            if any(health.get("ownership_unknown") for _, _, health, _ in entries):
                raise RecordingBusy("recording ownership unavailable")
            for slot_id, status, health, _ in entries:
                if _owns_current_work(status, health):
                    owner = self._owners.get(slot_id)
                    if _same_path(status.get("output_path"), output_path):
                        raise ValueError("output is already owned by another recording")
                    if _same_path(status.get("parts_directory"), parts_path):
                        raise ValueError("retained parts are already owned by another recording")
                    if same_page(status.get("source_url"), canonical_page) or (
                        owner is not None and owner.page == canonical_page
                    ):
                        raise RecordingDuplicate("public LIVE page already owned")
                    if expected_room is not None and (
                        same_room(status.get("room_id"), expected_room)
                        or (owner is not None and owner.room_id == expected_room)
                    ):
                        raise RecordingDuplicate("public LIVE room already owned")
            selected = next(
                (entry for entry in entries if entry[2].get("available") is True), None
            )
            if selected is None:
                raise RecordingBusy("recording capacity is unavailable")
            slot_id, _, _, controller = selected
            started = controller.start(page, output, **options)
            # The lock keeps both claims atomic with the accepted session.
            self._owners.claim(slot_id, _session_id(started.get("session_id")),
                               canonical_page, expected_room)
            return _with_slot(slot_id, started)

    def stop(self, session_id: str | None = None) -> dict:
        """Stop one explicit session, or the sole current owner for legacy calls."""
        if session_id is not None:
            session_id = _session_id(session_id)
        with self._lock:
            entries = self._entries()
            owned = [entry for entry in entries if _owns_current_work(*entry[1:3])]
            if session_id is None:
                if len(owned) > 1:
                    raise RecordingAmbiguous("multiple recordings require a session ID")
                if not owned:
                    return self.status_unlocked(entries)
                selected = owned[0]
            else:
                selected = next(
                    (entry for entry in owned if entry[1].get("session_id") == session_id),
                    None,
                )
                if selected is None:
                    raise RecordingNotFound("session is not active")
            return _with_slot(selected[0], selected[3].stop())

    def shutdown(self) -> None:
        """Signal every controller concurrently, then wait for all finalizers."""
        with self._lock:
            self._closed = True
            workers = [Thread(target=controller.shutdown,
                              name=f"tikrec-slot-{index}-shutdown", daemon=False)
                       for index, controller in enumerate(self._controllers, 1)]
            for worker in workers:
                worker.start()
        for worker in workers:
            worker.join()

    def status_unlocked(self, entries) -> dict:
        """Choose the latest settled result while the manager lock is already held."""
        non_idle = [entry for entry in entries if entry[1].get("state") != "idle"]
        selected = max(non_idle, key=lambda entry: _started_at(entry[1])) if non_idle else entries[0]
        return _with_slot(selected[0], selected[1])

    def _entries(self):
        entries = []
        for index, controller in enumerate(self._controllers, 1):
            status = self._safe_status(controller)
            health = self._safe_health(controller)
            slot_id = f"slot-{index}"
            uncertain = self._owners.refresh(
                slot_id, controller, status, health, _owns_current_work(status, health)
            )
            if status.get("state") == "unavailable":
                health = {**health, "available": False}
            if uncertain:
                health = {**health, "ownership_unknown": True}
            entries.append((slot_id, status, health, controller))
        if any(health.get("ownership_unknown") for _, _, health, _ in entries):
            # An unidentified current owner makes every new allocation unsafe.
            entries = [(slot, status, {**health, "available": False}, controller)
                       for slot, status, health, controller in entries]
        return entries

    def _health(self, slot_id, value):
        return {"slot_id": slot_id, **{
            key: value.get(key) for key in (
                "available", "active", "shutting_down",
                "recovery_state", "recovery_reason",
            )
        }}

    @staticmethod
    def _safe_status(controller):
        try:
            value = dict(controller.status())
        except Exception:
            value = {"state": "unavailable", "active": False,
                     "error": "controller_state_unavailable"}
        return value

    @staticmethod
    def _safe_health(controller):
        try:
            value = controller.health()
        except Exception:
            return {"available": False, "active": False,
                    "recovery_state": "failed", "recovery_reason": "ambiguous_state"}
        return value if isinstance(value, dict) else {"available": False, "active": False}


def _with_slot(slot_id: str, status: dict) -> dict:
    return {**dict(status), "slot_id": slot_id}


def _owns_current_work(status: dict, health: dict) -> bool:
    return (status.get("active") is True
            or (health.get("available") is False and status.get("state") != "idle"))


def _started_at(status: dict) -> float:
    value = status.get("started_at")
    return float(value) if type(value) in {int, float} else float("-inf")


def _session_id(value: object) -> str:
    try:
        canonical = str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("session_id must be a canonical UUID") from None
    if value != canonical:
        raise ValueError("session_id must be a canonical UUID")
    return canonical


def _same_path(value: object, candidate: Path) -> bool:
    """Compare native paths without requiring candidate targets to exist."""
    if not isinstance(value, str):
        return False
    try:
        return Path(value).resolve(strict=False) == candidate.resolve(strict=False)
    except OSError:
        # If parent inspection fails, retain the lexical native-path guard.
        return Path(value) == candidate
