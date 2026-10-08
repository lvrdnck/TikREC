"""Bounded exact secondary errors survive loss of every product output sink."""
import sys

from tikrec.operational_reporting import DisabledConsole, Reporting


def test_both_channels_are_disabled_with_exact_errors_and_no_retry(monkeypatch):
    console_error, disk_error = OSError('secret console text'), OSError('secret disk text')
    calls = []
    class Console:
        def write(self, text):
            calls.append('console')
            raise console_error
    class Disk:
        def emit(self, event, **values):
            calls.append('disk')
            raise disk_error
    console = Console()
    monkeypatch.setattr(sys, 'stdout', console)
    reporting = Reporting()
    assert reporting.write(Disk(), 'failure', primary_type='ValueError') is disk_error
    assert reporting.errors == [('disk', disk_error), ('console', console_error)]
    assert isinstance(sys.stdout, DisabledConsole) and sys.stdout.original is console
    for _ in range(100):
        assert reporting.write(Disk(), 'shutdown', complete=False) is None
        sys.stdout.flush()
    assert calls == ['disk', 'console'] and len(reporting.errors) == 2


def test_surviving_disk_summary_excludes_exception_text(monkeypatch):
    values = []
    class Console:
        def write(self, text):
            raise BrokenPipeError('secret exception text')
    class Disk:
        def emit(self, event, **fields):
            values.append(fields)
    monkeypatch.setattr(sys, 'stdout', Console())
    reporting = Reporting()
    assert isinstance(reporting.write(Disk(), 'ready'), BrokenPipeError)
    assert reporting.write(Disk(), 'shutdown', complete=False) is None
    assert values[-1]['reporting_failures'] == [{'channel': 'console', 'type': 'BrokenPipeError'}]
    assert 'secret' not in repr(values)
