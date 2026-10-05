"""Validation receipt semantic consistency checks for the new narrow authority."""

from .session_journal_types import require


def check_report(report, binding):
    """Reject contradictory success, wrong target or unbounded semantic findings."""
    from pathlib import Path
    require(type(report) is dict and type(report.get("passed")) is bool
            and report.get("target") == str(Path(binding["workspace"]) / binding["candidate"]["name"])
            and report.get("target_type") == "unpublished_candidate" and report.get("deep") is True
            and report.get("output_availability") == "present"
            and type(report.get("findings")) in (list, tuple) and len(report["findings"]) <= 64,
            "invalid candidate validation report")
    for finding in report["findings"]:
        require(type(finding) is dict and finding.get("level") in {"error", "warning"}
                and type(finding.get("message")) is str and len(finding["message"]) <= 4096,
                "invalid candidate validation finding")
    require(report["passed"] == (not any(f["level"] == "error" for f in report["findings"])),
            "validation outcome contradicts findings")
    if report["passed"]:
        require(report.get("media_integrity") == "passed" and all(report.get(k) == "passed" for k in
                ("final_output_inspection", "final_output_decode", "packet_dts"))
                and type(report.get("packet_count")) is int and report["packet_count"] > 0,
                "validation success lacks media checks")
