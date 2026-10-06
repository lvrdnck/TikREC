"""One-shot owned assembly plus same-candidate durable validation, never publication."""

import subprocess
import json
from dataclasses import asdict

from .attempt_coordinator import AttemptError
from .assembly_types import AssemblyError
from .candidate_validation_diagnostics import ValidationDiagnostics
from .candidate_validation_execution import CandidateValidationExecution
from .candidate_validation_plan import commands
from .journal_assembly import JournalAssembly
from .part_validation import validate_decoding
from .session_journal_types import digest, require
from .validation import _ResultBuilder
from .validation_media import _validate_output


class ValidationError(RuntimeError):
    """Retain the first failure, exact adapter and all native/evidence owners."""

    def __init__(self, adapter, original):
        super().__init__("candidate validation failed or ambiguous; ownership retained")
        self.adapter, self.original, self.report = adapter, original, adapter.report
        self.diagnostics = tuple(adapter.coordinator.errors)


class JournalValidation:
    """No reopen, retry, adoption or publication; one held candidate per invocation."""

    def __init__(self, authority, *, candidate_publication=False, **options):
        self.assembly = JournalAssembly(authority, candidate_validation=True, candidate_publication=candidate_publication, **options)
        self.coordinator = self.assembly.coordinator
        self.capability, self.report, self.error, self.used = None, None, None, False

    def run(self):
        """Assemble once, inspect/decode/check DTS while original protection stays held."""
        runner = self.coordinator
        with runner.run_lock:
            require(not self.used, "candidate validation is single-use")
            self.used = True
            try:
                assembled = self.assembly.run()
                if assembled is None:
                    return None
                candidate = runner.journal.scratch(runner.token)["candidate"]
                binding = {"session_id": assembled.session_id, "token": runner.token, "candidate": candidate,
                           "workspace": str(runner.scratch.path),
                           "commands": commands(str(self.assembly.ffprobe.resolve()), assembled.candidate)}
                if getattr(runner, "publication_capable", False):
                    binding["transport"] = "retained_stdin"
                    binding["commands"] = commands(str(self.assembly.ffprobe.resolve()), assembled.candidate,
                                                   retained_stdin=True)
                self.capability = CandidateValidationExecution(runner, binding)
                runner._fault("before_validation_authority")
                self.capability.begin()
                result = _ResultBuilder(assembled.candidate, "unpublished_candidate", True)
                result.output_availability = "present"
                def execute(command, **_):
                    index = self.capability.index
                    collector = ValidationDiagnostics(index)
                    try:
                        require(command == commands(str(self.assembly.ffprobe.resolve()), assembled.candidate)[index],
                                "unexpected media validation command")
                        evidence = self.capability.execute(binding["commands"][index], collector)
                    except BaseException as error:
                        # inspect_media's best-effort API may catch OSError;
                        # keep the execution failure independently before reuse.
                        if self.error is None:
                            self.error = error
                        raise
                    stderr = collector.stderr_text(evidence)
                    if index == 0 and stderr:
                        result.finding("error", "output_probe_diagnostics", stderr[:4096], assembled.candidate)
                    return subprocess.CompletedProcess(command, evidence.root_exit_code,
                        bytes(collector.stdout).decode("utf-8"), stderr)
                # Validate the output itself. Pending publication manifests are
                # neither modified nor used as candidate-validation prerequisites.
                _validate_output(assembled.candidate, result, True, str(self.assembly.ffprobe.resolve()), execute,
                    readable_check=self.capability.readable if binding.get("transport") == "retained_stdin" else None)
                if self.error is not None:
                    raise self.error
                if self.capability.index == 1:
                    # Failed container inspection skips decode in the legacy API;
                    # consume the remaining fixed check and record its outcome.
                    error = validate_decoding(assembled.candidate, str(self.assembly.ffprobe.resolve()), execute)
                    result.final_output_decode = "failed" if error else "passed"
                    if error:
                        result.finding("error", "output_decode", error[:4096], assembled.candidate)
                collector = ValidationDiagnostics(2)
                evidence = self.capability.execute(binding["commands"][2], collector)
                packet_errors = collector.packet_problems
                if evidence.root_exit_code != 0 or collector.seen[1]:
                    packet_errors.append(collector.stderr_text(evidence)[:4096] or "packet probe failed")
                for message in packet_errors:
                    result.finding("error", "output_packet_dts", message, assembled.candidate)
                for message in collector.packet_warnings:
                    result.finding("warning", "output_packet_dts_warning", message, assembled.candidate)
                if any(f.level == "error" for f in result.findings):
                    result.media_integrity = "failed"
                self.report = {**asdict(result.finish()), "packet_dts": "failed" if packet_errors else "passed",
                               "packet_count": collector.packet_count}
                for finding in self.report["findings"]:
                    if len(finding["message"]) > 4096:
                        finding["message"] = finding["message"][:2000] + "\n[bounded excerpt]\n" + finding["message"][-2000:]
                self.capability.revalidate()
                runner._fault("after_validation_result")
                self.capability.revalidate()
                children = []
                for child in runner.journal.child_history(runner.token, after=candidate["sequence"], limit=3):
                    for field in ("intent", "identity", "exit", "diagnostics"):
                        child[field] = None if child[field] is None else json.loads(child[field])
                    children.append(child)
                evidence = {"report": self.report, "children": children, "binding_hash": digest(binding)}
                runner._fault("before_validation_receipt")
                self.capability.revalidate()
                runner._transition("finish_validation", runner.journal.finish_validation, evidence)
                runner._fault("after_validation_receipt")
                self.capability.revalidate()
                if not self.report["passed"]:
                    raise ValueError("candidate failed media validation")
                return self.report
            except BaseException as original:
                self.error = original.original if isinstance(original, (AttemptError, AssemblyError)) else original
                runner.cancelled.set()
                if runner.scratch is not None:
                    runner.validation_retained = True
                    runner.scratch.hold(self.error)
                raise ValidationError(self, self.error) from self.error

    def cancel(self, timeout=5):
        """Revoke execution and bound exact owned validator cancellation."""
        return self.coordinator.cancel(timeout)

    def close(self, timeout=5):
        """Close proven child controls; retain candidate/input pins for this phase."""
        return self.coordinator.close(timeout)
