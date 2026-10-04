"""Frozen schema 2 from accepted a96bd6e9; no migration."""

SCHEMA_V2 = r"""
CREATE TABLE catalog(id TEXT PRIMARY KEY, version INTEGER NOT NULL CHECK(version=2)) STRICT;
CREATE TABLE sessions(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
 intent TEXT NOT NULL, creator TEXT NOT NULL, expected_room TEXT, room TEXT,
 automatic_claim TEXT UNIQUE,
 origin_slot INTEGER NOT NULL CHECK(origin_slot IN (1,2)),
 generation INTEGER NOT NULL CHECK(generation>0),
 phase TEXT NOT NULL CHECK(phase IN ('reserved','capturing','closing','queued','running',
 'failed','blocked','completed','no_assembly')),
 revision INTEGER NOT NULL CHECK(revision>0),
 stop INTEGER NOT NULL DEFAULT 0 CHECK(stop IN (0,1)), recovery TEXT,
 seal TEXT, seal_hash TEXT,
 CHECK((seal IS NULL)=(seal_hash IS NULL))) STRICT;
CREATE TABLE bindings(slot INTEGER PRIMARY KEY CHECK(slot IN (1,2)),
 generation INTEGER NOT NULL CHECK(generation>=0),
 session TEXT UNIQUE REFERENCES sessions(id)) STRICT;
CREATE TABLE units(session TEXT PRIMARY KEY REFERENCES sessions(id),
 kind TEXT NOT NULL CHECK(kind IN ('capture','task'))) STRICT;
CREATE TABLE artifacts(session TEXT NOT NULL REFERENCES sessions(id),
 kind TEXT NOT NULL CHECK(kind IN ('output','parts')), identity TEXT NOT NULL,
 PRIMARY KEY(session,kind), UNIQUE(identity)) STRICT;
CREATE TABLE rooms(room TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES sessions(id)) STRICT;
CREATE TABLE attempts(token TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES sessions(id),
 number INTEGER NOT NULL CHECK(number>0),
 state TEXT NOT NULL CHECK(state IN ('running','failed','completed')), proof TEXT,
 UNIQUE(session,number)) STRICT;
CREATE TABLE queue_entries(position INTEGER PRIMARY KEY AUTOINCREMENT,
 session TEXT NOT NULL REFERENCES sessions(id), operation TEXT NOT NULL UNIQUE
 REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED) STRICT;
CREATE TABLE tasks(session TEXT PRIMARY KEY REFERENCES sessions(id),
 state TEXT NOT NULL CHECK(state IN ('queued','running','failed','blocked','completed')),
 revision INTEGER NOT NULL CHECK(revision>0), attempt INTEGER NOT NULL DEFAULT 0,
 token TEXT UNIQUE REFERENCES attempts(token), error TEXT, proof TEXT,
 queue_order INTEGER NOT NULL UNIQUE REFERENCES queue_entries(position) CHECK(queue_order>0),
 CHECK(attempt>=0), CHECK(state!='running' OR (token IS NOT NULL AND attempt>0))) STRICT;
CREATE UNIQUE INDEX one_finalizer ON tasks((1)) WHERE state='running';
CREATE INDEX task_phase ON tasks(state,queue_order);
CREATE INDEX session_queue_entries ON queue_entries(session,position DESC);
CREATE INDEX outstanding_sessions ON sessions(id) WHERE phase NOT IN ('completed','no_assembly');
CREATE INDEX running_attempts ON attempts(token) WHERE state='running';
CREATE INDEX room_session ON rooms(session);
CREATE TABLE automatic_receipts(claim TEXT PRIMARY KEY,
 session TEXT NOT NULL UNIQUE REFERENCES sessions(id), intent_hash TEXT NOT NULL) STRICT;
CREATE TABLE operations(id TEXT PRIMARY KEY, kind TEXT NOT NULL,
 arguments_hash TEXT NOT NULL, result TEXT NOT NULL) STRICT;
CREATE TRIGGER limit_work BEFORE INSERT ON units WHEN (SELECT count(*) FROM units)>=8
 BEGIN SELECT RAISE(ABORT,'outstanding work limit'); END;
CREATE TRIGGER immutable_session BEFORE UPDATE OF id,intent,creator,expected_room,
 origin_slot,generation,automatic_claim ON sessions BEGIN SELECT RAISE(ABORT,'immutable session'); END;
CREATE TRIGGER immutable_room BEFORE UPDATE OF room ON sessions
 WHEN OLD.room IS NOT NULL AND NEW.room IS NOT OLD.room
 BEGIN SELECT RAISE(ABORT,'immutable room'); END;
CREATE TRIGGER immutable_seal BEFORE UPDATE OF seal,seal_hash ON sessions
 WHEN OLD.seal IS NOT NULL AND (NEW.seal IS NOT OLD.seal OR NEW.seal_hash IS NOT OLD.seal_hash)
 BEGIN SELECT RAISE(ABORT,'immutable seal'); END;
CREATE TRIGGER keep_history BEFORE DELETE ON sessions
 BEGIN SELECT RAISE(ABORT,'keep session history'); END;
CREATE TRIGGER keep_operations BEFORE DELETE ON operations
 BEGIN SELECT RAISE(ABORT,'keep operation receipts'); END;
CREATE TRIGGER immutable_operations BEFORE UPDATE ON operations
 BEGIN SELECT RAISE(ABORT,'immutable operation receipts'); END;
CREATE TRIGGER keep_receipts BEFORE DELETE ON automatic_receipts
 BEGIN SELECT RAISE(ABORT,'keep acceptance receipts'); END;
CREATE TRIGGER immutable_receipts BEFORE UPDATE ON automatic_receipts
 BEGIN SELECT RAISE(ABORT,'immutable acceptance receipts'); END;
CREATE TRIGGER immutable_attempt BEFORE UPDATE OF token,session,number ON attempts
 BEGIN SELECT RAISE(ABORT,'immutable attempt identity'); END;
CREATE TRIGGER keep_attempt BEFORE DELETE ON attempts
 BEGIN SELECT RAISE(ABORT,'keep attempt history'); END;
CREATE TRIGGER immutable_queue_entry BEFORE UPDATE ON queue_entries
 BEGIN SELECT RAISE(ABORT,'immutable queue entry'); END;
CREATE TRIGGER keep_queue_entry BEFORE DELETE ON queue_entries
 BEGIN SELECT RAISE(ABORT,'keep queue history'); END;
"""
