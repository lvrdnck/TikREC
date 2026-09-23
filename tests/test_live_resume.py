"""Resume through real writers and ordinary reconnects without network/FFmpeg."""

import json
from threading import Event

import pytest

from tests.test_capture_resume import stream
from tests.test_reconciliation import SIGNED, reconciler, saved_session
from tests.test_writer import read_part
from tikrec.live_resume import capture_live_resume
from tikrec.session_resume import prepare_resume
from tikrec.tiktok import LiveResolution, TikTokOfflineError


def test_service_resume_then_reconnect_keeps_numbering_bytes_and_fresh_timestamps(tmp_path):
    store, job, _ = saved_session(tmp_path)
    old = {p.name: p.read_bytes() for p in (tmp_path / "out.parts").glob("*.flv")}
    recovery = reconciler(store, resolver=lambda _: LiveResolution("123", SIGNED))
    result = recovery.reconcile()
    resolutions, sources, finalized = [], [], []
    def resolve(page):
        resolutions.append(page)
        if len(resolutions) == 1:
            return LiveResolution("123", SIGNED + "2")
        raise TikTokOfflineError("offline", status=4)
    def source(url):
        sources.append(url)
        return iter(stream(90000 if len(sources) == 1 else 10))
    def finalize(parts, output):
        finalized.extend(parts)
        output.write_bytes(b"final")
        return output
    recovery.resolver, recovery.finalizer = resolve, finalize
    recorded = recovery.resume(result, tag_source=source, clock=lambda: 2000,
                               observation_clock=lambda: 2000, sleeper=lambda _: None)
    assert sources == [SIGNED, SIGNED + "2"]
    assert len(resolutions) == 4
    assert recorded.resumed and recorded.resume_start_index == 3
    assert [p.name for p in recorded.parts] == [f"part-{i:04d}.flv" for i in range(1, 5)]
    assert old == {p.name: p.read_bytes() for p in recorded.parts[:2]}
    assert [t.timestamp for t in read_part(recorded.parts[2])] == [0, 0, 0, 5, 10]
    assert [t.timestamp for t in read_part(recorded.parts[3])] == [0, 0, 0, 5, 10]
    assert finalized == list(recorded.parts)
    facts = json.loads((tmp_path / "out.parts/session.json").read_text())
    assert facts["session_id"] == job.session_id and facts["started_at"] == 1000
    assert facts["room_id"] == "123" and facts["connection_count"] == 5
    evidence = (tmp_path / "out.parts/connections.jsonl").read_text()
    assert "secret" not in evidence
    events = [json.loads(line) for line in evidence.splitlines()]
    assert any(e.get("event") == "capture_resume" and e["next_part_index"] == 3 for e in events)
    assert [e["connection"] for e in events if "event" not in e] == [3, 4, 5]


def test_later_different_live_is_never_connected(tmp_path):
    _, job, _ = saved_session(tmp_path)
    sources = []
    def source(url):
        sources.append(url)
        return iter(stream())
    recorded = capture_live_resume(
        job.source_url, parts_directory=tmp_path / "out.parts", output_path=tmp_path / "out.mp4",
        session_id=job.session_id, resolution=LiveResolution("123", SIGNED),
        resolver=lambda _: LiveResolution("456", "https://cdn.test/new.flv"), tag_source=source,
        finalizer=lambda parts, output: output, sleeper=lambda _: None, media_inspector=lambda _: None)
    assert sources == [SIGNED] and len(recorded.parts) == 3
    assert json.loads((tmp_path / "out.parts/session.json").read_text())["room_id"] == "123"
    events = [json.loads(line) for line in (tmp_path / "out.parts/connections.jsonl").read_text().splitlines()]
    assert events[-1]["outcome"] == "live_changed"
    assert not any(e.get("event") == "room_status" for e in events)


def test_prior_stop_event_never_opens_resumed_source(tmp_path):
    _, job, _ = saved_session(tmp_path)
    stop = Event()
    stop.set()
    recorded = capture_live_resume(
        job.source_url, parts_directory=tmp_path / "out.parts", output_path=tmp_path / "out.mp4",
        session_id=job.session_id, resolution=LiveResolution("123", SIGNED), stop_event=stop,
        tag_source=lambda _: pytest.fail("must not open source"),
        finalizer=lambda parts, output: output, media_inspector=lambda _: None)
    assert recorded.interrupted and len(recorded.parts) == 2


def test_same_room_check_is_repeated_before_resume(tmp_path):
    _, job, _ = saved_session(tmp_path)
    with pytest.raises(ValueError, match="conflicts"):
        capture_live_resume(job.source_url, parts_directory=tmp_path / "out.parts",
                            output_path=tmp_path / "out.mp4", session_id=job.session_id,
                            resolution=LiveResolution("456", SIGNED))
    assert not (tmp_path / "out.parts/connections.jsonl").exists()


def test_fresh_resume_preflight_rejects_changed_creator_without_mutation(tmp_path):
    store, job, _ = saved_session(tmp_path)
    assert reconciler(store, resolver=lambda _: LiveResolution("123", SIGNED)).reconcile().outcome == "resume"
    path = tmp_path / "out.parts/session.json"
    values = json.loads(path.read_text())
    values["creator"] = "beta"
    path.write_text(json.dumps(values))
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="creator|identity"):
        capture_live_resume(job.source_url, parts_directory=tmp_path / "out.parts",
                            output_path=tmp_path / "out.mp4", session_id=job.session_id,
                            resolution=LiveResolution("123", SIGNED),
                            tag_source=lambda _: pytest.fail("source must not open"),
                            media_inspector=lambda _: None)
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("saved_creator", ["creator", None])
def test_fresh_resume_accepts_equivalent_or_legacy_absent_creator(tmp_path, saved_creator):
    _, job, _ = saved_session(tmp_path)
    path = tmp_path / "out.parts/session.json"
    if saved_creator is not None:
        values = json.loads(path.read_text())
        values["creator"] = saved_creator
        path.write_text(json.dumps(values))
    stop = Event()
    stop.set()
    recorded = capture_live_resume(
        "https://www.tiktok.com/@Creator/live", parts_directory=tmp_path / "out.parts",
        output_path=tmp_path / "out.mp4", session_id=job.session_id,
        resolution=LiveResolution("123", SIGNED), stop_event=stop,
        tag_source=lambda _: pytest.fail("stopped resume must not open source"),
        finalizer=lambda parts, output: output, media_inspector=lambda _: None)
    assert recorded.resumed
    assert json.loads(path.read_text()).get("creator") == saved_creator


def test_repeated_crash_reserves_new_connection_and_increments_resume_count(tmp_path):
    store, job, _ = saved_session(tmp_path)
    first = reconciler(store, resolver=lambda _: LiveResolution("123", SIGNED)).reconcile()
    assert first.job.resume_count == 1
    # A committed resume decision can outlive a crash before its new connection is opened.
    second = reconciler(store, resolver=lambda _: LiveResolution("123", SIGNED)).reconcile()
    assert second.job.resume_count == 2
    session = prepare_resume(tmp_path / "out.parts", session_id=job.session_id)
    assert session.next_connection == 3 and session.retained.next_index == 3


def test_source_error_signed_url_is_redacted_from_resumed_connection_evidence(tmp_path):
    _, job, _ = saved_session(tmp_path)
    def source(url):
        raise OSError("read failed " + url)
    def resolve(page):
        raise TikTokOfflineError("offline", status=4)
    capture_live_resume(job.source_url, parts_directory=tmp_path / "out.parts",
        output_path=tmp_path / "out.mp4", session_id=job.session_id,
        resolution=LiveResolution("123", SIGNED), resolver=resolve, tag_source=source,
        finalizer=lambda parts, output: output, sleeper=lambda _: None, media_inspector=lambda _: None)
    evidence = (tmp_path / "out.parts/connections.jsonl").read_text()
    assert "secret" not in evidence and "[URL redacted]" in evidence
