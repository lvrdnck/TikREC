"""Exact-job disposable readers and FFprobe against real committed capture evidence."""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import pytest

from tests.owned_process_helpers import Events, managed_process
from tests.sealed_input_helpers import acquire, hashes, sealed
from tikrec.part_validation import validate_part

pytestmark = pytest.mark.skipif(os.name != "nt", reason="native contained readers")


def test_reader_barrier_protection_until_whole_job_exit(sealed, managed_process):
    owner, bridge, row = sealed
    before = hashes(owner.root.parent)
    with acquire(sealed) as guard, Events() as events:
        process = managed_process()
        process.session_id = bridge.intent.session_id
        process.attempt_token = str(uuid4())
        proof = guard.revalidate()
        child = """
import sys
from pathlib import Path
from tests.owned_process_probe import events, wait
api, handles = events(sys.argv[2:])
with Path(sys.argv[1]).open('rb') as reader:
    assert reader.read(3) == b'FLV'
    api.SetEvent(handles[0])
    wait(api, handles[1])
print('reader final tail', flush=True)
"""
        process.start(Path(sys._base_executable), ["-c", child, str(proof.flv_inputs[0]), *events.names],
                      cwd=owner.root.parent, before_resume=lambda identity: guard.revalidate() and identity)
        try:
            events.wait()
            assert process.poll().state == "running"
            assert proof.flv_inputs[0].read_bytes()
            with pytest.raises(OSError):
                proof.flv_inputs[0].open("ab")
            with pytest.raises(OSError):
                proof.flv_inputs[0].unlink()
            guard.revalidate()
        finally:
            events.release()
        evidence = process.wait(10)
        assert evidence.state == "confirmed_exited" and evidence.active_processes == 0
        assert evidence.stream_status == ("complete", "complete")
        assert evidence.stdout == b"reader final tail\r\n"
        guard.revalidate()
        process.close(5)
    assert hashes(owner.root.parent) == before
    assert owner.journal.session(bridge.intent.session_id) == row


def test_bounded_owned_ffprobe_existing_validators_and_unchanged_evidence(sealed, managed_process):
    owner, bridge, row = sealed
    before, status = hashes(owner.root.parent), owner.journal.status()
    executable = Path(shutil.which("ffprobe")).resolve()
    children = []
    with acquire(sealed) as guard:
        def run(command, **_options):
            child = managed_process(diagnostic_limit=65536)
            child.session_id, child.attempt_token = bridge.intent.session_id, str(uuid4())
            def authorize(identity):
                # Explicit fixture permission plus guard proof. No journal launch
                # write or queued-task claim is made by this test-only reader.
                assert identity.session_id == bridge.intent.session_id
                guard.revalidate()
                return identity
            child.start(executable, command[1:], cwd=owner.root.parent, before_resume=authorize)
            evidence = child.wait(20)
            assert evidence.state == "confirmed_exited" and evidence.active_processes == 0
            assert evidence.root_exit_code == 0 and evidence.stream_status == ("complete", "complete")
            assert evidence.error is None and evidence.truncated == (0, 0)
            guard.revalidate()
            child.close(5)
            children.append(evidence)
            return subprocess.CompletedProcess(command, evidence.root_exit_code,
                                                evidence.stdout.decode(), evidence.stderr.decode())
        proof = guard.revalidate()
        for part in proof.flv_inputs:
            problems, warnings = validate_part(part, str(executable), run)
            assert not problems and not warnings
        assert len(children) == 2
        marker_hash = proof.marker_sha256
    assert hashes(owner.root.parent) == before
    assert owner.journal.status() == status
    assert owner.journal.session(bridge.intent.session_id) == row
    assert not Path(bridge.intent.output_path).exists()
    report = {"hashes": before, "unchanged": True, "session_id": bridge.intent.session_id,
              "seal_hash": row["seal_hash"], "revision": row["revision"],
              "marker_lease_hash": marker_hash, "validators": "part decode + packet DTS passed",
              "children": [{k: v for k, v in asdict(e).items() if k not in {"stdout", "stderr"}}
                           for e in children]}
    (owner.root.parent / "sealed-reader-evidence.json").write_text(json.dumps(report, indent=2))


def test_native_controls_are_not_inherited_by_reader(sealed, managed_process):
    owner, _, _ = sealed
    with acquire(sealed) as guard:
        process = managed_process()
        handles = [held.handle for held in guard.handles]
        # GetFileType distinguishes inherited disk controls from unrelated handle
        # numbers reused for the child's console/pipes. Identity is also checked.
        code = """
import ctypes, json, sys
from tikrec.capture_handoff_native import _kernel, _Information
api = _kernel()
results = []
for value in json.loads(sys.argv[1]):
    info = _Information()
    ok = api.GetFileInformationByHandle(value, ctypes.byref(info))
    if ok:
        results.append([info.volume, info.index_high, info.index_low])
print(json.dumps(results), flush=True)
"""
        originals = [(i.volume, i.index_high, i.index_low) for i in
                     (held._information() for held in guard.handles)]
        process.start(Path(sys._base_executable), ["-c", code, json.dumps(handles)],
                      cwd=owner.root.parent, before_resume=lambda identity: guard.revalidate() and identity)
        evidence = process.wait(10)
        assert evidence.state == "confirmed_exited" and evidence.stream_status == ("complete", "complete")
        assert evidence.root_exit_code == 0
        assert not set(map(tuple, json.loads(evidence.stdout))).intersection(originals)
        guard.revalidate()
        process.close(5)


def test_unknown_reader_lifetime_keeps_read_guard_held(sealed, managed_process, monkeypatch):
    owner, _, _ = sealed
    with acquire(sealed) as guard, Events() as events:
        process = managed_process()
        process.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", "leaf",
            str(owner.root.parent), *events.names], cwd=owner.root.parent,
            before_resume=lambda identity: guard.revalidate() and identity)
        events.wait()
        status = process.native.status
        def unavailable():
            raise OSError("native lifetime proof temporarily unavailable")
        monkeypatch.setattr(process.native, "status", unavailable)
        try:
            assert process.poll().state == "exit_unknown"
            assert process.native.process is not None and not guard.closed
            with pytest.raises(OSError):
                guard.revalidate().flv_inputs[0].open("ab")
        finally:
            monkeypatch.setattr(process.native, "status", status)
            events.release()
        assert process.wait(10).state == "confirmed_exited"
        guard.revalidate()
        process.close(5)
