"""Distinct running-attempt input protocol; original queued-only guard stays strict."""

from .sealed_inputs import SealedInputs, SealedInputError
from .sealed_input_validation import original_h_binding, verify_inventory
from .session_journal_types import require


class ClaimedInputs(SealedInputs):
    """Continuously held evidence with explicit receipt-scoped successor revisions."""

    def __init__(self, authority, token, owner, revision, seal_hash, fault):
        self.token, self.owner = token, owner
        row = authority.journal.owned_attempt(token)
        require(row is not None, "missing claimed attempt")
        super().__init__(authority, row["session_id"], revision, seal_hash, fault)

    def _target(self):
        with self.authority.lock:
            self.authority.assert_held()
            row = self.authority.journal.claimed_input(self.token)
        owned, task = row["owned"], row["task"]
        require(owned["owner"] == self.owner and owned["revision"] == self.revision
                and owned["seal_hash"] == self.seal_hash and row["phase"] == "running"
                and task["state"] == "running" and task["token"] == self.token
                and task["attempt"] == owned["attempt"], "stale claimed input owner")
        intent, seal = original_h_binding(row, owned["h_revision"], row["h_queue"], row["h_receipt"])
        require(intent.root == self.authority.media.identity, "claimed root/catalog conflicts")
        return row, intent, seal

    def _verify(self):
        self.lifecycle.assert_held()
        for held in self.handles[:2]:
            held.verify()
        owned = self._snapshot["owned"]
        result = verify_inventory(self.authority, self._snapshot, self.intent, self.seal,
            self.directory, self.files, self.marker, h_receipt=self._snapshot["h_receipt"],
            h_revision=owned["h_revision"])
        require(owned["marker_hash"] in (None, result), "attempt marker observation conflicts")
        return result

    def advance(self, receipt):
        """Accept exactly one confirmed transition without silently refreshing stale evidence."""
        with self._lock:
            require(self.acquired and not self.closed and receipt["token"] == self.token
                    and receipt["owner"] == self.owner and receipt["previous_revision"] == self.revision
                    and receipt["revision"] == self.revision + 1, "invalid guard transition")
            previous = self.revision
            self.revision = receipt["revision"]
            try:
                row, _, _ = self._target()
                require(row["owned"]["last_operation"] == receipt["operation"]
                        and {k: v for k, v in row.items() if k != "owned"} ==
                            {k: v for k, v in self._snapshot.items() if k != "owned"},
                        "guard successor changed original evidence")
                self._snapshot = row
            except BaseException:
                self.revision = previous
                raise
            return self.revalidate()


def acquire_claimed_inputs(authority, token, owner, revision, seal_hash, *, fault=lambda _: None):
    """Acquire explicit claimed ownership plus original H; neither token alone suffices."""
    guard = ClaimedInputs(authority, token, owner, revision, seal_hash, fault)
    try:
        guard._acquire()
        return guard
    except BaseException as original:
        guard.extra_handles.extend(getattr(original, "lifecycle_retained_handles", ()))
        guard.extra_descriptors.extend(getattr(original, "lifecycle_retained_descriptors", ()))
        try:
            guard.close()
        except BaseException:
            pass
        raise SealedInputError(guard, original) from original
