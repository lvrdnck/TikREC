"""Validate explicit trusted-network service binding and authentication."""

import ipaddress

DEFAULT_HOST = "127.0.0.1"


def validate_bind(host: str, token: str | None) -> str:
    """Require explicit IP binding and a secret for all non-loopback addresses."""
    host = DEFAULT_HOST if host == "localhost" else host
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError("host must be a loopback, LAN, or Tailscale IP address") from None
    if token is not None and (not 16 <= len(token) <= 512
                              or any(not 33 <= ord(c) <= 126 for c in token)):
        raise ValueError("token must contain 16–512 printable ASCII characters without spaces")
    if not address.is_loopback and token is None:
        raise ValueError("non-loopback binding requires TIKREC_TOKEN or --token-file")
    return str(address)
