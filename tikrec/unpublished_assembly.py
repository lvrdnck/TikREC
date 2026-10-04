"""Internal closed-input assembly; no journal authority or publication side effects."""

import subprocess
from pathlib import Path
from threading import Event, RLock

from .assembly_diagnostics import AssemblyDiagnostics
from .assembly_process import execute_child
from .assembly_types import AssemblyCancelled, AssemblyChild, AssemblyError, UnpublishedCandidate
from .decode_diagnostics import input_decode_health
from .finalize_media import _validate_parts, _write_concat_manifest, _build_ffmpeg_command, progress_command
from .finalize_plan import plan_media
from .frame_rate import inspect_frame_rate
from .owned_process import OwnedProcess
from .owned_process_types import uuid_key


class UnpublishedAssembly:
    """Single-use, caller-owned closed FLVs -> an unpublished candidate.

    The trusted caller supplies immutable/closed inputs and exclusive scratch
    ownership. This primitive does not establish native sealed-input authority,
    persist launch claims, validate media, or grant permission to queued inputs.
    Retain this object or AssemblyError after failure to reconcile exact owners.
    All hooks/factories/observers must return promptly, as for OwnedProcess.
    """

    def __init__(self, *, session_id, attempt_token, inputs, work_scope, candidate,
                 ffmpeg, ffprobe, before_resume, progress=None, process_factory=OwnedProcess):
        self.session_id, self.attempt_token = uuid_key(session_id), uuid_key(attempt_token)
        self.inputs = tuple(Path(part) for part in inputs)
        self.work_scope, self.candidate = Path(work_scope), Path(candidate)
        self.ffmpeg, self.ffprobe = Path(ffmpeg), Path(ffprobe)
        if not callable(before_resume) or not callable(process_factory):
            raise ValueError("explicit before-resume authorization and process factory required")
        self.before_resume, self.progress, self.process_factory = before_resume, progress, process_factory
        self._lock, self._cancelled = RLock(), Event()
        self._started, self._active = False, None
        self._children, self._errors = [], []
        self.plan, self._assembly, self._ready = None, None, False

    def _record(self, error):
        with self._lock:
            if error is not None and not any(error is existing for existing in self._errors):
                self._errors.append(error)

    def _check_cancelled(self):
        if self._cancelled.is_set():
            raise AssemblyCancelled("assembly invocation cancelled")

    def cancel(self):
        """Irreversibly cancel, with bounded exact-job cleanup and streaming observation."""
        self._cancelled.set()
        with self._lock:
            active = self._active
        if active is not None:
            owner, collector = active
            evidence = owner.cancel(5, observer=collector.observe)
            self._record(evidence.error)
            for error in evidence.diagnostics:
                self._record(error)

    def _prepare(self):
        self._check_cancelled()
        if not self.inputs or not all(part.is_absolute() for part in self.inputs):
            raise ValueError("explicit absolute closed FLV inputs required")
        ordered = _validate_parts(self.inputs)
        if len({part.resolve() for part in ordered}) != len(ordered):
            raise ValueError("duplicate closed inputs refused")
        if not self.work_scope.is_absolute() or not self.candidate.is_absolute():
            raise ValueError("explicit absolute attempt scope/candidate required")
        scope, candidate = self.work_scope.resolve(), self.candidate.resolve()
        if candidate.parent != scope or candidate.suffix.lower() != ".mp4":
            raise ValueError("MP4 candidate must be an immediate child of attempt scope")
        if any(scope.is_relative_to(part.resolve().parent) or part.resolve().is_relative_to(scope)
               for part in ordered):
            raise ValueError("attempt scratch must be separate from source evidence")
        for executable in (self.ffmpeg, self.ffprobe):
            if not executable.is_absolute() or not executable.is_file() or executable.suffix.lower() != ".exe":
                raise ValueError("explicit existing executable required")
        self.work_scope, self.candidate = scope, candidate
        # mkdir is exclusive, so an occupied attempt (including broken links)
        # cannot be silently adopted. No unlink/replace occurs anywhere here.
        self.work_scope.mkdir()
        self._check_cancelled()
        return ordered

    def _probe(self, part):
        def runner(command, **_options):
            # Reuse the existing frame-rate command/parser while substituting
            # owned execution. Its synchronous timeout is not an assembly limit.
            collector = AssemblyDiagnostics(probe=True)
            evidence = execute_child(self, "frame_rate", command, collector)
            return subprocess.CompletedProcess(command, evidence.root_exit_code,
                stdout=bytes(collector.stdout).decode("utf-8"),
                stderr=evidence.stderr.decode("utf-8", errors="replace"))
        return inspect_frame_rate(part, ffprobe=str(self.ffprobe), runner=runner)

    def result(self):
        """Snapshot execution/diagnostic facts with reachable exact owners, never publication."""
        children = tuple(AssemblyChild(phase, command, owner.evidence(), owner)
                         for phase, command, owner, _ in self._children)
        unknown = any(c.evidence.state == "exit_unknown" for c in children)
        state = ("exit_unknown" if unknown else "cancelled" if self._cancelled.is_set()
                 else "candidate_ready" if self._ready and not self._errors else "failed")
        health = self._assembly.input_health() if self._assembly else input_decode_health("unknown")
        complete = bool(self._children) and all(collector.complete for *_, collector in self._children)
        return UnpublishedCandidate(self.session_id, self.attempt_token, state, self.candidate,
            self.work_scope, self.plan, children, health, complete,
            self._errors[0] if self._errors else None, tuple(self._errors[1:]))

    def run(self):
        """Assemble once; failures retain artifacts and raise an owner-bearing AssemblyError."""
        with self._lock:
            if self._started:
                raise ValueError("assembly is single-use")
            self._started = True
        try:
            ordered = self._prepare()
            self.plan = plan_media(ordered, frame_rate_inspector=self._probe)
            self._check_cancelled()
            manifest = _write_concat_manifest(ordered, self.work_scope) if self.plan.stream_copy else None
            command = _build_ffmpeg_command(ordered, self.candidate, ffmpeg=self.ffmpeg,
                manifest=manifest, target_size=self.plan.target_size, nominal_rate=self.plan.nominal_rate)
            command = progress_command(command, self.progress is not None)
            self._assembly = AssemblyDiagnostics(decode=not self.plan.stream_copy, progress=self.progress)
            execute_child(self, "assembly", command, self._assembly)
            self._check_cancelled()
            if not self.candidate.is_file() or self.candidate.stat().st_size == 0:
                raise RuntimeError("successful FFmpeg exit did not create a nonempty candidate")
            self._ready = True
        except BaseException as error:
            self._record(error)
            raise AssemblyError(self, self.result()) from self._errors[0]
        return self.result()
