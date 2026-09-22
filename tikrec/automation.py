"""Coordinate one crash-safe automatic start after each monitoring cycle."""

from __future__ import annotations

from threading import Lock

from .automation_state import (
    AutomationState,
    AutomationStateError,
    AutomationStateStore,
    PendingAutomaticStart,
)
from .automation_jobs import (
    job_matches_claim,
    job_matches_observation,
    job_proves_no_claimed_start,
    prior_session_id,
)
from .automation_status import automation_snapshot
from .recording import RecordingBusy
from .tiktok_identity import canonical_room_id


class AutomationCoordinator:
    """Select, claim, and start at most one admitted LIVE per complete cycle."""

    def __init__(self, controller, admission, store: AutomationStateStore) -> None:
        self._controller = controller
        self._admission = admission
        self._store = store
        self._lock = Lock()
        self._stopping = False
        self._operational = True
        self._blocked_reason: str | None = None
        self._state = AutomationState()
        self._latest_cycle_count = 0
        self._selected_creator: str | None = None
        self._started_creator: str | None = None
        self._started_session_id: str | None = None
        self._started_output_path: str | None = None
        self._cycle_results: dict[str, dict] = {}
        self._load_and_reconcile()

    def stop(self) -> None:
        """Prevent all later cycle callbacks from starting a recording."""
        with self._lock:
            self._stopping = True

    def cycle_completed(self, monitoring: dict) -> None:
        """Consume one complete detection cycle and attempt at most one start."""
        with self._lock:
            cycle = monitoring.get("cycle_count")
            if self._stopping or type(cycle) is not int or cycle <= self._latest_cycle_count:
                return
            self._begin_cycle(cycle)
            if not self._operational:
                self._block_live_creators(monitoring)
                return
            rearmed = self._apply_rearm_and_existing_job(monitoring)
            if not self._operational:
                self._block_live_creators(monitoring)
                return
            admitted = self._admission.evaluate(monitoring)
            ready = self._classify(admitted, rearmed)
            if not ready:
                return
            selected = min(ready)
            self._selected_creator = selected
            for creator in ready:
                if creator != selected:
                    self._cycle_results[creator] = _result(
                        "not_selected", "single_slot_selected_other"
                    )
            # Allocate again immediately before claiming; older status paths are advisory.
            refreshed = self._admission.evaluate(monitoring)
            candidate = _creator(refreshed, selected)
            admission = candidate.get("admission", {}) if candidate else {}
            if admission.get("state") != "ready":
                self._cycle_results[selected] = _result(
                    admission.get("state", "blocked"),
                    admission.get("reason") or "admission_unavailable",
                )
                return
            observed = _creator(monitoring, selected)
            self._attempt(selected, observed, admission)

    def snapshot(self, monitoring: dict) -> dict:
        """Add fresh admission plus safe durable/current automation facts."""
        admitted = self._admission.evaluate(monitoring)
        with self._lock:
            return automation_snapshot(
                admitted,
                state=self._state,
                operational=self._operational,
                stopping=self._stopping,
                blocked_reason=self._blocked_reason,
                latest_cycle_count=self._latest_cycle_count,
                cycle_results=self._cycle_results,
                selected_creator=self._selected_creator,
                started_creator=self._started_creator,
                started_session_id=self._started_session_id,
                started_output_path=self._started_output_path,
            )

    def _load_and_reconcile(self) -> None:
        try:
            self._state = self._store.load()
        except (AutomationStateError, OSError):
            self._disable("automation_state_unavailable")
            return
        claim = self._state.pending_claim
        if claim is None:
            return
        try:
            job = self._controller.status()
        except Exception:
            self._disable("automation_state_ambiguous")
            return
        if job_matches_claim(job, claim):
            consumed = self._state.consumed()
            consumed[claim.creator] = claim.room_id
            self._replace_state(consumed, None, "automation_state_ambiguous")
        elif job_proves_no_claimed_start(job, claim):
            self._replace_state(
                self._state.consumed(), None, "automation_state_ambiguous"
            )
        else:
            self._disable("automation_state_ambiguous")

    def _begin_cycle(self, cycle: int) -> None:
        self._latest_cycle_count = cycle
        self._selected_creator = self._started_creator = None
        self._started_session_id = self._started_output_path = None
        self._cycle_results = {}

    def _apply_rearm_and_existing_job(self, monitoring: dict) -> set[str]:
        consumed = self._state.consumed()
        before = dict(consumed)
        rearmed = set()
        try:
            job = self._controller.status()
        except Exception:
            self._disable("automation_state_ambiguous")
            return rearmed
        for item in monitoring.get("creators", []):
            creator = item.get("creator")
            if item.get("state") == "live" and job_matches_observation(job, item):
                consumed[creator] = item["room_id"]
            elif item.get("state") == "offline" and creator in consumed:
                consumed.pop(creator)
                rearmed.add(creator)
        if consumed != before:
            self._replace_state(
                consumed, self._state.pending_claim, "automation_state_unavailable"
            )
        return rearmed

    def _classify(self, monitoring: dict, rearmed: set[str]) -> list[str]:
        ready = []
        consumed = self._state.consumed()
        for item in monitoring.get("creators", []):
            creator = item.get("creator")
            if item.get("state") != "live":
                self._cycle_results[creator] = _result(
                    "rearmed" if creator in rearmed else "not_applicable",
                    "offline_observed" if creator in rearmed else None,
                )
                continue
            room_id = item.get("room_id")
            if consumed.get(creator) == room_id:
                self._cycle_results[creator] = _result(
                    "suppressed", "same_room_consumed"
                )
                continue
            admission = item.get("admission", {})
            if admission.get("state") == "ready":
                ready.append(creator)
                self._cycle_results[creator] = _result("eligible")
            else:
                self._cycle_results[creator] = _result(
                    admission.get("state", "blocked"),
                    admission.get("reason") or "admission_unavailable",
                )
        return ready

    def _attempt(self, creator: str, observation: dict | None, admission: dict) -> None:
        try:
            previous_session = prior_session_id(self._controller.status())
        except Exception:
            self._cycle_results[creator] = _result(
                "blocked", "controller_state_unavailable"
            )
            return
        try:
            room_id = canonical_room_id(observation["room_id"])
            claim = PendingAutomaticStart(
                creator, room_id, admission["output_path"],
                admission["parts_directory"], previous_session,
            )
            claim.validate()
        except (KeyError, TypeError, ValueError, AutomationStateError):
            self._cycle_results[creator] = _result(
                "blocked", "identity_unavailable"
            )
            return
        if not self._replace_state(
            self._state.consumed(), claim, "automation_state_unavailable"
        ):
            self._cycle_results[creator] = _result(
                "blocked", "automation_state_unavailable"
            )
            return
        page = f"https://www.tiktok.com/@{creator}/live"
        try:
            started = self._controller.start(
                page, claim.output_path, expected_room_id=room_id
            )
        except RecordingBusy:
            self._rejected(creator, "start_rejected_busy")
            return
        except Exception:
            # A monitor callback must never kill future detection cycles.
            self._rejected(creator, "start_rejected")
            return
        consumed = self._state.consumed()
        consumed[creator] = room_id
        promoted = self._replace_state(
            consumed, None, "automation_state_ambiguous"
        )
        self._started_creator = creator
        self._started_session_id = started.get("session_id")
        self._started_output_path = claim.output_path
        self._cycle_results[creator] = _result(
            "started", None if promoted else "state_promotion_pending"
        )

    def _rejected(self, creator: str, reason: str) -> None:
        cleared = self._replace_state(
            self._state.consumed(), None, "automation_state_ambiguous"
        )
        self._cycle_results[creator] = _result(
            "failed", reason if cleared else "claim_clear_failed"
        )

    def _replace_state(
        self, consumed: dict[str, str], claim: PendingAutomaticStart | None,
        failure_reason: str,
    ) -> bool:
        state = AutomationState(tuple(sorted(consumed.items())), claim)
        try:
            self._store.save(state)
        except Exception:
            self._disable(failure_reason)
            return False
        self._state = state
        return True

    def _block_live_creators(self, monitoring: dict) -> None:
        for item in monitoring.get("creators", []):
            if item.get("state") == "live":
                self._cycle_results[item.get("creator")] = _result(
                    "blocked", self._blocked_reason
                )

    def _disable(self, reason: str) -> None:
        self._operational = False
        self._blocked_reason = reason


def _creator(snapshot: dict, creator: str) -> dict | None:
    return next(
        (item for item in snapshot.get("creators", [])
         if item.get("creator") == creator),
        None,
    )


def _result(state: str, reason: str | None = None) -> dict:
    return {"state": state, "reason": reason}
