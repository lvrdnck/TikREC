"""Validate fixed manifest evidence for recovered writer crash artifacts."""

from copy import deepcopy
import hashlib
from pathlib import Path

from .session_parts import part_index


def evidence_name(session_id: str, index: int) -> str:
    """Return the deterministic evidence-only name for one writer index."""
    return f".tikrec-writer-crash-{session_id}-part-{index:04d}.evidence"


def recovery_record(plan, timestamp: float) -> dict:
    """Build non-secret manifest evidence for one recovered writer part."""
    return {
        "timestamp": timestamp,
        "part": plan.recovered.name,
        "evidence": plan.evidence.name,
        "source_sha256": plan.source_sha256,
        "source_bytes": plan.source_bytes,
        "recovered_bytes": plan.recovered_bytes,
        "discarded_trailing_bytes": plan.source_bytes - plan.recovered_bytes,
    }


def commit_manifest_recovery(manifest, recovery: dict, parts, *,
                             expected_digest: str | None = None, guard=None) -> None:
    """Atomically append one idempotent writer-recovery record to a manifest."""
    if (expected_digest is not None and
            hashlib.sha256(manifest.path.read_bytes()).hexdigest() != expected_digest):
        raise ValueError("manifest changed before recovery commit")
    values = deepcopy(manifest._require_values())
    records = values.setdefault("writer_recoveries", [])
    if not isinstance(records, list):
        raise ValueError("conflicting writer recovery evidence")
    prior = next((record for record in records
                  if isinstance(record, dict) and record.get("part") == recovery["part"]), None)
    if prior is not None:
        comparable = {key: value for key, value in prior.items() if key != "timestamp"}
        expected = {key: value for key, value in recovery.items() if key != "timestamp"}
        if comparable != expected:
            raise ValueError("conflicting writer recovery evidence")
        return
    records.append(deepcopy(recovery))
    values["part_count"] = len(tuple(parts))
    values["recovery_performed"] = True
    previous = manifest._values
    manifest._values = values
    try:
        manifest._write(expected_digest=expected_digest, guard=guard)
    except BaseException:
        manifest._values = previous
        raise


def recovery_records(manifest: dict) -> list[dict]:
    """Return the optional recovery list or reject a conflicting schema value."""
    records = manifest.get("writer_recoveries", [])
    if not isinstance(records, list):
        raise ValueError("invalid writer recovery evidence")
    return records


def validate_recorded_evidence(directory, retained, records, evidence) -> set[int]:
    """Require every recorded evidence file to match its immutable recovered prefix."""
    recorded: set[int] = set()
    available = {path.name: path for path in evidence}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("part"), str):
            raise ValueError("invalid writer recovery evidence")
        index = part_index(Path(record["part"]))
        evidence_name = record.get("evidence")
        path = available.get(evidence_name)
        part = directory / record["part"]
        if index in recorded or part not in retained.parts or path is None:
            raise ValueError("writer recovery evidence conflicts with retained media")
        if path.is_symlink() or not path.is_file():
            raise ValueError("writer recovery evidence is not a regular file")
        source_bytes = record.get("source_bytes")
        source_sha256 = record.get("source_sha256")
        recovered_bytes = record.get("recovered_bytes")
        discarded = record.get("discarded_trailing_bytes")
        if (type(source_bytes) is not int or type(recovered_bytes) is not int
                or type(discarded) is not int or source_bytes <= 0
                or not isinstance(source_sha256, str) or len(source_sha256) != 64
                or any(character not in "0123456789abcdef" for character in source_sha256)
                or recovered_bytes <= 0 or recovered_bytes + discarded != source_bytes
                or discarded < 0 or path.stat().st_size != source_bytes
                or file_sha256(path) != source_sha256
                or part.stat().st_size != recovered_bytes
                or not same_prefix(path, part, recovered_bytes)):
            raise ValueError("writer recovery byte evidence is inconsistent")
        recorded.add(index)
    return recorded


def validate_record_schema(records: list[dict], timestamp_validator) -> None:
    """Validate optional schema fields before filesystem ownership checks."""
    expected = {"timestamp", "part", "evidence", "source_sha256", "source_bytes",
                "recovered_bytes", "discarded_trailing_bytes"}
    for record in records:
        if not isinstance(record, dict) or set(record) != expected:
            raise ValueError("invalid writer recovery record")
        if not timestamp_validator(record["timestamp"]):
            raise ValueError("invalid writer recovery timestamp")
        if (not isinstance(record["part"], str) or not isinstance(record["evidence"], str)
                or Path(record["part"]).name != record["part"]
                or Path(record["evidence"]).name != record["evidence"]):
            raise ValueError("invalid writer recovery paths")
        part_index(Path(record["part"]))


def same_prefix(source: Path, recovered: Path, count: int) -> bool:
    """Compare a bounded source prefix with one recovered part."""
    with source.open("rb") as left, recovered.open("rb") as right:
        remaining = count
        while remaining:
            size = min(64 * 1024, remaining)
            if left.read(size) != right.read(size):
                return False
            remaining -= size
    return True


def file_sha256(path: Path) -> str:
    """Hash one regular artifact without retaining any media bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
