"""Retry FIFO survives bounded process death; no power-loss guarantee is inferred."""

import json
import subprocess
import sys

import pytest

from tests.session_journal_helpers import capture, intent, journal, rows, uid
from tikrec.session_journal import SessionJournal
from tikrec.session_journal_types import AttemptExitProof


CHILD = r'''
import json, os, sys
from pathlib import Path
from tests.test_session_journal_fifo import fifo_operation
from tikrec.session_journal import SessionJournal
path, catalog, boundary, record_path = sys.argv[1:]
store = SessionJournal(Path(path), catalog)
operation, selected, earlier, invoke = fifo_operation(store, 'retry_failed')
Path(record_path).write_text(json.dumps({'operation': operation, 'session': selected.session_id,
                                      'earlier': earlier.session_id, 'task': store.session(selected.session_id)['task']}))
original_connect = store._connect
def connect():
    connection = original_connect()
    connection.execute('PRAGMA cache_size=1')
    return connection
def fault(kind, point):
    if (kind, point) == ('retry_failed', boundary): os._exit(91)
store._connect, store._fault = connect, fault
invoke(store)
'''


@pytest.mark.parametrize("boundary", ["after_writes", "before_commit", "after_commit"])
def test_retry_process_death_reconciles_same_entry_before_claiming(tmp_path, boundary):
    store = journal(tmp_path)
    unrelated, _ = capture(store, intent("unrelated", "999"))
    before = store.session(unrelated.session_id)
    request_path = tmp_path / "request.json"
    child = subprocess.run([sys.executable, "-c", CHILD, str(store.path), store.catalog_id,
                            boundary, str(request_path)], capture_output=True, text=True, timeout=15)
    assert child.returncode == 91, child.stderr
    request = json.loads(request_path.read_text())
    assert store.path.with_name(store.path.name + "-journal").exists() == (boundary != "after_commit")
    reopened = SessionJournal(store.path, store.catalog_id)
    receipt = reopened.operation(request["operation"])
    assert (receipt is not None) == (boundary == "after_commit")
    assert len(rows(reopened)["queue_entries"]) == (3 if receipt is not None else 2)
    task = request["task"]
    proof = AttemptExitProof(request["session"], task["token"], "owned-exit")
    result = reopened.retry_failed(request["operation"], request["session"], task["revision"],
                                   task["attempt"], task["token"], proof)
    assert result == json.loads(reopened.operation(request["operation"])["result"])
    durable = rows(reopened)
    assert reopened.retry_failed(request["operation"], request["session"], task["revision"],
                                 task["attempt"], task["token"], proof) == result
    assert rows(reopened) == durable and len(durable["queue_entries"]) == 3
    assert reopened.session(unrelated.session_id) == before
    assert reopened.claim_next(uid(), uid())["session_id"] == request["earlier"]
