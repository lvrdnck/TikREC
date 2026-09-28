"""Native POSIX retention journal compatibility for literal filename bytes."""

import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from tests.test_writer import audio, audio_configuration, avc_configuration, video
from tikrec.configuration import Configuration, ConfigurationStore
from tikrec.manifest import SessionManifest
from tikrec.media import MediaInfo
from tikrec.retention_audit import RetentionAudit
from tikrec.retention_execute import execute_retention
from tikrec.retention_locality import proven_local
from tikrec.retention_plan import plan_retention
from tikrec.writer import write_parts


@unittest.skipUnless(sys.platform.startswith("linux"), "native Linux path semantics")
class PosixRetentionHistoryTests(unittest.TestCase):
    """Require an executor-produced journal to reopen after media is gone."""

    def test_literal_backslash_session_reopens_completed_schema_one_history(self):
        with tempfile.TemporaryDirectory(prefix="tikrec-posix-gate-", dir="/var/tmp") as temp:
            root = Path(temp) / "recordings"
            root.mkdir()
            if not proven_local(root):
                self.skipTest("/var/tmp is not a proven local volume")
            name = r"a\..\b"
            parts = root / f"{name}.parts"
            parts.mkdir()
            write_parts([audio_configuration(90), avc_configuration(100, b"config"),
                         video(120, 1), audio(125)], parts)
            output = root / f"{name}.mp4"
            output.write_bytes(b"completed output")
            media = MediaInfo("h264", "aac", 720, 1280, "mov,mp4", 12.5)
            session_id = str(uuid.uuid4())
            manifest = SessionManifest(
                parts, output, "tiktok_live", creator="alpha", session_id=session_id,
                clock=iter((1000.0, 1010.0)).__next__, media_inspector=lambda _: media)
            manifest.start(connection_count=1)
            manifest.finish("completed", tuple(parts.glob("part-*.flv")),
                            output_path=output, interrupted=False,
                            finalization_status="completed")
            config = ConfigurationStore(Path(temp) / "config.json")
            config.save(Configuration(retention_max_age_days=1))
            inspector = lambda _: media
            planned = plan_retention(root, config.load(), clock=lambda: 2_000_000.0,
                                     media_inspector=inspector)
            self.assertEqual(planned["sessions"][0]["classification"], "eligible")
            audit_path = Path(temp) / "audit" / "history.jsonl"
            execute_retention(root, session_id, config, audit_path=audit_path,
                              job_paths=(Path(temp) / "job1.json", Path(temp) / "job2.json"),
                              clock=lambda: 2_000_000.0, media_inspector=inspector)
            self.assertFalse(parts.exists())
            self.assertFalse(output.exists())
            with RetentionAudit(root, audit_path):
                pass


if __name__ == "__main__":
    unittest.main()
