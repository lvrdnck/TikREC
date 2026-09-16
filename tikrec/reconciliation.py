"""Decide service restart recovery before permitting a conflicting user start."""

import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Literal

from .capture import CaptureResult
from .finalization_recovery import (plan_finalization_partial,
                                       preserve_finalization_partial)
from .finalize import finalize_parts
from .job_state import JobState, JobStateStore
from .media import inspect_media
from .recovery_evidence import append_recovery_record
from .recovery_session import completed_output_is_proven, inspect_recovery_session
from .session_resume import prepare_resume
from .capture_control import CaptureControl, CaptureStopped
from .network_evidence import append_network_record
from .retry_policy import RecoveryExhausted
from .startup_network import resolve_startup_patiently
from .tiktok import (LiveResolution, TikTokOfflineError, TikTokResolutionTransientError,
                     _is_http_flv_url, resolve_live, same_live)
from .writer_recovery import recover_writer_partial
from .writer_recovery_evidence import recovery_record


@dataclass(frozen=True)
class ReconciliationResult:
    """Safe typed decision; the signed resolution is private transient transport."""

    outcome: Literal["idle", "settled", "resume", "deferred", "failed", "exhausted"]
    job: JobState | None = None
    reason: str | None = None
    resolution: LiveResolution | None = field(default=None, repr=False, compare=False)
    error: str | None = None

    @property
    def blocked(self):
        """Prevent new starts while identity or storage remains unresolved."""
        return self.outcome in {"deferred", "failed"}


@dataclass(frozen=True)
class DeferredReconciliationResult(ReconciliationResult):
    """Retryable identity failure; no terminal or finalization transition was made."""

    outcome: Literal["deferred"] = "deferred"


class StartupReconciler:
    """Conservative startup decisions with optional bounded patient identity recovery."""

    def __init__(self, store: JobStateStore, *, resolver: Callable = resolve_live,
                 finalizer: Callable = finalize_parts, resume_capture: Callable | None = None,
                 clock: Callable = time.time, media_inspector: Callable = inspect_media,
                 inspector: Callable = inspect_recovery_session,
                 resume_preflight: Callable = prepare_resume, save_job: Callable | None = None,
                 should_stop: Callable = lambda: False,
                 writer_validator: Callable[[Path], None] | None = None):
        self.store, self.resolver, self.finalizer = store, resolver, finalizer
        self.clock, self.media_inspector = clock, media_inspector
        self.inspector, self.resume_preflight = inspector, resume_preflight
        self.writer_validator = writer_validator
        self.save_job = save_job or self._save
        self.should_stop = should_stop
        if resume_capture is None:
            from .live_resume import capture_live_resume
            resume_capture = capture_live_resume
        self.resume_capture = resume_capture

    def reconcile(self, *, observe: Callable = lambda job: None, retry_policy=None,
                  recovery_clock=time.monotonic, control=None,
                  recovery_observer: Callable = lambda status: None) -> ReconciliationResult:
        """Load, validate, and settle intent before any resumed connection opens."""
        job = None
        session = None
        failure_reason = "ambiguous_state"
        failure_message = "invalid durable job state; preserve artifacts"
        evidence_ready = False
        try:
            job = self.store.load()
            if job is None:
                return ReconciliationResult("idle")
            if not job.needs_reconciliation:
                return ReconciliationResult("settled", job)
            # Expose progress without replacing the saved capture/finalization phase.
            observe(replace(job, state="reconciling"))
            failure_message = "invalid or conflicting session storage; preserve artifacts"
            session = self.inspector(job, clock=self.clock, media_inspector=self.media_inspector)
            if session.writer_recovery is not None:
                plan = session.writer_recovery
                if not (job.state == "recovering"
                        and job.recovery_reason == "writer_partial_recovery"):
                    job = self.save_job(replace(
                        job, state="recovering", recovery_reason="writer_partial_recovery"
                    ))
                    observe(job)
                recover_writer_partial(plan, validator=self.writer_validator)
                session.manifest.record_writer_recovery(
                    recovery_record(plan, self.clock()), session.retained.parts
                )
                session = self.inspector(
                    job, clock=self.clock, media_inspector=self.media_inspector
                )
                if session.writer_recovery is not None:
                    raise ValueError("writer recovery did not settle storage")
            output = Path(job.output_path)
            if output.exists():
                failure_reason = "existing_output"
                failure_message = "existing output lacks matching completion evidence; preserve it"
            values = session.manifest.snapshot()
            partial = plan_finalization_partial(
                output, job.session_id, job_state=job.state,
                finalization_status=values["finalization"]["status"],
            )
            if output.exists():
                if not completed_output_is_proven(session, output, self.media_inspector):
                    raise ValueError("existing output is ambiguous")
                return self._completed(job, session, "existing_output")
            if values["finalization"]["status"] == "completed":
                failure_reason = "existing_output"
                failure_message = "completed session output is missing; manual recovery required"
                raise ValueError("completed manifest has no output")
            if job.stop_requested or job.state == "finalizing":
                reason = "user_stop" if job.stop_requested else "recovery_finalization"
                return self._finalize(job, session, reason, observe, partial=partial)
            if not job.may_resume:
                failure_reason = "identity_unavailable" if job.room_id is None else "ambiguous_state"
                failure_message = "saved job is ineligible for automatic capture resume"
                raise ValueError("saved job is not eligible for capture resume")
            prepared = self.resume_preflight(
                Path(job.parts_directory), output_path=output, session_id=job.session_id,
                source_type="tiktok_live", clock=self.clock, media_inspector=self.media_inspector)
            if prepared.manifest.snapshot().get("room_id") != job.room_id:
                raise ValueError("manifest cannot prove saved LIVE identity")
            evidence_ready = True
            self._event(job, session, "process_restart")
            if self.should_stop():
                return self._finalize(replace(job, stop_requested=True), session, "user_stop", observe)
            try:
                failure_message = "public LIVE identity could not be established; preserve artifacts"
                if retry_policy is None:
                    resolution = self.resolver(job.source_url)
                else:
                    def network_observed(phase, recovery):
                        nonlocal job
                        if phase in {"entered", "recovered"}:
                            job = self.save_job(replace(job,
                                state="recovering_network" if phase == "entered" else "reconciling",
                                recovery_reason="network_outage" if phase == "entered" else "network_recovered"))
                            observe(job)
                        if phase != "wait":
                            append_network_record(Path(job.parts_directory) / "connections.jsonl",
                                timestamp=self.clock(), session_id=job.session_id, phase=phase, recovery=recovery)
                        recovery_observer({**recovery.status(), "phase": phase})
                    resolution = resolve_startup_patiently(self.resolver, job.source_url,
                        policy=retry_policy, control=control or CaptureControl(None, time.sleep),
                        clock=recovery_clock, wall_clock=self.clock, notify=network_observed)
            except (CaptureStopped, KeyboardInterrupt):
                return self._finalize(replace(job, stop_requested=True), session, "user_stop", observe)
            except RecoveryExhausted:
                # Exhaustion ends automatic capture eligibility without inventing room-end evidence.
                session.manifest.fail(session.retained.parts, "patient recovery window exhausted; room end is unproven",
                                      finalization_status="not_started")
                job = self.save_job(replace(job, state="failed", ended_at=self.clock(),
                                            recovery_reason="outage_timeout"))
                return ReconciliationResult("exhausted", job, "outage_timeout",
                    error="patient recovery window exhausted; room end is unproven; retained parts preserved")
            except TikTokOfflineError:
                return self._finalize(job, session, "room_ended", observe)
            except TikTokResolutionTransientError:
                self._event(job, session, "identity_unavailable")
                return DeferredReconciliationResult(job=job, reason="identity_unavailable",
                    error="temporary public LIVE resolution failure; recovery remains pending")
            if (not isinstance(resolution, LiveResolution)
                    or not isinstance(resolution.flv_url, str)
                    or not _is_http_flv_url(resolution.flv_url)):
                raise ValueError("resolver did not establish structured LIVE identity")
            if not same_live(job.room_id, resolution):
                return self._finalize(job, session, "live_changed", observe)
            job = replace(job, state="resuming", resume_count=job.resume_count + 1,
                          recovery_reason="process_restart")
            # Publish the decision atomically before any media-resume worker can consume it.
            job = self.save_job(job)
            if job.stop_requested:
                return self._finalize(job, session, "user_stop", observe)
            observe(job)
            self._event(job, session, "process_restart")
            return ReconciliationResult("resume", job, "process_restart", resolution)
        except Exception:
            # Arbitrary exception text can contain secrets; expose only a fixed reason.
            # Invalid evidence is not appended to or rewritten while reporting failure.
            if evidence_ready:
                try:
                    self._event(job, session, "ambiguous_state")
                except Exception:
                    pass  # Failed evidence writes cannot justify touching the retained media.
            return ReconciliationResult("failed", job, failure_reason, error=failure_message)

    def _save(self, job):
        self.store.save(job)
        return job

    def resume(self, result: ReconciliationResult, **options) -> CaptureResult:
        """Run explicit session continuation using the already proven first resolution."""
        if result.outcome != "resume":
            raise ValueError("reconciliation did not authorize capture resume")
        # The resumed reconnect loop must retain the application's injected/offline boundaries.
        for name, value in {"resolver": self.resolver, "finalizer": self.finalizer,
                            "manifest_clock": self.clock, "media_inspector": self.media_inspector}.items():
            options.setdefault(name, value)
        return self.resume_capture(
            result.job.source_url, parts_directory=Path(result.job.parts_directory),
            output_path=Path(result.job.output_path), session_id=result.job.session_id,
            resolution=result.resolution, **options)

    def _event(self, job, session, reason):
        append_recovery_record(Path(job.parts_directory) / "connections.jsonl",
                               timestamp=self.clock(), session_id=job.session_id,
                               reason=reason, resume_count=job.resume_count)

    def _completed(self, job, session, reason):
        job = replace(job, state="completed", ended_at=self.clock(),
                      finalization_completed=True, recovery_reason=reason)
        self._event(job, session, reason)
        job = self.save_job(job)
        return ReconciliationResult("settled", job, reason)

    def _finalize(self, job, session, reason, observe, *, partial=None):
        job = replace(job, state="finalizing", recovery_reason=reason)
        job = self.save_job(job)
        observe(job)
        self._event(job, session, reason)
        self._event(job, session, "recovery_finalization")
        session.manifest.mark_recovery(Path(job.output_path), session.retained.parts)
        try:
            if partial is not None:
                preserve_finalization_partial(partial)
            self.finalizer(session.retained.parts, Path(job.output_path))
        except Exception:
            # Close the observed recovery attempt so a later retry has a valid end boundary.
            session.manifest.fail(session.retained.parts, "recovery finalization failed",
                                  finalization_status="failed")
            return ReconciliationResult("failed", job, "recovery_finalization",
                                        error="recovery finalization failed; retained parts preserved")
        # This is the observed reconciliation end, never an invented process-death time.
        session.manifest.complete(session.retained.parts, output_path=Path(job.output_path),
                                  interrupted=True, finalization_status="completed")
        return self._completed(job, session, reason)
