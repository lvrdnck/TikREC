"""Adapt existing persisted automatic claims to schema-10 indexed acceptance."""

from dataclasses import asdict
from uuid import NAMESPACE_URL, uuid5

from .service_runtime_capture import start_capture
from .session_journal_types import encode, require


def claim_id(claim):
    """Derive a stable UUID from the entire already-persisted schema-1 claim.

    No new state/schema is needed: every field, including previous session,
    participates. A different intended path/generation has a different key.
    This key identifies acceptance only and never restores writer authority.
    """
    claim.validate()
    return str(uuid5(NAMESPACE_URL, 'tikrec-isolated-automatic-v1:' + encode(asdict(claim))))


def reconcile_claim(runtime, claim):
    """Use indexed validated historical receipt; idle slots are not negative proof."""
    with runtime.lock:
        runtime.authority.assert_held()
        receipt = runtime.journal.automatic_receipt(claim_id(claim))
        if receipt is None:
            return False
        row = runtime.journal.session(receipt['session'])
        intent = row['intent']
        require(row['creator'] == claim.creator and row['expected_room'] == claim.room_id
                and intent['output_path'] == claim.output_path
                and intent['parts_path'] == claim.parts_directory,
                'automatic accepted intent conflicts')
        return True


def start_automatic(runtime, claim, raw):
    """Commit the deterministic persisted-claim key with original acceptance."""
    return start_capture(runtime, 'https://www.tiktok.com/@' + claim.creator + '/live',
        claim.output_path, raw, claim.room_id, automatic_claim=claim_id(claim))
