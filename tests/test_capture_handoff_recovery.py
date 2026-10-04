"""Existing coalesced recovery evidence is sealed only after a proved normal end."""

import json
import os
from pathlib import Path

import pytest

from tests.capture_handoff_helpers import authority, local_media, observations, reserve
from tikrec.capture_handoff import CaptureHandoffError
from tikrec.live_recovery import OutageCaptureError
from tikrec.retry_policy import RetryPolicy
from tikrec.tiktok import TikTokOfflineError, TikTokResolutionTransientError, _ResolvedLiveUrl

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires native Windows recovered capture")


@pytest.mark.parametrize("tamper", [False, True])
def test_recovered_coalesced_resolver_failures_preserve_actual_control_contract(tmp_path, tamper):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        actions = iter((_ResolvedLiveUrl("https://fixture.invalid/source.flv", 2, room_id="123"),
                        TikTokResolutionTransientError("retry one"), TikTokResolutionTransientError("retry two"),
                        _ResolvedLiveUrl("https://fixture.invalid/source.flv", 2, room_id="123"),
                        TikTokOfflineError("ended", room_id="123")))
        def resolver(_):
            value = next(actions)
            if isinstance(value, Exception):
                raise value
            return value
        opts = observations(data)
        opts.update(resolver=resolver, recovery_waiter=lambda *_: None)
        if tamper:
            reached = []
            def fault(boundary):
                if boundary == "before_inventory":
                    reached.append(True)
                    path = Path(bridge.intent.parts_path, "connections.jsonl")
                    values = [json.loads(v) for v in path.read_text().splitlines()]
                    values = [v for v in values if v.get("phase") != "recovered"]
                    path.write_text("".join(json.dumps(v) + "\n" for v in values))
            bridge._fault = fault
            with pytest.raises(CaptureHandoffError):
                bridge.run(**opts)
            assert owner.journal.session(bridge.intent.session_id)["seal"] is None
            assert reached, "must corrupt the closed recovery evidence, not fail earlier"
        else:
            assert bridge.run(**opts).phase == "queued"
            values = [json.loads(v) for v in Path(bridge.intent.parts_path, "connections.jsonl").read_text().splitlines()]
            assert [v["connection"] for v in values if "outcome" in v] == [1, 2, 4, 5]
            assert [v["phase"] for v in values if v.get("event") == "network_recovery"] == ["entered", "recovered"]
            assert len([a for a in owner.journal.session(bridge.intent.session_id)["seal"]["artifacts"]
                        if a["role"] == "flv"]) == 2


def test_exhausted_recovery_preserves_original_error_and_retained_parts_without_H(tmp_path):
    data = local_media(tmp_path / "fixture.flv")
    with authority(tmp_path) as owner:
        bridge = reserve(owner)
        calls, elapsed = [], [0.0]
        def resolver(_):
            calls.append(True)
            if len(calls) == 1:
                return _ResolvedLiveUrl("https://fixture.invalid/source.flv", 2, room_id="123")
            raise TikTokResolutionTransientError("unproved room end")
        def wait(_, delay):
            elapsed[0] += delay
        opts = observations(data)
        opts.update(resolver=resolver, recovery_waiter=wait, recovery_clock=lambda: elapsed[0],
                    retry_policy=RetryPolicy(1.0, (0.6,), 0.6))
        with pytest.raises(CaptureHandoffError) as caught:
            bridge.run(**opts)
        assert isinstance(caught.value.original, OutageCaptureError)
        assert caught.value.original.parts
        row = owner.journal.session(bridge.intent.session_id)
        assert row["phase"] == "closing" and row["task"] is None and row["seal"] is None
        assert Path(bridge.intent.parts_path, "part-0001.flv").exists()
