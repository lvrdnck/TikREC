"""Scoped writer lifetime accounting remains bounded and refuses unknown acquisitions."""

import os
from pathlib import Path

import pytest

from tikrec.capture_writer_owners import CaptureWriterOwners, open_capture_file, writer_scope
from tikrec.session_journal_types import JournalError

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows original native writer proof')


def test_closed_control_writers_do_not_accumulate_objects(tmp_path):
    owner = CaptureWriterOwners('original', 1)
    with writer_scope(owner):
        for _ in range(100):
            with open_capture_file(tmp_path / 'control.jsonl', 'a', encoding='utf-8') as stream:
                stream.write('generated\n')
            assert not owner.streams and not owner.native_close_guards
        assert not owner.retired()  # A live capture execution cannot claim retirement.
    assert owner.retired() and owner.opened == owner.closed == 100
    with pytest.raises(JournalError):
        owner.open(tmp_path / 'escaped', 'xb')
    with open_capture_file(tmp_path / 'ordinary', 'xb') as ordinary:
        assert ordinary.__class__.__module__ == '_io'
    assert owner.opened == 100


def test_unknown_acquisition_stays_incomplete(tmp_path, monkeypatch):
    owner = CaptureWriterOwners('original', 1)
    primary = OSError('generated unconfirmed acquisition')
    def fail(*args, **options):
        raise primary
    monkeypatch.setattr(Path, 'open', fail)
    with writer_scope(owner), pytest.raises(OSError) as raised:
        open_capture_file(tmp_path / 'unknown', 'xb')
    assert raised.value is primary and owner.errors == [primary]
    assert not owner.retire() and owner.acquisition_uncertain


def test_cleanup_diagnostics_are_bounded_and_overflow_cannot_authorize_retirement():
    owner = CaptureWriterOwners('original', 1)
    for index in range(33):
        owner._error(OSError(str(index)))
    assert len(owner.errors) == 32 and owner.acquisition_uncertain
    assert not owner.known_cleanup([OSError('unknown source close')])
