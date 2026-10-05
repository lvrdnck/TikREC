"""Attempt-bound scratch reservation and protected unpublished candidate evidence."""

import hashlib
import os
from dataclasses import asdict
from pathlib import Path

from .capture_handoff_native import NativeHandle, child_identity
from .session_journal_types import ArtifactIdentity, digest, require


class ScratchHandle(NativeHandle):
    """Retain exact partial acquisition and unconfirmed native close identity."""

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except BaseException as original:
            # Inherited construction already tries exact cleanup. A failed
            # close exposes this owner explicitly, without traceback access.
            if getattr(self, "handle", None) is not None:
                original.scratch_native_owner = self
            raise

    def close(self):
        """Keep a failed CloseHandle/_close reachable until native close confirms."""
        if self.handle is None:
            return
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
            self.handle = None
        elif self.api.CloseHandle(self.handle):
            self.handle = None
        else:
            raise OSError("scratch native handle close was not confirmed")


class AttemptScratch:
    """One local scratch capability; receipts never reconstruct this native owner."""

    def __init__(self, runner, intent):
        self.runner, self.intent = runner, intent
        self.path = Path(intent["workspace_path"])
        self.parent = runner.authority.media
        self.workspace = None
        self.created = False
        self.artifacts = {}
        self.observed = None
        self.candidate_ready = False
        self.failure = None

    @classmethod
    def reserve(cls, runner, helpers=()):
        """Persist a generated, input-bound sibling scope before exclusive mkdir."""
        require(runner.claimed is not None and runner.guard is not None
                and not runner.closed and not runner.cancelled.is_set(), "current attempt required")
        require(type(helpers) in (list, tuple) and len(helpers) <= 31
                and all(type(x) is str for x in helpers), "invalid scratch helper declarations")
        names = ["candidate.mp4", *helpers]
        require(len(set(names)) == len(names), "duplicate scratch declarations")
        name = f".tikrec-attempt-{runner.token}"
        path = runner.authority.root / name
        parent = runner.authority.media.identity
        workspace = ArtifactIdentity(parent.volume, parent.components + (name.casefold(),))
        session = runner.journal.session(runner.claimed["session_id"])
        owner = runner.journal.owned_attempt(runner.token)
        intent = {"catalog_id": runner.journal.catalog_id,
                  "session_id": runner.claimed["session_id"], "h_operation": owner["h_operation"],
                  "h_revision": owner["h_revision"], "seal_hash": runner.guard.seal_hash,
                  "marker_hash": runner.guard.revalidate().marker_sha256, "workspace_path": str(path),
                  "parent": asdict(parent), "workspace": asdict(workspace),
                  "artifacts": [{"name": "candidate.mp4", "role": "candidate", "required": True},
                                *[{"name": x, "role": "helper", "required": False} for x in helpers]]}
        require(not workspace.overlaps(ArtifactIdentity(**{**session["intent"]["output"],
                "components": tuple(session["intent"]["output"]["components"])}))
                and not workspace.overlaps(ArtifactIdentity(**{**session["intent"]["parts"],
                "components": tuple(session["intent"]["parts"]["components"])})),
                "scratch overlaps sealed input or final output")
        scratch = cls(runner, intent)
        runner.scratch = scratch
        runner._transition("reserve_scratch", runner.journal.reserve_scratch, intent)
        runner._fault("after_scratch_intent")
        scratch._create()
        return scratch

    def _create(self):
        """Exclusively create and immediately retain the observed directory owner."""
        self.runner.authority.assert_held()
        self.parent.verify()
        try:
            self.workspace = ScratchHandle.create_directory(self.parent, self.path.name)
        except BaseException as error:
            self.workspace = getattr(error, "scratch_native_owner", None)
            self.created = bool(getattr(error, "scratch_native_created", False))
            raise
        self.created = True
        self.runner._fault("after_scratch_create")
        require(self.workspace.identity == ArtifactIdentity(
            self.intent["workspace"]["volume"], tuple(self.intent["workspace"]["components"])),
            "created scratch native identity conflicts")
        self._revalidate()
        self._assert_empty()
        self.runner._transition("bind_scratch", self.runner.journal.bind_scratch,
                                asdict(self.workspace.identity), self.workspace.stamp)
        self.runner._fault("after_scratch_bind")
        self._revalidate()
        self._assert_empty()

    def _assert_empty(self):
        """Refuse any unexplained entry before the one authorized writer starts."""
        require(not sorted(entry.name for entry in os.scandir(self.path)),
                "scratch inventory is not empty before writer")

    def _revalidate(self):
        """Recheck inputs, complete observed inventory and every held artifact unlocked."""
        self.runner.authority.assert_held()
        self.runner.guard.revalidate()
        require(self.workspace is not None and self.workspace.handle is not None,
                "scratch native owner unavailable")
        self.parent.verify()
        self.workspace.verify()
        require(self.workspace.identity == ArtifactIdentity(
            self.intent["workspace"]["volume"], tuple(self.intent["workspace"]["components"])),
            "scratch namespace identity changed")
        if self.observed is not None:
            names = sorted(entry.name for entry in os.scandir(self.path))
            require(names == [item["name"] for item in self.observed],
                    "scratch inventory changed after observation")
            for item in self.observed:
                held = self.artifacts[item["name"]]
                held.verify()
                require(asdict(held.identity) == item["identity"] and held.size == item["size"]
                        and held.stamp == item["stamp"], "scratch artifact evidence changed")

    def assert_outputs_absent(self, outputs):
        """Fence declared candidate/helper collisions at both process authorization edges."""
        self._revalidate()
        self._assert_empty()
        declared = {item["name"] for item in self.intent["artifacts"]}
        require(set(outputs) <= declared, "writer requested undeclared scratch output")
        for name in outputs:
            target = self.path / name
            require(not target.exists() and not target.is_symlink(),
                    "declared scratch output already exists")
            require(child_identity(self.workspace, name) == ArtifactIdentity(
                self.workspace.identity.volume, self.workspace.identity.components + (name.casefold(),)),
                "scratch output namespace alias")

    def run_writer(self, executable, arguments, *, timeout, outputs=("candidate.mp4",), phase="writer"):
        """Run a separately authorized output child with explicit reserved artifacts."""
        outputs = tuple(outputs)
        require(outputs and len(outputs) == len(set(outputs)), "explicit unique output declarations required")
        return self.runner.run_writer_child(executable, arguments, cwd=self.path,
            phase=phase, timeout=timeout, outputs=outputs)

    def _observe_artifacts(self, outputs):
        """Pin every entry against new writes/deletion; refuse aliases or undeclared files."""
        self._revalidate()
        names = sorted(entry.name for entry in os.scandir(self.path))
        declared = {item["name"] for item in self.intent["artifacts"]}
        require(set(names) <= declared and set(outputs) == set(names),
                "scratch contains unexplained or missing artifacts")
        observed = []
        for name in names:
            try:
                # Validation opts into read sharing at original acquisition. This
                # same read/write owner still denies all new writes and deletion.
                held = ScratchHandle(self.path / name,
                    share_mode=1 if getattr(self.runner, "validation_readers", False) else 0)
            except BaseException as original:
                partial = getattr(original, "scratch_native_owner", None)
                if partial is not None:
                    self.artifacts[name] = partial
                for cleanup in getattr(original, "capture_cleanup_errors", ()):
                    self.runner._error(cleanup)
                raise
            self.artifacts[name] = held
            held.flush()
            require(held.identity.volume == self.workspace.identity.volume
                    and held.identity.components[:-1] == self.workspace.identity.components
                    and held.identity.components[-1] == name.casefold(),
                    "artifact native identity escaped scratch scope")
            observed.append({"name": name, "identity": asdict(held.identity),
                             "size": held.size, "stamp": held.stamp})
        self.observed = observed
        self._revalidate()
        return observed

    @staticmethod
    def _hash(held):
        """Hash only through the write-protected held identity, never a reopened path."""
        digest_value = hashlib.sha256()
        os.lseek(held.fd, 0, os.SEEK_SET)
        while chunk := os.read(held.fd, 1024 * 1024):
            digest_value.update(chunk)
        return digest_value.hexdigest()

    def seal_candidate(self, launch, *, input_decode="unknown"):
        """Preserve every candidate/helper owner if sealing stops at any boundary."""
        try:
            return self._seal_candidate(launch, input_decode=input_decode)
        except BaseException as original:
            self.hold(original)
            raise

    def _seal_candidate(self, launch, *, input_decode="unknown"):
        """Commit native artifact bindings, then an unvalidated unpublished outcome."""
        require(not self.candidate_ready and input_decode in {"clean", "degraded", "unknown"},
                "scratch candidate already sealed or classification invalid")
        child = self.runner.journal.owned_attempt(self.runner.token)["child"]
        require(child is not None and child["id"] == launch and child["intent"].get("access") == "write"
                and child["exit"] is not None and child["exit"]["state"] == "confirmed_exited"
                and child["exit"]["code"] == 0 and child["diagnostics"] is not None
                and child["diagnostics"]["complete"] and child["cleanup"] == 1,
                "writer execution evidence is incomplete")
        outputs = child["intent"]["outputs"]
        self._revalidate()
        observed = self._observe_artifacts(outputs)
        by_name = {item["name"]: item for item in observed}
        require("candidate.mp4" in by_name and by_name["candidate.mp4"]["size"] > 0,
                "candidate is empty or absent")
        self.runner._fault("after_candidate_created")
        self._revalidate()
        self.runner._transition("bind_scratch_artifacts", self.runner.journal.bind_scratch_artifacts,
                                launch, observed)
        self.runner._fault("after_artifact_bind")
        candidate = by_name["candidate.mp4"]
        held = self.artifacts["candidate.mp4"]
        self._revalidate()
        sha = self._hash(held)
        self._revalidate()
        require(held.size == candidate["size"] and held.stamp == candidate["stamp"],
                "candidate changed while hashing")
        evidence = {**candidate, "sha256": sha, "input_decode": input_decode,
                    "diagnostics_hash": digest(child["diagnostics"])}
        self._revalidate()
        self.runner._fault("before_candidate_ready")
        self._revalidate()
        self.runner._transition("seal_candidate", self.runner.journal.seal_candidate, launch, evidence)
        self.candidate_ready = True
        self.runner._fault("after_candidate_ready")
        return self.runner.journal.scratch(self.runner.token)["candidate"]

    def hold(self, original=None):
        """Keep all partials and exact native owners after failure or cancellation."""
        if self.failure is None:
            self.failure = original
        self.runner.cancelled.set()
        try:
            record = self.runner.journal.scratch(self.runner.token)
            if record is None or record["state"] in {"held", "candidate_ready"}:
                return
            first = (self.failure if self.failure is not None else
                     RuntimeError("attempt scratch cancelled before candidate sealing"))
            reason = {"first": repr(first)[:2048],
                      "secondary": [repr(error)[:2048] for error in self.runner.errors[:32]]}
            self.runner._transition("hold_scratch", self.runner.journal.hold_scratch, reason)
        except BaseException as error:
            self.runner._error(error)

    def protection_evidence(self):
        """Report retained local handles separately from durable candidate state."""
        return {"candidate_ready_local": self.candidate_ready,
                "workspace_retained": self.workspace is not None and self.workspace.handle is not None,
                "artifacts_retained": sorted(name for name, held in self.artifacts.items()
                                              if held.handle is not None or held.fd is not None)}

    def close_candidate_protection(self):
        """Release local pins only after candidate ownership and child exit are durable."""
        record = self.runner.journal.scratch(self.runner.token)
        require(record is not None and record["state"] == "candidate_ready",
                "failed or ambiguous scratch protection must remain retained")
        errors = []
        for held in reversed(list(self.artifacts.values())):
            try:
                held.close()
            except BaseException as error:
                errors.append(error)
        if self.workspace is not None:
            try:
                self.workspace.close()
            except BaseException as error:
                errors.append(error)
        if errors:
            for error in errors:
                self.runner._error(error)
            return False
        return True
