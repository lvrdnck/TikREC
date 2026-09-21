"""Focused tests for lazy CLI diagnostic preference resolution."""

import json

from tikrec.diagnostics import effective_debug_tracebacks


def test_explicit_debug_choice_does_not_read_malformed_configuration(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{", encoding="utf-8")
    assert effective_debug_tracebacks(True, str(path)) is True
    assert effective_debug_tracebacks(False, str(path)) is False


def test_missing_and_configured_debug_defaults(tmp_path) -> None:
    path = tmp_path / "config.json"
    assert effective_debug_tracebacks(None, str(path)) is False
    path.write_text(json.dumps({
        "schema_version": 1, "debug_tracebacks": True,
    }), encoding="utf-8")
    assert effective_debug_tracebacks(None, str(path)) is True
