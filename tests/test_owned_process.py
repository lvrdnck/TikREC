"""Single-use native process ownership never claims media completion."""

import os
import sys
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from tests.owned_process_helpers import managed_process
from tikrec.owned_process import OwnedProcess, ProcessOwnerError

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Windows owned process creation")


def test_explicit_authorization_and_native_exit(tmp_path, managed_process):
    child = managed_process()
    observed = []
    def authorize(identity):
        assert child.evidence().state == "suspended"
        assert identity.session_id == child.session_id and identity.attempt_token == child.attempt_token
        assert identity.pid > 0 and identity.created > 0
        observed.append(identity)
        return identity
    child.start(Path(sys._base_executable), ["-c", "print('owned')"], cwd=tmp_path, before_resume=authorize)
    result = child.wait(10)
    assert result.state == "confirmed_exited" and result.root_exit_code == 0
    assert result.active_processes == 0 and result.stdout == b"owned\r\n"
    assert result.identity == observed[0] and result.error is None
    assert child.close().state == "confirmed_exited" and child.native.process is None
    assert child.close().state == "confirmed_exited"
    with pytest.raises(ValueError, match="single-use"):
        child.start(Path(sys._base_executable), [], cwd=tmp_path, before_resume=authorize)


@pytest.mark.parametrize("bad", ["session", "attempt", "pid", "created", "image"])
def test_mismatched_before_resume_identity_never_executes(tmp_path, managed_process, bad):
    child = managed_process()
    output = tmp_path / "forbidden.txt"
    def authorize(identity):
        field = {"session": "session_id", "attempt": "attempt_token", "pid": "pid",
                 "created": "created", "image": "image"}[bad]
        value = str(uuid4()) if bad in {"session", "attempt"} else (
            identity.pid + 1 if bad == "pid" else identity.created + 1 if bad == "created" else "false.exe")
        return replace(identity, **{field: value})
    with pytest.raises(ProcessOwnerError) as caught:
        child.start(Path(sys._base_executable), ["-c", f"open({str(output)!r},'w').write('bad')"],
                    cwd=tmp_path, before_resume=authorize)
    assert not output.exists()
    assert caught.value.evidence.state == "confirmed_exited"
    assert isinstance(caught.value.original, ValueError)
    assert child.close().state == "confirmed_exited"


def test_token_alone_is_not_authorization_and_bad_inputs_are_not_created(tmp_path, managed_process):
    child = managed_process()
    with pytest.raises(ProcessOwnerError) as caught:
        child.start(Path(sys._base_executable), ["-c", "raise AssertionError('not authorized')"],
                    cwd=tmp_path, before_resume=lambda _: True)
    assert caught.value.evidence.state == "confirmed_exited"
    second = managed_process()
    with pytest.raises(ProcessOwnerError):
        second.start(Path("python"), [], cwd=tmp_path, before_resume=lambda x: x)
    assert second.evidence().state == "not_created"
