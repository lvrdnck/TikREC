"""Actual connected supervisor exposes committed-only boundaries for disposable death."""

import json
import hashlib
import shutil
import sys
from pathlib import Path

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tests.owned_process_probe import events, wait
from tikrec.journal_assembly import JournalAssembly
from tikrec.owned_process_api import check


def main():
    """Pause the actual adapter without substituting its helper or FFmpeg command."""
    mode, directory, *names = sys.argv[1:]
    root = Path(directory)
    api, barriers = events(names)
    with authority(root) as owner:
        # This supervisor runs the base interpreter, which intentionally has no
        # pytest dependency. Build a one-part real H fixture using stdlib helpers.
        data = local_media(root / "one-source1.flv")
        bridge = reserve(owner)
        assert bridge.run(**observations(data)).phase == "queued"
        original = owner.journal.session(bridge.intent.session_id)
        (owner.root / "unrelated.bin").write_bytes(b"unrelated committed bytes")
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in owner.root.rglob("*")
                  if p.is_file() and p.name != ".tikrec-lifecycle.lock"}
        sources = {str(p): p.read_bytes().hex() for p in root.glob("*-source*.flv")}
        adapter = JournalAssembly(owner, ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
            ffprobe=Path(shutil.which("ffprobe")).resolve())
        runner = adapter.coordinator
        def pause():
            process = None if not runner.children else runner.children[-1]["process"]
            native = None if process is None else process.native
            data = {"path": str(owner.journal.path), "catalog": owner.journal.catalog_id,
                "session": original["id"], "original": original, "original_hashes": before,
                "sources": sources, "token": runner.token,
                "workspace": str(owner.root / (".tikrec-attempt-" + runner.token)),
                "handle": 0 if native is None else native.process or 0,
                "requested_final": bridge.intent.output_path}
            (root / "context.json").write_text(json.dumps(data))
            check(api.SetEvent(barriers[0]))
            wait(api, barriers[1])
        def fault(point):
            if point == mode:
                pause()
        def transaction(kind, point):
            if mode == kind + "_" + point:
                pause()
        runner._fault, owner.journal._fault = fault, transaction
        adapter.run()
        adapter.close()


if __name__ == "__main__":
    main()
