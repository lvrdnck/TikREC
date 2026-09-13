"""Offline checks for conservative retained-part discovery and FLV framing."""

import pytest

from tests.test_writer import (audio, audio_configuration, avc_configuration,
                               video)
from tikrec.session_parts import discover_parts, part_index, part_order
from tikrec.writer import write_parts


def populate(directory, count=2):
    for index in range(1, count + 1):
        write_parts([audio_configuration(90), avc_configuration(100, b"config"),
                     video(120, 1), audio(125)], directory, start_index=index)


def test_discovers_contiguous_parts_and_next_index(tmp_path):
    populate(tmp_path, 3)
    result = discover_parts(tmp_path)
    assert [path.name for path in result.parts] == ["part-0001.flv", "part-0002.flv", "part-0003.flv"]
    assert result.next_index == 4


def test_numeric_order_continues_past_four_digits(tmp_path):
    paths = [tmp_path / name for name in ["part-10000.flv", "part-9999.flv", "part-0002.flv"]]
    assert [p.name for p in sorted(paths, key=part_order)] == ["part-0002.flv", "part-9999.flv", "part-10000.flv"]
    assert part_index(paths[0]) == 10000


@pytest.mark.parametrize("name", ["part-1.flv", "part-0000.flv", "part-00001.flv",
    "part-0001.FLV", "part-１２３４.flv", "part-0001-copy.flv", "other.flv",
    "part-0001.flv.backup"])
def test_malformed_part_names_are_not_resume_inputs(tmp_path, name):
    populate(tmp_path, 1)
    extra = tmp_path / name
    extra.write_bytes(b"preserve")
    with pytest.raises(ValueError):
        discover_parts(tmp_path)
    assert extra.read_bytes() == b"preserve"


@pytest.mark.parametrize("name", [".part-0002.flv.partial", "part-0002.flv.partial",
                                  ".session.json.partial"])
def test_partials_block_resume_and_remain_untouched(tmp_path, name):
    populate(tmp_path, 1)
    partial = tmp_path / name
    partial.write_bytes(b"interrupted")
    with pytest.raises(ValueError, match="partial"):
        discover_parts(tmp_path)
    assert partial.read_bytes() == b"interrupted"


def test_gaps_and_missing_first_part_fail(tmp_path):
    populate(tmp_path, 3)
    (tmp_path / "part-0002.flv").unlink()
    with pytest.raises(ValueError, match="contiguous"):
        discover_parts(tmp_path)
    (tmp_path / "part-0001.flv").unlink()
    with pytest.raises(ValueError, match="contiguous"):
        discover_parts(tmp_path)


def test_unrelated_nonmedia_files_are_ignored(tmp_path):
    populate(tmp_path, 1)
    (tmp_path / "notes.txt").write_text("user note")
    (tmp_path / "session.json").write_text("{}")
    (tmp_path / "connections.jsonl").write_text("")
    assert len(discover_parts(tmp_path).parts) == 1


def test_empty_or_missing_directory_fails(tmp_path):
    with pytest.raises(ValueError, match="no completed"):
        discover_parts(tmp_path)
    with pytest.raises(ValueError, match="existing"):
        discover_parts(tmp_path / "missing")


@pytest.mark.parametrize("damage", ["empty", "bad_header", "truncate", "previous_size", "version"])
def test_obviously_damaged_parts_fail_without_repair(tmp_path, damage):
    populate(tmp_path, 1)
    path = tmp_path / "part-0001.flv"
    original = path.read_bytes()
    damaged = {"empty": b"", "bad_header": b"BAD" + original[3:],
               "truncate": original[:-1], "previous_size": original[:-4] + b"\0\0\0\0",
               "version": original[:3] + b"\x02" + original[4:]}[damage]
    path.write_bytes(damaged)
    with pytest.raises(ValueError, match="structural"):
        discover_parts(tmp_path)
    assert path.read_bytes() == damaged


@pytest.mark.parametrize("tags", [
    [video(0, 1)], [avc_configuration(0, b"config"), video(0, 2)],
    [avc_configuration(0, b"config")],
    [avc_configuration(0, b"config"), video(0, 1), audio(1)],
])
def test_missing_config_keyframe_or_aac_config_is_invalid(tmp_path, tags):
    path = tmp_path / "part-0001.flv"
    path.write_bytes(b"FLV\x01\x05\0\0\0\x09\0\0\0\0" + b"".join(t.encoded() for t in tags))
    with pytest.raises(ValueError, match="structural"):
        discover_parts(tmp_path)


def test_part_name_directory_is_rejected(tmp_path):
    (tmp_path / "part-0001.flv").mkdir()
    with pytest.raises(ValueError):
        discover_parts(tmp_path)


def test_finalizer_keeps_numeric_order_for_large_part_numbers(tmp_path):
    from tikrec.finalize import _validate_parts

    populate(tmp_path, 1)
    data = (tmp_path / "part-0001.flv").read_bytes()
    paths = [tmp_path / "part-10000.flv", tmp_path / "part-9999.flv"]
    for path in paths:
        path.write_bytes(data)
    assert _validate_parts(paths) == tuple(reversed(paths))
