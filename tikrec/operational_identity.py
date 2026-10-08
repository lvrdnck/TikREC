"""Prospective headless import/config/tool identity, without production discovery."""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from .pilot_identity import local, check_tools
from .session_journal_types import require


def identity(configuration, ffmpeg, ffprobe):
    """Record the actual loaded package and selected tools before opening state."""
    require(os.name == 'nt' and sys.version_info >= (3, 11) and
            sqlite3.sqlite_version_info >= (3, 35), 'operational mode requires native Windows Python 3.11+')
    root = Path(__file__).absolute().parents[1]
    hashes = {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
              for p in sorted((root / 'tikrec').glob('*.py'))}
    revision = None
    try:
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root,
                                          text=True, timeout=10, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        pass  # Installed source identity is the package fingerprint, not guessed Git provenance.
    config = local(configuration)
    require(config.is_file() and config.stat().st_size <= 1024**2, 'explicit configuration unavailable')
    return {'checkout': str(root), 'import_path': str(Path(__file__).absolute()),
            'supervisor_pid': os.getpid(), 'parent_pid': os.getppid(),
            'source_sha256': hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
            'revision': revision, 'python': sys.executable, 'python_version': sys.version.split()[0],
            'sqlite_version': sqlite3.sqlite_version}, {
                'path': str(config), 'sha256': hashlib.sha256(config.read_bytes()).hexdigest()}, check_tools(ffmpeg, ffprobe)
