"""Strict JSON object reader for per-user configuration documents."""


def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON names before defaults could hide a prior value."""
    values: dict[str, object] = {}
    for name, value in pairs:
        if name in values:
            raise ValueError(f"duplicate field: {name}")
        values[name] = value
    return values
