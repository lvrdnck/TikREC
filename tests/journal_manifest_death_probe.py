"""Real disposable supervisor pauses the new manifest preparation/staging/install/result path."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tests.owned_process_probe import events, wait
from tikrec.journal_manifest import JournalManifest
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
        adapter = JournalManifest(owner, ffmpeg=Path(shutil.which("ffmpeg")).resolve(),
            ffprobe=Path(shutil.which("ffprobe")).resolve())
        runner = adapter.coordinator
        def pause():
            child = runner.children[-1]["process"]
            native = child.native
            context = {"path": str(owner.journal.path), "catalog": owner.journal.catalog_id,
                "session": original["id"], "original": original, "hashes": before,
                "token": runner.token, "workspace": str(runner.scratch.path),
                "handle": 0 if native is None else native.process or 0,
                "requested_final": bridge.intent.output_path,
                "manifest": str(Path(bridge.intent.parts_path) / "session.json"),
                "history": str(Path(bridge.intent.parts_path) / f".tikrec-manifest-{runner.token}.original.json"),
                "stage": str(Path(bridge.intent.parts_path) / f".tikrec-manifest-{runner.token}.successor.json")}
            (root / "context.json").write_text(json.dumps(context))
            check(api.SetEvent(barriers[0]))
            wait(api, barriers[1])
        def fault(point):
            if point == mode:
                pause()
        def transaction(kind, point):
            selected = kind
            if kind == "manifest_step":
                cap = runner.manifest_owner
                selected += "_" + ("installed" if cap.installed else "preserved" if cap.preserved else "staged")
            if mode == selected + "_" + point:
                pause()
        runner._fault, owner.journal._fault = fault, transaction
        from tikrec import manifest_completion as completion
        native, create = completion.rename_no_replace, completion.create_stage
        def rename(*args):
            kind = "install" if args[2] == "session.json" else "preserve"
            if mode == "immediately_before_" + kind:
                pause()
            native(*args)
            if mode == "immediately_after_" + kind:
                pause()
        def stage(*args):
            value = create(*args)
            if mode == "immediately_after_create":
                pause()
            return value
        completion.rename_no_replace, completion.create_stage = rename, stage
        adapter.run()


if __name__ == "__main__":
    main()
