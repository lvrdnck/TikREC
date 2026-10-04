"""Portable assembly state doubles; no native containment claims."""

from uuid import uuid4

import pytest

import tikrec.owned_process as process_module
from tests.owned_process_state_helpers import Native
from tests.test_finalize import write_part


@pytest.fixture
def assembly_fixture(tmp_path, monkeypatch):
    """Use real process-owner logic with deterministic creation/status/stream doubles."""
    controls = {"chunks": [], "code": 0, "phases": [], "owners": [], "fault": None}
    executable = tmp_path / "fixture.exe"
    executable.write_bytes(b"never launched")
    source = tmp_path / "source"
    source.mkdir()
    parts = [source / "part-0001.flv", source / "part-0002.flv"]
    for part in parts:
        write_part(part, b"same")

    class Child(Native):
        def create(self, executable, arguments, cwd, fault):
            self.arguments = arguments
            super().create(executable, arguments, cwd, fault)

        def resume(self):
            super().resume()
            if "-show_entries" in self.arguments:
                self.tail = {"stdout": controls.get("probe_output", b'{"streams":[{"avg_frame_rate":"25/1"}]}')}
            else:
                from pathlib import Path
                Path(self.arguments[-1]).write_bytes(b"candidate or failed partial")
                self.streams.queues["stderr"].extend(controls["chunks"])

        def status(self):
            code, active = super().status()
            return (None, active) if code is None else (controls["code"], active)

        def close(self):
            if controls.get("cleanup_error"):
                raise controls["cleanup_error"]
            super().close()

    monkeypatch.setattr(process_module, "NativeChild", Child)
    def make(session, attempt):
        owner = process_module.OwnedProcess(session, attempt, diagnostic_limit=32)
        controls["owners"].append(owner)
        if controls["fault"]:
            owner._fault = controls["fault"]
        return owner

    def build(**changes):
        from tikrec.unpublished_assembly import UnpublishedAssembly
        options = dict(session_id=str(uuid4()), attempt_token=str(uuid4()), inputs=parts,
                       work_scope=tmp_path / "attempt", candidate=tmp_path / "attempt/candidate.mp4",
                       ffmpeg=executable, ffprobe=executable, process_factory=make,
                       before_resume=lambda identity: controls["phases"].append(identity) or identity)
        options.update(changes)
        return UnpublishedAssembly(**options)
    yield build, controls, parts
    controls.pop("cleanup_error", None)
    for owner in controls["owners"]:
        owner._fault = lambda _: None
        owner.close()
