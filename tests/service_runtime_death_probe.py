"""Real disposable runtime supervisor; parent owns exact death barriers."""

import json
import shutil
import sys
import time
from pathlib import Path

from tests.capture_handoff_helpers import local_media, observations
from tests.owned_process_probe import events, wait
from tikrec.capture_handoff_authority import operation_id
from tikrec.owned_process_api import check
from tikrec.service_runtime import IsolatedServiceRuntime
from tikrec.session_journal import SessionJournal


def main():
    """Pause connected runtime settlement or fresh startup recovery before death."""
    mode, directory, *names = sys.argv[1:]
    base = Path(directory)
    api, barriers = events(names)
    saved = base / 'runtime-context.json'
    options = {}
    if mode.startswith('recovery:'):
        context = json.loads(saved.read_text())
        journal, root = SessionJournal(Path(context['path']), context['catalog']), Path(context['root'])
        def fault(point):
            if point == mode.split(':')[1]:
                check(api.SetEvent(barriers[0]))
                wait(api, barriers[1])
        options['recovery_fault'] = fault
    else:
        state, root = base / 'state', base / 'media'
        state.mkdir()
        root.mkdir()
        journal = SessionJournal.initialize(state / 'sessions.sqlite3', operation_id())
        data = local_media(base / 'fixture.flv')
        options['observations'] = lambda bridge: observations(data, room=bridge.intent.expected_room)
        def fault(point):
            if point == mode:
                deadline = time.monotonic() + 15
                # Terminal work is historical and no longer in the bounded queue.
                required = 1 if mode == 'after_terminal_release' else 2
                while len(journal.status()['tasks']) < required:
                    assert time.monotonic() < deadline
                    time.sleep(0.01)
                runner = runtime.current.coordinator
                context = {'path': str(journal.path), 'catalog': journal.catalog_id,
                    'root': str(root), 'session': runner.claimed['session_id'], 'token': runner.token}
                saved.write_text(json.dumps(context))
                check(api.SetEvent(barriers[0]))
                wait(api, barriers[1])
        options['settlement_options'] = {'fault': fault}
    runtime = IsolatedServiceRuntime(journal, root,
        ffmpeg=Path(shutil.which('ffmpeg')).resolve(), ffprobe=Path(shutil.which('ffprobe')).resolve(),
        **options).start_runtime()
    if not mode.startswith('recovery:'):
        for name, room in (('old', '123'), ('next', '456')):
            runtime.start('https://www.tiktok.com/@example.creator/live', str(root / (name + '.mp4')),
                          expected_room_id=room, raw_copy=True)
            # Different rooms of one page can be accepted only after the old H.
            if name == 'old':
                deadline = time.monotonic() + 15
                while journal.session(runtime.latest[1])['phase'] not in {'queued', 'running', 'completed'}:
                    assert time.monotonic() < deadline
                    time.sleep(0.01)
    runtime.worker.join()


if __name__ == '__main__':
    main()
