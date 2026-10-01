"""Owner confirmation, one request, uncertain transport and truthful display outcomes."""

from io import StringIO
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tikrec.managed_retention_cli import run_managed_delete
from tikrec.remote import RemoteError


@pytest.fixture
def client_fixture(monkeypatch):
    import tikrec.managed_retention_cli as cli
    session_id = str(uuid4())
    calls = []
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        def managed_preview(self, target):
            calls.append(("preview", target))
            return dict(session_id=session_id, root="/var/lib/tikrec/recordings",
                        creator="alpha", ended_at=1000, output="/var/lib/tikrec/recordings/a.mp4",
                        parts="/var/lib/tikrec/recordings/a.parts", file_count=3,
                        total_file_bytes=123, preview_digest="f" * 64)
        def managed_delete(self, target, digest):
            calls.append(("delete", target, digest))
            if isinstance(self.result, BaseException):
                raise self.result
            return self.result
        result = dict(code=0, stdout="COMPLETE: deleted session\n", stderr="")
    monkeypatch.setattr(cli, "RemoteClient", Client)
    args = SimpleNamespace(session_id=session_id, root=None, confirm=session_id,
                           server="http://127.0.0.1:8766", token_file=None, timeout=60)
    return args, Client, calls


def test_preview_exact_confirmation_and_one_request(client_fixture):
    args, _, calls = client_fixture
    out = StringIO()
    assert run_managed_delete(args, out, StringIO(), StringIO()) == 0
    assert [call[0] for call in calls] == ["preview", "delete"]
    assert args.session_id in out.getvalue() and "COMPLETE" in out.getvalue()


def test_wrong_or_missing_confirmation_never_dispatches_delete(client_fixture):
    args, _, calls = client_fixture
    args.confirm = "other"
    with pytest.raises(ValueError, match="exactly match"):
        run_managed_delete(args, StringIO(), StringIO(), StringIO())
    assert calls == []
    args.confirm = None
    with pytest.raises(ValueError, match="not provided"):
        run_managed_delete(args, StringIO(), StringIO(), StringIO("wrong\n"))
    assert [call[0] for call in calls] == ["preview"]


@pytest.mark.parametrize("failure", [RemoteError("response lost"), KeyboardInterrupt(), SystemExit()])
def test_lost_response_is_uncertain_without_retry(client_fixture, failure):
    args, client, calls = client_fixture
    client.result = failure
    err = StringIO()
    assert run_managed_delete(args, StringIO(), err, StringIO()) == 3
    assert "do not retry" in err.getvalue()
    assert len(calls) == 2


@pytest.mark.parametrize("result", [dict(code=0), dict(code=0, stdout=None, stderr=""),
                                  dict(code=True, stdout="", stderr="")])
def test_malformed_result_and_diagnostic_failure_remain_uncertain(client_fixture, result):
    args, client, calls = client_fixture
    client.result = result
    class BrokenStream(StringIO):
        def write(self, value):
            raise OSError("diagnostic unavailable")
    assert run_managed_delete(args, StringIO(), BrokenStream(), StringIO()) == 3
    assert len(calls) == 2


@pytest.mark.parametrize("code", [0, 1, 3, 130])
def test_display_failure_preserves_proven_service_result(client_fixture, code):
    args, client, _ = client_fixture
    client.result = dict(code=code, stdout="service result", stderr="")
    class Stream(StringIO):
        def write(self, value):
            if value == "service result":
                raise OSError("display failure")
            return super().write(value)
    assert run_managed_delete(args, Stream(), StringIO(), StringIO()) == code
