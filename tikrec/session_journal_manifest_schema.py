"""Schema 8 adds only immutable control preparation and observed transition facts."""

MANIFEST_SCHEMA = """
CREATE TABLE manifest_preparations(token TEXT PRIMARY KEY REFERENCES publication_results(token),
 binding TEXT NOT NULL, operation TEXT NOT NULL UNIQUE REFERENCES operations(id)
 DEFERRABLE INITIALLY DEFERRED) STRICT;
CREATE TABLE manifest_steps(token TEXT NOT NULL REFERENCES manifest_preparations(token),
 phase TEXT NOT NULL CHECK(phase IN ('staged','preserved','installed')), evidence TEXT NOT NULL,
 operation TEXT NOT NULL UNIQUE REFERENCES operations(id) DEFERRABLE INITIALLY DEFERRED,
 PRIMARY KEY(token,phase)) STRICT;
CREATE TRIGGER immutable_manifest_preparation BEFORE UPDATE ON manifest_preparations
 BEGIN SELECT RAISE(ABORT,'immutable manifest preparation'); END;
CREATE TRIGGER keep_manifest_preparation BEFORE DELETE ON manifest_preparations
 BEGIN SELECT RAISE(ABORT,'keep manifest predecessor and successor'); END;
CREATE TRIGGER immutable_manifest_step BEFORE UPDATE ON manifest_steps
 BEGIN SELECT RAISE(ABORT,'immutable manifest result'); END;
CREATE TRIGGER keep_manifest_step BEFORE DELETE ON manifest_steps
 BEGIN SELECT RAISE(ABORT,'keep manifest intermediate evidence'); END;
"""
