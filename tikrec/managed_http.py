"""Strict authenticated routes for the existing service's managed authority."""

import json

from .managed_registry import current
from .managed_retention import delete, preview, promote_policy


_ROUTES = {"/managed/retention/preview": preview, "/managed/retention/delete": delete,
           "/managed/retention/policy": promote_policy}


def handle_managed(handler) -> bool:
    """Handle only bounded managed routes after the service authenticates the client."""
    if handler.path not in _ROUTES:
        return False
    authority = current()
    if authority is None:
        handler._json(404, {"error": "managed storage is not enabled"})
        return True
    lengths = handler.headers.get_all("Content-Length", [])
    try:
        size = int(lengths[0]) if len(lengths) == 1 else 0
        if (handler.headers.get_content_type() != "application/json"
                or handler.headers.get("Transfer-Encoding") is not None or not 0 < size <= 8192):
            raise ValueError("invalid managed request headers")
        from .configuration_json import unique_fields
        body = json.loads(handler.rfile.read(size), object_pairs_hook=unique_fields)
        if not isinstance(body, dict):
            raise ValueError("managed request must be an object")
        result = _ROUTES[handler.path](authority, body)
    except (OSError, ValueError, TypeError, AttributeError):
        handler._json(400, {"error": "managed request refused; preserve evidence and check service state"})
    except Exception:
        # A lost/failed deletion response is ambiguous. Clients must never retry it.
        handler._json(500, {"error": "managed operation failed; preserve evidence and audit"})
    else:
        handler._json(200, result)
    return True
