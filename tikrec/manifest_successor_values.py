"""Pure schema-1 completion building without capture lifecycle mutation or probes."""

import base64
import hashlib
import json
from copy import deepcopy

from .decode_diagnostics import safe_input_decode_health
from .session_journal_types import require


def packed(data):
    """Retain recoverable exact bytes and a digest, bounded to a control document."""
    require(type(data) is bytes and 0 < len(data) <= 1024 * 1024, "invalid manifest bytes")
    return {"bytes": base64.b64encode(data).decode("ascii"), "sha256": hashlib.sha256(data).hexdigest()}


def unpacked(value):
    """Decode immutable evidence and reject inconsistent digests or encodings."""
    require(type(value) is dict and type(value.get("bytes")) is str and len(value["bytes"]) <= 1398104,
            "invalid manifest byte evidence")
    data = base64.b64decode(value["bytes"], validate=True)
    require(packed(data)["sha256"] == value["sha256"], "manifest byte hash conflicts")
    return data


def successor_bytes(predecessor, session, report):
    """Complete only finalization/media; preserve capture facts and prior errors exactly."""
    values = json.loads(predecessor)
    intent = session["intent"]
    require(type(values) is dict and values.get("schema_version") == 1
            and values.get("session_id") == session["id"]
            and values.get("parts_directory") == intent["parts_path"]
            and values.get("output_path") == intent["output_path"]
            and values.get("status") in {"completed", "interrupted", "failed"}
            and type(values.get("finalization")) is dict
            and values["finalization"].get("status") == "pending", "manifest predecessor conflicts")
    result = deepcopy(values)
    result["finalization"]["status"] = "completed"
    result["finalization"]["input_decode"] = safe_input_decode_health(report["assembly_input_decode"])
    media = report["output_media"]
    require(type(media) is dict and set(media) == {"video_codec", "audio_codec", "width", "height"},
            "owned media facts missing")
    result["media"] = deepcopy(media)
    # Match existing public JSON formatting; this path does not call its unowned writer.
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
