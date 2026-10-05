"""Real disposable supervisor paused before and after durable scratch commits."""

import hashlib
import json
import sys
from pathlib import Path

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tests.owned_process_probe import events, wait
from tikrec.attempt_coordinator import AttemptCoordinator
from tikrec.owned_process_api import check


def main():
    """Expose committed-only inspection after exact supervisor termination."""
    mode, directory, *names = sys.argv[1:]
    root = Path(directory)
    api, barriers = events(names)
    data = local_media(root / "source.flv")
    with authority(root) as owner:
        bridge = reserve(owner)
        assert bridge.run(**observations(data)).phase == "queued"
        original = owner.journal.session(bridge.intent.session_id)
        originals = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in owner.root.rglob("*") if path.is_file()
                     and path.name != ".tikrec-lifecycle.lock"}
        runner = AttemptCoordinator(owner)
        def pause():
            child = None if not runner.children else runner.children[-1]["process"]
            native = None if child is None else child.native
            context = {"path": str(owner.journal.path), "catalog": owner.journal.catalog_id,
                "session": bridge.intent.session_id, "token": runner.token,
                "workspace": str(owner.root / (".tikrec-attempt-" + runner.token)),
                "handle": 0 if native is None else native.process or 0,
                "original_hashes": originals, "original": original}
            (root / "context.json").write_text(json.dumps(context), encoding="utf-8")
            check(api.SetEvent(barriers[0]))
            wait(api, barriers[1])
        def boundary(point):
            if point == mode:
                pause()
        def transaction(kind, point):
            if mode == kind + "_" + point:
                pause()
        runner._fault, owner.journal._fault = boundary, transaction
        runner.claim()
        scratch = runner.reserve_scratch(helpers=("z.txt", "a.txt"))
        code = "from pathlib import Path;" + ";".join(
            "Path(" + repr(name) + ").write_bytes(b'disposable candidate/helper')"
            for name in ("candidate.mp4", "z.txt", "a.txt"))
        scratch.run_writer(Path(sys._base_executable), ["-c", code], timeout=15,
                           outputs=("z.txt", "candidate.mp4", "a.txt"))
        scratch.seal_candidate(runner.children[-1]["launch"])
        runner.close()


if __name__ == "__main__":
    main()
