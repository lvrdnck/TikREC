"""Bind every authorized retention file to a stable byte observation."""

from __future__ import annotations

from pathlib import Path

from .writer_recovery_evidence import prove_recovery_bytes


def bind_file_bytes(root: Path, order: tuple, recoveries: list[dict], volume,
                    digest_reader) -> tuple[tuple[tuple[str, str], ...],
                                             tuple[tuple[str, str], ...]]:
    """Hash all authorized files and retain the writer-recovery proof subset."""
    files = {item.relative_path: item for item in order if item.kind == "file"}
    hashes = {name: digest_reader(root, item, volume)
              for name, item in files.items()}
    proof_names = {str(Path(order[-2].relative_path) / name)
                   for record in recoveries
                   for name in (record["evidence"], record["part"])}
    if not proof_names.issubset(files):
        raise ValueError("retention recovery proof is outside the artifact allowlist")
    for record in recoveries:
        evidence = str(Path(order[-2].relative_path) / record["evidence"])
        if (hashes[evidence] != record["source_sha256"]
                or not prove_recovery_bytes(root / evidence,
                                            root / order[-2].relative_path / record["part"],
                                            record["source_bytes"],
                                            record["recovered_bytes"],
                                            record["source_sha256"])):
            raise ValueError("retention recovery byte proof changed")
    return tuple(sorted(hashes.items())), tuple(sorted(
        (name, hashes[name]) for name in proof_names))
