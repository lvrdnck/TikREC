"""Native proof rejects writable ancestors, ACLs, aliases, and replaced roots."""

import os
import sys

import pytest

from tikrec.managed_paths import ProtectedPath, check_permissions


pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="native Linux")


def test_owner_writable_ancestor_refused(tmp_path):
    path = tmp_path / "root"
    path.mkdir(mode=0o750)
    with pytest.raises(ValueError, match="ownership|exclusion"):
        ProtectedPath(path, os.getuid())


@pytest.mark.parametrize("mode", [0o777, 0o770, 0o707, 0o4750])
def test_permissions_refuse_extra_write_or_special_bits(tmp_path, mode):
    path = tmp_path / "file"
    path.write_bytes(b"evidence")
    path.chmod(mode)
    with path.open("rb") as handle:
        with pytest.raises(ValueError, match="ownership|exclusion"):
            check_permissions(handle.fileno(), path.stat(), os.getuid(), directory=False)


def test_multiple_links_refused(tmp_path):
    path = tmp_path / "file"
    path.write_bytes(b"evidence")
    path.chmod(0o640)
    os.link(path, tmp_path / "alias")
    with path.open("rb") as handle:
        with pytest.raises(ValueError, match="ownership|exclusion"):
            check_permissions(handle.fileno(), path.stat(), os.getuid(), directory=False)
