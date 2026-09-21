"""Read-only timing comparison for established TikTok room resolution."""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

from .tiktok import TikTokOfflineError, _resolve_room
from .tiktok_bound import resolve_live_bound
from .tiktok_identity import LiveResolution, canonical_room_id


@dataclass(frozen=True, slots=True)
class RequestTiming:
    """Safe timing for one public resolver request, without its URL."""

    stage: str
    seconds: float
    succeeded: bool


class _TimedResponse:
    def __init__(self, response, *, stage, started, clock, observations):
        self._response = response
        self._reader = response
        self._stage, self._started = stage, started
        self._clock, self._observations = clock, observations
        self._recorded = False

    def __enter__(self):
        self._reader = self._response.__enter__()
        return self

    def __exit__(self, *arguments):
        return self._response.__exit__(*arguments)

    def read(self):
        try:
            body = self._reader.read()
        except Exception:
            self._record(False)
            raise
        self._record(True)
        return body

    def _record(self, succeeded):
        if not self._recorded:
            self._observations.append(RequestTiming(
                self._stage, max(0.0, self._clock() - self._started), succeeded
            ))
            self._recorded = True


class _TimedOpener:
    def __init__(self, opener, *, clock):
        self._opener, self._clock = opener, clock
        self.observations: list[RequestTiming] = []

    def __call__(self, request, **options):
        stage = _request_stage(request.full_url)
        started = self._clock()
        try:
            response = self._opener(request, **options)
        except Exception:
            self.observations.append(RequestTiming(
                stage, max(0.0, self._clock() - started), False
            ))
            raise
        return _TimedResponse(
            response, stage=stage, started=started, clock=self._clock,
            observations=self.observations,
        )


@dataclass(frozen=True, slots=True)
class _Run:
    safe: dict[str, Any]
    resolution: LiveResolution | None


def benchmark_resolution(
    live_url: str,
    room_id: str,
    *,
    samples: int = 3,
    timeout: float = 15,
    opener: Callable[..., Any] = urlopen,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Compare current bound resolution with direct known-room refresh read-only."""
    if not isinstance(samples, int) or isinstance(samples, bool) or not 1 <= samples <= 20:
        raise ValueError("samples must be an integer from 1 through 20")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    saved_room_id = canonical_room_id(room_id)
    pairs = []
    for index in range(samples):
        order = ("bound", "direct") if index % 2 == 0 else ("direct", "bound")
        runs = {}
        for path in order:
            runs[path] = _run_resolution(
                path, live_url, saved_room_id, timeout=timeout,
                opener=opener, clock=clock,
            )
        pairs.append(_pair_report(index + 1, order, saved_room_id, runs))
    return {
        "schema_version": 1,
        "saved_room_id": saved_room_id,
        "sample_count": samples,
        "pairs": pairs,
        "summary": _summary(pairs),
    }


def _run_resolution(path, live_url, room_id, *, timeout, opener, clock):
    timed_opener = _TimedOpener(opener, clock=clock)
    started = clock()
    resolution = None
    outcome = "error"
    status = None
    error_type = None
    try:
        if path == "bound":
            resolution = resolve_live_bound(
                live_url, room_id, opener=timed_opener, timeout=timeout
            )
            # Production rejects a proven account-room change after bound resolution.
            outcome = "live" if resolution.room_id == room_id else "different_room"
        else:
            resolution = _resolve_room(room_id, opener=timed_opener, timeout=timeout)
            outcome = "live"
    except TikTokOfflineError as error:
        outcome, status = "offline", error.status
        error_type = type(error).__name__
        room = error.room_id
    except Exception as error:
        error_type = type(error).__name__
        room = None
    else:
        room = resolution.room_id
        status = resolution.room_status
    total = max(0.0, clock() - started)
    safe = {
        "path": path,
        "outcome": outcome,
        "room_id": room,
        "room_status": status,
        "error_type": error_type,
        "total_seconds": total,
        "requests": [asdict(item) for item in timed_opener.observations],
    }
    # Only live results survive long enough for in-memory equivalence comparison.
    return _Run(safe, resolution if outcome in {"live", "different_room"} else None)


def _pair_report(number, order, room_id, runs):
    bound, direct = runs["bound"], runs["direct"]
    both_live = bound.safe["outcome"] == direct.safe["outcome"] == "live"
    room_equal = bool(both_live and _equal(bound, direct, "room_id")
                      and bound.resolution.room_id == room_id)
    label_equal = bool(both_live and _equal(bound, direct, "rendition_label"))
    source_equal = bool(both_live and _equal(bound, direct, "rendition_source"))
    transport_equal = bool(both_live and _equal(bound, direct, "flv_url"))
    comparable = room_equal and label_equal and source_equal and transport_equal
    equivalence = {
        "comparable": comparable,
        "room_id_equal": room_equal,
        "rendition_label_equal": label_equal,
        "rendition_source_equal": source_equal,
        "media_transport_equal": transport_equal,
    }
    savings = (
        bound.safe["total_seconds"] - direct.safe["total_seconds"]
        if comparable else None
    )
    return {
        "sample": number,
        "order": list(order),
        "bound": bound.safe,
        "direct": direct.safe,
        "equivalence": equivalence,
        "direct_savings_seconds": savings,
    }


def _equal(left, right, name):
    return getattr(left.resolution, name) == getattr(right.resolution, name)


def _summary(pairs):
    comparable = [pair for pair in pairs if pair["equivalence"]["comparable"]]
    savings = [pair["direct_savings_seconds"] for pair in comparable]
    return {
        "comparable_sample_count": len(comparable),
        "bound_total_median_seconds": _median(comparable, "bound"),
        "direct_total_median_seconds": _median(comparable, "direct"),
        "direct_savings_median_seconds": statistics.median(savings) if savings else None,
        "bound_live_page_median_seconds": _request_median(comparable, "bound", "live_page"),
        "bound_public_lookup_median_seconds": _request_median(
            comparable, "bound", "public_account_lookup"
        ),
        "bound_room_info_median_seconds": _request_median(comparable, "bound", "room_info"),
        "direct_room_info_median_seconds": _request_median(comparable, "direct", "room_info"),
    }


def _median(pairs, path):
    values = [pair[path]["total_seconds"] for pair in pairs]
    return statistics.median(values) if values else None


def _request_median(pairs, path, stage):
    values = [
        request["seconds"]
        for pair in pairs
        for request in pair[path]["requests"]
        if request["stage"] == stage
    ]
    return statistics.median(values) if values else None


def _request_stage(url):
    parsed = urlsplit(url)
    if parsed.hostname == "webcast.tiktok.com" and parsed.path == "/webcast/room/info/":
        return "room_info"
    if parsed.path == "/api-live/user/room/":
        return "public_account_lookup"
    if parsed.hostname and (
        parsed.hostname == "tiktok.com" or parsed.hostname.endswith(".tiktok.com")
    ):
        return "live_page"
    return "other_public_request"
