"""Disposable process-death probe running actual local capture and journal H."""

import json
import os
import sys
from pathlib import Path

from tests.capture_handoff_helpers import authority, observations, reserve
from tikrec.source import iter_tags


def main():
    """Die at the requested boundary, leaving all authoritative files intact."""
    root, fixture, boundary = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    data = fixture.read_bytes()
    empty = boundary.startswith("empty_")
    boundary = boundary.removeprefix("empty_")
    with authority(root) as owner:
        old = reserve(owner, raw=not empty)
        with (root / "context.json").open("w") as handle:
            json.dump({"catalog": owner.journal.catalog_id, "old": old.intent.session_id}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        if boundary in {"after_marker", "confirmed_h"}:
            def fault(name):
                if name == boundary:
                    os._exit(73)
            old._fault = fault
        elif boundary != "after_slot_reuse":
            def fault(kind, name):
                if kind == ("settle_empty_capture" if empty else "handoff") and name == boundary:
                    os._exit(73)
            owner.journal._fault = fault
        options = observations(data)
        if empty:
            options["tag_source"] = lambda _: iter(())
        old.run(**options)
        if boundary == "after_slot_reuse":
            new = reserve(owner, "two", "456", raw=False, slot=1)
            options = observations(data, "456")
            def source(_):
                for tag in iter_tags((data,)):
                    yield tag
                    if tag.tag_type == 9 and tag.is_media:
                        # The real writer has consumed this keyframe before next().
                        os._exit(73)
            options["tag_source"] = source
            new.run(**options)
        raise AssertionError("crash boundary was never exercised")


if __name__ == "__main__":
    main()
