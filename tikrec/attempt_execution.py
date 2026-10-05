"""Sequential child execution and independent exit/EOF/cleanup evidence."""

import hashlib
from dataclasses import asdict
from pathlib import Path

from .owned_process import _timeout
from .session_journal_types import require


class StreamEvidence:
    """Count/hash all observed chunks while retaining only the process owner's prefix."""

    def __init__(self, observer):
        self.observer, self.failed = observer, False
        self.counts = {name: 0 for name in ("stdout", "stderr")}
        self.hashes = {name: hashlib.sha256() for name in self.counts}

    def observe(self, name, chunk):
        """Account before calling trusted observers; a callback failure remains explicit."""
        self.counts[name] += len(chunk)
        self.hashes[name].update(chunk)
        if self.observer is not None and not self.failed:
            try:
                self.observer(name, chunk)
            except BaseException:
                self.failed = True
                raise

    def record(self, evidence):
        """Report diagnostic completeness independently of native-confirmed exit."""
        return {"complete": not self.failed and evidence.error is None
                and evidence.stream_status in {("complete", "complete"), ("not_open", "not_open")},
                "status": list(evidence.stream_status), "counts": self.counts,
                "sha256": {name: value.hexdigest() for name, value in self.hashes.items()},
                "prefix": [evidence.stdout.hex(), evidence.stderr.hex()],
                "dropped": list(evidence.truncated), "observer_failed": self.failed,
                "errors": [repr(e)[:1024] for e in (evidence.error, *evidence.diagnostics) if e is not None]}


def finish_child(runner, child, timeout):
    """Keep native exit, streaming completion and local cleanup as separate receipts."""
    process = child["process"]
    evidence = process.evidence()
    if evidence.state not in {"not_created", "confirmed_exited"}:
        evidence = process.cancel(timeout, observer=child["streams"].observe)
    if evidence.state not in {"not_created", "confirmed_exited"}:
        raise RuntimeError("unknown whole-job lifetime; retain protected inputs")
    original = None
    if not child["exit_recorded"]:
        try:
            runner._record(child, "exit", {"state": evidence.state,
                "identity": None if evidence.identity is None else asdict(evidence.identity),
                "code": evidence.root_exit_code, "active": evidence.active_processes})
            child["exit_recorded"] = True
            runner._fault("after_exit_record")
        except BaseException as error:
            original = error
    # Durable acknowledgement failure must not skip independent exact cleanup.
    evidence = process.close(timeout, observer=child["streams"].observe)
    if original is not None:
        raise original
    if not child["diagnostics_recorded"]:
        runner._record(child, "diagnostics", child["streams"].record(evidence))
        child["diagnostics_recorded"] = True
    if not process.closed:
        raise evidence.error or RuntimeError("native cleanup incomplete; retain input protection")
    if not child["cleanup_recorded"]:
        runner._record(child, "cleanup", 1)
        child["cleanup_recorded"] = True
    return evidence


def run_child(runner, executable, arguments, cwd, phase, timeout, observer, outputs=()):
    """Consume a reader or separately declared scratch-writer creation capability."""
    _timeout(timeout)
    require(runner.claimed is not None and runner.guard is not None and not runner.cancelled.is_set()
            and not runner.closed, "attempt cannot launch")
    executable, cwd = Path(executable), Path(cwd)
    require(executable.is_absolute() and executable.is_file() and executable.suffix.lower() == ".exe"
            and cwd.is_absolute() and cwd.is_dir(), "explicit executable and working scope required")
    require(type(arguments) in {list, tuple}, "explicit argument vector required")
    outputs = tuple(sorted(outputs))
    if outputs:
        require(runner.scratch is not None and cwd.resolve() == runner.scratch.path,
                "writer must use its bound attempt scratch scope")
        runner.scratch.assert_outputs_absent(outputs)
    proof = runner.guard.revalidate()
    for previous in runner.children[-1:]:
        require(previous["process"].closed and previous["cleanup_recorded"], "prior local cleanup unresolved")
    launch = runner.uuid()
    intent = {"executable": str(executable.resolve()), "arguments": list(arguments), "cwd": str(cwd),
              "phase": phase, "seal_hash": proof.seal_hash, "marker_hash": proof.marker_sha256,
              "predecessor": None if not runner.children else runner.children[-1]["launch"]}
    if outputs:
        intent.update(access="write", outputs=list(outputs))
    runner._transition("launch_intent", runner.journal.launch_intent, launch, intent)
    # Reachability precedes creation. Each fresh object is permanently tied to this launch.
    child = {"launch": launch, "process": runner.process_factory(proof.session_id, runner.token),
             "streams": StreamEvidence(observer), "authorized": False, "creation_used": False,
             "exit_recorded": False, "diagnostics_recorded": False, "cleanup_recorded": False,
             "intent": intent}
    runner.children.append(child)
    runner._fault("after_launch_intent")
    process, prior_fault = child["process"], child["process"]._fault
    def native_fault(boundary):
        prior_fault(boundary)
        runner._fault("native_" + boundary)
    process._fault = native_fault
    original = None
    try:
        require(not child["creation_used"], "child creation capability already consumed")
        child["creation_used"] = True
        process.start(executable, arguments, cwd=cwd,
            before_resume=lambda identity: runner._authorize(child, identity),
            resume_guard=lambda identity: runner._resume(child, identity))
        evidence = process.wait(timeout, observer=child["streams"].observe)
        if evidence.error is not None:
            raise evidence.error
        require(evidence.state == "confirmed_exited", "unknown whole-job lifetime")
        runner.guard.revalidate()
    except BaseException as error:
        original = error
    try:
        evidence = finish_child(runner, child, timeout)
    except BaseException as secondary:
        if original is None:
            original = secondary
        else:
            runner._error(secondary)
    if original is not None:
        raise original
    require(evidence.root_exit_code == 0, "read-only child failed")
    return evidence
