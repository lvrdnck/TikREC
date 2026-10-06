"""Actual recovery supervisor paused while newly acquired native proof is live."""

import json
import sys
from pathlib import Path

from tests.owned_process_probe import events, wait
from tikrec.capture_handoff_authority import CaptureAuthority
from tikrec.session_journal import SessionJournal
from tikrec.owned_process_api import check


def main():
    """Expose the committed generation before the parent terminates this process."""
    mode, context_path, *names = sys.argv[1:]
    source = json.loads(Path(context_path).read_text(encoding='utf-8'))
    api, barriers = events(names)
    journal = SessionJournal(Path(source['path']), source['catalog'])
    with CaptureAuthority(journal, Path(source['root'])) as owner:
        def fault(point):
            if point == mode:
                record = owner.journal.release_recovery(source['token'])
                saved = {key: source[key] for key in ('path', 'catalog', 'root', 'session', 'token')}
                saved['generation'] = record['head']['generation']
                saved['state'] = record['head']['state']
                Path(context_path).with_name('recovery-context.json').write_text(
                    json.dumps(saved), encoding='utf-8')
                check(api.SetEvent(barriers[0]))
                wait(api, barriers[1])
        owner.recover_prepared_release(source['session'], source['token'], fault=fault)


if __name__ == '__main__':
    main()
