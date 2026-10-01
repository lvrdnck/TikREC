"""Process-local managed authority installed only by the dedicated service."""

from contextlib import contextmanager, nullcontext
from functools import wraps


_authority = None


def current():
    """Return this service's authority; ordinary owner processes have none."""
    return _authority


@contextmanager
def installed(authority):
    """Wire the protected service before recovery or monitoring can begin."""
    global _authority
    if _authority is not None:
        raise ValueError("managed authority is already installed")
    _authority = authority
    try:
        yield
    finally:
        _authority = None


def reserve_root(root, mode):
    """Reserve a managed writer or require an already exclusive retention scope."""
    if _authority is None:
        return nullcontext()
    _authority.check_root(root)
    if mode == "retention":
        _authority.assert_exclusive()
        return nullcontext()
    return _authority.gate.writer()


def state_write(function):
    """Keep every authoritative state promotion inside the same mutation gate."""
    @wraps(function)
    def guarded(self, *args, **kwargs):
        authority = current()
        reservation = nullcontext()
        if authority is not None:
            authority.check_state_path(self.path)
            reservation = authority.gate.writer()
        with reservation:
            return function(self, *args, **kwargs)
    return guarded


def managed_start(function):
    """Reserve service acceptance before a slot can persist or launch a worker."""
    @wraps(function)
    def guarded(self, url, output, **options):
        authority = current()
        if authority is None:
            return function(self, url, output, **options)
        authority.check_output(output)
        with authority.gate.writer():
            return function(self, url, output, **options)
    return guarded


def managed_cycle(function):
    """Skip a monitoring cycle during retention without disabling automation."""
    @wraps(function)
    def guarded(self, *args, **kwargs):
        authority = current()
        if authority is None:
            return function(self, *args, **kwargs)
        reservation = authority.gate.writer()
        try:
            reservation.__enter__()
        except ValueError:
            return
        try:
            return function(self, *args, **kwargs)
        finally:
            reservation.__exit__(None, None, None)
    return guarded
