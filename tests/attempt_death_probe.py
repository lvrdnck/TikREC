"""Disposable native supervisor with real H/journal/guard; bounded death barriers."""

import json
import sys
from pathlib import Path

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tests.owned_process_probe import events, wait
from tikrec.attempt_coordinator import AttemptCoordinator
from tikrec.owned_process_api import check


def main():
    """Pause declared lifetime boundaries for independent exact-handle owner death."""
    mode, directory, *names = sys.argv[1:]
    root = Path(directory)
    api, barriers = events(names)
    data = local_media(root / "source.flv")
    with authority(root) as owner:
        bridge = reserve(owner)
        assert bridge.run(**observations(data)).phase == "queued"
        runner = AttemptCoordinator(owner)
        def pause():
            child = None if not runner.children else runner.children[-1]["process"]
            native = None if child is None else child.native
            context = {"path": str(owner.journal.path), "catalog": owner.journal.catalog_id,
                       "session": bridge.intent.session_id, "token": runner.token,
                       "owner": runner.owner, "handle": 0 if native is None else native.process or 0}
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
        # Running children block on the test release event. Exit-record tests use
        # a naturally exiting reader so durable exit is actually native-confirmed.
        code = "print('final diagnostic tail')"
        if mode in {"native_after_create", "child_identity_before_commit", "after_identity", "native_after_resume"}:
            code = "from tests.owned_process_probe import events,wait;" + \
                   "api,handles=events(" + repr(names) + ");wait(api,handles[1])"
        runner.run_child(Path(sys._base_executable), ["-c", code],
                         cwd=root, phase="probe", timeout=25)
        runner.close()


if __name__ == "__main__":
    main()
