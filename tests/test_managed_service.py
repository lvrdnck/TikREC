"""Two-slot capture creates managed evidence under service authority from birth."""

from pathlib import Path
from threading import Event

import pytest

from tests.managed_fixture import managed_fixture, service_action, SERVICE_UID, inspect, execute
from tests.test_writer import audio_configuration, avc_configuration, video, audio
from tikrec.capture import CaptureResult
from tikrec.job_state import JobStateStore
from tikrec.manifest import SessionManifest
from tikrec.recording import RecordingController
from tikrec.recording_manager import RecordingManager
from tikrec.writer import write_parts


def test_both_slots_create_service_owned_media_and_refuse_occupied_retention(managed_fixture):
    def run(authority, _):
        entered = [Event(), Event()]
        finish = Event()
        def capture(url, **options):
            index = 0 if "@beta/" in url else 1
            options["state"]("recording")
            entered[index].set()
            assert finish.wait(10)
            directory, output = options["parts_directory"], options["output_path"]
            directory.mkdir()
            parts = write_parts([audio_configuration(90), avc_configuration(100, b"config"),
                                 video(120, 1), audio(125)], directory)
            manifest = SessionManifest(directory, output, "tiktok_live", creator=("beta", "gamma")[index],
                                       session_id=options["session_id"], clock=lambda: 1000,
                                       media_inspector=inspect)
            manifest.start(connection_count=1)
            options["state"]("finalizing")
            output.write_bytes(b"synthetic completed output")
            manifest.finish("completed", parts, output_path=output, interrupted=False,
                            finalization_status="completed")
            return CaptureResult(parts, output)
        controllers = tuple(RecordingController(capture=capture, store=JobStateStore(path))
                            for path in authority.job_paths)
        manager = RecordingManager(controllers)
        authority.quiescent = manager.quiescent
        try:
            for name in ("beta", "gamma"):
                manager.start(f"https://www.tiktok.com/@{name}/live", str(authority.root / f"{name}.mp4"))
            assert all(event.wait(10) for event in entered)
            assert manager.health()["active_count"] == 2
            with pytest.raises(ValueError, match="active mutation|slots"):
                execute(authority, managed_fixture[5])
            assert not any(job["stop_requested"] for job in manager.jobs())
            finish.set()
            for controller in controllers:
                controller._worker.join(10)
                assert not controller._worker.is_alive()
            assert manager.quiescent()
            authority.validate()
            for name in ("beta", "gamma"):
                for path in [authority.root / f"{name}.mp4", authority.root / f"{name}.parts",
                             *(authority.root / f"{name}.parts").iterdir()]:
                    assert path.stat().st_uid == SERVICE_UID
                    assert path.stat().st_mode & 0o022 == 0
            with authority.retention_scope(authority.root):
                with pytest.raises(ValueError, match="busy"):
                    manager.start("https://www.tiktok.com/@new/live", str(authority.root / "new.mp4"))
        finally:
            finish.set()
            manager.shutdown()
    service_action(managed_fixture, run)
