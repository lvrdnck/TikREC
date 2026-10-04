"""Real disposable children and barriers, with independent exact-job cleanup."""

import os
import sys
import time
from pathlib import Path
from threading import Event, Thread
from uuid import uuid4

import pytest

from tests.owned_process_helpers import Events, managed_process
from tests.test_finalize import write_part
from tests.test_unpublished_assembly_media import guarded_factory
from tikrec.assembly_types import AssemblyError
from tikrec.unpublished_assembly import UnpublishedAssembly

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows assembly barriers")


def scripted_attempt(tmp_path, managed, script, *, authorization=None, fault=None, decode=False):
    """Substitute disposable Python payloads through the real contained process owner."""
    source = tmp_path / "source"
    source.mkdir()
    part = source / "part-0001.flv"
    write_part(part, b"same")
    parts = [part]
    if decode:
        second = source / "part-0002.flv"
        write_part(second, b"different")
        parts.append(second)
    owners = []
    def make(session, attempt):
        owner = guarded_factory(managed)(session, attempt)
        owners.append(owner)
        start, guard = owner.start, owner._fault
        def launch(_executable, arguments, *, cwd, before_resume):
            owner._assembly_probe = "-show_entries" in arguments
            payload = ("print('{\"streams\":[{\"avg_frame_rate\":\"25/1\"}]}')" if owner._assembly_probe
                       else script.replace("CANDIDATE", repr(str(Path(arguments[-1])))))
            return start(Path(sys._base_executable), ["-c", payload], cwd=cwd, before_resume=before_resume)
        owner.start = launch
        if fault:
            owner._fault = lambda boundary: (guard(boundary), fault(owner, boundary))
        return owner
    scope = tmp_path / "attempt"
    attempt = UnpublishedAssembly(session_id=str(uuid4()), attempt_token=str(uuid4()), inputs=[part],
        work_scope=scope, candidate=scope / "candidate.mp4", ffmpeg=Path(sys._base_executable),
        ffprobe=Path(sys._base_executable), before_resume=authorization or (lambda identity: identity),
        process_factory=make)
    attempt.inputs = tuple(parts)
    return attempt, owners


def test_cancel_blocked_native_authorization_never_executes(tmp_path, managed_process):
    entered, release, failures = Event(), Event(), []
    def authorize(identity):
        entered.set()
        assert release.wait(10)
        return identity
    attempt, owners = scripted_attempt(tmp_path, managed_process,
        "open(CANDIDATE,'wb').write(b'forbidden')", authorization=authorize)
    def run():
        try:
            attempt.run()
        except BaseException as error:
            failures.append(error)
    thread = Thread(target=run)
    thread.start()
    try:
        assert entered.wait(10)
        attempt.cancel()
        assert owners[0].evidence().state == "confirmed_exited"
        attempt.cancel()
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive() and len(failures) == 1
    assert failures[0].result.state == "cancelled" and not attempt.candidate.exists()


def test_real_final_stderr_after_collection_includes_unterminated_tail(tmp_path, managed_process):
    with Events() as barrier:
        tail = b"[h264 @ 0x1] corrupt slice caf\xc3\xa9"
        script = ("import os; from tests.owned_process_probe import events,wait; "
                  "open(CANDIDATE,'wb').write(b'unpublished'); "
                  f"a,b=events({barrier.names!r}); a.SetEvent(b[0]); wait(a,b[1]); "
                  f"os.write(2,{tail!r})")
        def fault(owner, boundary):
            if boundary == "after_resume":
                barrier.wait()
                status, fired = owner.native.status, []
                def exit_boundary():
                    if not fired:
                        fired.append(True)
                        barrier.release()
                        assert owner.native.api.WaitForSingleObject(owner.native.process, 10000) == 0
                    deadline = time.monotonic() + 10
                    while True:
                        code, active = status()
                        if code is not None and active == 0:
                            return code, active
                        assert time.monotonic() < deadline
                        time.sleep(0.005)
                owner.native.status = exit_boundary
        attempt, _ = scripted_attempt(tmp_path, managed_process, script, fault=fault)
        lines = []
        attempt.progress = lines.append
        result = attempt.run()
        assert result.diagnostics_complete and result.children[0].evidence.stderr == tail
        assert lines == ["ffmpeg: " + tail.decode()]
        assert not (tmp_path / "final.mp4").exists()


def test_real_failed_partial_retained_and_exact_job_closed(tmp_path, managed_process):
    attempt, owners = scripted_attempt(tmp_path, managed_process,
        "import os; open(CANDIDATE,'wb').write(b'failed partial'); os.write(2,b'failed tail'); raise SystemExit(7)")
    with pytest.raises(AssemblyError) as caught:
        attempt.run()
    assert attempt.candidate.read_bytes() == b"failed partial"
    assert caught.value.result.children[0].evidence.root_exit_code == 7
    assert "failed tail" in str(caught.value.original) and owners[0].closed


def test_native_unknown_exit_owner_is_retained_for_reconciliation(tmp_path, managed_process):
    original = []
    def fault(owner, boundary):
        if boundary == "after_resume":
            original.append(owner.native.status)
            owner.native.status = lambda: (_ for _ in ()).throw(OSError("native query fault"))
    attempt, owners = scripted_attempt(tmp_path, managed_process,
        "import time; open(CANDIDATE,'wb').write(b'uncertain'); time.sleep(20)", fault=fault)
    with pytest.raises(AssemblyError) as caught:
        attempt.run()
    result = caught.value.result
    assert result.state == "exit_unknown" and result.children[0].owner is owners[0]
    assert not owners[0].closed and len(result.children) == 1
    owners[0].native.status = original[0]
    assert owners[0].close(5).state == "confirmed_exited"


def test_cancel_native_execution_preserves_partial_and_collects_tail(tmp_path, managed_process):
    with Events() as barrier:
        script = ("import time,os; from tests.owned_process_probe import events; "
                  "open(CANDIDATE,'wb').write(b'cancelled partial'); os.write(2,b'last warning'); "
                  f"a,b=events({barrier.names!r}); a.SetEvent(b[0]); time.sleep(20)")
        attempt, owners = scripted_attempt(tmp_path, managed_process, script)
        failures = []
        def run():
            try:
                attempt.run()
            except BaseException as error:
                failures.append(error)
        thread = Thread(target=run)
        thread.start()
        try:
            barrier.wait()
            attempt.cancel()
            attempt.cancel()
        finally:
            attempt.cancel()
            thread.join(10)
        assert not thread.is_alive() and failures[0].result.state == "cancelled"
        assert attempt.candidate.read_bytes() == b"cancelled partial"
        assert owners[0].closed and owners[0].evidence().state == "confirmed_exited"
        assert owners[0].evidence().stderr == b"last warning"


def test_native_cleanup_fault_preserves_first_failure_and_reachable_owner(tmp_path, managed_process):
    original = []
    def fault(owner, boundary):
        if boundary == "after_resume":
            original.append(owner.native.close)
            owner.native.close = lambda: (_ for _ in ()).throw(OSError("secondary exact-handle cleanup"))
    attempt, owners = scripted_attempt(tmp_path, managed_process,
        "open(CANDIDATE,'wb').write(b'partial'); raise SystemExit(7)", fault=fault)
    try:
        with pytest.raises(AssemblyError) as caught:
            attempt.run()
        result = caught.value.result
        assert "exited with code 7" in str(caught.value.original)
        assert any("secondary exact-handle cleanup" in str(e) for e in result.diagnostics)
        assert result.children[0].evidence.state == "confirmed_exited" and not owners[0].closed
        assert attempt.candidate.read_bytes() == b"partial"
    finally:
        owners[0].native.close = original[0]
        owners[0].close()


def test_native_reencode_diagnostics_beyond_prefix_and_final_utf8(tmp_path, managed_process, monkeypatch):
    import tikrec.finalize_plan as plan
    monkeypatch.setattr(plan, "avc_configuration_dimensions", lambda _: (64, 64))
    script = ("import os; open(CANDIDATE,'wb').write(b'candidate'); "
              "[os.write(2,b'ignored warning\\n'*100) for _ in range(40)]; "
              "os.write(2,b'[h264 @ 0x1] corrupt slice caf\\xc3'); os.write(2,b'\\xa9')")
    attempt, owners = scripted_attempt(tmp_path, managed_process, script, decode=True)
    result = attempt.run()
    assert len(owners) == 3 and result.diagnostics_complete
    assert result.input_decode["status"] == "degraded"
    assert result.input_decode["diagnostic_codes"] == ["h264_bitstream"]
    evidence = result.children[-1].evidence
    assert evidence.truncated[1] > 0 and b"corrupt slice" not in evidence.stderr
    assert evidence.state == "confirmed_exited" and evidence.stream_status == ("complete", "complete")
