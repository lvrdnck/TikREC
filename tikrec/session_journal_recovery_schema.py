"""Schema-10 append-only authority for prepared-success restart recovery."""

RECOVERY_SCHEMA = """
CREATE TABLE release_recovery_heads(
 token TEXT PRIMARY KEY REFERENCES release_preparations(token),
 generation INTEGER NOT NULL CHECK(generation BETWEEN 1 AND 32),
 state TEXT NOT NULL CHECK(state IN ('authorized','proved','cleaned','uncertain','released')),
 authority_operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 proof_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 cleanup_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 result_operation TEXT UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED) STRICT;
CREATE TABLE release_recovery_authorities(
 token TEXT NOT NULL REFERENCES release_preparations(token), generation INTEGER NOT NULL CHECK(generation BETWEEN 1 AND 32),
 authority TEXT NOT NULL, evidence TEXT NOT NULL,
 operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 PRIMARY KEY(token,generation), UNIQUE(token,authority)) STRICT;
CREATE TABLE release_recovery_proofs(
 token TEXT NOT NULL, generation INTEGER NOT NULL CHECK(generation BETWEEN 1 AND 32), evidence TEXT NOT NULL,
 operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 PRIMARY KEY(token,generation),
 FOREIGN KEY(token,generation) REFERENCES release_recovery_authorities(token,generation)) STRICT;
CREATE TABLE release_recovery_cleanups(
 token TEXT NOT NULL, generation INTEGER NOT NULL CHECK(generation BETWEEN 1 AND 32), evidence TEXT NOT NULL,
 operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 PRIMARY KEY(token,generation),
 FOREIGN KEY(token,generation) REFERENCES release_recovery_authorities(token,generation)) STRICT;
CREATE TABLE release_recovery_results(
 token TEXT PRIMARY KEY REFERENCES release_preparations(token), generation INTEGER NOT NULL CHECK(generation BETWEEN 1 AND 32),
 evidence TEXT NOT NULL,
 operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(token,generation) REFERENCES release_recovery_authorities(token,generation),
 FOREIGN KEY(token,generation) REFERENCES release_recovery_proofs(token,generation),
 FOREIGN KEY(token,generation) REFERENCES release_recovery_cleanups(token,generation)) STRICT;
CREATE TRIGGER immutable_recovery_authority BEFORE UPDATE ON release_recovery_authorities
 BEGIN SELECT RAISE(ABORT,'immutable recovery authority'); END;
CREATE TRIGGER keep_recovery_authority BEFORE DELETE ON release_recovery_authorities
 BEGIN SELECT RAISE(ABORT,'keep recovery authority history'); END;
CREATE TRIGGER immutable_recovery_proof BEFORE UPDATE ON release_recovery_proofs
 BEGIN SELECT RAISE(ABORT,'immutable recovery proof'); END;
CREATE TRIGGER keep_recovery_proof BEFORE DELETE ON release_recovery_proofs
 BEGIN SELECT RAISE(ABORT,'keep recovery proof history'); END;
CREATE TRIGGER immutable_recovery_cleanup BEFORE UPDATE ON release_recovery_cleanups
 BEGIN SELECT RAISE(ABORT,'immutable recovery cleanup'); END;
CREATE TRIGGER keep_recovery_cleanup BEFORE DELETE ON release_recovery_cleanups
 BEGIN SELECT RAISE(ABORT,'keep recovery cleanup history'); END;
CREATE TRIGGER immutable_recovery_result BEFORE UPDATE ON release_recovery_results
 BEGIN SELECT RAISE(ABORT,'immutable recovery result'); END;
CREATE TRIGGER keep_recovery_result BEFORE DELETE ON release_recovery_results
 BEGIN SELECT RAISE(ABORT,'keep recovery result history'); END;
CREATE TRIGGER monotone_recovery_head BEFORE UPDATE ON release_recovery_heads
 WHEN NEW.token!=OLD.token OR OLD.state='released' OR NEW.generation<OLD.generation
 OR NEW.generation>OLD.generation+1
 BEGIN SELECT RAISE(ABORT,'recovery fencing head is monotone'); END;
CREATE TRIGGER keep_recovery_head BEFORE DELETE ON release_recovery_heads
 BEGIN SELECT RAISE(ABORT,'keep recovery fencing head'); END;
CREATE TRIGGER keep_recovered_terminal_task BEFORE UPDATE ON tasks
 WHEN OLD.state='completed' AND EXISTS(SELECT 1 FROM release_recovery_results WHERE token=OLD.token)
 BEGIN SELECT RAISE(ABORT,'irreversible recovered settlement'); END;
CREATE TRIGGER keep_recovered_terminal_attempt BEFORE UPDATE ON attempts
 WHEN OLD.state='completed' AND EXISTS(SELECT 1 FROM release_recovery_results WHERE token=OLD.token)
 BEGIN SELECT RAISE(ABORT,'irreversible recovered settlement'); END;
CREATE TRIGGER keep_recovered_terminal_session BEFORE UPDATE ON sessions
 WHEN OLD.phase='completed' AND EXISTS(SELECT 1 FROM tasks t JOIN release_recovery_results r
 ON r.token=t.token WHERE t.session=OLD.id)
 BEGIN SELECT RAISE(ABORT,'immutable recovered session'); END;
"""
