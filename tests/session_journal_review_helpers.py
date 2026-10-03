"""Logical-corruption fixtures use normal constraints, never disable the schema."""

import sqlite3
from dataclasses import asdict

from tikrec.session_journal_types import digest, encode


def seed_reserved(store, selected, slot, *, receipt="valid", receipt_session=None, terminal=False):
    """Insert individually valid conflicting intent directly in a disposable DB."""
    values = asdict(selected)
    with sqlite3.connect(store.path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        columns = [row[1] for row in connection.execute("PRAGMA table_info(sessions)")]
        # Both reviewed version 1 and its explicit successor are testable unchanged.
        names = ["id", "intent", "creator", "expected_room", "origin_slot", "generation", "phase", "revision"]
        parameters = [selected.session_id, encode(values), selected.creator, selected.expected_room,
                      slot, 1, "no_assembly" if terminal else "reserved", 1]
        if "automatic_claim" in columns:
            names.append("automatic_claim")
            parameters.append(selected.automatic_claim)
        connection.execute(f"INSERT INTO sessions({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
                           parameters)
        if not terminal:
            connection.execute("UPDATE bindings SET generation=1,session=? WHERE slot=?",
                               (selected.session_id, slot))
            connection.execute("INSERT INTO units VALUES (?,'capture')", (selected.session_id,))
            for kind in ("output", "parts"):
                connection.execute("INSERT INTO artifacts VALUES (?,?,?)",
                                   (selected.session_id, kind, encode(values[kind])))
            if selected.expected_room is not None:
                connection.execute("INSERT INTO rooms VALUES (?,?)", (selected.expected_room, selected.session_id))
        if selected.automatic_claim is not None and receipt != "missing":
            connection.execute("INSERT INTO automatic_receipts VALUES (?,?,?)",
                               (selected.automatic_claim, receipt_session or selected.session_id,
                                "0" * 64 if receipt == "wrong_hash" else digest(values)))
