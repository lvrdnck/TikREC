"""Fresh cooperative namespace checks; native pins remain a separate authority."""
import errno
import os
import stat
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from tikrec.pilot_identity import local
from tikrec.session_journal_types import JournalError


@pytest.mark.parametrize('directory', [False, True])
def test_regular_targets_and_absent_leaf(tmp_path, directory):
    target = tmp_path / 'target'
    target.mkdir() if directory else target.write_bytes(b'fixture')
    assert local(target) == target
    assert local(target, exists=False) == target
    absent = tmp_path / 'absent'
    assert local(absent, exists=False) == absent
    with pytest.raises(JournalError):
        local(absent)


@pytest.mark.parametrize('value', ['relative', r'\\server\share\home', r'C:\safe\..\home'])
def test_non_native_or_parent_traversal_refuses(value):
    with pytest.raises(JournalError):
        local(value, exists=False)


def test_missing_and_non_directory_ancestors_refuse(tmp_path):
    with pytest.raises((JournalError, OSError)):
        local(tmp_path / 'missing' / 'leaf', exists=False)
    file = tmp_path / 'file'; file.write_bytes(b'fixture')
    with pytest.raises((JournalError, OSError)):
        local(file / 'leaf', exists=False)


def test_hardlinked_file_refuses(tmp_path):
    file = tmp_path / 'file'; file.write_bytes(b'fixture')
    alias = tmp_path / 'alias'; alias.hardlink_to(file)
    for target in (file, alias):
        with pytest.raises(JournalError, match='multiply linked'):
            local(target)


@pytest.mark.parametrize('directory,dangling', [(False, False), (True, False), (False, True), (True, True)])
def test_native_symlink_and_dangling_leaf_refuse(tmp_path, directory, dangling):
    target = tmp_path / 'target'
    if not dangling:
        target.mkdir() if directory else target.write_bytes(b'fixture')
    link = tmp_path / 'link'
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as error:
        pytest.skip(f'native symlink creation unavailable: winerror={getattr(error, "winerror", None)}')
    try:
        for exists in (True, False):
            with pytest.raises(JournalError, match='redirected'):
                local(link, exists=exists)
        if directory and not dangling:
            with pytest.raises(JournalError):
                local(link / 'new', exists=False)
    finally:
        link.unlink()


@pytest.mark.skipif(os.name != 'nt', reason='native Windows junction')
def test_native_junction_target_and_ancestor_refuse(tmp_path):
    target = tmp_path / 'target'; target.mkdir()
    link = tmp_path / 'junction'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
    if result.returncode:
        pytest.skip('native junction creation unavailable')
    try:
        for path in (link, link / 'new'):
            with pytest.raises(JournalError, match='redirected'):
                local(path, exists=False)
        target.rmdir()
        with pytest.raises(JournalError, match='redirected'):
            local(link, exists=False)
    finally:
        link.rmdir()


@pytest.mark.parametrize('code', [errno.EACCES, errno.EIO, errno.EBUSY])
def test_uncertain_metadata_is_sanitized_refusal(tmp_path, monkeypatch, code):
    target = tmp_path / 'private-name'
    original = Path.stat
    def metadata(path, **kwargs):
        if path == target:
            raise OSError(code, 'private metadata detail', str(target))
        return original(path, **kwargs)
    monkeypatch.setattr(Path, 'stat', metadata)
    with pytest.raises(JournalError, match='metadata unavailable') as caught:
        local(target, exists=False)
    assert 'private' not in str(caught.value)


@pytest.mark.parametrize('mode,attributes', [(stat.S_IFREG, 0x400), (stat.S_IFLNK, 0)])
def test_regular_looking_reparse_metadata_refuses(tmp_path, monkeypatch, mode, attributes):
    target = tmp_path / 'target'; target.write_bytes(b'fixture')
    original = Path.stat
    def metadata(path, **kwargs):
        if path == target:
            return SimpleNamespace(st_mode=mode, st_nlink=1, st_file_attributes=attributes)
        return original(path, **kwargs)
    monkeypatch.setattr(Path, 'stat', metadata)
    with pytest.raises(JournalError, match='redirected'):
        local(target)


@pytest.mark.parametrize('exists', [True, False])
def test_related_facts_use_one_no_follow_query_per_component(tmp_path, monkeypatch, exists):
    target = tmp_path / 'target'; target.write_bytes(b'fixture')
    original = Path.stat; queries = []
    def metadata(path, **kwargs):
        queries.append((path, kwargs.get('follow_symlinks', True)))
        return original(path, **kwargs)
    monkeypatch.setattr(Path, 'stat', metadata)
    assert local(target, exists=exists) == target
    # Preserve the separate final known-target revalidation after the ancestor walk.
    expected = Counter((p, False) for p in (target, *target.parents))
    if exists:
        expected[(target, False)] += 1
    assert Counter(queries) == expected


@pytest.mark.parametrize('ancestor', [False, True])
def test_success_does_not_authorize_replaced_or_missing_namespace(tmp_path, ancestor):
    parent = tmp_path / 'parent'; parent.mkdir()
    target = parent / 'target'; target.write_bytes(b'fixture')
    assert local(target) == target
    target.unlink()
    if ancestor:
        parent.rmdir(); parent.write_bytes(b'replaced directory')
    with pytest.raises((JournalError, OSError)):
        local(target)
    if not ancestor:
        target.write_bytes(b'new file'); alias = parent / 'alias'; alias.hardlink_to(target)
        with pytest.raises(JournalError):
            local(target)


def test_known_target_revalidated_after_ancestor_observations(tmp_path, monkeypatch):
    target = tmp_path / 'target'; target.write_bytes(b'fixture')
    original = Path.stat
    def metadata(path, **kwargs):
        if path == tmp_path and target.exists():
            target.unlink()
        return original(path, **kwargs)
    monkeypatch.setattr(Path, 'stat', metadata)
    with pytest.raises(JournalError):
        local(target)


def test_each_successful_invocation_reads_fresh_metadata(tmp_path, monkeypatch):
    target = tmp_path / 'target'; target.mkdir()
    original = Path.stat; observations = []
    def metadata(path, **kwargs):
        observations.append((path, kwargs.get('follow_symlinks', True)))
        return original(path, **kwargs)
    monkeypatch.setattr(Path, 'stat', metadata)
    local(target); first = list(observations); observations.clear()
    local(target)
    assert observations == first and all(not follow for _, follow in observations)


@pytest.mark.parametrize('winerror', [5, 32, 1117])
def test_windows_access_sharing_io_errors_are_not_absence(tmp_path, monkeypatch, winerror):
    target = tmp_path / 'target'; original = Path.stat
    def metadata(path, **kwargs):
        if path == target or path == tmp_path:
            error = OSError(errno.EACCES, 'private Windows error', str(path))
            error.winerror = winerror
            raise error
        return original(path, **kwargs)
    monkeypatch.setattr(Path, 'stat', metadata)
    with pytest.raises(JournalError, match='metadata unavailable'):
        local(target, exists=False)
