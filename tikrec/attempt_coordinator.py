"""One-shot internal attempt owner; unfinished readers never settle finalization."""

import json
from contextlib import contextmanager
from dataclasses import asdict
from threading import Event, RLock
from uuid import uuid4

from .claimed_inputs import acquire_claimed_inputs
from .owned_process import OwnedProcess
from .session_journal_types import JournalUncertain, digest, require


class AttemptError(RuntimeError):
    """Retain the first failure, secondary errors, processes and protected inputs."""

    def __init__(self, coordinator, original):
        super().__init__("unfinished attempt held; inspect durable and native evidence")
        self.coordinator, self.original = coordinator, original
        self.diagnostics = tuple(coordinator.errors)
        self.diagnostics_dropped = coordinator.errors_dropped


class AttemptCoordinator:
    """Single-use local capability over an explicit authority and permanent attempt.

    Reopen can inspect records but cannot rebuild this capability. Closing revokes
    execution and releases input protection only after exact local child cleanup.
    Successful read-only children leave the task running/held with its unit/pins.
    """

    def __init__(self, authority, *, process_factory=OwnedProcess, fault=lambda _: None):
        self.authority, self.journal = authority, authority.journal
        self.process_factory, self._fault = process_factory, fault
        self.token, self.owner = self.uuid(), self.uuid()
        self.revision, self.claimed, self.used, self.closed = None, None, False, False
        self.guard, self.children, self.errors = None, [], []
        self.scratch = None
        self.errors_dropped = 0
        self.cancelled, self.gate, self.run_lock = Event(), RLock(), RLock()
        self.transition_lock = RLock()

    @staticmethod
    def uuid():
        """Allocate a fresh permanent operation/launch identity, never a retry token."""
        return str(uuid4())

    def _error(self, error):
        if len(self.errors) < 32:
            self.errors.append(error)
        else:
            self.errors_dropped += 1

    def _call(self, kind, method, arguments, receipt_arguments=None):
        operation = self.uuid()
        try:
            return method(operation, *arguments)
        except JournalUncertain as original:
            # One bounded reconciliation of this exact operation; never reissue it.
            try:
                row = self.journal.operation(operation)
                require(row is not None and row["kind"] == kind and row["arguments_hash"] ==
                        digest(arguments if receipt_arguments is None else receipt_arguments),
                        "uncertain operation cannot be reconciled")
                result = json.loads(row["result"])
            except BaseException as secondary:
                self._error(secondary)
                raise original
            self._error(original)
            return result

    def _transition(self, kind, method, *tail, receipt_tail=None):
        with self.transition_lock:
            with self.gate:
                if kind in {"launch_intent", "child_identity", "bind_owned_inputs", "reserve_scratch",
                            "bind_scratch", "bind_scratch_artifacts", "seal_candidate",
                            "begin_validation", "finish_validation", "prepare_publication", "observe_publication",
                            "prepare_manifest", "manifest_step"}:
                    require(not self.cancelled.is_set() and not self.closed, "attempt execution revoked")
                args = [self.token, self.owner, self.revision, *tail]
                receipt_args = None if receipt_tail is None else [self.token, self.owner, self.revision, *receipt_tail]
                result = self._call(kind, method, args, receipt_args)
                self.revision = result["revision"]
            # Long held-file checks run without authority/DB locks or resume gate.
            if self.guard is not None:
                self.guard.advance(result)
            return result

    def claim(self):
        """Claim FIFO once, reconcile acknowledgement, then acquire protected original H."""
        with self.run_lock:
            require(not self.used and not self.closed and not self.cancelled.is_set(), "single-use coordinator")
            self.used = True
            try:
                with self.gate:
                    self.claimed = self._call("claim_owned", self.journal.claim_owned, [self.token, self.owner])
                    if self.claimed is None:
                        return None
                    self.revision = self.claimed["revision"]
                self._fault("after_claim")
                row = self.journal.owned_attempt(self.token)
                self.guard = acquire_claimed_inputs(self.authority, self.token, self.owner,
                    self.revision, row["seal_hash"], fault=self._fault,
                    manifest_completion=getattr(self, "manifest_capable", False))
                self._transition("bind_owned_inputs", self.journal.bind_owned_inputs,
                                 self.guard.revalidate().marker_sha256)
                return self.claimed
            except BaseException as original:
                self.guard = getattr(original, "guard", self.guard)
                self.cancelled.set()
                raise AttemptError(self, original) from original

    def _record(self, child, field, value):
        return self._transition("child_" + field, self.journal.child_record,
            child["launch"], field, value, receipt_tail=[child["launch"], value])

    def _authorize(self, child, identity):
        require(not child["authorized"], "historical authorization cannot resume again")
        self.guard.revalidate()
        if child.get("validation") is not None:
            child["validation"].revalidate()
        if child.get("intent", {}).get("access") == "write":
            require(self.scratch is not None, "writer scratch owner unavailable")
            self.scratch.assert_outputs_absent(child["intent"]["outputs"])
        self._record(child, "identity", asdict(identity))
        child["authorized"] = True
        self._fault("after_identity")
        return identity

    @contextmanager
    def _resume(self, child, identity):
        self._fault("before_resume_fence")
        self.guard.revalidate()
        if child.get("validation") is not None:
            child["validation"].revalidate()
        if child.get("validation") is not None and child["validation"].binding.get("transport") == "retained_stdin":
            import os
            # Hashing shares the inherited file object's cursor. Rewind after
            # the final pre-resume proof, while the child is still suspended.
            os.lseek(self.scratch.artifacts["candidate.mp4"].fd, 0, os.SEEK_SET)
        if child.get("intent", {}).get("access") == "write":
            self.scratch.assert_outputs_absent(child["intent"]["outputs"])
        with self.gate:
            require(not self.cancelled.is_set() and not self.closed and child["authorized"],
                    "local launch authorization revoked")
            with self.journal.resume_fence(self.token, self.owner, self.revision,
                                           child["launch"], asdict(identity)):
                yield

    def run_child(self, executable, arguments, *, cwd, phase, timeout, observer=None, on_exit=None):
        """Execute one explicit contained reader; no task completion or media publication."""
        from .attempt_execution import run_child
        with self.run_lock:
            try:
                return run_child(self, executable, arguments, cwd, phase, timeout, observer, on_exit=on_exit)
            except BaseException as original:
                self.cancelled.set()
                if self.scratch is not None:
                    self.scratch.hold(original)
                raise AttemptError(self, original) from original

    def reserve_scratch(self, *, helpers=()):
        """Reserve and bind one fresh generated attempt workspace and declarations."""
        from .attempt_scratch import AttemptScratch
        with self.run_lock:
            try:
                require(self.scratch is None, "attempt scratch reservation is single-use")
                return AttemptScratch.reserve(self, helpers)
            except BaseException as original:
                self.cancelled.set()
                if self.scratch is not None:
                    self.scratch.hold(original)
                raise AttemptError(self, original) from original

    def run_writer_child(self, executable, arguments, *, cwd, phase, timeout,
                         outputs=("candidate.mp4",), observer=None, on_exit=None):
        """Run one declared writer; timeout=None permits cancellation-aware assembly."""
        from .attempt_execution import run_child
        with self.run_lock:
            try:
                require(outputs and self.scratch is not None and not self.scratch.candidate_ready,
                        "bound attempt scratch is required for writer authority")
                return run_child(self, executable, arguments, cwd, phase, timeout, observer, outputs, on_exit)
            except BaseException as original:
                self.cancelled.set()
                if self.scratch is not None:
                    self.scratch.hold(original)
                raise AttemptError(self, original) from original

    def cancel(self, timeout=5):
        """Fence resume immediately, then cancel exact jobs and revoke durable permission."""
        with self.gate:
            self.cancelled.set()
        # Never acquire a process lock while holding the resume gate (inverse order).
        # Sequential launch requires every predecessor's proven exit/cleanup;
        # only the latest child can retain live controls, independent of history.
        for child in self.children[-1:]:
            child["process"].cancel(timeout, observer=child["streams"].observe)
        if self.revision is not None:
            with self.transition_lock:
                row = self.journal.owned_attempt(self.token)
                if row["state"] == "held":
                    self._transition("revoke_owned", self.journal.revoke_owned)
        if self.scratch is not None:
            self.scratch.hold()

    def close(self, timeout=5):
        """Keep guards and uncertain/unclean process owners reachable together."""
        from .attempt_execution import finish_child
        try:
            self.cancel(timeout)
        except BaseException as error:
            self._error(error)
        with self.run_lock:
            for child in self.children[-1:]:
                try:
                    finish_child(self, child, timeout)
                except BaseException as error:
                    self._error(error)
            safe = all(child["process"].closed and child["process"].evidence().state in
                       {"not_created", "confirmed_exited"} for child in self.children[-1:])
            scratch_safe = True
            if safe and self.guard is not None and not getattr(self, "validation_retained", False):
                try:
                    self.guard.revalidate()
                except BaseException as error:
                    self._error(error)
                try:
                    self.guard.close()
                except BaseException as error:
                    self._error(error)
            if self.scratch is not None:
                if safe and self.scratch.candidate_ready and not getattr(self, "validation_retained", False):
                    try:
                        self.scratch.close_candidate_protection()
                    except BaseException as error:
                        self._error(error)
                protection = self.scratch.protection_evidence()
                scratch_safe = not protection["workspace_retained"] and not protection["artifacts_retained"]
            self.closed = safe and scratch_safe and (self.guard is None or self.guard.closed)
            return self.closed

    def cleanup_evidence(self):
        """Distinguish execution revocation from complete local resource cleanup."""
        with self.run_lock:
            return {"execution_revoked": self.cancelled.is_set(), "cleanup_complete": self.closed,
                    "scratch": None if self.scratch is None else self.scratch.protection_evidence(),
                    "manifest": None if getattr(self, "manifest_owner", None) is None else {
                        "predecessor_retained": self.manifest_owner.predecessor.handle is not None,
                        "successor_retained": self.manifest_owner.stage is not None and self.manifest_owner.stage.handle is not None,
                        "preserved": self.manifest_owner.preserved, "installed": self.manifest_owner.installed}}
