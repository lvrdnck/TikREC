"""POSIX refuses destructive execution but retains advisory/history support."""

import json
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
from tikrec.retention_plan import _plan_retention_with_snapshot
from tikrec.retention_authorization import authorize
from tikrec.retention_mutation import remove_authorized, quarantine_relative
from tikrec.writer import write_parts


@unittest.skipUnless(sys.platform.startswith("linux"), "native Linux path semantics")
class PosixRetentionHistoryTests(unittest.TestCase):
    """Require an executor-produced journal to reopen after media is gone."""

    def test_refusal_preserves_every_artifact_and_old_history_remains_readable(self):
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
            # Even an occupied old quarantine name must remain untouched.
            occupied = root / ".tikrec-retention-old"
            occupied.write_bytes(b"unexpected occupant")
            before = {str(path.relative_to(root)): path.read_bytes()
                      for path in root.rglob("*") if path.is_file()}
            with self.assertRaisesRegex(ValueError, "POSIX retention is read-only"):
                execute_retention(root, session_id, config, audit_path=audit_path,
                                  job_paths=(Path(temp) / "job1.json", Path(temp) / "job2.json"),
                                  clock=lambda: 2_000_000.0, media_inspector=inspector)
            self.assertEqual(before, {str(path.relative_to(root)): path.read_bytes()
                                      for path in root.rglob("*") if path.is_file()})
            self.assertFalse(audit_path.exists())
            self.assertFalse((root / ".tikrec-lifecycle.lock").exists())
            fresh, claims, proofs = _plan_retention_with_snapshot(
                root, config.load(), clock=lambda: 2_000_000.0,
                media_inspector=inspector, bind_bytes=True)
            auth = authorize(root, fresh["sessions"][0], config.load(), claims,
                             proofs[str(parts)])
            operation = str(uuid.uuid4())
            private = root / quarantine_relative(auth.order[0], operation, 0)
            private.write_bytes(b"collision must survive")
            with self.assertRaisesRegex(ValueError, "POSIX retention is read-only"):
                remove_authorized(root, auth.order[0], auth.volume,
                                  dict(auth.artifact_byte_hashes)[auth.order[0].relative_path],
                                  operation, 0, lambda _: self.fail("unexpected mutation sync"))
            self.assertEqual(private.read_bytes(), b"collision must survive")
            self.assertTrue((root / auth.order[0].relative_path).exists())
            # Construct a synthetic historical schema-1 journal, without relying
            # on the now-disabled POSIX executor to create new destructive work.
            with RetentionAudit(root, audit_path) as audit:
                audit.append("intent", operation, timestamp=2_000_000.0, root=str(root),
                             session_id=session_id, creator="alpha", ended_at=1010.0,
                             max_age_days=1, protected=False, protected_creators=[],
                             order=[item.relative_path for item in auth.order],
                             artifacts=[item.audit_dict() for item in auth.order])
                for item in auth.order:
                    audit.append("attempt", operation, path=item.relative_path)
                    audit.append("deleted", operation, path=item.relative_path)
                audit.append("completed", operation, deleted_count=len(auth.order))
            with RetentionAudit(root, audit_path):
                pass
            self.assertEqual(json.loads(audit_path.read_text().splitlines()[-1])["event"],
                             "completed")


if __name__ == "__main__":
    unittest.main()
