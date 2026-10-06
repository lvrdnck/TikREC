"""Fixed read-only FFprobe phases for one protected unpublished candidate."""

from pathlib import Path

from .session_journal_types import require


def commands(ffprobe, candidate, *, retained_stdin=False):
    """Bind only output inspection, full decode and streamed packet DTS checks."""
    executable, target = str(ffprobe), str(candidate)
    result = [
        [executable, "-v", "error", "-show_streams", "-show_format", "-show_entries",
         "stream=codec_type,codec_name,width,height:format=format_name,duration", "-of", "json", target],
        [executable, "-v", "error", "-show_frames", "-show_entries", "frame=media_type",
         "-of", "csv=p=0", target],
        [executable, "-v", "error", "-show_packets", "-show_entries", "packet=stream_index,dts",
         "-of", "compact=p=0:nk=0", target],
    ]
    if retained_stdin:
        # The inherited descriptor is seekable and references the original native
        # owner. No path reopen can coexist with its narrow DELETE access.
        result = [c[:-1] + ["-fd", "0", "fd:"] for c in result]
    return result


def binding_commands(binding):
    """Derive only fixed path or explicit retained-descriptor validation commands."""
    return commands(binding["commands"][0][0], Path(binding["workspace"]) / binding["candidate"]["name"],
                    retained_stdin=binding.get("transport") == "retained_stdin")


def check_launch(connection, row, intent):
    """Reject arbitrary post-candidate processes even with a validation phase label."""
    import json
    validation = connection.execute("SELECT * FROM candidate_validations WHERE token=?", (row["token"],)).fetchone()
    require(validation is not None and validation["operation"] == intent["validation_operation"]
            and connection.execute("SELECT 1 FROM validation_receipts WHERE token=?", (row["token"],)).fetchone()
            is None, "candidate-ready attempt lacks open validation authority")
    binding = json.loads(validation["binding"])
    index = row["sequence"] - binding["candidate"]["sequence"]
    require(index in range(3) and intent["validation_index"] == index
            and intent["phase"] == "candidate_validation"
            and [intent["executable"], *intent["arguments"]] == binding["commands"][index]
            and Path(intent["cwd"]) == Path(binding["workspace"]), "candidate validator intent conflicts")
