"""Sequential owned-child execution without an overall assembly deadline."""

import time

from .finalize import FinalizationError, _ffmpeg_failure
from .owned_process_types import ProcessOwnerError


def execute_child(attempt, phase, command, collector):
    """Retain every owner before creation; preserve first failure through cleanup."""
    attempt._check_cancelled()
    for previous in attempt._children:
        evidence = previous[2].evidence()
        if evidence.state not in {"not_created", "confirmed_exited"}:
            raise RuntimeError("prior child lifetime is unknown; successor refused")
        if not previous[2].closed:
            raise RuntimeError("prior child controls were not released; successor refused")
    owner = attempt.process_factory(attempt.session_id, attempt.attempt_token)
    if (owner.session_id, owner.attempt_token) != (attempt.session_id, attempt.attempt_token):
        raise ValueError("process owner identity does not match assembly attempt")
    with attempt._lock:
        attempt._children.append((phase, tuple(command), owner, collector))
        attempt._active = owner, collector

    def authorize(identity):
        attempt._check_cancelled()
        authorized = attempt.before_resume(identity)
        attempt._check_cancelled()
        if phase == "assembly" and (attempt.candidate.exists() or attempt.candidate.is_symlink()):
            raise FileExistsError(f"candidate occupied before resume: {attempt.candidate}")
        return authorized

    try:
        attempt._check_cancelled()
        owner.start(command[0], command[1:], cwd=attempt.work_scope, before_resume=authorize)
        while True:
            attempt._check_cancelled()
            evidence = owner.poll(observer=collector.observe)
            if evidence.error is not None:
                raise evidence.error
            if evidence.state == "confirmed_exited":
                # Only final EOF reconciliation has a fixed bound. A running
                # assembly may legitimately take hours; poll never times it out.
                evidence = owner.wait(5, observer=collector.observe)
                if evidence.error is not None:
                    raise evidence.error
                if evidence.root_exit_code != 0:
                    raise FinalizationError(_ffmpeg_failure(command,
                        evidence.stderr.decode("utf-8", errors="replace"), evidence.root_exit_code))
                # Interpret the final unterminated diagnostic before cleanup so
                # an explicit execution/parser failure remains the first error.
                collector.finish(evidence)
                if collector.problems or collector.failures:
                    raise (collector.problems + collector.failures)[0]
                break
            if evidence.state == "exit_unknown":
                raise RuntimeError("owned child lifetime is unknown")
            time.sleep(0.005)
    except BaseException as error:
        attempt._record(error.original if isinstance(error, ProcessOwnerError) else error)
    finally:
        # Keep helper files and candidates even after proved exit. There is no
        # filesystem cleanup that can race an uncertain child or hide a partial.
        try:
            evidence = owner.close(5, observer=collector.observe)
            if evidence.error is not None:
                attempt._record(evidence.error)
            for diagnostic in evidence.diagnostics:
                attempt._record(diagnostic)
            collector.finish(evidence)
            for problem in collector.problems:
                attempt._record(problem)
            for failure in collector.failures:
                attempt._record(failure)
            if evidence.state not in {"not_created", "confirmed_exited"}:
                attempt._record(RuntimeError("owned child lifetime remains unknown"))
        except BaseException as error:
            attempt._record(error)
        with attempt._lock:
            attempt._active = None
    if attempt._errors:
        raise attempt._errors[0]
    if not collector.complete:
        raise RuntimeError("incomplete child diagnostics")
    return evidence
