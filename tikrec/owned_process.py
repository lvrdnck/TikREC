"""Isolated Windows child-lifetime owner, unused by synchronous finalization/service."""

import math
import time
from pathlib import Path
from threading import RLock

from .owned_process_native import NativeChild
from .owned_process_api import identity as native_identity
from .owned_process_types import ProcessEvidence, ProcessIdentity, ProcessOwnerError, uuid_key


def _timeout(value):
    if type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 30:
        raise ValueError("bounded timeout must be between zero and 30 seconds")
    return value


class OwnedProcess:
    """Single-use UUID/attempt owner with creation-time containment and bounded polling.

    before_resume must return the exact identity after independently authorizing
    the current durable claim. Tokens alone are not fresh permission. Hooks and
    observers are trusted caller code and must return promptly; native I/O never
    waits for stream lines or spawns reader threads. An unknown lifetime retains
    handles: callers must keep this owner, reconcile/close it, and not replace it.
    """

    def __init__(self, session_id, attempt_token, *, diagnostic_limit=16384):
        self.session_id, self.attempt_token = uuid_key(session_id), uuid_key(attempt_token)
        if type(diagnostic_limit) is not int or not 0 <= diagnostic_limit <= 65536:
            raise ValueError("diagnostic byte limit must be between zero and 65536")
        self.limit, self.native, self.identity = diagnostic_limit, None, None
        self.state, self.started, self.closed = "not_created", False, False
        self.code, self.active, self.cancel_requested = None, None, False
        self.buffers, self.dropped, self.errors = {"stdout": bytearray(), "stderr": bytearray()}, [0, 0], []
        self.errors_dropped = 0
        self.lock, self._fault = RLock(), lambda _: None

    def __enter__(self):
        """Retain this single-use owner for bounded cleanup on scope exit."""
        return self

    def __exit__(self, *_exc):
        """Preserve a body error and attach cleanup failures, or raise accumulated evidence."""
        result = self.close()
        if (result.state == "exit_unknown" or result.error is not None) and (len(_exc) < 2 or _exc[1] is None):
            raise ProcessOwnerError(result)
        if len(_exc) > 1 and _exc[1] is not None and result.error is not None:
            _exc[1].process_cleanup_errors = [*getattr(_exc[1], "process_cleanup_errors", ()),
                                              result.error, *result.diagnostics]

    def _record(self, error):
        for item in (error, *getattr(error, "process_cleanup_errors", ())):
            if not any(item is existing for existing in self.errors):
                # Repeated failed native polls must not create an unbounded error log.
                if len(self.errors) < 32:
                    self.errors.append(item)
                else:
                    self.errors_dropped += 1

    def evidence(self):
        """Return a snapshot without turning a PID, EOF or token into exit/launch proof."""
        with self.lock:
            return ProcessEvidence(self.session_id, self.attempt_token, self.state, self.identity,
                self.code, self.active, bytes(self.buffers["stdout"]), bytes(self.buffers["stderr"]),
                tuple(self.dropped), self.cancel_requested, self.errors[0] if self.errors else None,
                tuple(self.errors[1:]), self.errors_dropped)

    def start(self, executable, arguments, *, cwd, before_resume):
        """Create contained/suspended; authorize native identity before exact-thread resume."""
        with self.lock:
            if self.started or self.closed:
                raise ValueError("owned process is single-use")
            self.started = True
        try:
            executable, cwd = Path(executable), Path(cwd)
            if not executable.is_absolute() or not executable.is_file() or executable.suffix.lower() != ".exe":
                raise ValueError("explicit absolute executable required")
            if not cwd.is_absolute() or not cwd.is_dir():
                raise ValueError("explicit existing working/output scope required")
            if type(arguments) not in {list, tuple} or not all(type(a) is str and "\0" not in a for a in arguments):
                raise ValueError("explicit argument vector required; no shell")
            if not callable(before_resume):
                raise ValueError("fresh before-resume authorization hook required")
            with self.lock:
                self.native = NativeChild()
                self.native.create(executable.resolve(), arguments, cwd, self._creation_boundary)
                self.identity = ProcessIdentity(self.session_id, self.attempt_token, *self.native.initial)
                self.state = "suspended"
            # Do not hold the native-owner lock during trusted durable authorization:
            # another caller can cancel a blocked suspended launch without resuming it.
            authorized = before_resume(self.identity)
            with self.lock:
                if type(authorized) is not ProcessIdentity or authorized != self.identity:
                    raise ValueError("before-resume identity/authorization mismatch")
                if self.cancel_requested or self.state != "suspended":
                    raise ValueError("cancelled/stale suspended launch cannot resume")
                self.native.verify(self.native.initial)
                self._fault("before_resume")
                self.native.resume()
                self.state = "running"
                self._fault("after_resume")
            return self.evidence()
        except BaseException as error:
            with self.lock:
                self._record(error)
                if self.native is not None and self.native.process is not None:
                    self.state = "exit_unknown"
                    # A fault immediately after creation must not discard obtainable
                    # creation evidence before bounded cleanup closes the held object.
                    if self.identity is None:
                        try:
                            self.native.initial = self.native.initial or native_identity(self.native.api, self.native.process)
                            self.identity = ProcessIdentity(self.session_id, self.attempt_token, *self.native.initial)
                        except BaseException as diagnostic:
                            self._record(diagnostic)
            self.close(5)
            raise ProcessOwnerError(self.evidence()) from error

    def _creation_boundary(self, name):
        if self.native.process is not None:
            self.state = "suspended"
        self._fault(name)

    def _collect(self, observer):
        for index, name in enumerate(("stdout", "stderr")):
            # Per-call drain is bounded even when the child continuously writes.
            for _ in range(8):
                chunk = self.native.streams.read(name)
                if not chunk:
                    break
                room = self.limit - len(self.buffers[name])
                self.buffers[name].extend(chunk[:room])
                self.dropped[index] += max(0, len(chunk) - room)
                if observer is not None:
                    observer(name, chunk)

    def poll(self, *, observer=None):
        """Poll exact handles and bounded diagnostic chunks; descendants prevent exit proof."""
        with self.lock:
            if self.native is None or self.closed or self.state == "confirmed_exited":
                return self.evidence()
            try:
                if self.native.process is not None:
                    self._collect(observer)
                self.code, self.active = self.native.status()
                if self.code is not None and self.active == 0:
                    self.state = "confirmed_exited"
                elif self.state != "suspended":
                    self.state = "running"
            except BaseException as error:
                self._record(error)
                self.state = "exit_unknown"
            return self.evidence()

    def wait(self, timeout, *, observer=None):
        """Bound whole-job waiting; timeout retains handles and supplies no exit proof."""
        deadline = time.monotonic() + _timeout(timeout)
        while True:
            result = self.poll(observer=observer)
            if result.state in {"not_created", "confirmed_exited"}:
                return result
            if result.state == "exit_unknown" and result.error is not None:
                return result
            if time.monotonic() >= deadline:
                with self.lock:
                    self.state = "exit_unknown"
                    self._record(TimeoutError("whole-job exit was not confirmed within wait bound"))
                return self.evidence()
            time.sleep(min(0.005, max(0, deadline - time.monotonic())))

    def cancel(self, timeout=5):
        """Request termination only of this exact job, then independently prove whole-job exit."""
        _timeout(timeout)
        with self.lock:
            self.cancel_requested = True
            if self.native is None or self.closed or self.state == "confirmed_exited":
                return self.evidence()
            try:
                self.native.terminate()
            except BaseException as error:
                self._record(error)
                self.state = "exit_unknown"
        return self.wait(timeout)

    def close(self, timeout=5):
        """Bound cleanup; unknown lifetime retains exact handles for explicit reconciliation."""
        _timeout(timeout)
        if self.native is not None and self.native.process is not None and self.state != "confirmed_exited":
            self.cancel(timeout)
        with self.lock:
            if self.native is not None:
                if self.native.process is not None and self.state != "confirmed_exited":
                    return self.evidence()
                try:
                    self.native.close()
                except BaseException as error:
                    self._record(error)
                    return self.evidence()
            self.closed = True
            return self.evidence()
