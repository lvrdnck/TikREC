"""Two real replacement writers coexist with two old queued fixture sessions."""

import os
from pathlib import Path
from threading import Event, Thread

import pytest

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tikrec.capture_handoff_native import NativeHandle
from tikrec.session_journal_types import JournalConflict
from tikrec.source import iter_tags

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows concurrent capture")


def test_two_real_writers_after_two_handoffs_and_late_old_callbacks_refused(tmp_path, monkeypatch):
    import tikrec.live as module
    original, callbacks = module.write_live_connection, []
    def remember(*args, **kwargs):
        callbacks.append(kwargs["on_part_retained"])
        return original(*args, **kwargs)
    monkeypatch.setattr(module, "write_live_connection", remember)
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        old = (reserve(owner), reserve(owner, "two", "222", "other", raw=False))
        for bridge, room in zip(old, ("123", "222")):
            bridge.run(**observations(data, room))
        originals = [owner.journal.session(b.intent.session_id) for b in old]
        saved = callbacks[0]
        new = (reserve(owner, "three", "456", raw=False, slot=1),
               reserve(owner, "four", "789", "other", raw=False, slot=2))
        release, ready = Event(), (Event(), Event())
        results, errors = [], []
        def run(index):
            def source(_):
                for tag in iter_tags((data,)):
                    yield tag
                    if tag.tag_type == 9 and tag.is_media and not ready[index].is_set():
                        ready[index].set()
                        assert release.wait(10), "source close barrier timed out"
            options = observations(data, ("456", "789")[index])
            options["tag_source"] = source
            try:
                results.append(new[index].run(**options))
            except BaseException as error:
                errors.append(error)
        threads = [Thread(target=run, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        try:
            assert all(event.wait(5) for event in ready)
            status = owner.journal.status()
            assert [b["session"] for b in status["bindings"]] == [b.intent.session_id for b in new]
            assert len(status["tasks"]) == 2
            for bridge in new:
                path = Path(bridge.intent.parts_path, ".part-0001.flv.partial")
                with pytest.raises(OSError):
                    NativeHandle(path)
            with pytest.raises(JournalConflict):
                saved(Path(old[0].intent.parts_path, "part-9999.flv"))
            assert [owner.journal.session(b.intent.session_id) for b in old] == originals
        finally:
            release.set()
            for thread in threads:
                thread.join(10)
        assert not errors and len(results) == 2 and all(r.phase == "queued" for r in results)
        assert [t["session"] for t in owner.journal.status()["tasks"]][:2] == [b.intent.session_id for b in old]
