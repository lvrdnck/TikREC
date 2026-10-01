"""Explicit owner consent delegated to the dedicated existing service."""

from pathlib import Path

from .control_cli import read_token
from .remote import RemoteClient, RemoteError
from .retention_delete_cli import _diagnose, _show_preview, _typed_confirmation, canonical_uuid
from .retention_preview import RetentionPreview


def run_managed_delete(arguments, stdout, stderr, stdin, *, opener=None) -> int:
    """Preview, confirm once and submit one service request without automatic retry."""
    session_id = canonical_uuid(arguments.session_id)
    if arguments.root is not None:
        raise ValueError("managed retention uses the service's fixed root; omit ROOT")
    if arguments.confirm is not None and arguments.confirm != session_id:
        raise ValueError("confirmation UUID does not exactly match target")
    client = RemoteClient(arguments.server, token=read_token(arguments.token_file),
                          timeout=arguments.timeout, opener=opener)
    value = client.managed_preview(session_id)
    if value.get("session_id") != session_id:
        raise ValueError("managed service returned a different preview target")
    preview = RetentionPreview(
        root=Path(value["root"]), session_id=session_id, creator=value["creator"],
        ended_at=value["ended_at"], output=Path(value["output"]), parts=Path(value["parts"]),
        file_count=value["file_count"], total_file_bytes=value["total_file_bytes"], guard=())
    _show_preview(preview, stdout)
    if arguments.confirm is None and not _typed_confirmation(stdin, stdout, session_id):
        raise ValueError("exact session UUID confirmation was not provided")
    try:
        result = client.managed_delete(session_id, value["preview_digest"])
    except (RemoteError, KeyboardInterrupt, SystemExit):
        # A dispatched request may have mutated storage before the response was lost.
        # Preserve the existing post-intent uncertainty rule conservatively here.
        _diagnose(stderr, ["PARTIAL/UNCERTAIN: managed deletion response unavailable; "
                           "preserve service audit and remaining artifacts; do not retry"])
        return 3
    code = result.get("code")
    if (type(code) is not int or code not in {0, 1, 3, 130}
            or not isinstance(result.get("stdout"), str)
            or not isinstance(result.get("stderr"), str)):
        _diagnose(stderr, ["PARTIAL/UNCERTAIN: invalid managed deletion result; do not retry"])
        return 3
    try:
        stdout.write(result["stdout"])
        stderr.write(result["stderr"])
    except BaseException:
        # A response proving durable COMPLETE remains true even if display fails.
        return code
    return code
