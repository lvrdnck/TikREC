"""Explicit source, native path and usable-tool proofs for the foreground pilot."""
import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

from .session_journal_types import JournalError, require


def local(path, *, exists=True):
    """Reject aliases, redirections, nonlocal paths and missing known identities."""
    path = Path(path)
    require(path.is_absolute() and str(path) == str(path.absolute())
            and not str(path).startswith('\\\\') and '..' not in path.parts,
            'pilot paths must be explicit native absolute paths')
    items = [path, *path.parents]
    if exists:
        # Keep the known-target revalidation after the complete ancestor walk.
        items.append(path)
    for item in items:
        try:
            # One fresh no-follow observation supplies all related facts. Following
            # existence checks can misclassify a dangling redirection as a new leaf.
            info = item.lstat()
        except FileNotFoundError:
            require(item == path and not exists, 'missing pilot parent or state')
            continue
        except OSError:
            raise JournalError('pilot path metadata unavailable') from None
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                'redirected pilot path')
        directory = stat.S_ISDIR(info.st_mode)
        require(item == path or directory, 'pilot ancestor is not a directory')
        require(directory or info.st_nlink == 1, 'multiply linked pilot file')
    return path


def source_identity(checkout, revision, expected_hash=None):
    """Bind the actual import to an explicitly identified development Git checkout."""
    require(os.name == 'nt' and sys.version_info >= (3, 11), 'pilot requires Windows Python 3.11+')
    require(sqlite3.sqlite_version_info >= (3, 35), 'pilot SQLite is unsupported')
    root = local(checkout)
    require(root == Path(__file__).absolute().parents[1], 'pilot import is from another checkout')
    def git(*arguments):
        return subprocess.check_output(['git', *arguments], cwd=root, text=True,
                                       encoding='utf-8', timeout=10).strip()
    require(Path(git('rev-parse', '--show-toplevel')) == root, 'pilot Git root conflicts')
    require(git('branch', '--show-current') == 'codex/capture-journal-handoff', 'pilot branch conflicts')
    require(git('remote', 'get-url', 'origin') == 'https://github.com/lvrdnck/TikREC.git', 'pilot origin conflicts')
    require(len(revision) == 40 and git('rev-parse', 'HEAD') == revision, 'pilot revision conflicts')
    files = sorted((root / 'tikrec').glob('*.py'))
    hashes = {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in files}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    # Normalize Git's Windows line endings; raw frozen-run hashes remain separate.
    require(expected_hash is None or digest == expected_hash, 'pilot source fingerprint conflicts')
    return {'checkout': str(root), 'revision': revision, 'source_sha256': digest,
            'python': sys.executable, 'python_version': sys.version.split()[0],
            'sqlite_version': sqlite3.sqlite_version, 'backend': 'isolated_schema10_pilot'}


def check_tools(ffmpeg, ffprobe):
    """Check the selected binaries, encoders and decoders before creating pilot state."""
    result = {}
    for name, path in [('ffmpeg', ffmpeg), ('ffprobe', ffprobe)]:
        path = local(path)
        require(path.is_file(), 'pilot tool is not a regular file')
        completed = subprocess.run([str(path), '-version'], capture_output=True, timeout=10)
        require(completed.returncode == 0 and completed.stdout.startswith(name.encode() + b' version'),
                'pilot media tool is unusable')
        result[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'version': completed.stdout.splitlines()[0][:256].decode('utf-8', errors='replace')}
    for kind, codec in [('encoder', 'libx264'), ('encoder', 'aac'), ('decoder', 'h264'), ('decoder', 'aac')]:
        completed = subprocess.run([str(ffmpeg), '-hide_banner', '-h', kind + '=' + codec],
                                   capture_output=True, timeout=10)
        require(completed.returncode == 0 and (kind.title() + ' ' + codec).encode() in completed.stdout,
                'pilot required media capability is unavailable')
    return result
