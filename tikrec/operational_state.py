"""Explicit fresh operational home, with no pilot or legacy-state adoption."""
import json
import os

from .automation_state import AutomationState, AutomationStateStore, AutomationStateError, _claim_document
from .pilot_identity import local
from .pilot_state import PilotState
from .session_journal import SessionJournal
from .session_journal_types import identifier, require
from .configuration_json import unique_fields


class KnownAutomationStore(AutomationStateStore):
    """Refuse missing/oversized committed state instead of recreating empty history."""

    def load(self):
        """Bound the persistent creator map before the existing strict JSON loader."""
        require(local(self.path).stat().st_size <= 1024**2, 'automation state exceeds bound')
        return super().load()

    def initialize(self):
        """Create empty automation only during explicit fresh-home initialization."""
        super().save(AutomationState())

    def save(self, state):
        """Bound creator history before persistence; never recreate a lost known file."""
        try:
            local(self.path)
            state.validate()
            document = {'schema_version': state.schema_version, 'consumed_rooms': state.consumed(),
                        'pending_claim': _claim_document(state.pending_claim)}
            require(len((json.dumps(document, indent=2, sort_keys=True) + '\n').encode()) <= 1024**2,
                    'operational automation history exceeds bound')
        except (OSError, ValueError):
            # Existing coordinator halts acknowledgement safely on its typed store error.
            raise AutomationStateError('operational automation state unavailable') from None
        super().save(state)


class ServiceState(PilotState):
    """Reuse exact native pin cleanup, with a distinct operational profile contract."""

    def identities(self):
        """Bind stable directories/catalog; automation replacement is intentionally atomic."""
        paths = [self.home, *(self.home / n for n in ('state', 'media', 'automation', 'logs')),
                 self.home / 'state' / 'sessions.sqlite3']
        result = {}
        for path in paths:
            info = local(path).stat()
            result[str(path)] = [info.st_dev, info.st_ino]
        return result

    def open(self, mode, catalog_id, source):
        """Initialize only an absent home; known reopen requires original profile/objects."""
        identifier(catalog_id)
        home = local(self.home, exists=mode == 'reopen')
        from pathlib import Path
        checkout = Path(source['checkout'])
        require(home != checkout and home not in checkout.parents and checkout not in home.parents,
                'service home overlaps source')
        if mode == 'init':
            require(not home.exists(), 'fresh service home already exists')
            parent = self._pin(home.parent)
            self._create(parent, home.name)
            for name in ('state', 'media', 'automation', 'logs'):
                self._create(self.pins[1], name)
            self.journal = SessionJournal.initialize(home / 'state' / 'sessions.sqlite3', catalog_id)
            self.automation = KnownAutomationStore(home / 'automation' / 'automation.json')
            self.automation.initialize()
            document = {'version': 1, 'profile': 'operational_schema10', 'catalog_id': catalog_id,
                        'source_sha256': source['source_sha256'], 'identities': self.identities()}
            with (home / 'service.json').open('x', encoding='utf-8') as stream:
                json.dump(document, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            for path in (home, *(home / n for n in ('state', 'media', 'automation', 'logs'))):
                self._pin(local(path))
            names = set()
            for path in home.iterdir():
                names.add(path.name)
                require(len(names) <= 7, 'unknown operational home contents')
            require(names <=
                    {'state', 'media', 'automation', 'logs', 'service.json', 'control.json'},
                    'unknown operational home contents')
            marker = local(home / 'service.json')
            require(marker.stat().st_size <= 8192, 'service identity exceeds bound')
            document = json.loads(marker.read_text(encoding='utf-8'), object_pairs_hook=unique_fields)
            require(type(document) is dict and type(document.get('version')) is int,
                    'service marker version is invalid')
            require(document == {'version': 1, 'profile': 'operational_schema10',
                    'catalog_id': catalog_id, 'source_sha256': source['source_sha256'],
                    'identities': self.identities()}, 'known service identity conflicts')
            self.journal = SessionJournal(local(home / 'state' / 'sessions.sqlite3'), catalog_id)
            self.automation = KnownAutomationStore(local(home / 'automation' / 'automation.json'))
        require(len({path.stat().st_dev for path in (home / 'state', home / 'media')}) == 1,
                'operational home must use one native volume')
        self.automation.load()
        return self
