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
                 process_factory=OwnedProcess, fault=lambda _: None, candidate_validation=False, candidate_publication=False, manifest_completion=False, candidate_limit_bytes=None, writer_budget=None):
        self.coordinator = AttemptCoordinator(authority, process_factory=process_factory, fault=fault)
        require(not candidate_publication or candidate_validation, "publication requires validation")
        require(not manifest_completion or candidate_publication, "completion requires publication")
        self.coordinator.manifest_capable = manifest_completion
        self.coordinator.publication_capable = candidate_publication
        self.coordinator.validation_readers = candidate_validation
        self.ffmpeg, self.ffprobe = Path(ffmpeg), Path(ffprobe)
        require(candidate_limit_bytes is None or type(candidate_limit_bytes) is int
                and 131072 <= candidate_limit_bytes <= 512 * 1024**2, "invalid candidate byte limit")
        self.candidate_limit_bytes = candidate_limit_bytes
        require(writer_budget is None or callable(writer_budget), 'writer budget must be a trusted policy')
        self.writer_budget = writer_budget
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
            limit = self.candidate_limit_bytes
            if self.writer_budget is not None:
                limit = self.writer_budget()
                require(type(limit) is int and limit >= 131072, 'invalid operational writer budget')
            if limit is not None:
                # Explicit pilot/operational policies cap growth before launch intent is hashed.
                # Near-cap output is refused below; a clean mux exit cannot prove full media.
                command[-1:-1] = ['-fs', str(limit)]
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
            if limit is not None:
                # Seal only unpublished bytes first: accepted cleanup needs that exact
                # durable identity. Near-cap refusal never enters validation/publication.
                margin = min(16 * 1024**2, limit // 8)
                if self.receipt['size'] >= limit - margin:
                    # This known opt-in refusal precedes every validator/publication.
                    # Wrappers permit original local cleanup, never terminal accounting.
                    runner.pilot_candidate_refused = self.writer_budget is None
                    runner.candidate_budget_refused = self.writer_budget is not None
                    require(False, 'candidate approached writer budget; preserve unfinished evidence')
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
