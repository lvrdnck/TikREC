"""Versioned isolated SQLite authority; no production path or import side effects."""

import hashlib
import sqlite3


APPLICATION_ID = 0x544B524A
SCHEMA_VERSION = 1

# STRICT tables and CHECKs reject malformed rows even outside the public operations.
SCHEMA = """
CREATE TABLE catalog(id TEXT PRIMARY KEY, version INTEGER NOT NULL CHECK(version=1)) STRICT;
CREATE TABLE sessions(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
 intent TEXT NOT NULL, creator TEXT NOT NULL, expected_room TEXT, room TEXT,
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
CREATE TABLE tasks(session TEXT PRIMARY KEY REFERENCES sessions(id),
 state TEXT NOT NULL CHECK(state IN ('queued','running','failed','blocked','completed')),
 revision INTEGER NOT NULL CHECK(revision>0), attempt INTEGER NOT NULL DEFAULT 0,
 token TEXT UNIQUE REFERENCES attempts(token), error TEXT, proof TEXT,
 CHECK(attempt>=0), CHECK(state!='running' OR (token IS NOT NULL AND attempt>0))) STRICT;
CREATE UNIQUE INDEX one_finalizer ON tasks((1)) WHERE state='running';
CREATE INDEX task_phase ON tasks(state,session);
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
 origin_slot,generation ON sessions BEGIN SELECT RAISE(ABORT,'immutable session'); END;
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
"""


def schema_fingerprint(connection: sqlite3.Connection) -> str:
    """Bind every declared table/index/trigger, excluding SQLite's private metadata."""
    rows = connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master "
                              "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
    return hashlib.sha256(repr([tuple(row) for row in rows]).encode()).hexdigest()


def expected_fingerprint() -> str:
    """Calculate the versioned schema signature without touching any filesystem."""
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(SCHEMA)
        return schema_fingerprint(connection)
