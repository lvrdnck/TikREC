"""Portable deterministic native doubles; these are state evidence, not Windows proof."""

from collections import deque
from uuid import uuid4

import pytest

import tikrec.owned_process as module


class Streams:
    """Expose final bytes/EOF only after the exact injected status boundary."""

    def __init__(self):
        self.queues = {name: deque() for name in ("stdout", "stderr")}
        self.eof, self.exited, self.no_eof = set(), False, False
        self.error, self.reads, self.closed = None, 0, False

    def close_child(self):
        """Model the independently releasable parent write copies, absent in this double."""

    def read(self, name, maximum=8192):
        """Model bounded native byte reads and independently observable EOF."""
        self.reads += 1
        if self.error:
            raise self.error
        if self.queues[name]:
            chunk = self.queues[name].popleft()
            if len(chunk) > maximum:
                self.queues[name].appendleft(chunk[maximum:])
            return chunk[:maximum]
        if self.exited and not self.no_eof:
            self.eof.add(name)
        return b""


class Native:
    """Count create/resume/terminate/close without launching any OS process."""

    instances = []

    def __init__(self):
        self.process = self.job = self.thread = None
        self.initial, self.streams = None, Streams()
        self.resumes = self.terminations = self.closes = 0
        self.tail, self.status_hook = {}, None
        self.instances.append(self)

    def create(self, executable, arguments, cwd, fault):
        """Mirror the owned creation boundaries for lock/barrier ordering."""
        fault("before_create")
        self.process, self.job, self.thread = 101, 102, 103
        self.initial = 123, 456, str(executable)
        fault("after_create")

    def verify(self, expected):
        """Require the exact identity even in state-only probes."""
        assert expected == self.initial

    def resume(self):
        """Count execution authorization rather than pretending to run a child."""
        self.resumes += 1

    def status(self):
        """Publish tail bytes precisely between collection and exit observation."""
        if self.status_hook:
            self.status_hook()
        for name, chunk in self.tail.items():
            self.streams.queues[name].append(chunk)
        self.tail = {}
        self.streams.exited = True
        return 0, 0

    def terminate(self):
        """Count exact-owner termination requests."""
        self.terminations += 1
        self.streams.exited = True

    def close(self):
        """Record resource release separately from process lifetime."""
        self.closes += 1
        self.process = self.job = self.thread = None
        self.streams.closed = True


@pytest.fixture
def state_owner(tmp_path, monkeypatch):
    """Supply explicit disposable paths and native doubles on every platform."""
    executable = tmp_path / "fixture.exe"
    executable.write_bytes(b"not executable; never launched")
    Native.instances = []
    monkeypatch.setattr(module, "NativeChild", Native)
    owner = module.OwnedProcess(str(uuid4()), str(uuid4()), diagnostic_limit=5)
    return owner, executable
