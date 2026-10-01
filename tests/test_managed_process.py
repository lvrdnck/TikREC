"""Trusted runtime rejects login identities, ordinary Python and writable imports."""

import os
import sys

import pytest

from tikrec.managed_process import verify_runtime


pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="native Linux")


def test_ordinary_python_cannot_establish_managed_authority(tmp_path):
    with pytest.raises(ValueError, match="non-login|isolated"):
        verify_runtime(os.getuid(), tmp_path)
