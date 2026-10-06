"""Strict original-input proof with one exact locally owned control successor."""

import hashlib
import json

from .capture_handoff_marker import MARKER_NAME, validate_pending_values
from .session_journal_types import require


def check_inputs(cap):
    """Check every original input and only the declared native control chain."""
    guard = cap.runner.guard
    require(guard.manifest_successor is cap and cap.operation is not None
            and guard.files[cap.predecessor_index] is cap.predecessor
            and cap.predecessor.handle == cap.original_handle, "control successor owner changed")
    guard.directory.verify()
    require(guard.directory.identity == guard.intent.parts, "manifest parent changed")
    expected = [a.identity.components[-1] for a in guard.seal.artifacts] + [MARKER_NAME]
    if cap.stage is not None and cap.stage.handle is not None:
        expected.append(cap.stage_name)
    if cap.preserved:
        expected.remove('session.json')
        expected.append(cap.history.name)
    if cap.installed:
        expected.remove(cap.stage_name)
        expected.append('session.json')
    def inventory():
        names = [p.name.casefold() for p in guard.directory.path.iterdir()]
        require(len(names) <= 4099 and len(set(names)) == len(names)
                and sorted(names) == sorted(expected), "manifest successor inventory changed")
    inventory()
    for index, (artifact, held) in enumerate(zip(guard.seal.artifacts, guard.files, strict=True)):
        held.verify()
        identity = cap.history_identity if index == cap.predecessor_index and cap.preserved else artifact.identity
        require(held.identity == identity and held.size == artifact.size and held.stamp == artifact.stamp,
                "original manifest/input native evidence changed")
        if artifact.control_hash is not None:
            require(hashlib.sha256(held.read_control()).hexdigest() == artifact.control_hash,
                    "original control bytes changed")
    if cap.stage is not None:
        cap.stage.verify()
        identity = cap.manifest_identity if cap.installed else cap.stage_identity
        require(cap.stage.identity == identity and cap.stage.path ==
                (cap.manifest if cap.installed else guard.directory.path / cap.stage_name),
                "declared successor native namespace changed")
        if cap.written:
            require(cap.stage.read_control() == cap.successor and cap.stage.stamp == cap.staged_stamp,
                    "staged/installed manifest bytes changed")
        else:
            require(cap.stage.size == 0, "unconfirmed control write")
    marker = guard.marker
    marker.verify()
    require(marker.identity.volume == guard.intent.parts.volume and marker.identity.components ==
            guard.intent.parts.components + (MARKER_NAME,), "marker namespace changed")
    data = marker.read_control()
    values = json.loads(data)
    row, owned = guard._snapshot, guard._snapshot['owned']
    validate_pending_values(guard.authority, guard.intent.session_id, row, values, row['h_receipt'])
    require(values['operation'] == row['h_receipt']['id'] and values['revision'] + 1 == owned['h_revision'],
            "original pending marker H changed")
    inventory()
    for held in (*guard.files, marker, *(() if cap.stage is None else (cap.stage,))):
        held.verify()
    return hashlib.sha256(data).hexdigest()
