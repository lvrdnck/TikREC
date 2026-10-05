"""Versioned isolated SQLite authority; no production path or import side effects."""

import hashlib
import sqlite3


APPLICATION_ID = 0x544B524A
SCHEMA_VERSION = 5

# STRICT tables and CHECKs reject malformed rows even outside the public operations.
SCHEMA = """
CREATE TABLE catalog(id TEXT PRIMARY KEY, version INTEGER NOT NULL CHECK(version=5)) STRICT;
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
 kind TEXT NOT NULL CHECK(kind IN ('capture','task','evidence'))) STRICT;
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
CREATE INDEX sealed_empty_sessions ON sessions(id) WHERE phase='no_assembly' AND seal IS NOT NULL;
CREATE INDEX running_attempts ON attempts(token) WHERE state='running';
CREATE INDEX room_session ON rooms(session);
CREATE TABLE automatic_receipts(claim TEXT PRIMARY KEY,
 session TEXT NOT NULL UNIQUE REFERENCES sessions(id), intent_hash TEXT NOT NULL) STRICT;
CREATE TABLE operations(id TEXT PRIMARY KEY, kind TEXT NOT NULL,
 arguments_hash TEXT NOT NULL, result TEXT NOT NULL) STRICT;
CREATE TABLE attempt_owners(token TEXT PRIMARY KEY REFERENCES attempts(token),
 owner TEXT NOT NULL UNIQUE, revision INTEGER NOT NULL CHECK(revision>0),
 state TEXT NOT NULL CHECK(state IN ('held','revoked')),
 claim_operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 h_operation TEXT NOT NULL REFERENCES operations(id), h_revision INTEGER NOT NULL,
 seal_hash TEXT NOT NULL, marker_hash TEXT,
 sequence INTEGER NOT NULL DEFAULT 0 CHECK(sequence>=0),
 last_operation TEXT NOT NULL REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED) STRICT;
CREATE TABLE child_launches(id TEXT PRIMARY KEY, token TEXT NOT NULL REFERENCES attempt_owners(token),
 sequence INTEGER NOT NULL CHECK(sequence>0), intent TEXT NOT NULL,
 identity TEXT, exit TEXT, diagnostics TEXT, cleanup INTEGER NOT NULL DEFAULT 0 CHECK(cleanup IN (0,1)),
 intent_operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 identity_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 exit_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 diagnostics_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 cleanup_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(token,sequence), CHECK((identity IS NULL)=(identity_operation IS NULL)),
 CHECK((exit IS NULL)=(exit_operation IS NULL)),
 CHECK((diagnostics IS NULL)=(diagnostics_operation IS NULL)),
 CHECK((cleanup=0)=(cleanup_operation IS NULL)), CHECK(cleanup=0 OR exit IS NOT NULL)) STRICT;
CREATE TABLE scratch_owners(token TEXT PRIMARY KEY REFERENCES attempt_owners(token),
 owner TEXT NOT NULL, session TEXT NOT NULL REFERENCES sessions(id), intent TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('reserved','bound','candidate_ready','held')),
 workspace_identity TEXT, workspace_stamp TEXT,
 hold_reason TEXT, hold_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 intent_operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 bind_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 writer_launch TEXT UNIQUE REFERENCES child_launches(id), writer_sequence INTEGER,
 latest_operation TEXT NOT NULL REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 CHECK((workspace_identity IS NULL AND bind_operation IS NULL AND state IN ('reserved','held'))
    OR (workspace_identity IS NOT NULL AND bind_operation IS NOT NULL
        AND state IN ('bound','candidate_ready','held'))),
 CHECK((state='held')=(hold_operation IS NOT NULL)),
 CHECK((hold_operation IS NULL)=(hold_reason IS NULL)),
 CHECK((writer_launch IS NULL)=(writer_sequence IS NULL))) STRICT;
CREATE TABLE scratch_artifacts(token TEXT NOT NULL REFERENCES scratch_owners(token),
 name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('candidate','helper')),
 required INTEGER NOT NULL CHECK(required IN (0,1)), identity TEXT, size INTEGER, stamp TEXT,
 bind_operation TEXT REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 PRIMARY KEY(token,name), CHECK((identity IS NULL)=(bind_operation IS NULL)),
 CHECK((identity IS NULL)=(size IS NULL)), CHECK((identity IS NULL)=(stamp IS NULL))) STRICT;
CREATE TABLE scratch_candidates(token TEXT PRIMARY KEY REFERENCES scratch_owners(token),
 name TEXT NOT NULL, launch TEXT NOT NULL REFERENCES child_launches(id), sequence INTEGER NOT NULL,
 identity TEXT NOT NULL, size INTEGER NOT NULL CHECK(size>0), stamp TEXT NOT NULL,
 sha256 TEXT NOT NULL, seal_hash TEXT NOT NULL, marker_hash TEXT NOT NULL,
 execution TEXT NOT NULL, validation TEXT NOT NULL CHECK(validation='not_checked'),
 publication TEXT NOT NULL CHECK(publication='unpublished'),
 operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED) STRICT;
CREATE TRIGGER immutable_owner BEFORE UPDATE OF token,owner,claim_operation,h_operation,h_revision,seal_hash
 ON attempt_owners BEGIN SELECT RAISE(ABORT,'immutable owned attempt'); END;
CREATE TRIGGER keep_owner BEFORE DELETE ON attempt_owners
 BEGIN SELECT RAISE(ABORT,'keep owned attempt'); END;
CREATE TRIGGER irreversible_owner BEFORE UPDATE OF state ON attempt_owners
 WHEN OLD.state='revoked' AND NEW.state!='revoked'
 BEGIN SELECT RAISE(ABORT,'revocation is irreversible'); END;
CREATE TRIGGER immutable_marker_observation BEFORE UPDATE OF marker_hash ON attempt_owners
 WHEN OLD.marker_hash IS NOT NULL
 BEGIN SELECT RAISE(ABORT,'immutable attempt marker observation'); END;
CREATE TRIGGER immutable_launch BEFORE UPDATE OF id,token,sequence,intent,intent_operation ON child_launches
 BEGIN SELECT RAISE(ABORT,'immutable child intent'); END;
CREATE TRIGGER immutable_child_identity BEFORE UPDATE OF identity,identity_operation ON child_launches
 WHEN OLD.identity IS NOT NULL BEGIN SELECT RAISE(ABORT,'immutable child identity'); END;
CREATE TRIGGER immutable_child_exit BEFORE UPDATE OF exit,exit_operation ON child_launches
 WHEN OLD.exit IS NOT NULL BEGIN SELECT RAISE(ABORT,'immutable child exit'); END;
CREATE TRIGGER immutable_child_diagnostics BEFORE UPDATE OF diagnostics,diagnostics_operation ON child_launches
 WHEN OLD.diagnostics IS NOT NULL BEGIN SELECT RAISE(ABORT,'immutable child diagnostics'); END;
CREATE TRIGGER immutable_child_cleanup BEFORE UPDATE OF cleanup,cleanup_operation ON child_launches
 WHEN OLD.cleanup=1 BEGIN SELECT RAISE(ABORT,'immutable child cleanup'); END;
CREATE TRIGGER immutable_scratch_intent BEFORE UPDATE OF token,owner,session,intent,intent_operation
 ON scratch_owners BEGIN SELECT RAISE(ABORT,'immutable scratch intent'); END;
CREATE TRIGGER keep_scratch BEFORE DELETE ON scratch_owners
 BEGIN SELECT RAISE(ABORT,'keep scratch ownership'); END;
CREATE TRIGGER immutable_scratch_bind BEFORE UPDATE OF workspace_identity,workspace_stamp,bind_operation
 ON scratch_owners WHEN OLD.workspace_identity IS NOT NULL
 BEGIN SELECT RAISE(ABORT,'immutable scratch binding'); END;
CREATE TRIGGER immutable_scratch_writer BEFORE UPDATE OF writer_launch,writer_sequence ON scratch_owners
 WHEN OLD.writer_launch IS NOT NULL BEGIN SELECT RAISE(ABORT,'immutable scratch writer authority'); END;
CREATE TRIGGER immutable_scratch_artifact BEFORE UPDATE ON scratch_artifacts
 WHEN OLD.identity IS NOT NULL BEGIN SELECT RAISE(ABORT,'immutable scratch artifact binding'); END;
CREATE TRIGGER keep_scratch_artifact BEFORE DELETE ON scratch_artifacts
 BEGIN SELECT RAISE(ABORT,'keep scratch artifact history'); END;
CREATE TRIGGER keep_candidate BEFORE DELETE ON scratch_candidates
 BEGIN SELECT RAISE(ABORT,'keep unpublished candidate evidence'); END;
CREATE TRIGGER immutable_candidate BEFORE UPDATE ON scratch_candidates
 BEGIN SELECT RAISE(ABORT,'immutable unpublished candidate evidence'); END;
CREATE TRIGGER keep_launch BEFORE DELETE ON child_launches
 BEGIN SELECT RAISE(ABORT,'keep child launch'); END;
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
