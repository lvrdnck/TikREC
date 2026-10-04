"""Disposable native children; every barrier and child operation has a hard bound."""

import ctypes as C
import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from tikrec.owned_process import OwnedProcess, ProcessOwnerError
from tikrec.owned_process_api import H, check, identity, kernel


def events(names):
    """Open only test-owned barriers, never production objects."""
    api = kernel()
    api.OpenEventW.argtypes, api.OpenEventW.restype = [C.c_uint32, C.c_int, C.c_wchar_p], H
    api.SetEvent.argtypes, api.SetEvent.restype = [H], C.c_int
    return api, [check(api.OpenEventW(0x100002, False, name)) for name in names]


def wait(api, handle):
    """Fail independently if the supervising test does not release its barrier."""
    if api.WaitForSingleObject(handle, 20000) != 0:
        raise TimeoutError("disposable child barrier expired")


def main():
    """Exercise real ownership without touching a journal or queued session."""
    mode, directory, *names = sys.argv[1:]
    api, barriers = events(names)
    if mode == "leaf":
        check(api.SetEvent(barriers[0]))
        wait(api, barriers[1])
        return
    if mode == "tree":
        leaf = subprocess.Popen([sys._base_executable, "-m", "tests.owned_process_probe", "leaf", directory, *names[:2]], close_fds=True)
        print(json.dumps({"handle": int(leaf._handle)}), flush=True)
        wait(api, barriers[2])
        # Deliberately let the root exit while the contained descendant remains.
        return
    owner = OwnedProcess(str(uuid4()), str(uuid4()))
    context = Path(directory) / "context.json"
    def snapshot():
        data = {"handle": owner.native.process or 0}
        if owner.native.process:
            data["identity"] = identity(api, owner.native.process)
        context.write_text(json.dumps(data), encoding="utf-8")
    def authorize(value):
        snapshot()
        if mode == "before_resume":
            check(api.SetEvent(barriers[0]))
            wait(api, barriers[1])
        return value
    def boundary(value):
        if value == mode:
            snapshot()
            check(api.SetEvent(barriers[0]))
            wait(api, barriers[1])
    owner._fault = boundary
    child_names = names[:2]
    private = None
    if mode in {"last_handle", "running_tree"}:
        api.CreateEventW.argtypes, api.CreateEventW.restype = [H, C.c_int, C.c_int, C.c_wchar_p], H
        child_names = ["Local\\TikREC-private-" + str(uuid4()), names[1]]
        private = check(api.CreateEventW(None, True, False, child_names[0]))
    try:
        child_mode = "tree" if mode == "running_tree" else "leaf"
        child_names = [*child_names, names[1]] if mode == "running_tree" else child_names
        owner.start(Path(sys._base_executable), ["-m", "tests.owned_process_probe", child_mode, directory, *child_names],
                    cwd=Path(directory), before_resume=authorize)
    except ProcessOwnerError as error:
        if mode != "incompatible":
            raise
        context.write_text(json.dumps({"state": error.evidence.state, "error": str(error.original)}))
        check(api.SetEvent(barriers[0]))
        return
    if mode == "running_tree":
        wait(api, private)
        deadline = time.monotonic() + 10
        while not owner.poll().stdout:
            assert time.monotonic() < deadline
            time.sleep(0.005)
        descendant = json.loads(owner.evidence().stdout)["handle"]
        held = H()
        check(api.DuplicateHandle(owner.native.process, descendant, api.GetCurrentProcess(), C.byref(held), 0, False, 2))
        data = json.loads(context.read_text())
        data["descendant"] = held.value
        context.write_text(json.dumps(data))
        check(api.SetEvent(barriers[0]))
    if mode == "last_handle":
        extra = H()
        current = api.GetCurrentProcess()
        check(api.DuplicateHandle(current, owner.native.job, current, C.byref(extra), 0, False, 2))
        wait(api, private)
        check(api.CloseHandle(owner.native.job))
        owner.native.job = None
        # Closing one of two handles must leave the child alive; the last kills it.
        snapshot()
        assert api.WaitForSingleObject(owner.native.process, 0) == 258
        check(api.SetEvent(barriers[0]))
        wait(api, barriers[1])
        check(api.CloseHandle(extra))
        assert api.WaitForSingleObject(owner.native.process, 10000) == 0
        return
    wait(api, barriers[1])
    assert owner.close(5).state == "confirmed_exited"


if __name__ == "__main__":
    main()
