"""Single-use live namespace successor for the original validated candidate owner."""

import json
import os
from dataclasses import asdict
from pathlib import Path

from .publication_native import rename_no_replace
from .session_journal_types import ArtifactIdentity, digest, encode, require


class CandidatePublication:
    """Historical receipts cannot recreate this continuously retained local capability."""

    def __init__(self, validation):
        self.validation, self.runner = validation, validation.coordinator
        runner = self.runner
        require(getattr(runner, "publication_capable", False) and validation.used and validation.error is None
                and validation.report is not None and validation.report["passed"]
                and validation.capability is not None and validation.capability.index == 3,
                "live publication-capable validation required")
        require(getattr(runner, "publication_owner", None) is None, "publication capability already allocated")
        runner.publication_owner = self
        self.scratch = runner.scratch
        self.held = self.scratch.artifacts["candidate.mp4"]
        self.original_handle, self.original_fd = self.held.handle, self.held.fd
        self.parent = runner.authority.media
        session = runner.journal.session(runner.claimed["session_id"])
        self.output = Path(session["intent"]["output_path"])
        self.destination = ArtifactIdentity(session["intent"]["output"]["volume"],
                                            tuple(session["intent"]["output"]["components"]))
        owner = runner.journal.owned_attempt(runner.token)
        self.binding = {k: owner[k] for k in
                        ("session_id", "token", "owner", "h_operation", "h_revision", "seal_hash", "marker_hash")}
        self.binding.update(candidate=owner["scratch"]["candidate"], validation=runner.journal.validation(runner.token),
            inventory=self.scratch.observed, workspace=asdict(self.scratch.workspace.identity),
            destination={"path": str(self.output), "identity": asdict(self.destination),
                         "parent": asdict(self.parent.identity), "parent_stamp": self.parent.stamp})
        # Freeze canonical bytes; tuple/list JSON representation must match receipts.
        self.binding = json.loads(encode(self.binding))
        self.operation, self.used, self.moved = None, False, False

    def _live(self):
        require(not self.runner.closed and not self.runner.cancelled.is_set() and self.scratch.failure is None
                and self.validation.error is None and self.validation.capability.runner is self.runner
                and self.runner.publication_owner is self and self.runner.scratch is self.scratch
                and self.scratch.artifacts["candidate.mp4"] is self.held
                and self.held.handle == self.original_handle and self.held.fd == self.original_fd,
                "publication live ownership revoked or replaced")

    def _parent(self):
        self.parent.verify()
        require(self.output.parent == self.parent.path and self.output.suffix.casefold() == ".mp4"
                and asdict(self.parent.identity) == asdict(ArtifactIdentity(
                    self.binding["destination"]["parent"]["volume"], tuple(self.binding["destination"]["parent"]["components"])))
                and self.parent.stamp.split(":")[:2] == self.binding["destination"]["parent_stamp"].split(":")[:2]
                and self.destination.volume == self.held.identity.volume
                and self.destination.components == self.parent.identity.components + (self.output.name.casefold(),),
                "publication destination parent/volume conflicts")

    def check_scratch(self):
        """Accept only the declared local successor, with every other inventory check strict."""
        require(self.moved and self.scratch.publication_successor is self,
                "unproved scratch successor")
        self._parent()
        expected = [a for a in self.binding["inventory"] if a["name"] != "candidate.mp4"]
        require(sorted(e.name for e in os.scandir(self.scratch.path)) == [a["name"] for a in expected],
                "publication scratch successor inventory changed")
        for item in expected:
            held = self.scratch.artifacts[item["name"]]
            held.verify()
            require(json.loads(encode(asdict(held.identity))) == item["identity"] and held.size == item["size"]
                    and held.stamp == item["stamp"], "publication helper changed")
        self.held.verify()
        candidate = self.binding["candidate"]
        require(self.held.identity == self.destination and self.held.path == self.output
                and self.held.stamp == candidate["stamp"] and self.held.size == candidate["size"]
                and self.held._path_identity() == self.destination, "publication output native proof changed")

    def revalidate(self):
        """Bracket durable/native boundaries with exact input/inventory/byte proof."""
        self._live()
        self._parent()
        if not self.moved:
            self.validation.capability.revalidate()
            require(not self.output.exists() and not self.output.is_symlink(), "publication destination exists")
        else:
            self.scratch._revalidate()
            require(self.validation.capability._hash(self.held) == self.binding["candidate"]["sha256"],
                    "published bytes changed")
            self.scratch._revalidate()
        require(self.runner.journal.validation(self.runner.token) == self.binding["validation"],
                "publication validation evidence changed")

    def promote(self):
        """Prepare once, rename once, append only observed proof; never replay uncertainty."""
        require(not self.used, "publication capability is single-use")
        self.used = True
        runner = self.runner
        self.revalidate()
        runner._fault("before_publication_preparation")
        self.revalidate()
        prepared = runner._transition("prepare_publication", runner.journal.prepare_publication, self.binding)
        self.operation = prepared["operation"]
        runner._fault("after_publication_preparation")
        self.revalidate()
        runner._fault("before_publication_fence")
        self.revalidate()
        # No callbacks, inventory scans, hashing or waiting inside this fence.
        # Event-setting cancellation and durable revocation serialize with rename.
        with runner.gate:
            self._live()
            with runner.journal.publication_fence(runner.token, runner.owner, runner.revision,
                                                  self.operation, digest(self.binding)):
                rename_no_replace(self.held, self.parent, self.output.name)
                self.moved = True
                self.held.path, self.held.identity = self.output, self.destination
                self.scratch.publication_successor = self
        runner._fault("after_publication_native")
        self.revalidate()
        candidate = self.binding["candidate"]
        evidence = {"state": "observed_published", "preparation_operation": self.operation,
            "binding_hash": digest(self.binding), "identity": self.binding["destination"]["identity"],
            "size": candidate["size"], "stamp": candidate["stamp"], "sha256": candidate["sha256"]}
        runner._fault("before_publication_result")
        self.revalidate()
        runner._transition("observe_publication", runner.journal.observe_publication, evidence)
        runner._fault("after_publication_result")
        self.revalidate()
        return evidence
