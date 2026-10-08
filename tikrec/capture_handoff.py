"""Internal real-LIVE capture closure and confirmed durable ownership transfer."""

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Event

from .capture_completion import CaptureEnded
from .capture_control import CaptureStopped
from .capture_fence import CaptureFence
from .capture_handoff_authority import operation_id
from .capture_handoff_inventory import closed_inventory
from .capture_handoff_marker import MARKER_NAME, marker_values, persist_marker
from .capture_handoff_native import NativeHandle
from .live import capture_live
from .session_journal_types import ReservationReleaseProof, encode, require


class _HandoffInputs(ExitStack):
    """Keep failed original proof owners reachable after ExitStack has unwound."""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def enter_context(self, held):
        """Register the original proof owner before its context can throw."""
        self.bridge.handoff_input_owners.append(held)
        return super().enter_context(held)

    def __exit__(self, *exc):
        try:
            return super().__exit__(*exc)
        finally:
            # Retain exact owners, never retry saved descriptor/handle numbers.
            self.bridge.handoff_input_owners[:] = [h for h in self.bridge.handoff_input_owners
                if h.handle is not None or h.fd is not None]


@dataclass(frozen=True)
class HandoffResult:
    """Confirmed ownership, separately from MP4 completion and post-H diagnostics.

    Later teardown errors never populate capture failure or undo this receipt.
    Notification errors remain available individually and in post_h_errors.
    """

    session_id: str
    phase: str
    receipt: dict
    requested_output: str
    failure: BaseException | None = None
    notification_error: BaseException | None = None
    post_h_errors: tuple[BaseException, ...] = ()


class CaptureHandoffError(RuntimeError):
    """Unproved close retains its original failure, cleanup evidence and responsibility."""

    def __init__(self, error, cleanup_errors):
        super().__init__("capture handoff unproved; durable responsibility retained")
        self.original, self.cleanup_errors = error, tuple(cleanup_errors)


class CaptureBridge:
    """One single-use accepted UUID/generation; never recreated from a receipt."""

    def __init__(self, authority, intent, binding, lease):
        self.authority, self.intent, self.binding, self.lease = authority, intent, binding, lease
        self.handoff_inputs_retired = False
        self.handoff_input_owners = []
        self.stop_event, self.started = Event(), False
        self.fence = CaptureFence(intent.session_id, binding["generation"], self._opening,
                                  track_inputs=authority.cleanup_guards)
        self.handoff_operation, self.admit_operation = operation_id(), operation_id()
        self.warnings, self.failure = set(), None
        self._fault = lambda _: None

    def _current(self):
        self.authority.assert_held()
        self.lease.assert_held()
        row = self.authority.journal.session(self.intent.session_id)
        bindings = self.authority.journal.status()["bindings"]
        require(row is not None and row["generation"] == self.binding["generation"]
                and any(b["session"] == self.intent.session_id
                        and b["generation"] == self.binding["generation"] for b in bindings),
                "capture no longer owns its binding")
        self.binding["revision"] = row["revision"]
        return row

    @contextmanager
    def _opening(self):
        with self.authority.lock:
            row = self._current()
            if row["stop"]:
                raise CaptureStopped()
            require(row["phase"] == "capturing" and row["room"] is not None,
                    "fresh admitted writer authority required")
            yield

    def stop(self):
        """Serialize committed stop intent with fresh admission and native writer opening."""
        with self.authority.lock:
            row = self._current()
            self.binding = self.authority.invoke(self.authority.journal.capture_intent, operation_id(),
                self.intent.session_id, row["generation"], row["revision"], stop=True, recovery="user_stop")
            self.stop_event.set()

    def _room(self, room):
        with self.authority.lock:
            row = self._current()
            if row["stop"]:
                raise CaptureStopped()
            if row["phase"] == "reserved":
                self.binding = self.authority.invoke(self.authority.journal.admit, self.admit_operation,
                    self.intent.session_id, row["generation"], row["revision"], room)
            else:
                require(row["phase"] == "capturing" and row["room"] == room,
                        "room cannot change admitted capture")
            # Even a successfully replayed admission receipt is only historical evidence.
            current = self._current()
            if current["stop"]:
                raise CaptureStopped()
            require(current["phase"] == "capturing" and current["room"] == room,
                    "admission acknowledgement lost fresh writer permission")

    def _warning(self, message, observer):
        self.warnings.add("raw_warning")
        if observer is not None:
            observer(message)

    def _never_admitted(self, error=None):
        row = self._current()
        require(row["phase"] == "reserved" and not Path(self.intent.parts_path).exists()
                and not Path(self.intent.output_path).exists() and not self.fence.cleanup_errors,
                "unadmitted reservation has retained or ambiguous evidence")
        self.fence.close()
        if error is not None and not row["stop"]:
            self.authority.invoke(self.authority.journal.capture_intent, operation_id(),
                self.intent.session_id, row["generation"], row["revision"], recovery="identity_unavailable")
            row = self._current()
        proof = ReservationReleaseProof(self.intent.session_id, row["generation"],
                                        ":".join(self.authority.catalog.initial.split(":")[:2]))
        receipt = self.authority.invoke(self.authority.journal.settle_reservation, operation_id(),
            self.intent.session_id, row["generation"], row["revision"], proof)
        self.lease.close()
        return HandoffResult(self.intent.session_id, "no_assembly", receipt, self.intent.output_path, error)

    def _hold(self, error):
        error = self.fence.primary_error or error
        self.fence.cleanup_errors.extend(getattr(error, "capture_cleanup_errors", ()))
        self.failure = error
        try:
            if self.fence.active:
                self.fence.close()
            with self.authority.lock:
                row = self.authority.journal.session(self.intent.session_id)
                if row["phase"] in {"reserved", "capturing", "closing"}:
                    self.authority.invoke(self.authority.journal.capture_intent, operation_id(),
                        self.intent.session_id, row["generation"], row["revision"], closing=True,
                        recovery="ambiguous_state")
        except BaseException as cleanup:
            self.fence.cleanup_errors.append(cleanup)
        raise CaptureHandoffError(error, self.fence.cleanup_errors) from error

    def _finish_handoff(self, receipt, phase, notify, errors):
        # Confirmation is irreversible locally: cleanup cannot revive capture ownership.
        def record(error, secondary=()):
            for diagnostic in (error, *getattr(error, "capture_cleanup_errors", ()), *secondary):
                if not any(diagnostic is previous for previous in errors):
                    errors.append(diagnostic)
        try:
            self.lease.close()
        except BaseException as error:
            record(error, self.lease.cleanup_errors)
        notification_error = None
        # Lease release and projection each run even if an earlier teardown failed.
        for project in (lambda: self._fault("after_h"), lambda: notify(receipt) if notify is not None else None):
            try:
                project()
            except BaseException as error:
                record(error)
                notification_error = notification_error or error
        return HandoffResult(self.intent.session_id, phase, receipt, self.intent.output_path,
                             notification_error=notification_error, post_h_errors=tuple(errors))

    def run(self, *, notify=None, **observations):
        """Run the real recorder, then hold native closure proof until H is confirmed.

        Inject room/source observations for offline harnesses. Identity, raw policy,
        writer, finalizer and owned control callbacks cannot be overridden.
        """
        allowed = {"resolver", "bound_resolver", "tag_source", "raw_tag_source", "sleeper",
                   "clock", "manifest_clock", "observation_clock", "media_inspector", "progress",
                   "heartbeat", "warning", "state", "retry_policy", "offline_confirmation_checks",
                   "offline_confirmation_interval", "backoff_seconds", "recovery_waiter", "recovery_clock"}
        require(set(observations) <= allowed, "bridge ownership options cannot be overridden")
        with self.authority.lock:
            require(not self.started, "capture bridge is single-use")
            self.started = True
            row = self._current()
            require(row["phase"] == "reserved", "historical binding is not a writer launch")
            if row["stop"]:
                return self._never_admitted()
        warning = observations.pop("warning", None)
        try:
            result = capture_live(f"https://www.tiktok.com/@{self.intent.creator}/live",
                parts_directory=Path(self.intent.parts_path), output_path=Path(self.intent.output_path),
                raw_copy_dir=Path(self.intent.parts_path) if self.intent.raw_copy else None,
                session_id=self.intent.session_id, room_identity=self._room, stop_event=self.stop_event,
                warning=lambda message: self._warning(message, warning), _capture_only=True,
                _capture_fence=self.fence, **observations)
        except BaseException as error:
            with self.authority.lock:
                if self.authority.journal.session(self.intent.session_id)["phase"] == "reserved":
                    try:
                        return self._never_admitted(error)
                    except BaseException as cleanup:
                        self.fence.cleanup_errors.append(cleanup)
            return self._hold(error)
        receipt, post_h_errors = None, []
        try:
            require(type(result) is CaptureEnded and not self.fence.cleanup_errors,
                    "source/writer closure was not proved")
            require(self.fence.inputs is None or self.fence.inputs.retired(),
                    "raw native closure was not proved")
            self.fence.close()
            with self.authority.lock:
                row = self._current()
                if row["phase"] == "reserved":
                    return self._never_admitted()
                self.binding = self.authority.invoke(self.authority.journal.capture_intent, operation_id(),
                    self.intent.session_id, row["generation"], row["revision"], closing=True,
                    stop=result.interrupted, recovery="user_stop" if result.interrupted else "room_ended")
            self._fault("before_inventory")
            with _HandoffInputs(self) as inputs:
                seal, verify = closed_inventory(inputs, self.intent, self.binding["generation"], result,
                                                self.warnings, self.fence.source_items, fault=self._fault)
                values = marker_values(self.authority, self.intent, self.binding, self.handoff_operation, seal)
                marker = Path(self.intent.parts_path) / MARKER_NAME
                self._fault("before_marker")
                persist_marker(marker, values)
                held_marker = inputs.enter_context(NativeHandle(marker))
                held_marker.flush()
                require(held_marker.read_control().decode("utf-8").strip() ==
                        encode(values),
                        "pending marker write did not preserve control intent")
                self._fault("after_marker")
                with self.authority.lock:
                    current = self._current()
                    require(current["revision"] == values["revision"],
                            "pending control revision changed before handoff")
                    verify()
                    held_marker.verify()
                    self.authority.pending.add(self.intent.session_id)
                    method = (self.authority.journal.handoff if seal.disposition == "assembly"
                              else self.authority.journal.settle_empty_capture)
                    phase = "queued" if seal.disposition == "assembly" else "no_assembly"
                    # Set the boundary immediately on confirmed/reconciled receipt,
                    # before pending projection, fault hooks or native ExitStack teardown.
                    receipt = self.authority.invoke(method, self.handoff_operation, self.intent.session_id,
                        values["generation"], values["revision"], seal)
                    self.authority.pending.discard(self.intent.session_id)
                    # Only a confirmed/reconciled receipt makes capacity observable to this authority.
                self._fault("confirmed_h")
            # This is local native readiness, not another H or durable accounting phase.
            # The compatible root lease/projection may still fail and remain supervised.
            self.handoff_inputs_retired = True
        except BaseException as error:
            if receipt is None:
                return self._hold(error)
            post_h_errors.extend((error, *getattr(error, "capture_cleanup_errors", ())))
        return self._finish_handoff(receipt, phase, notify, post_h_errors)
