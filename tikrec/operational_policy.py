"""Fresh-space backpressure for one dedicated native service volume."""
import shutil
from threading import RLock

from .storage_status import GIB, StorageStatus


class OperatingPolicy:
    """Observe physical occupancy; never reserve guessed output bytes or scan history."""

    def __init__(self, home, reserve_gib, *, disk_usage=None):
        self.home = home
        self.reserve = reserve_gib * GIB
        self.disk_usage = disk_usage or shutil.disk_usage
        self.lock = RLock()
        self.failed = False
        self.last = {}
        # The same-volume envelope leaves cleanup space below the capture cutoff.
        self.margins = {'admission': 4 * GIB, 'finalization': 2 * GIB, 'capture': GIB // 2}

    def snapshot(self):
        """Check both scopes every time; redirected/missing storage is unknown."""
        from .pilot_identity import local
        result = {}
        for name in ('state', 'media'):
            try:
                path = local(self.home / name)
                free = self.disk_usage(path).free
                if type(free) is not int or free < 0:
                    free = None
            except Exception:
                free = None
            result[name] = free
        with self.lock:
            self.last = result
        return result

    def reason(self, phase):
        """Use current physical free bytes, including all retained and partial files."""
        values = self.snapshot().values()
        if self.failed or any(value is None for value in values):
            return 'storage_unavailable'
        # A queued task needs the minimum writer budget before spending its one attempt.
        floor = self.reserve + self.margins[phase] + (16 * 1024**2 if phase == 'finalization' else 0)
        return 'low_free_space' if min(values) < floor else None

    def storage(self, name):
        """Present the same admission floor to existing automation and health policy."""
        result = StorageStatus(self.home / name, self.reserve // GIB, disk_usage=self.disk_usage)
        result.minimum_free_bytes += self.margins['admission']
        result.warning_free_bytes = max(20 * GIB, 2 * result.minimum_free_bytes)
        return result

    def writer_budget(self):
        """Cap this writer's growth from fresh physical space, not an input-size estimate."""
        values = self.snapshot().values()
        if any(value is None for value in values):
            raise ValueError('operational writer storage unavailable')
        budget = min(values) - self.reserve - self.margins['finalization']
        if budget < 16 * 1024**2:
            raise ValueError('operational writer headroom unavailable')
        return budget

    @staticmethod
    def stop_capture(bridge):
        """Commit one pressure stop on the original still-writing binding only."""
        authority, sid = bridge.authority, bridge.intent.session_id
        with authority.lock:
            # Source and supervisor can observe pressure together. Serialize the check
            # with the same native-opening/H fence, never bump a closing seal revision.
            if bridge.stop_event.is_set():
                return False
            if not any(b['session'] == sid and b['generation'] == bridge.binding['generation']
                       for b in authority.journal.status()['bindings']):
                return False
            row = authority.journal.session(sid)
            if row['stop']:
                bridge.stop_event.set()
                return False
            if row['phase'] not in {'reserved', 'capturing'}:
                return False
            bridge.stop()
            return True

    def supervise(self, runtime):
        """Fence only exact owned work, independently of HTTP or finalizer progress."""
        capture_reason = self.reason('capture')
        finalizer_reason = self.reason('finalization')
        with runtime.lock:
            adapter = runtime.current
            entries = tuple(runtime.captures.items())
        if capture_reason:
            for sid, entry in entries:
                if not entry['done'] and not entry['bridge'].stop_event.is_set():
                    self.stop_capture(entry['bridge'])
        if finalizer_reason and adapter is not None and not adapter.coordinator.cancelled.is_set():
            # Signal original captures first. Cancellation can wait on a native child.
            adapter.cancel(5)
        runtime.wake.set()
        return capture_reason
