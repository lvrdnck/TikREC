"""Offline normalization tests for configured public creator identity."""

import pytest

from tikrec.creator_identity import (
    CreatorIdentityError,
    normalize_creator,
    validate_creator_handle,
    validate_monitored_creators,
)


@pytest.mark.parametrize(("value", "expected"), [
    ("Creator_Name", "creator_name"),
    ("@Creator.Name", "creator.name"),
    ("https://www.tiktok.com/@Creator_Name/live", "creator_name"),
    ("https://www.tiktok.com/@Creator.Name/live?lang=en#player", "creator.name"),
])
def test_supported_creator_forms_normalize_without_network(
    value: str, expected: str
) -> None:
    assert normalize_creator(value) == expected


@pytest.mark.parametrize("value", [
    "", "@", "two creators", ".creator", "creator.", "a" * 25,
    "creator/name", "http://www.tiktok.com/@creator/live",
    "https://tiktok.com/@creator/live",
    "https://m.tiktok.com/@creator/live",
    "https://person@www.tiktok.com/@creator/live",
    "https://www.tiktok.com:443/@creator/live",
    "https://www.tiktok.com/@creator/video/1",
    "https://www.tiktok.com/@creator/live/extra",
    "https://www.tiktok.com/@creator/live/",
    "https://www.tiktok.com//@creator/live",
    "https://www.tiktok.com/@creator%2Fbad/live",
])
def test_malformed_creator_values_are_rejected(value: str) -> None:
    with pytest.raises(CreatorIdentityError, match="creator"):
        normalize_creator(value)


def test_persisted_creator_handles_must_already_be_canonical_and_unique() -> None:
    assert validate_creator_handle("creator.name") == "creator.name"
    assert validate_monitored_creators(("first", "second_creator")) == (
        "first", "second_creator",
    )
    for invalid in ("Creator", "@creator", "creator.", 1, None):
        with pytest.raises(CreatorIdentityError):
            validate_creator_handle(invalid)
    with pytest.raises(CreatorIdentityError, match="ordered list"):
        validate_monitored_creators(["creator"])
    with pytest.raises(CreatorIdentityError, match="duplicates"):
        validate_monitored_creators(("creator", "creator"))
