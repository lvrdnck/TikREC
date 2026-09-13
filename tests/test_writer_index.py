"""Offline allocation regressions for the writer's existing start_index API."""

import pytest

from tests.test_writer import avc_configuration, video
from tikrec.writer import write_parts


@pytest.mark.parametrize("index", [0, -1, True, False, "3", 3.0, None])
def test_index_must_be_a_positive_integer(tmp_path, index):
    with pytest.raises(ValueError):
        write_parts([], tmp_path, start_index=index)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("existing", ["part-0003.flv", ".part-0003.flv.partial"])
def test_explicit_allocation_preserves_final_and_partial_collisions(tmp_path, existing):
    path = tmp_path / existing
    path.write_bytes(b"immutable")
    with pytest.raises(FileExistsError):
        write_parts([avc_configuration(10, b"config"), video(20, 1)], tmp_path, start_index=3)
    assert path.read_bytes() == b"immutable"


def test_default_and_arbitrary_index_with_avc_roll(tmp_path):
    tags = [avc_configuration(10, b"one"), video(20, 1),
            avc_configuration(30, b"two"), video(40, 1)]
    assert [p.name for p in write_parts(tags, tmp_path / "fresh")] == ["part-0001.flv", "part-0002.flv"]
    assert [p.name for p in write_parts(tags, tmp_path / "resumed", start_index=3)] == ["part-0003.flv", "part-0004.flv"]


def test_collision_created_during_iteration_preserves_both_artifacts(tmp_path):
    path = tmp_path / "part-0003.flv"

    def source():
        yield avc_configuration(10, b"config")
        yield video(20, 1)
        path.write_bytes(b"do not replace")

    with pytest.raises(FileExistsError):
        write_parts(source(), tmp_path, start_index=3)
    assert path.read_bytes() == b"do not replace"
    assert (tmp_path / ".part-0003.flv.partial").exists()
