"""Explicit journal initialization/reopen and receipt-backed short transactions."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
from pathlib import Path

from .session_journal_schema import (APPLICATION_ID, SCHEMA, SCHEMA_VERSION,
                                   expected_fingerprint, schema_fingerprint)
from .session_journal_receipts import validate_operation_receipt
from .session_journal_types import (JournalBusy, JournalConflict, JournalError,
                                  JournalUncertain, digest, encode, identifier, require)


def _file_identity(path: Path) -> tuple[int, int]:
    # Reject redirected parents as well as the database; never invent a new authority.
    for candidate in (path, *path.parents):
        attributes = getattr(candidate.lstat(), "st_file_attributes", 0)
        require(not candidate.is_symlink() and not attributes & 0x400,
                "redirected journal state")
    require(not str(path).startswith("\\\\"), "journal must use native local storage")
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "invalid journal file")
    return info.st_dev, info.st_ino


def _translate(error: sqlite3.Error) -> JournalError:
    code = getattr(error, "sqlite_errorcode", 0) & 255
    if code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
        return JournalBusy("journal lock timeout; retry only by operation identity")
    if isinstance(error, sqlite3.IntegrityError):
        return JournalConflict("journal constraint refused operation")
    return JournalError("invalid or unavailable journal; preserve state")


class JournalStore:
    """No default path: every instance reopens one explicitly identified catalog."""

    @classmethod
    def initialize(cls, path: Path, catalog_id: str):
        """Exclusively create fresh state; a failed initialization is never erased."""
        identifier(catalog_id)
        path = Path(path).absolute()
        # The caller must create a deliberate state directory; opening cannot mkdir it.
        require(path.parent.is_dir(), "missing journal parent")
        for parent in (path.parent, *path.parent.parents):
            attributes = getattr(parent.lstat(), "st_file_attributes", 0)
            require(not parent.is_symlink() and not attributes & 0x400, "redirected journal parent")
        require(not str(path).startswith("\\\\"), "journal must use native local storage")
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        connection = None
        try:
            connection = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True,
                                         isolation_level=None, timeout=1)
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=EXTRA")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=1000")
            require(connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
                    and connection.execute("PRAGMA synchronous").fetchone()[0] == 3
                    and connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
                    and connection.execute("PRAGMA busy_timeout").fetchone()[0] == 1000,
                    "initial journal settings unavailable")
            connection.executescript("BEGIN EXCLUSIVE;\n" + SCHEMA)
            connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.execute("INSERT INTO catalog VALUES (?,?)", (catalog_id, SCHEMA_VERSION))
            connection.executemany("INSERT INTO bindings VALUES (?,0,NULL)", [(1,), (2,)])
            try:
                connection.commit()
            except BaseException as error:
                raise JournalUncertain("initialization outcome unknown; reopen same catalog") from error
        finally:
            if connection is not None:
                connection.close()
        return cls(path, catalog_id)

    def __init__(self, path: Path, catalog_id: str, *, fault=None):
        """Reopen existing known state, verifying identity/schema/integrity/settings."""
        identifier(catalog_id)
        self.path, self.catalog_id, self._fault = Path(path).absolute(), catalog_id, fault
        try:
            self._identity = _file_identity(self.path)
            self._schema = expected_fingerprint()
            connection = self._connect()
            try:
                connection.execute("BEGIN")
                require(connection.execute("PRAGMA quick_check").fetchone()[0] == "ok",
                        "journal integrity failure")
                require(connection.execute("PRAGMA foreign_key_check").fetchone() is None,
                        "journal foreign key failure")
                self._audit(connection)
            finally:
                connection.close()
        except sqlite3.Error as error:
            raise _translate(error) from error
        except OSError as error:
            raise JournalError("missing or unavailable journal; preserve state") from error
        except (TypeError, KeyError, json.JSONDecodeError) as error:
            raise JournalError("invalid journal ownership; preserve state") from error

    def _connect(self):
        require(_file_identity(self.path) == self._identity, "journal file replaced")
        connection = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                                     isolation_level=None, timeout=1)
        try:
            connection.row_factory = sqlite3.Row
            # Inspect mode BEFORE changing anything: an unexpected WAL catalog is refused.
            require(connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete",
                    "unexpected journal mode")
            connection.execute("PRAGMA synchronous=EXTRA")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=1000")
            require(connection.execute("PRAGMA synchronous").fetchone()[0] == 3
                    and connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
                    and connection.execute("PRAGMA busy_timeout").fetchone()[0] == 1000,
                    "journal settings unavailable")
            require(connection.execute("PRAGMA application_id").fetchone()[0] == APPLICATION_ID
                    and connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
                    and schema_fingerprint(connection) == self._schema,
                    "unexpected journal schema")
            metadata = connection.execute("SELECT id,version FROM catalog LIMIT 2").fetchall()
            require(len(metadata) == 1 and tuple(metadata[0]) == (self.catalog_id, SCHEMA_VERSION),
                    "unexpected catalog identity")
            require(_file_identity(self.path) == self._identity, "journal file replaced")
            return connection
        except BaseException:
            connection.close()
            raise

    def _inject(self, kind: str, boundary: str) -> None:
        # Only test fault hooks run here; production callers must never do I/O in them.
        if self._fault is not None:
            self._fault(kind, boundary)

    def _mutate(self, operation: str, kind: str, arguments: object, action):
        identifier(operation)
        arguments_hash = digest(arguments)
        connection, committing = None, False
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            self._audit(connection)
            prior = connection.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
            if prior is not None:
                if prior["kind"] != kind or prior["arguments_hash"] != arguments_hash:
                    raise JournalConflict("operation identity reused with different arguments")
                result = validate_operation_receipt(connection, prior)
                connection.rollback()
                return result
            self._inject(kind, "after_begin")
            result = action(connection)
            self._inject(kind, "after_writes")
            connection.execute("INSERT INTO operations VALUES (?,?,?,?)",
                               (operation, kind, arguments_hash, encode(result)))
            self._audit(connection)
            self._inject(kind, "before_commit")
            committing = True
            connection.commit()
            self._inject(kind, "after_commit")
            return result
        except BaseException as error:
            if committing:
                # Even an apparently failed COMMIT can have committed. Do NOT refund.
                raise JournalUncertain(f"operation {operation} outcome unknown; reconcile receipt") from error
            if connection is not None and connection.in_transaction:
                try:
                    connection.rollback()
                except BaseException as rollback_error:
                    raise JournalUncertain(f"operation {operation} rollback uncertain") from rollback_error
            if isinstance(error, sqlite3.Error):
                raise _translate(error) from error
            if isinstance(error, OSError):
                raise JournalError("missing or unavailable journal") from error
            raise
        finally:
            if connection is not None:
                try:
                    connection.close()
                except BaseException as error:
                    raise JournalUncertain(f"operation {operation} close uncertain; reconcile receipt") from error

    def _read(self, action):
        connection = None
        try:
            connection = self._connect()
            connection.execute("BEGIN")
            return action(connection)
        except sqlite3.Error as error:
            raise _translate(error) from error
        except OSError as error:
            raise JournalError("missing or unavailable journal") from error
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _audit(connection) -> None:
        from .session_journal_checks import audit
        audit(connection)

    def operation(self, operation: str) -> dict | None:
        """Reconcile an ambiguous acknowledgement using its permanent durable receipt."""
        identifier(operation)
        def read(connection):
            row = connection.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
            if row is not None:
                validate_operation_receipt(connection, row)
            return None if row is None else dict(row)
        return self._read(read)

    def diagnostics(self) -> dict:
        """Report actual linked engine/source identity and verified connection policy."""
        def read(connection):
            return {"sqlite_version": sqlite3.sqlite_version,
                    "source_id": connection.execute("SELECT sqlite_source_id()").fetchone()[0],
                    "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
                    "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
                    "foreign_keys": connection.execute("PRAGMA foreign_keys").fetchone()[0],
                    "busy_timeout": connection.execute("PRAGMA busy_timeout").fetchone()[0]}
        return self._read(read)
