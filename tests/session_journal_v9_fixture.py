"""Frozen schema-9 layout used to prove refusal without migration or writes."""

from tests.session_journal_v8_fixture import SCHEMA as SCHEMA_V8


_SETTLEMENT_SCHEMA_V9 = """
CREATE TABLE release_preparations(token TEXT PRIMARY KEY REFERENCES attempt_owners(token),
 binding TEXT NOT NULL, operation TEXT NOT NULL UNIQUE REFERENCES operations(id)
 DEFERRABLE INITIALLY DEFERRED) STRICT;
CREATE TABLE release_cleanups(token TEXT PRIMARY KEY REFERENCES release_preparations(token),
 evidence TEXT NOT NULL, operation TEXT NOT NULL UNIQUE REFERENCES operations(id)
 DEFERRABLE INITIALLY DEFERRED) STRICT;
CREATE TABLE release_results(token TEXT PRIMARY KEY REFERENCES release_cleanups(token),
 evidence TEXT NOT NULL, operation TEXT NOT NULL UNIQUE REFERENCES operations(id)
 DEFERRABLE INITIALLY DEFERRED) STRICT;
CREATE INDEX active_task_units ON units(kind,session);
CREATE INDEX active_task_states ON tasks(state,session) WHERE state!='completed';
CREATE TRIGGER immutable_release_preparation BEFORE UPDATE ON release_preparations
 BEGIN SELECT RAISE(ABORT,'immutable release preparation'); END;
CREATE TRIGGER keep_release_preparation BEFORE DELETE ON release_preparations
 BEGIN SELECT RAISE(ABORT,'keep release preparation'); END;
CREATE TRIGGER immutable_release_cleanup BEFORE UPDATE ON release_cleanups
 BEGIN SELECT RAISE(ABORT,'immutable release cleanup'); END;
CREATE TRIGGER keep_release_cleanup BEFORE DELETE ON release_cleanups
 BEGIN SELECT RAISE(ABORT,'keep release cleanup'); END;
CREATE TRIGGER immutable_release_result BEFORE UPDATE ON release_results
 BEGIN SELECT RAISE(ABORT,'immutable release result'); END;
CREATE TRIGGER keep_release_result BEFORE DELETE ON release_results
 BEGIN SELECT RAISE(ABORT,'keep release result'); END;
CREATE TRIGGER keep_owned_terminal_task BEFORE UPDATE ON tasks
 WHEN OLD.state='completed' AND EXISTS(SELECT 1 FROM release_results WHERE token=OLD.token)
 BEGIN SELECT RAISE(ABORT,'irreversible owned settlement'); END;
CREATE TRIGGER keep_owned_terminal_attempt BEFORE UPDATE ON attempts
 WHEN OLD.state='completed' AND EXISTS(SELECT 1 FROM release_results WHERE token=OLD.token)
 BEGIN SELECT RAISE(ABORT,'irreversible owned settlement'); END;
CREATE TRIGGER keep_owned_terminal_session BEFORE UPDATE ON sessions
 WHEN OLD.phase='completed' AND EXISTS(SELECT 1 FROM tasks t JOIN release_results r ON r.token=t.token WHERE t.session=OLD.id)
 BEGIN SELECT RAISE(ABORT,'immutable completed owned session'); END;
"""

SCHEMA = SCHEMA_V8.replace('CHECK(version=8)', 'CHECK(version=9)') + _SETTLEMENT_SCHEMA_V9
