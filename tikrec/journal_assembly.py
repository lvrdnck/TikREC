"""Internal one-shot sealed FIFO session -> durable unpublished MP4 candidate."""

import subprocess
from pathlib import Path
from threading import RLock

from .assembly_diagnostics import AssemblyDiagnostics
from .assembly_launcher import concat_launch
from .assembly_types import AssemblyChild, AssemblyError, UnpublishedCandidate
from .attempt_coordinator import AttemptCoordinator, AttemptError
from .decode_diagnostics import input_decode_health
from .finalize import FinalizationError, _ffmpeg_failure
from .finalize_media import _validate_parts, _build_ffmpeg_command, progress_command
from .finalize_plan import plan_media
from .frame_rate import inspect_frame_rate
from .owned_process import OwnedProcess
from .session_journal_types import require


class JournalAssembly:
    """Use explicit held authority once; keep all owners reachable after uncertainty.

    There is no authority discovery, scheduler, publication, validation, retry or
    settlement. The same AttemptCoordinator owns every probe, writer and scratch
    artifact. Trusted hooks/progress/factories must return promptly.
    """

    def __init__(self, authority, *, ffmpeg, ffprobe, progress=None,
                 process_factory=OwnedProcess, fault=lambda _: None):
        self.coordinator = AttemptCoordinator(authority, process_factory=process_factory, fault=fault)
        self.ffmpeg, self.ffprobe = Path(ffmpeg), Path(ffprobe)
        self.progress, self.plan, self.receipt = progress, None, None
        self.collectors, self.error = [], None
        self._started, self._lock = False, RLock()

    def _check(self):
        require(not self.coordinator.cancelled.is_set(), "assembly execution revoked")

    def _execute(self, command, collector, *, writer=False, outputs=()):
        runner = self.coordinator
        self._check()
        self.collectors.append(collector)
        def interpret(evidence):
            if evidence.root_exit_code != 0:
                raise FinalizationError(_ffmpeg_failure(command,
                    evidence.stderr.decode("utf-8", errors="replace"), evidence.root_exit_code))
            # Final unterminated errors are interpreted before success and
            # independently of the bounded prefix retained by OwnedProcess.
            collector.finish(evidence)
            if collector.problems or collector.failures:
                raise (collector.problems + collector.failures)[0]
            require(collector.complete, "assembly diagnostics incomplete")
        if writer:
            evidence = runner.run_writer_child(command[0], command[1:], cwd=runner.scratch.path,
                phase="assembly", timeout=None, outputs=outputs, observer=collector.observe, on_exit=interpret)
        else:
            evidence = runner.run_child(command[0], command[1:], cwd=runner.authority.root.parent,
                phase="frame_rate", timeout=30, observer=collector.observe, on_exit=interpret)
        # Native exit and streamed receipt are necessary but not sufficient:
        # interpret final unterminated errors and diagnostic health before seal.
        self._check()
        return evidence

    def _probe(self, part):
        def run(command, **_):
            collector = AssemblyDiagnostics(probe=True)
            evidence = self._execute(command, collector)
            return subprocess.CompletedProcess(command, evidence.root_exit_code,
                bytes(collector.stdout).decode("utf-8"), evidence.stderr.decode("utf-8", errors="replace"))
        return inspect_frame_rate(part, ffprobe=str(self.ffprobe), runner=run)

    def result(self):
        """Snapshot owners/execution facts; no snapshot grants further permission."""
        runner, scratch = self.coordinator, self.coordinator.scratch
        children = tuple(AssemblyChild(c["intent"]["phase"],
            (c["intent"]["executable"], *c["intent"]["arguments"]), c["process"].evidence(), c["process"])
            for c in runner.children)
        state = ("exit_unknown" if any(c.evidence.state == "exit_unknown" for c in children)
                 else "failed" if self.error is not None else "cancelled" if runner.cancelled.is_set()
                 else "candidate_ready" if self.receipt is not None else "not_started")
        health = (self.collectors[-1].input_health() if self.plan is not None and self.collectors
                  else input_decode_health("unknown"))
        return UnpublishedCandidate(None if runner.claimed is None else runner.claimed["session_id"],
            runner.token, state, None if scratch is None else scratch.path / "candidate.mp4",
            None if scratch is None else scratch.path, self.plan, children, health,
            bool(self.collectors) and all(c.complete for c in self.collectors),
            self.error, tuple(runner.errors))

    def run(self):
        """Claim at most one FIFO task and seal only same-attempt unpublished evidence."""
        with self._lock:
            require(not self._started, "assembly is single-use")
            self._started = True
        runner = self.coordinator
        try:
            runner.authority.assert_held()
            for executable in (self.ffmpeg, self.ffprobe):
                require(executable.is_absolute() and executable.is_file()
                        and executable.suffix.casefold() == ".exe", "explicit media executable required")
            if runner.claim() is None:
                return None
            inputs = _validate_parts(runner.guard.revalidate().flv_inputs)
            self.plan = plan_media(inputs, frame_rate_inspector=self._probe)
            runner.guard.revalidate()
            runner._fault("after_media_plan")
            self._check()
            scratch = runner.reserve_scratch(helpers=("concat.ffconcat",) if self.plan.stream_copy else ())
            command = _build_ffmpeg_command(inputs, scratch.path / "candidate.mp4", ffmpeg=self.ffmpeg,
                manifest=scratch.path / "concat.ffconcat" if self.plan.stream_copy else None,
                target_size=self.plan.target_size, nominal_rate=self.plan.nominal_rate)
            command = progress_command(command, self.progress is not None)
            outputs = ("candidate.mp4", "concat.ffconcat") if self.plan.stream_copy else ("candidate.mp4",)
            if self.plan.stream_copy:
                executable, arguments = concat_launch(command, inputs)
                command = [str(executable), *arguments]
            runner._fault("before_assembly_writer")
            collector = AssemblyDiagnostics(decode=not self.plan.stream_copy, progress=self.progress)
            self._execute(command, collector, writer=True, outputs=outputs)
            runner._fault("after_assembly_diagnostics")
            self._check()
            health = collector.input_health()["status"]
            self.receipt = scratch.seal_candidate(runner.children[-1]["launch"],
                input_decode="unknown" if health == "not_checked" else health)
            return self.result()
        except BaseException as original:
            self.error = original.original if isinstance(original, AttemptError) else original
            runner.cancelled.set()
            if runner.scratch is not None:
                runner.scratch.hold(self.error)
            raise AssemblyError(self, self.result()) from self.error

    def cancel(self, timeout=5):
        """Revoke current execution and bound cancellation of the exact owned job."""
        return self.coordinator.cancel(timeout)

    def close(self, timeout=5):
        """Report completed resource cleanup separately from execution revocation."""
        return self.coordinator.close(timeout)
