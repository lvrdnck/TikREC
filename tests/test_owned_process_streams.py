"""Bounded pipe draining, explicit arguments, restricted handles and context errors."""

import ctypes as C
import json
import os
import sys
from pathlib import Path

import pytest

from tests.owned_process_helpers import Events, managed_process
from tikrec.owned_process import ProcessOwnerError
from tikrec.owned_process_api import D, H, check

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows native streams")


def test_large_streams_without_newlines_are_bounded_and_drained(tmp_path, managed_process):
    child = managed_process(diagnostic_limit=101)
    script = "import os; os.write(1,b'A'*1048576); os.write(2,b'B'*1048576)"
    child.start(Path(sys._base_executable), ["-c", script], cwd=tmp_path, before_resume=lambda value: value)
    seen = {"stdout": 0, "stderr": 0}
    def observer(name, chunk):
        seen[name] += len(chunk)
    result = child.wait(10, observer=observer)
    assert result.state == "confirmed_exited" and result.root_exit_code == 0
    assert result.stdout == b"A" * 101 and result.stderr == b"B" * 101
    assert result.truncated == (1048576 - 101, 1048576 - 101)
    assert seen == {"stdout": 1048576, "stderr": 1048576}


def test_observer_error_can_be_closed_without_losing_original(tmp_path, managed_process):
    child = managed_process()
    original = RuntimeError("observer failed")
    child.start(Path(sys._base_executable), ["-c", "import os,time; os.write(1,b'x'); time.sleep(20)"],
                cwd=tmp_path, before_resume=lambda value: value)
    def observe(*_):
        raise original
    result = child.wait(10, observer=observe)
    assert result.state == "exit_unknown" and result.error is original
    assert child.close(5).state == "confirmed_exited"
    assert child.evidence().error is original


def test_argument_vector_never_uses_shell_and_parent_never_joins_job(tmp_path, managed_process):
    child = managed_process()
    values = ["space here", 'quote"here', "trailing\\", "& echo forbidden > forbidden.txt", "", "λ"]
    def authorize(value):
        member, flags = C.c_int(), D()
        api = child.native.api
        check(api.IsProcessInJob(api.GetCurrentProcess(), child.native.job, C.byref(member)))
        assert not member.value
        for handle in [child.native.job, child.native.process, child.native.thread, *child.native.streams.readers.values()]:
            check(api.GetHandleInformation(handle, C.byref(flags)))
            assert not flags.value & 1
        return value
    child.start(Path(sys._base_executable), ["-c", "import json,sys; print(json.dumps(sys.argv[1:]))", *values],
                cwd=tmp_path, before_resume=authorize)
    result = child.wait(10)
    assert json.loads(result.stdout) == values and not (tmp_path / "forbidden.txt").exists()


def test_unlisted_inheritable_handle_is_not_inherited(tmp_path, managed_process):
    with Events() as barrier:
        api, handle = barrier.api, barrier.handles[0]
        check(api.SetHandleInformation(handle, 1, 1))
        child = managed_process()
        script = ("import ctypes; a=ctypes.WinDLL('kernel32',use_last_error=True); "
                  "a.SetEvent.argtypes=[ctypes.c_void_p]; "
                  f"print(bool(a.SetEvent({handle})))")
        child.start(Path(sys._base_executable), ["-c", script], cwd=tmp_path, before_resume=lambda value: value)
        assert child.wait(10).stdout == b"False\r\n"
        assert api.WaitForSingleObject(handle, 0) == 258


def test_context_preserves_body_error_and_cleanup_diagnostic(tmp_path, managed_process, monkeypatch):
    child = managed_process()
    child.start(Path(sys._base_executable), ["-c", "pass"], cwd=tmp_path, before_resume=lambda value: value)
    assert child.wait(10).state == "confirmed_exited"
    original, cleanup = ValueError("body"), OSError("close")
    saved = child.native.api.CloseHandle
    def fail(_):
        raise cleanup
    monkeypatch.setattr(child.native.api, "CloseHandle", fail)
    with pytest.raises(ValueError) as caught:
        with child:
            raise original
    assert caught.value is original and cleanup in original.process_cleanup_errors
    assert child.poll().state == "confirmed_exited"
    monkeypatch.setattr(child.native.api, "CloseHandle", saved)
    child.close()


def test_context_reports_cleanup_failure_on_successful_exit(tmp_path, managed_process, monkeypatch):
    child = managed_process()
    child.start(Path(sys._base_executable), ["-c", "pass"], cwd=tmp_path, before_resume=lambda value: value)
    assert child.wait(10).state == "confirmed_exited"
    saved, cleanup = child.native.api.CloseHandle, OSError("close")
    def fail(_):
        raise cleanup
    monkeypatch.setattr(child.native.api, "CloseHandle", fail)
    with pytest.raises(ProcessOwnerError) as caught:
        with child:
            pass
    assert caught.value.original is cleanup and caught.value.evidence.state == "confirmed_exited"
    monkeypatch.setattr(child.native.api, "CloseHandle", saved)
    child.close()
