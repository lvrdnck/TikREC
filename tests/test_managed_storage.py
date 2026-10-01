"""Native managed authority, provenance, state and ordinary-owner exclusion."""

import json
import os

import pytest

from tests.managed_fixture import (managed_fixture, as_uid, owner_probe, service_action,
                                   SERVICE_UID, OWNER_UID)


def test_owner_reads_but_cannot_write_replace_or_remove(managed_fixture):
    root = managed_fixture[1]
    assert as_uid(OWNER_UID, lambda _: owner_probe(root)) >= 3
    service_action(managed_fixture, lambda authority, _: authority.validate())


@pytest.mark.parametrize("target", ["root", "ancestor", "state", "definition", "artifact"])
def test_writable_or_owner_owned_authority_refused(managed_fixture, target):
    base, root, parts, state, definition, _ = managed_fixture
    path = {"root": root, "ancestor": base, "state": state,
            "definition": definition, "artifact": parts / "part-0001.flv"}[target]
    path.chmod(0o777)
    from tikrec.managed_storage import ManagedStorage
    def refused(_):
        with pytest.raises(ValueError, match="ownership|exclusion"):
            ManagedStorage(definition)
    as_uid(SERVICE_UID, refused)


def test_marker_and_legacy_media_cannot_be_adopted(managed_fixture):
    root, definition = managed_fixture[1], managed_fixture[4]
    (root / ".tikrec-managed.json").unlink()
    from tikrec.managed_storage import ManagedStorage
    def refused(_):
        with pytest.raises(OSError):
            ManagedStorage(definition)
    as_uid(SERVICE_UID, refused)
    assert (root / "alpha.mp4").exists()


def test_root_replacement_and_policy_state_changes_detected(managed_fixture):
    def proof(authority, _):
        # Only the trusted UID can perform this injected namespace fault.
        saved = authority.state / "saved-config"
        authority.config_path.rename(saved)
        authority.config_path.symlink_to(saved)
        with pytest.raises(ValueError, match="redirected|special"):
            authority.validate()
    service_action(managed_fixture, proof)


def test_paths_and_state_changes_share_exclusion(managed_fixture):
    from tikrec.configuration import ConfigurationStore
    from tikrec.lifecycle_lock import acquire_lifecycle
    def proof(authority, _):
        with pytest.raises(ValueError, match="outside"):
            authority.check_output(authority.state / "evil.mp4")
        config = ConfigurationStore(authority.config_path)
        with authority.retention_scope(authority.root):
            with pytest.raises(ValueError, match="busy"):
                config.save(config.load())
            with pytest.raises(ValueError, match="busy"):
                acquire_lifecycle(authority.root, "writer")
        with acquire_lifecycle(authority.root, "writer"):
            with pytest.raises(ValueError, match="active mutation"):
                with authority.retention_scope(authority.root):
                    pass
    service_action(managed_fixture, proof)


def test_pinned_root_replacement_is_refused(managed_fixture):
    def proof(authority, connection):
        connection.send(("replace-root", str(authority.root)))
        assert connection.recv() == "replaced"
        with pytest.raises(ValueError, match="identity changed"):
            authority.validate()
    service_action(managed_fixture, proof)


def test_unjoined_uid_child_refuses_quiescence(managed_fixture):
    def proof(authority, _):
        import multiprocessing
        child_end, parent_end = multiprocessing.Pipe()
        pid = os.fork()
        if pid == 0:
            parent_end.close()
            child_end.recv()
            os._exit(0)
        child_end.close()
        try:
            with pytest.raises(ValueError, match="child|peer"):
                with authority.retention_scope(authority.root):
                    pass
        finally:
            parent_end.send("stop")
            os.waitpid(pid, 0)
    service_action(managed_fixture, proof)
