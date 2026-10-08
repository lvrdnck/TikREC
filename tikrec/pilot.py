"""Opt-in Windows foreground pilot; ordinary serve/configuration remain legacy."""
import argparse
import getpass
from pathlib import Path

from .pilot_command import PilotCommand, emit
from .pilot_identity import check_tools, source_identity
from .pilot_limits import PilotEnvelope
from .session_journal_types import require


def parser():
    """Require every nonsecret source/state/tool identity explicitly on the command."""
    result = argparse.ArgumentParser(description=__doc__)
    for name in ('checkout', 'home', 'ffmpeg', 'ffprobe'):
        result.add_argument('--' + name, type=Path, required=True)
    result.add_argument('--revision', required=True, help='exact current development HEAD')
    result.add_argument('--source-sha256', required=True, help='reviewed normalized package-source fingerprint')
    result.add_argument('--catalog-id', required=True, help='explicit canonical UUID, same on reopen')
    result.add_argument('--mode', choices=('init', 'reopen'), required=True)
    result.add_argument('--port', type=int, required=True, help='explicit loopback port; 0 chooses a free port')
    return result


def main(argv=None):
    """Launch explicitly; retain failed-start owners until confirmed original-thread cleanup."""
    options = parser().parse_args(argv)
    owner = None
    try:
        require(0 <= options.port <= 65535, 'invalid pilot port')
        source = source_identity(options.checkout, options.revision, options.source_sha256)
        tools = check_tools(options.ffmpeg, options.ffprobe)
        envelope = PilotEnvelope(options.home)
        envelope.launch_ready()
        # The prompt does not discover environment credentials or print a secret.
        token = getpass.getpass('New isolated pilot bearer secret (at least 24 characters): ')
        require(type(token) is str and 24 <= len(token) <= 256 and token.isascii()
                and all(33 <= ord(c) <= 126 for c in token), 'invalid pilot bearer secret')
        emit('preflight', **source, tools=tools, required_free_bytes=16 * 1024**3)
        owner = PilotCommand(options, envelope)
        owner.start(source, token)
        token = None
        return owner.run()
    except BaseException as error:
        emit('failure', reason='pilot_startup_refused', primary_type=type(error).__name__)
        if owner is None:
            return 2
        if owner.primary is None:
            owner.primary = error
        if owner.cleanup():
            return 2
        # An interrupted start never drops attached server/native owners on return.
        return owner.run()


if __name__ == '__main__':
    raise SystemExit(main())
