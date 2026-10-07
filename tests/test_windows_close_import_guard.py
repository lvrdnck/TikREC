"""Portable collection guard runs before any Windows-only fixture imports."""

import builtins
import runpy
from pathlib import Path

import pytest


@pytest.mark.parametrize('platform', ['linux', 'darwin', 'freebsd'])
def test_windows_close_skips_before_native_import(monkeypatch, platform):
    """Execute the real module with an unavailable Windows import, preserving assertions."""
    import sys
    original = builtins.__import__
    attempted = []
    def guarded(name, *args, **kwargs):
        if name == 'msvcrt' or name.startswith('tests.journal_assembly_helpers'):
            attempted.append(name)
            raise ModuleNotFoundError(name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(sys, 'platform', platform)
    monkeypatch.setattr(builtins, '__import__', guarded)
    with pytest.raises(pytest.skip.Exception, match='requires Windows'):
        runpy.run_path(str(Path(__file__).with_name('test_release_recovery_windows_close.py')))
    assert not attempted
