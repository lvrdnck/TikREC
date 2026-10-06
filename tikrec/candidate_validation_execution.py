"""Live validation capability cannot be reconstructed from journal inspection."""

import hashlib
import os

from .attempt_execution import run_child
from .session_journal_types import require


class CandidateValidationExecution:
    """Keep the original scratch owner and binding through three exact validators."""

    def __init__(self, runner, binding):
        self.runner, self.binding = runner, binding
        self.operation, self.index = None, 0
        require(getattr(runner, "validation_readers", False) and runner.scratch.candidate_ready
                and runner.scratch.failure is None, "live validation-readable candidate required")
        runner.validation_retained = True

    def revalidate(self):
        """Recheck complete inventory and native bytes without replacing any owner."""
        scratch = self.runner.scratch
        scratch._revalidate()
        candidate = self.binding["candidate"]
        held = scratch.artifacts[candidate["name"]]
        require(held.handle is not None and held.fd is not None
                and held.size == candidate["size"] and held.stamp == candidate["stamp"]
                and self._hash(held) == candidate["sha256"], "validation candidate bytes changed")
        scratch._revalidate()

    def readable(self):
        """Prove nonempty regular candidate bytes through original native ownership."""
        self.revalidate()
        held = self.runner.scratch.artifacts[self.binding["candidate"]["name"]]
        os.lseek(held.fd, 0, os.SEEK_SET)
        require(held.size > 0 and len(os.read(held.fd, 1)) == 1, "candidate unreadable")
        return True

    def _hash(self, held):
        """Hash the retained descriptor with cancellation checks between bounded reads."""
        value = hashlib.sha256()
        os.lseek(held.fd, 0, os.SEEK_SET)
        while True:
            require(not self.runner.cancelled.is_set(), "validation execution revoked")
            chunk = os.read(held.fd, 1024 * 1024)
            if not chunk:
                return value.hexdigest()
            value.update(chunk)

    def begin(self):
        """Persist a single-use authority only after native candidate revalidation."""
        self.revalidate()
        result = self.runner._transition("begin_validation", self.runner.journal.begin_validation, self.binding)
        self.operation = result["operation"]
        self.runner._fault("after_validation_authority")
        self.revalidate()

    def execute(self, command, collector):
        """Run only the next fixed validator, retaining bounded cleanup on all faults."""
        require(self.operation is not None and self.index < 3
                and command == self.binding["commands"][self.index], "validation command not authorized")
        runner = self.runner
        with runner.run_lock:
            evidence = run_child(runner, command[0], command[1:], self.binding["workspace"],
                "candidate_validation", None, collector.observe, on_exit=collector.finish, validation=self)
            self.index += 1
            return evidence
