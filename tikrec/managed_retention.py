"""Bounded owner requests executed by the existing trusted storage service."""

from dataclasses import replace
from io import StringIO
from types import SimpleNamespace

from .configuration import ConfigurationStore, validate_retention_max_age_days
from .creator_identity import normalize_creator
from .retention_delete_cli import canonical_uuid, run_delete
from .retention_preview import prepare_preview, preview_digest


def preview(authority, body: dict, **options) -> dict:
    """Return exact target facts without persisting authority, audit or a ticket."""
    if set(body) != {"session_id"}:
        raise ValueError("managed preview accepts only session_id")
    session_id = canonical_uuid(body["session_id"])
    value = prepare_preview(authority.root, session_id,
                            ConfigurationStore(authority.config_path), **options)
    return dict(root=str(value.root), session_id=value.session_id, creator=value.creator,
                ended_at=value.ended_at, output=str(value.output), parts=str(value.parts),
                file_count=value.file_count, total_file_bytes=value.total_file_bytes,
                preview_digest=preview_digest(value))


def delete(authority, body: dict, **options) -> dict:
    """Reuse the normal truthful deletion executor/results with exact remote consent."""
    if set(body) != {"session_id", "confirm", "preview_digest"}:
        raise ValueError("managed delete requires exact UUID confirmation and preview digest")
    session_id = canonical_uuid(body["session_id"])
    digest = body["preview_digest"]
    if (body["confirm"] != session_id or not isinstance(digest, str) or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)):
        raise ValueError("managed deletion confirmation is invalid")
    stdout, stderr = StringIO(), StringIO()
    arguments = SimpleNamespace(session_id=session_id, root=str(authority.root), confirm=session_id)
    code = run_delete(arguments, ConfigurationStore(authority.config_path), stdout, stderr,
                      expected_preview_digest=digest, display_preview=False, **options)
    return dict(code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def promote_policy(authority, body: dict) -> dict:
    """Promote only bounded retention age/protection changes through trusted state."""
    if set(body) != {"action", "value"}:
        raise ValueError("managed policy accepts only action/value")
    action, value = body["action"], body["value"]
    if action not in {"age", "protect", "unprotect"}:
        raise ValueError("unknown managed policy action")
    if action == "age":
        value = None if value is None else validate_retention_max_age_days(value)
    else:
        value = normalize_creator(value)
    store = ConfigurationStore(authority.config_path)
    # Reserve before the policy lock, so a waiting promotion cannot race proof.
    with authority.gate.writer():
        authority.validate()
        def change(config):
            if action == "age":
                return replace(config, retention_max_age_days=value)
            creators = config.retention_protected_creators
            if action == "protect" and value not in creators:
                creators += (value,)
            elif action == "unprotect":
                creators = tuple(creator for creator in creators if creator != value)
            return replace(config, retention_protected_creators=creators)
        result = store.update(change)
    return dict(retention_max_age_days=result.retention_max_age_days,
                retention_protected_creators=list(result.retention_protected_creators))
