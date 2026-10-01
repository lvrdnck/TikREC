"""Provisioning refuses legacy roots before creating or rewriting any artifact."""

import os
import sys

import pytest


pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="native Linux")


def test_existing_base_is_never_adopted(tmp_path, monkeypatch):
    if os.geteuid() != 0:
        pytest.skip("administrator provisioning refusal")
    from types import SimpleNamespace
    from tikrec.managed_provision import provision
    import tikrec.managed_provision as module
    monkeypatch.setattr(module.pwd, "getpwnam", lambda _: SimpleNamespace(
        pw_uid=60031, pw_shell="/usr/sbin/nologin"))
    monkeypatch.setattr(module.grp, "getgrnam", lambda _: SimpleNamespace(gr_gid=60032))
    original = tmp_path / "legacy.mp4"
    original.write_bytes(b"original evidence")
    with pytest.raises(ValueError, match="existing"):
        provision(tmp_path, tmp_path / "definition", tmp_path / "code",
                  user="disposable", reader_group="disposable")
    assert original.read_bytes() == b"original evidence"
    assert list(tmp_path.iterdir()) == [original]
