"""Original raw streams and native references for opt-in pre-writer shutdown proof."""

import os

from .release_recovery_handles import NativeCloseGuard


class CaptureInputOwners:
    """Keep exact streams reachable even when optional raw diagnostics swallow close errors."""

    def __init__(self):
        self.native_close_guards, self.streams, self.errors = [], [], []
        self.acquisition_uncertain = False

    def _error(self, error):
        # RawCopy may swallow diagnostics; retain each original primary/secondary object here.
        for diagnostic in (error, *getattr(error, 'capture_cleanup_errors', ())):
            if not any(diagnostic is previous for previous in self.errors):
                self.errors.append(diagnostic)

    def open(self, path, mode, **options):
        """Register each original stream before guarding it or writing any bytes."""
        try:
            raw = path.open(mode, **options)
        except BaseException as error:
            # No returned stream is not evidence that an interrupted acquisition owns nothing.
            self.acquisition_uncertain = True
            self._error(error)
            raise
        entry = {'raw': raw, 'guard': None}
        self.streams.append(entry)
        if os.name != 'nt':
            # No equivalent native identity proof is claimed outside the pilot platform.
            return raw
        import msvcrt
        try:
            guard = NativeCloseGuard(self, msvcrt.get_osfhandle(raw.fileno()), raw.fileno(),
                                     resource_key='capture_raw')
        except BaseException as error:
            self._error(error)
            raise
        entry['guard'] = guard
        return _RawStream(self, raw, guard)

    def retire(self):
        """Retry only original native objects after source/callback shutdown is proved."""
        for entry in self.streams:
            raw, guard = entry['raw'], entry['guard']
            if guard is None:
                continue
            try:
                guard.close_retired_reference()
                if guard.retained:
                    guard.close(None if raw.closed else raw.close)
            except BaseException as error:
                self._error(error)
        return self.retired()

    def retired(self):
        """Require native retirement as well as Python closure; partial acquisitions refuse."""
        return (not self.acquisition_uncertain
                and all(e['guard'] is not None and not e['guard'].retained and e['raw'].closed
                    for e in self.streams)
                and all(not g.retained for g in self.native_close_guards))


class _RawStream:
    """Delegate raw/arrival I/O without losing suppressed primary or secondary faults."""

    def __init__(self, owner, raw, guard):
        self.owner, self.raw, self.guard = owner, raw, guard

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def close(self):
        """Retain actual faults even when RawCopy turns them into optional warnings."""
        try:
            self.guard.close(None if self.raw.closed else self.raw.close)
        except BaseException as error:
            self.owner._error(error)
            raise
