"""Read-only checks for simple service finalization recovery and existing output."""

import json
import math
from pathlib import Path

from .manifest import SessionManifest
from .session_resume import (_read_connections, _unique_values, _validate_manifest,
                             ResumeSession)
from .writer_recovery import inspect_writer_storage
from .creator_identity import normalize_creator


def inspect_recovery_session(job, *, clock, media_inspector):
    """Validate owned storage without relaxing explicit capture-resume eligibility."""
    directory, output = Path(job.parts_directory), Path(job.output_path)
    path = directory / "session.json"
    if not path.is_file() or path.is_symlink():
        raise ValueError("recovery needs a supported regular manifest")
    values = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_values)
    storage = inspect_writer_storage(directory, job, values)
    retained = storage.retained
    _validate_manifest(values, directory, retained, job.session_id, "tiktok_live",
                       finalization_recovery=True)
    if values.get("creator") is not None and values["creator"] != normalize_creator(job.source_url):
        raise ValueError("conflicting saved creator identity")
    # A service job always requests an output; null/different declarations are contradictions.
    if (not isinstance(values.get("output_path"), str)
            or Path(values["output_path"]).resolve() != output.resolve()):
        raise ValueError("conflicting recovery output")
    if values.get("room_id") is not None and values["room_id"] != job.room_id:
        raise ValueError("conflicting saved room identity")
    count, previous_end = _read_connections(directory, retained, job.session_id)
    if values["status"] != "recording" and count > values["connection_count"]:
        raise ValueError("closed manifest predates connection evidence")
    manifest = SessionManifest.load(path, clock=clock, media_inspector=media_inspector)
    if manifest is None or manifest.snapshot() != values:
        raise ValueError("manifest changed during recovery inspection")
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError("requested output is not a regular file")
    return ResumeSession(manifest, retained, job.session_id, values["status"],
                         max(count, values["connection_count"]) + 1, previous_end,
                         storage.recovery)


def completed_output_is_proven(session, output, media_inspector):
    """Require committed completion evidence plus bounded matching media inspection."""
    values = session.manifest.snapshot()
    if (values["finalization"]["status"] != "completed"
            or values["status"] not in {"completed", "interrupted"}
            or not output.is_file() or output.is_symlink() or output.stat().st_size == 0):
        return False
    info = media_inspector(output)
    if (info is None or not info.video_codec or not info.format_name
            or type(info.duration_seconds) not in {int, float}
            or not math.isfinite(info.duration_seconds) or info.duration_seconds <= 0):
        return False
    # Schema-1 optional codec facts need only match when the session actually recorded them.
    return all(value is None or getattr(info, name) == value
               for name, value in values["media"].items()
               if name in {"video_codec", "audio_codec", "width", "height"})
