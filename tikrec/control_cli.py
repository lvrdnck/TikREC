"""Argparse wiring and secret loading for service and remote commands."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from .remote import RemoteClient
from .service import DEFAULT_HOST, DEFAULT_PORT, serve, validate_bind


def add_control_commands(subcommands) -> None:
    """Extend the existing parser without changing the local recording commands."""
    server = subcommands.add_parser("serve", help="run persistent HTTP recording controls")
    server.add_argument("--host", default=DEFAULT_HOST, help="explicit loopback/LAN/Tailscale IP")
    server.add_argument("--port", type=int, default=DEFAULT_PORT)
    server.add_argument("--token-file", metavar="FILE", help="bearer secret; overrides TIKREC_TOKEN")
    remote = subcommands.add_parser("remote", help="control a trusted TikREC service")
    actions = remote.add_subparsers(dest="action", required=True)
    for name in ("health", "status", "start", "stop"):
        action = actions.add_parser(name)
        action.add_argument("--server", required=True, metavar="URL")
        action.add_argument("--token-file", metavar="FILE", help="overrides TIKREC_TOKEN")
        action.add_argument("--timeout", type=float, default=10, help="HTTP timeout in seconds")
        if name == "start":
            action.add_argument("url", metavar="TIKTOK_LIVE_URL")
            action.add_argument("--output", required=True, metavar="ABSOLUTE_PC_MP4_PATH")
            action.add_argument("--raw-copy", action="store_true",
                                help="opt in to raw/arrival evidence beside retained parts")


def read_token(token_file: str | None) -> str | None:
    """Read a secret from a file or environment; never put it in diagnostics."""
    if token_file is not None:
        try:
            token = Path(token_file).read_text(encoding="utf-8").rstrip("\r\n")
        except (OSError, UnicodeError):
            raise ValueError("could not read token file") from None
    else:
        token = os.environ.get("TIKREC_TOKEN")
    # Empty configured secrets are errors rather than silently disabling authentication.
    validate_bind(DEFAULT_HOST, token)
    return token


def run_control_command(arguments: argparse.Namespace, stdout: TextIO, *,
                        service_runner: Callable = serve,
                        remote_opener: Callable | None = None) -> int:
    """Run service or one remote action and print its safe JSON response."""
    token = read_token(arguments.token_file)
    if arguments.command == "serve":
        host = validate_bind(arguments.host, token)
        if not 1 <= arguments.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        print(f"Starting TikREC service on {host}:{arguments.port}", file=stdout, flush=True)
        service_runner(host=host, port=arguments.port, token=token)
        return 0
    client = RemoteClient(arguments.server, token=token, opener=remote_opener,
                          timeout=arguments.timeout)
    if arguments.action == "start":
        result = client.start(arguments.url, arguments.output, raw_copy=arguments.raw_copy)
    else:
        result = getattr(client, arguments.action)()
    print(json.dumps(result, indent=2, sort_keys=True), file=stdout)
    # Starting/stopping acknowledges a request; status exposes any asynchronous failure.
    return 1 if (result.get("state") == "failed"
                 or result.get("recovery_state") in {"deferred", "failed"}) else 0
