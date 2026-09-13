"""Offline regression checks for fresh connection state across explicit resume."""

import json
from threading import Event

import pytest

from tests.test_session_resume import ID, session, update
from tests.test_writer import (audio, audio_configuration, avc_configuration,
                               read_part, video)
from tikrec.capture import CaptureError, capture_tags, capture_url
from tikrec.capture_resume import capture_tags_resume, capture_url_resume


def stream(base=10):
    return [audio_configuration(base), avc_configuration(base, b"config"),
            video(base + 20, 1), audio(base + 25), video(base + 30, 2)]


def manifest(directory):
    return json.loads((directory / "session.json").read_text())


def test_resume_preserves_bytes_identity_start_and_joins_all_parts(tmp_path):
    directory = session(tmp_path)
    update(directory, room_id="12345")
    old = {p.name: p.read_bytes() for p in directory.glob("*.flv")}
    received = []
    output = tmp_path / "final.mp4"

    def finalizer(parts, target):
        received.extend(parts)
        target.write_bytes(b"output")
        return target

    result = capture_tags_resume(stream(), parts_directory=directory, output_path=output,
                                 finalizer=finalizer, clock=lambda: 2000,
                                 media_inspector=lambda _: None)
    assert [p.name for p in result.parts] == ["part-0001.flv", "part-0002.flv", "part-0003.flv"]
    assert received == list(result.parts)
    assert old == {p.name: p.read_bytes() for p in result.parts[:2]}
    assert result.resumed and result.resume_start_index == 3
    facts = manifest(directory)
    assert facts["session_id"] == ID and facts["started_at"] == 1000
    assert facts["room_id"] == "12345" and facts["source_type"] == "direct_flv"
    assert facts["part_count"] == 3 and facts["connection_count"] == 2
    assert facts["ended_at"] == 2000 and facts["elapsed_seconds"] == 1000
    assert facts["status"] == "completed" and facts["finalization"]["status"] == "completed"
    assert facts["recovery_performed"] and "resume_count" not in facts


def test_identical_codec_config_new_clock_and_config_roll_start_new_parts(tmp_path):
    directory = session(tmp_path)
    tags = stream(90000) + [avc_configuration(100000, b"different"), video(100020, 1)]
    result = capture_tags_resume(tags, parts_directory=directory, clock=lambda: 2000)
    assert [p.name for p in result.parts[-2:]] == ["part-0003.flv", "part-0004.flv"]
    assert [t.timestamp for t in read_part(result.parts[-2])] == [0, 0, 0, 5, 10]
    # AAC may carry across codec rolls within this new connection, never from the old process.
    assert [t.timestamp for t in read_part(result.parts[-1])] == [0, 0, 0]


def test_resume_waits_for_own_avc_header_and_keyframe(tmp_path):
    directory = session(tmp_path)
    tags = [video(1, 1), audio(2), avc_configuration(10, b"config"),
            video(20, 2), audio_configuration(25), video(30, 1)]
    result = capture_tags_resume(tags, parts_directory=directory)
    written = read_part(result.parts[-1])
    assert [t.payload for t in written] == [tags[2].payload, tags[4].payload, tags[5].payload]
    assert [t.timestamp for t in written] == [0, 0, 0]


def test_old_avc_and_aac_caches_are_not_reused(tmp_path):
    directory = session(tmp_path)
    result = capture_tags_resume([video(10, 1), audio(15)], parts_directory=directory)
    assert len(result.parts) == 2
    assert not (directory / "part-0003.flv").exists()


def test_old_aac_header_is_not_inserted_into_video_only_resumed_connection(tmp_path):
    directory = session(tmp_path)
    result = capture_tags_resume([avc_configuration(10, b"config"), video(20, 1)], parts_directory=directory)
    assert all(tag.tag_type == 9 for tag in read_part(result.parts[-1]))


def test_direct_flv_resume_uses_injected_source_and_safe_connection_evidence(tmp_path):
    directory = session(tmp_path)
    seen = []
    signed = "https://cdn.test/live.flv?signature=secret"

    def source(url):
        seen.append(url)
        return iter(stream())

    result = capture_url_resume(signed, parts_directory=directory, tag_source=source,
                                session_id=ID, clock=lambda: 2000)
    assert seen == [signed] and len(result.parts) == 3
    log = (directory / "connections.jsonl").read_text()
    assert "secret" not in log and signed not in log
    events = [json.loads(line) for line in log.splitlines()]
    assert events[0]["event"] == "capture_resume" and events[0]["reason"] == "explicit_resume"
    assert events[0]["next_part_index"] == 3 and events[0]["session_id"] == ID
    assert events[1]["connection"] == 2 and events[1]["part_start"] == "part-0003.flv"
    assert result.connections[0].number == 2


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt, "stop"])
def test_interruption_preserves_and_finalizes_old_and_new_parts(tmp_path, interrupt):
    output = tmp_path / "final.mp4"
    directory = session(tmp_path, output=output)
    stop = Event()
    calls = []

    def tags():
        yield from stream()[:3]
        if interrupt == "stop":
            stop.set()
            yield audio(50)
        else:
            raise interrupt()

    def finalizer(parts, target):
        calls.append(tuple(parts))
        assert stop.is_set() or interrupt is KeyboardInterrupt
        target.write_bytes(b"output")
        return target

    result = capture_tags_resume(tags(), parts_directory=directory, output_path=output,
                                 finalizer=finalizer, stop_event=stop, clock=lambda: 2000,
                                 media_inspector=lambda _: None)
    assert result.interrupted and len(result.parts) == 3 and calls == [result.parts]
    assert manifest(directory)["status"] == "interrupted"


def test_stop_before_connection_never_opens_source_and_retains_old_parts(tmp_path):
    directory = session(tmp_path)
    stop = Event()
    stop.set()
    calls = []
    result = capture_url_resume("https://cdn.test/live.flv", parts_directory=directory,
        stop_event=stop, tag_source=lambda _: calls.append(True), clock=lambda: 2000)
    assert result.interrupted and len(result.parts) == 2 and not calls


def test_source_failure_closes_source_and_preserves_all_parts(tmp_path):
    directory = session(tmp_path)
    closed = []

    def tags():
        try:
            yield from stream()
            raise OSError("read failed https://cdn.test/live.flv?secret=x")
        finally:
            closed.append(True)

    with pytest.raises(CaptureError) as failure:
        capture_tags_resume(tags(), parts_directory=directory, clock=lambda: 2000)
    assert len(failure.value.parts) == 3 and closed == [True]
    assert "secret=x" not in str(failure.value)
    assert manifest(directory)["status"] == "failed"
    assert "secret=x" not in (directory / "connections.jsonl").read_text()


def test_finalizer_failure_preserves_all_parts_and_identity(tmp_path):
    directory = session(tmp_path)

    def finalizer(*args):
        raise RuntimeError("mux failed")

    with pytest.raises(CaptureError) as failure:
        capture_tags_resume(stream(), parts_directory=directory, output_path=tmp_path / "final.mp4",
                            finalizer=finalizer, clock=lambda: 2000)
    assert len(failure.value.parts) == 3
    assert manifest(directory)["session_id"] == ID
    assert manifest(directory)["finalization"]["status"] == "failed"


def test_second_interrupt_during_finalization_retains_all_media(tmp_path):
    directory = session(tmp_path)

    def finalizer(*args):
        raise KeyboardInterrupt()

    result = capture_tags_resume(stream(), parts_directory=directory, output_path=tmp_path / "final.mp4",
                                 finalizer=finalizer, clock=lambda: 2000)
    assert result.interrupted and result.output_path is None and len(result.parts) == 3
    assert manifest(directory)["finalization"]["status"] == "interrupted"


def test_repeated_interrupted_resumes_append_evidence_and_increment_numbering(tmp_path):
    directory = session(tmp_path)

    def interrupted():
        yield from stream()
        raise KeyboardInterrupt()

    first = capture_tags_resume(interrupted(), parts_directory=directory, clock=lambda: 2000)
    original_log = (directory / "connections.jsonl").read_bytes()
    second = capture_tags_resume(interrupted(), parts_directory=directory, clock=lambda: 3000)
    assert first.parts[-1].name == "part-0003.flv" and second.parts[-1].name == "part-0004.flv"
    assert (directory / "connections.jsonl").read_bytes().startswith(original_log)
    assert second.connections[0].number == 3
    assert manifest(directory)["connection_count"] == 3 and manifest(directory)["reconnect_count"] == 2


def test_fresh_capture_still_refuses_resume_storage(tmp_path):
    directory = session(tmp_path)
    with pytest.raises(FileExistsError):
        capture_tags(stream(), parts_directory=directory)
    with pytest.raises(FileExistsError):
        capture_url("https://cdn.test/live.flv", parts_directory=directory, tag_source=lambda _: stream())


def test_invalid_resume_never_consumes_source_or_updates_manifest(tmp_path):
    directory = session(tmp_path)
    partial = directory / ".part-0003.flv.partial"
    partial.write_bytes(b"evidence")
    before = (directory / "session.json").read_bytes()
    calls = []
    with pytest.raises(ValueError):
        capture_url_resume("https://cdn.test/live.flv", parts_directory=directory,
                           tag_source=lambda _: calls.append(True))
    assert not calls and before == (directory / "session.json").read_bytes()
    assert partial.read_bytes() == b"evidence"


def test_existing_final_output_is_refused_before_opening_source(tmp_path):
    output = tmp_path / "final.mp4"
    directory = session(tmp_path, output=output)
    output.write_bytes(b"immutable output")
    original = (directory / "session.json").read_bytes()
    calls = []
    with pytest.raises(ValueError):
        capture_url_resume("https://cdn.test/live.flv", parts_directory=directory,
                           output_path=output, tag_source=lambda _: calls.append(True))
    assert not calls and output.read_bytes() == b"immutable output"
    assert (directory / "session.json").read_bytes() == original


def test_generic_resume_can_preserve_a_public_tiktok_session_without_resolution(tmp_path):
    directory = session(tmp_path)
    update(directory, source_type="tiktok_live", room_id="12345")
    result = capture_tags_resume(stream(), parts_directory=directory, source_type="tiktok_live")
    assert result.parts[-1].name == "part-0003.flv"
    assert manifest(directory)["source_type"] == "tiktok_live"
    assert manifest(directory)["room_id"] == "12345"
