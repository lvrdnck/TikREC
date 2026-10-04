"""R6–R7 deterministic state regressions, separate from native containment proof."""

from pathlib import Path
from threading import Event, Thread

import pytest

from tests.owned_process_state_helpers import Native, state_owner
from tikrec.owned_process import ProcessOwnerError


@pytest.mark.parametrize("action", ["close", "cancel"])
def test_validation_gap_cannot_create_after_cleanup_intent(tmp_path, monkeypatch, state_owner, action):
    owner, executable = state_owner
    entered, release, errors = Event(), Event(), []
    original = Path.is_file
    def validation(path):
        if path == executable:
            entered.set()
            assert release.wait(10)
        return original(path)
    monkeypatch.setattr(Path, "is_file", validation)
    def start():
        try:
            owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)
        except BaseException as error:
            errors.append(error)
    thread = Thread(target=start)
    thread.start()
    try:
        assert entered.wait(10)
        assert getattr(owner, action)(0).state == "not_created"
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive()
    assert not Native.instances and len(errors) == 1 and isinstance(errors[0], ProcessOwnerError)
    assert owner.close(0).state == "not_created" and owner.closed
    with pytest.raises(ValueError, match="single-use"):
        owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)


@pytest.mark.parametrize("action", ["close", "cancel"])
def test_cleanup_before_start_is_irreversible(tmp_path, state_owner, action):
    owner, executable = state_owner
    getattr(owner, action)(0)
    with pytest.raises(ValueError):
        owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)
    assert not Native.instances


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_status_boundary_tail_is_delivered_exactly_once(tmp_path, state_owner, stream):
    owner, executable = state_owner
    owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)
    owner.native.tail = {stream: b"final-tail"}
    seen = []
    result = owner.poll(observer=lambda name, data: seen.append((name, data)))
    assert result.state == "confirmed_exited"
    assert getattr(result, stream) == b"final" and seen == [(stream, b"final-tail")]
    assert result.truncated == ((5, 0) if stream == "stdout" else (0, 5))
    assert result.stream_status == ("complete", "complete")
    owner.poll(observer=lambda *value: seen.append(value))
    owner.wait(0, observer=lambda *value: seen.append(value))
    owner.close(0)
    owner.close(0)
    assert seen == [(stream, b"final-tail")]


def test_tail_beyond_one_batch_waits_for_eof_with_exact_accounting(tmp_path, state_owner):
    owner, executable = state_owner
    owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)
    owner.native.streams.queues["stderr"].append(b"abc")
    owner.native.tail = {"stderr": b"Z" * 200000}
    seen = []
    result = owner.poll(observer=lambda name, data: seen.append((name, data)))
    assert result.state == "confirmed_exited" and result.stream_status[1] == "pending"
    assert owner.native.streams.reads <= 20
    result = owner.wait(1, observer=lambda name, data: seen.append((name, data)))
    assert result.stream_status == ("complete", "complete")
    assert result.stderr == b"abcZZ" and result.truncated == (0, 199998)
    assert b"".join(data for name, data in seen if name == "stderr") == b"abc" + b"Z" * 200000


def test_final_drain_failure_preserves_exit_proof(tmp_path, state_owner):
    owner, executable = state_owner
    owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)
    original = OSError("final pipe read")
    owner.native.status_hook = lambda: setattr(owner.native.streams, "error", original)
    result = owner.poll()
    assert result.state == "confirmed_exited" and result.root_exit_code == 0 and result.active_processes == 0
    assert result.error is original and result.stream_status == ("incomplete", "incomplete")
    assert owner.close(0).state == "confirmed_exited"


def test_final_drain_timeout_is_explicit_and_does_not_release_readers_early(tmp_path, state_owner):
    owner, executable = state_owner
    owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)
    owner.native.streams.no_eof = True
    result = owner.poll()
    assert result.state == "confirmed_exited" and result.stream_status == ("pending", "pending")
    assert not owner.native.streams.closed
    result = owner.wait(0)
    assert result.state == "confirmed_exited" and isinstance(result.error, TimeoutError)
    assert result.stream_status == ("incomplete", "incomplete")
    assert not owner.native.streams.closed
    assert owner.close(0).stream_status == ("incomplete", "incomplete")


def test_final_observer_failure_retains_prefix_and_confirmed_exit(tmp_path, state_owner):
    owner, executable = state_owner
    owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)
    owner.native.tail = {"stdout": b"tail!more"}
    original, seen = RuntimeError("observer failed on final bytes"), []
    def observe(name, chunk):
        seen.append((name, chunk))
        raise original
    result = owner.poll(observer=observe)
    assert result.state == "confirmed_exited" and result.error is original
    assert result.stdout == b"tail!" and result.truncated == (4, 0)
    assert owner.wait(0).stream_status == ("complete", "complete")
    assert seen == [("stdout", b"tail!more")]


def test_empty_final_read_is_pending_until_later_tail_and_eof(tmp_path, state_owner):
    owner, executable = state_owner
    owner.start(executable, [], cwd=tmp_path, before_resume=lambda value: value)
    read, stage = owner.native.streams.read, []
    def delayed(name, maximum=8192):
        if name == "stdout" and owner.native.streams.exited:
            if not stage:
                stage.append("empty")
                return b""  # No EOF proof; a single extra read is insufficient.
            if stage == ["empty"]:
                owner.native.streams.queues[name].append(b"delayed-tail")
                stage.append("published")
        return read(name, maximum)
    owner.native.streams.read = delayed
    result = owner.poll()
    assert result.state == "confirmed_exited" and result.stdout == b""
    assert result.stream_status == ("pending", "complete")
    seen = []
    result = owner.wait(1, observer=lambda name, data: seen.append((name, data)))
    assert result.stdout == b"delay" and result.truncated == (7, 0)
    assert result.stream_status == ("complete", "complete") and seen == [("stdout", b"delayed-tail")]
