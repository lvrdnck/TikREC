"""Fresh pilot initialization and known-state reopening; no discovery or migration."""
import json
from pathlib import Path

from .automation_state import AutomationState, AutomationStateStore
from .capture_handoff_native import NativeHandle
from .pilot_identity import local
from .release_recovery_handles import NativeCloseGuard
from .session_journal import SessionJournal
from .session_journal_types import identifier, require


class PilotState:
    """Retain exact directory pins and failed native closes for explicit retries."""

    def __init__(self, home):
        self.home, self.pins = Path(home), []
        self.journal = None
        self.native_close_guards = []

    def _pin(self, path):
        held = NativeHandle(path, directory=True,
            cleanup_guard_factory=lambda h: NativeCloseGuard(self, h, resource_key='pilot_directory'))
        self.pins.append(held)
        return held

    def _create(self, parent, name):
        try:
            held = NativeHandle.create_directory(parent, name)
        except BaseException as error:
            held = getattr(error, 'scratch_native_owner', None)
            if held is not None:
                self.pins.append(held)
                held.cleanup_guard = NativeCloseGuard(self, held.handle, resource_key='pilot_directory')
            raise
        self.pins.append(held)
        held.cleanup_guard = NativeCloseGuard(self, held.handle, resource_key='pilot_directory')
        return held

    def open(self, mode, catalog_id, source):
        """Exclusively create a dedicated home or reopen its verified known catalog."""
        identifier(catalog_id)
        home = local(self.home, exists=mode == 'reopen')
        require(not (home == Path(source['checkout']) or Path(source['checkout']) in home.parents
                    or home in Path(source['checkout']).parents), 'pilot home overlaps source')
        if mode == 'init':
            require(not home.exists(), 'fresh pilot home already exists; never reset it')
            parent = self._pin(home.parent)
            self._create(parent, home.name)
            for name in ('state', 'media', 'automation'):
                self._create(self.pins[1], name)
            # Exclusive creation preserves even partial initialization failures.
            self.journal = SessionJournal.initialize(home / 'state' / 'sessions.sqlite3', catalog_id)
            self.automation = AutomationStateStore(home / 'automation' / 'automation.json')
            empty = {'schema_version': 1, 'consumed_rooms': {}, 'pending_claim': None}
            with self.automation.path.open('x', encoding='utf-8') as stream:
                json.dump(empty, stream)
            document = {'version': 1, 'catalog_id': catalog_id,
                        'source_sha256': source['source_sha256'], 'identities': self.identities()}
            with (home / 'pilot.json').open('x', encoding='utf-8') as stream:
                json.dump(document, stream, sort_keys=True)
        else:
            for path in (home, home / 'state', home / 'media', home / 'automation'):
                self._pin(local(path))
            require({p.name for p in home.iterdir()} <=
                    {'state', 'media', 'automation', 'pilot.json', 'control.json'}, 'unknown pilot home contents')
            document_path = local(home / 'pilot.json')
            require(document_path.stat().st_size <= 8192, 'pilot identity exceeds bound')
            document = json.loads(document_path.read_text(encoding='utf-8'))
            require(set(document) == {'version', 'catalog_id', 'source_sha256', 'identities'}
                    and document['version'] == 1 and document['catalog_id'] == catalog_id
                    and document['source_sha256'] == source['source_sha256']
                    and document['identities'] == self.identities(), 'pilot state/source identity conflicts')
            self.journal = SessionJournal(local(home / 'state' / 'sessions.sqlite3'), catalog_id)
            self.automation = AutomationStateStore(local(home / 'automation' / 'automation.json'))
        require(self.automation.load() == AutomationState(), 'pilot automation must be empty')
        require(len(self.journal.history(limit=9)) <= 8, 'pilot catalog lifetime limit exceeded')
        return self

    def identities(self):
        """Bind known state to exact local objects, rather than same-looking filenames."""
        paths = [self.home, *(self.home / n for n in ('state', 'media', 'automation')),
                 self.home / 'state' / 'sessions.sqlite3', self.home / 'automation' / 'automation.json']
        result = {}
        for path in paths:
            info = local(path).stat()
            result[str(path)] = [info.st_dev, info.st_ino]
        return result

    def close(self):
        """Retry only exact retained native owners; leave every artifact on disk."""
        errors = []
        for pin in reversed(self.pins):
            try:
                pin.close()
            except BaseException as error:
                errors.append(error)
        for guard in self.native_close_guards:
            try:
                # A failed duplicate close can outlive an already closed original pin.
                guard.close_retired_reference()
            except BaseException as error:
                errors.append(error)
        self.pins[:] = [p for p in self.pins if p.handle is not None or p.fd is not None]
        return not self.pins and not errors and not any(g.retained for g in self.native_close_guards)
