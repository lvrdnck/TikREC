"""Disposable privileged Linux harness; never operates on configured media."""

import json
import os
from pathlib import Path
import shutil
import tempfile
import traceback
from uuid import uuid4

import pytest

from tests.test_retention_plan import session, inspect, NOW


SERVICE_UID = 60031
OWNER_UID = 60032


@pytest.fixture
def managed_fixture(monkeypatch):
    """Provision fresh root-owned ancestors and distinct native service/reader UIDs."""
    if not hasattr(os, "fork") or os.geteuid() != 0:
        pytest.skip("native Linux two-UID tests require a disposable root test runtime")
    from tikrec import managed_storage

    # /tmp's writable ancestry is deliberately ineligible for managed authority.
    base = Path(tempfile.mkdtemp(prefix="tikrec-53-disposable-", dir="/var/lib"))
    base.chmod(0o755)
    root, state, code = (base / name for name in ("recordings", "state", "code"))
    for path in (root, state):
        path.mkdir(mode=0o750)
        os.chown(path, SERVICE_UID, OWNER_UID)
    code.mkdir(mode=0o755)
    storage_id = str(uuid4())
    marker = root / ".tikrec-managed.json"
    marker.write_text(json.dumps(dict(schema_version=1, storage_id=storage_id,
                                     recording_root=str(root))))
    marker.chmod(0o444)
    parts = session(root, "alpha")
    session_id = json.loads((parts / "session.json").read_text())["session_id"]
    for path in root.rglob("*"):
        if path != marker:
            os.chown(path, SERVICE_UID, OWNER_UID)
            path.chmod(0o750 if path.is_dir() else 0o640)
    config = state / "config.json"
    config.write_text(json.dumps(dict(schema_version=1, output_directory=str(root),
                                     retention_max_age_days=1)))
    os.chown(config, SERVICE_UID, OWNER_UID)
    config.chmod(0o640)
    definition = base / "managed.json"
    definition.write_text(json.dumps(dict(schema_version=1, service_uid=SERVICE_UID,
                                         recording_root=str(root), state_directory=str(state),
                                         code_directory=str(code), storage_id=storage_id)))
    definition.chmod(0o644)
    # The harness runs from the development checkout. Runtime installation is
    # verified separately; namespace/byte/exclusion checks use real kernel APIs.
    monkeypatch.setattr(managed_storage, "verify_runtime", lambda *_: None)
    try:
        yield base, root, parts, state, definition, session_id
    finally:
        shutil.rmtree(base)


def as_uid(uid, function):
    """Run one assertion callback in a separate unprivileged native process."""
    import multiprocessing

    parent, child = multiprocessing.Pipe()
    def run():
        parent.close()
        try:
            os.setgroups([])
            os.setgid(OWNER_UID)
            os.setuid(uid)
            child.send(("done", function(child)))
        except BaseException:
            child.send(("error", traceback.format_exc()))
        finally:
            child.close()
    process = multiprocessing.get_context("fork").Process(target=run)
    process.start()
    child.close()
    while True:
        if not parent.poll(30):
            process.kill()
            process.join()
            pytest.fail("disposable UID process timed out")
        event, result = parent.recv()
        if event == "owner-probe":
            try:
                as_uid(OWNER_UID, lambda _: owner_probe(Path(result), service_pid=process.pid))
            except BaseException:
                process.kill()
                process.join()
                raise
            parent.send("probed")
            continue
        if event == "replace-root":
            root = Path(result)
            root.rename(root.with_name("saved-root"))
            root.mkdir(mode=0o750)
            os.chown(root, SERVICE_UID, OWNER_UID)
            parent.send("replaced")
            continue
        process.join(10)
        assert process.exitcode == 0
        assert event == "done", result
        return result


def owner_probe(root, *, service_pid=None):
    """Prove evidence is readable while namespace and data write attempts fail."""
    files = [path for path in root.rglob("*") if path.is_file()]
    for path in files:
        if path.name != ".tikrec-lifecycle.lock":
            path.read_bytes()
        with pytest.raises(PermissionError):
            path.open("ab")
        with pytest.raises(PermissionError):
            path.rename(path.with_name(path.name + ".substituted"))
        with pytest.raises(PermissionError):
            path.unlink()
    for path in [root, *[path for path in root.rglob("*") if path.is_dir()]]:
        with pytest.raises(PermissionError):
            (path / "late-owner-child").mkdir()
        with pytest.raises(PermissionError):
            path.rename(path.with_name(path.name + ".replaced"))
    with pytest.raises(PermissionError):
        root.parent.rename(root.parent.with_name(root.parent.name + ".replaced"))
    with pytest.raises(PermissionError):
        os.setuid(SERVICE_UID)
    if service_pid is not None:
        with pytest.raises(PermissionError):
            os.listdir(f"/proc/{service_pid}/fd")
        with pytest.raises(PermissionError):
            os.kill(service_pid, 0)
    return len(files)


def service_action(fixture, action):
    """Install actual managed authority in the disposable service UID process."""
    from tikrec.managed_registry import installed
    from tikrec.managed_storage import ManagedStorage

    def run(connection):
        authority = ManagedStorage(fixture[4])
        try:
            with installed(authority):
                return action(authority, connection)
        finally:
            authority.close()
    return as_uid(SERVICE_UID, run)


def execute(authority, session_id, **options):
    """Use the ordinary executor with native authority and injected offline media I/O."""
    from tikrec.configuration import ConfigurationStore
    from tikrec.retention_execute import execute_retention

    return execute_retention(authority.root, session_id,
                             ConfigurationStore(authority.config_path),
                             clock=lambda: NOW, media_inspector=inspect, **options)
