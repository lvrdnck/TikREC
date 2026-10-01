"""Dedicated service authority over freshly provisioned Linux managed storage."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
from uuid import UUID

from .managed_gate import MutationGate
from .managed_paths import ProtectedPath, absolute_path, check_permissions, check_tree
from .managed_process import assert_quiescent_process, verify_runtime
from .retention_locality import local_volume


MARKER = ".tikrec-managed.json"
_FIELDS = {"schema_version", "service_uid", "recording_root", "state_directory",
           "code_directory", "storage_id"}


class ManagedStorage:
    """Pin protected storage and state for the sole trusted service process."""

    def __init__(self, definition_path: Path) -> None:
        self._pins = []
        self._singleton = None
        self._umask = None
        self.gate = MutationGate()
        self.quiescent = lambda: True
        try:
            if not sys.platform.startswith("linux"):
                raise ValueError("managed storage requires native Linux")
            definition = self._pin(Path(definition_path), 0, directory=False)
            document = _document(definition.descriptor)
            if (set(document) != _FIELDS or type(document["schema_version"]) is not int
                    or document["schema_version"] != 1
                    or type(document["service_uid"]) is not int or document["service_uid"] <= 0
                    or str(UUID(document["storage_id"])) != document["storage_id"]):
                raise ValueError("invalid managed storage definition")
            self.uid, self.storage_id = document["service_uid"], document["storage_id"]
            self.root = absolute_path(document["recording_root"])
            self.state = absolute_path(document["state_directory"])
            self.code = absolute_path(document["code_directory"])
            for first, second in ((self.root, self.state), (self.root, self.code),
                                  (self.state, self.code)):
                if first == second or first in second.parents or second in first.parents:
                    raise ValueError("managed storage, state and code must be disjoint")
            verify_runtime(self.uid, self.code)
            self._pin(self.root, self.uid)
            self._pin(self.state, self.uid)
            self._pin(self.code, 0)
            self._volumes = (local_volume(self.root), local_volume(self.state))
            if None in self._volumes:
                raise ValueError("managed storage locality could not be proven")
            self.marker = self.root / MARKER
            self._marker_bytes = self.marker.read_bytes()
            if json.loads(self._marker_bytes) != {
                "schema_version": 1, "storage_id": self.storage_id,
                "recording_root": str(self.root),
            }:
                raise ValueError("managed storage was not provisioned from inception")
            self.validate()
            self._open_singleton()
            # Service-created directories/files grant evidence readers no write bit.
            self._umask = os.umask(0o027)
        except BaseException:
            self.close()
            raise

    @property
    def config_path(self) -> Path:
        """Return the protected authoritative configuration location."""
        return self.state / "config.json"

    @property
    def job_paths(self) -> tuple[Path, Path]:
        """Return both protected durable slot paths."""
        return self.state / "job.json", self.state / "job-2.json"

    def _pin(self, path, uid, *, directory=True):
        held = ProtectedPath(path, uid, directory=directory)
        self._pins.append(held)
        return held

    def _open_singleton(self):
        import fcntl

        path = self.state / ".managed-service.lock"
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            check_permissions(descriptor, os.fstat(descriptor), self.uid, directory=False)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fsync(descriptor)
            os.fsync(self._pins[2].descriptor)
            self._singleton = descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def validate(self) -> None:
        """Prove current root/ancestor identities, storage ownership and locality."""
        for held in self._pins:
            held.assert_held()
        if (local_volume(self.root), local_volume(self.state)) != self._volumes:
            raise ValueError("managed storage volume changed")
        check_tree(self.root, self.uid, trusted_files=(self.marker,))
        check_tree(self.state, self.uid)
        if self.marker.read_bytes() != self._marker_bytes:
            raise ValueError("managed storage identity changed")

    def check_root(self, root: Path) -> None:
        """Restrict all recording/recovery/retention work to the exact managed root."""
        if absolute_path(root) != self.root:
            raise ValueError("managed service refuses writes outside its recording root")
        for held in self._pins:
            held.assert_held()

    def check_output(self, output: str | Path) -> None:
        """Accept only an immediate MP4 in the managed namespace."""
        path = absolute_path(output)
        self.check_root(path.parent)
        if path.suffix.lower() != ".mp4" or path.name.startswith("."):
            raise ValueError("managed output must be an immediate visible MP4")

    def check_state_path(self, path: Path) -> None:
        """Reject caller-selected state outside the protected authoritative directory."""
        path = absolute_path(path)
        if path.parent != self.state:
            raise ValueError("managed service state path is outside protected state")
        self._pins[2].assert_held()

    def check_retention_inputs(self, config_path, job_paths, audit_path) -> None:
        """Bind proof to authoritative state and the unchanged root-bound audit ledger."""
        from .retention_audit import default_audit_path
        if (Path(config_path) != self.config_path
                or job_paths is not None and tuple(job_paths) != self.job_paths
                or audit_path is not None and Path(audit_path) != default_audit_path(self.root)):
            raise ValueError("managed retention requires its authoritative policy/jobs/audit")

    @contextmanager
    def retention_scope(self, root: Path):
        """Exclude new mutations and prove natural quiescence before any authorization."""
        self.check_root(root)
        with self.gate.exclusive():
            self.assert_exclusive()
            yield

    def assert_exclusive(self) -> None:
        """Reprove authority and every relevant mutating process/resource."""
        self.gate.assert_exclusive()
        if self._singleton is None:
            raise ValueError("managed service singleton authority is unavailable")
        named, held = (self.state / ".managed-service.lock").lstat(), os.fstat(self._singleton)
        if (named.st_dev, named.st_ino) != (held.st_dev, held.st_ino):
            raise ValueError("managed service singleton identity changed")
        if not self.quiescent():
            raise ValueError("managed service recording slots are not quiescent")
        assert_quiescent_process(self.uid, self.root)
        self.validate()

    def close(self) -> None:
        """Release service authority only after all components and workers finish."""
        if self._umask is not None:
            os.umask(self._umask)
            self._umask = None
        if self._singleton is not None:
            os.close(self._singleton)
            self._singleton = None
        while self._pins:
            self._pins.pop().close()


def _document(descriptor: int) -> dict:
    data = os.pread(descriptor, 8193, 0)
    if len(data) > 8192:
        raise ValueError("managed storage definition exceeds its size limit")
    from .configuration_json import unique_fields
    result = json.loads(data, object_pairs_hook=unique_fields)
    if not isinstance(result, dict):
        raise ValueError("invalid managed storage definition")
    return result
