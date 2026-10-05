"""Real disposable supervisor pauses the new validation execution/receipt path."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tests.owned_process_probe import events, wait
from tikrec.journal_validation import JournalValidation
from tikrec.owned_process_api import check


def main():
    """Expose exact controls and committed facts before actual supervisor death."""
    mode, directory, *names = sys.argv[1:]
    root = Path(directory)
    api, barriers = events(names)
    with authority(root) as owner:
        data = local_media(root / "one-source1.flv")
        bridge = reserve(owner)
        assert bridge.run(**observations(data)).phase == "queued"
        original = owner.journal.session(bridge.intent.session_id)
        (owner.root / "unrelated.bin").write_bytes(b"preserved unrelated bytes")
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in owner.root.rglob("*")
                  if p.is_file() and p.name != ".tikrec-lifecycle.lock"}
        before.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*-source*.flv")})
        adapter = JournalValidation(owner, ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
            ffprobe=Path(shutil.which("ffprobe")).resolve())
        runner = adapter.coordinator
        def pause():
            child = runner.children[-1]["process"]
            native = child.native
            context = {"path": str(owner.journal.path), "catalog": owner.journal.catalog_id,
                "session": original["id"], "original": original, "hashes": before,
                "token": runner.token, "workspace": str(runner.scratch.path),
                "handle": 0 if native is None else native.process or 0,
                "requested_final": bridge.intent.output_path}
            (root / "context.json").write_text(json.dumps(context))
            check(api.SetEvent(barriers[0]))
            wait(api, barriers[1])
        def fault(point):
            validating = bool(runner.children) and runner.children[-1]["intent"].get("access") == "candidate_validation"
            if point == mode and (validating or point in {"before_validation_authority", "after_validation_authority"}):
                pause()
        def transaction(kind, point):
            if mode == kind + "_" + point:
                pause()
        runner._fault, owner.journal._fault = fault, transaction
        adapter.run()


if __name__ == "__main__":
    main()
