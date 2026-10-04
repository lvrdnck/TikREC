"""Internal source-ended evidence, distinct from synchronous MP4 results."""

from dataclasses import dataclass
from pathlib import Path

from .connection_log import ConnectionRecord


@dataclass(frozen=True)
class CaptureEnded:
    """A closed source requesting later assembly, without claiming an MP4 exists."""

    parts: tuple[Path, ...]
    requested_output: Path
    interrupted: bool
    connections: tuple[ConnectionRecord, ...]
    room_id: str | None
    source_ended: bool = True
    finalization_pending: bool = True


def end_capture(parts, output, manifest, records, interrupted):
    """Persist the capture timeline while keeping its original output work pending."""
    if output is None:
        raise ValueError("internal deferred capture requires an output identity")
    if manifest.active:
        manifest.complete(parts, interrupted=interrupted, finalization_status="pending")
    return CaptureEnded(tuple(parts), output, interrupted, tuple(records),
                        manifest.snapshot().get("room_id") if manifest.active else None)
