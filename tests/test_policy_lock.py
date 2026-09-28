"""Policy authority serializes across threads/processes without blocking reads."""

import os
import subprocess
import sys
import threading

import pytest

from tikrec.policy_lock import policy_lock


def test_another_thread_waits_and_same_thread_write_fails_closed(tmp_path):
    path = tmp_path / "config.json"
    entered, started = threading.Event(), threading.Event()

    def writer():
        started.set()
        with policy_lock(path, "write"):
            entered.set()

    with policy_lock(path) as lease:
        lease.assert_held()
        with pytest.raises(ValueError, match="inside retention"):
            with policy_lock(path, "write"):
                pass
        thread = threading.Thread(target=writer)
        thread.start()
        assert started.wait(2) and not entered.wait(0.1)
    thread.join(3)
    assert not thread.is_alive() and entered.is_set()


def test_process_waits_until_policy_authority_is_released(tmp_path):
    path = tmp_path / "config.json"
    script = ("import sys; from pathlib import Path; "
              "from tikrec.policy_lock import policy_lock; "
              "print('started', flush=True); "
              "lease=policy_lock(Path(sys.argv[1]), 'write'); lease.__enter__(); "
              "print('acquired', flush=True); lease.__exit__(None,None,None)")
    with policy_lock(path):
        process = subprocess.Popen([sys.executable, "-c", script, str(path)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert process.stdout.readline().strip() == "started"
            with pytest.raises(subprocess.TimeoutExpired):
                process.wait(timeout=0.15)
        except BaseException:
            process.kill()
            process.communicate()
            raise
    output, errors = process.communicate(timeout=5)
    assert process.returncode == 0 and output.strip() == "acquired", errors


def test_hardlinked_empty_lock_is_not_modified(tmp_path):
    source = tmp_path / "keep"
    source.write_bytes(b"")
    (tmp_path / ".config.json.retention-policy.lock").hardlink_to(source)
    with pytest.raises(ValueError, match="ambiguous"):
        with policy_lock(tmp_path / "config.json"):
            pass
    assert source.read_bytes() == b""


def test_nested_config_transaction_and_case_alias(tmp_path):
    path = tmp_path / "config.json"
    alias = type(path)(str(path).swapcase()) if os.name == "nt" else path
    with policy_lock(path, "write") as outer:
        with policy_lock(alias, "write") as inner:
            assert inner is outer


def test_redirected_configuration_cannot_bypass_policy_authority(tmp_path):
    target, alias = tmp_path / "target.json", tmp_path / "alias.json"
    target.write_text("{}")
    try:
        alias.symlink_to(target)
    except OSError:
        pytest.skip("symlink privilege unavailable")
    with pytest.raises(ValueError, match="configuration redirects"):
        with policy_lock(alias):
            pass


def test_process_exit_releases_policy_authority(tmp_path):
    script = ("import sys,time; from pathlib import Path; "
              "from tikrec.policy_lock import policy_lock; "
              "lease=policy_lock(Path(sys.argv[1])); lease.__enter__(); "
              "print('held',flush=True); time.sleep(30)")
    path = tmp_path / "config.json"
    child = subprocess.Popen([sys.executable, "-c", script, str(path)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "held"
    finally:
        child.terminate()
        child.communicate(timeout=5)
    with policy_lock(path) as lease:
        lease.assert_held()


@pytest.mark.skipif(os.name != "nt", reason="Windows short filename aliases")
def test_short_filename_alias_uses_same_policy_authority(tmp_path):
    import ctypes

    path = tmp_path / "long-configuration-name.json"
    path.write_text("{}")
    buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer)):
        pytest.skip("short filename unavailable")
    alias = type(path)(buffer.value)
    if alias.name.casefold() == path.name.casefold():
        pytest.skip("8.3 generation disabled on this volume")
    with policy_lock(path):
        with pytest.raises(ValueError, match="inside retention"):
            with policy_lock(alias, "write"):
                pass
