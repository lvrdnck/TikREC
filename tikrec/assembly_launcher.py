"""Exact concat-helper work bound in the durable contained writer argument vector."""

import json
import sys
from pathlib import Path

from .finalize_media import _concat_path


# Pass the complete trusted launcher as -c code, rather than importing a mutable
# module via ambient PYTHONPATH. Both code and payload are durable intent bytes.
# The wrapper never escapes its creation-time job: its FFmpeg child inherits
# containment and stdout/stderr, and whole-job membership gates completion.
CONCAT_LAUNCHER = """import json, os, subprocess, sys
from pathlib import Path
spec = json.loads(sys.argv[1])
try:
    if set(spec) != {'command', 'manifest', 'text'}:
        raise ValueError('invalid contained helper specification')
    if spec['manifest'] != 'concat.ffconcat' or not isinstance(spec['text'], str):
        raise ValueError('invalid contained manifest')
    if any(Path.cwd().iterdir()):
        raise FileExistsError('writer workspace is occupied')
    command = spec['command']
    if not isinstance(command, list) or not all(isinstance(x, str) for x in command):
        raise ValueError('invalid exact FFmpeg command')
    with open(spec['manifest'], 'x', encoding='utf-8', newline='\\n') as helper:
        helper.write(spec['text'])
        helper.flush()
        os.fsync(helper.fileno())
    # Inherit the already-contained job and native diagnostic pipes. No second
    # independent owner, shell, detached process or breakaway flags are used.
    code = subprocess.call(command, stdin=subprocess.DEVNULL, close_fds=True)
except BaseException as error:
    print('Error opening output file: contained assembly helper: ' + repr(error), file=sys.stderr)
    code = 1
sys.exit(code)
"""


def concat_launch(command, parts):
    """Bind the helper name, exact text and FFmpeg argv to one writer intent."""
    text = "".join(f"file {_concat_path(part.resolve())}\n" for part in parts)
    payload = json.dumps({"command": list(command), "manifest": "concat.ffconcat", "text": text},
                         sort_keys=True, separators=(",", ":"))
    return Path(sys._base_executable).resolve(), ["-I", "-c", CONCAT_LAUNCHER, payload]
