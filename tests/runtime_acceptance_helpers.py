"""Independent chunk barriers over generated FLV bytes and durable evidence."""

import hashlib
from pathlib import Path
from threading import Event

from tests.capture_handoff_helpers import observations
from tikrec.source import iter_tags


def progressing_sources(case, runtime, names):
    """Pause twice after real tags reached each writer, without replacing callbacks."""
    original = runtime.observations
    data = (runtime.root.parent / 'source-one.flv').read_bytes()
    ends, offset = [], 13
    while offset < len(data):
        offset += 11 + int.from_bytes(data[offset + 1:offset + 4], 'big') + 4
        ends.append(offset)
    assert offset == len(data) and len(ends) > 9
    # Whole-tag splits ensure the source barrier follows a processed writer tag.
    cuts = [0, ends[len(ends) // 3], ends[2 * len(ends) // 3], len(data)]
    barriers = {}
    for name in names:
        ready, advance = [Event(), Event()], [Event(), Event()]
        barriers[name] = ready, advance
        case.releases.extend(advance)

    def supplied(bridge):
        name = Path(bridge.intent.output_path).stem
        if name not in barriers:
            return original(bridge)
        ready, advance = barriers[name]

        def chunks(raw=None):
            for index in range(3):
                chunk = data[cuts[index]:cuts[index + 1]]
                if raw is not None:
                    raw.write(chunk)
                yield chunk
                if index < 2:
                    ready[index].set()
                    assert advance[index].wait(90), 'progressing source barrier unreleased'
            if raw is not None:
                raw.observe_read_end('eof')

        result = observations(data, room=bridge.intent.expected_room)
        result.update(tag_source=lambda _: iter_tags(chunks()),
                      raw_tag_source=lambda _, raw: iter_tags(chunks(raw)))
        return result

    runtime.observations = supplied
    return barriers, data


def immutable_session(journal, sid):
    """Snapshot original session identity/seal and its permanent H receipt."""
    row = journal.session(sid)
    identity = {key: row[key] for key in
                ('intent', 'seal', 'seal_hash', 'generation', 'origin_slot')}
    receipts = journal._read(lambda db: [tuple(r) for r in db.execute(
        "SELECT * FROM operations WHERE kind IN ('handoff','settle_empty_capture')")])
    return identity, receipts


def file_hashes(paths):
    """Hash explicitly supplied disposable files; never scan production media."""
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
