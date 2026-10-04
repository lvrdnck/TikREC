"""Real disposable capture/journal helpers; no LIVE, service or default state."""

import json
import subprocess
import time
from pathlib import Path

from tikrec.capture_handoff_authority import CaptureAuthority, operation_id
from tikrec.session_journal import SessionJournal
from tikrec.source import iter_tags
from tikrec.tiktok import TikTokOfflineError, _ResolvedLiveUrl


def local_media(path):
    """Generate short valid AVC/AAC source media through local ffmpeg only."""
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=10",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "0.6",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "3", "-c:a", "aac",
                    "-f", "flv", str(path)], check=True, capture_output=True, timeout=30)
    return path.read_bytes()


def authority(tmp_path):
    """Initialize one explicitly named fresh catalog and native disposable root."""
    state, media = tmp_path / "state", tmp_path / "media"
    state.mkdir()
    media.mkdir()
    journal = SessionJournal.initialize(state / "sessions.sqlite3", operation_id())
    return CaptureAuthority(journal, media)


def reserve(owner, name="one", room="123", creator="creator", raw=True, slot=None):
    """Accept immutable raw/output identity in a real journal before any source opens."""
    return owner.reserve(owner.root / (name + ".mp4"), creator, room, raw_copy=raw,
                         started_at=time.time(), automatic_claim=operation_id(), slot=slot)


def observations(data, room="123", *, escaped=None, source=None):
    """Resolve one proven fixture room and then end it through the actual LIVE loop."""
    actions = iter((_ResolvedLiveUrl("https://fixture.invalid/source.flv", 2, room_id=room),
                    TikTokOfflineError("fixture ended", room_id=room)))
    def resolver(_):
        value = next(actions)
        if isinstance(value, Exception):
            raise value
        return value
    def raw_source(_, raw):
        if escaped is not None:
            escaped.append(raw)
        def chunks():
            for offset in range(0, len(data), 256):
                chunk = data[offset:offset + 256]
                raw.write(chunk)
                yield chunk
            raw.observe_read_end("eof")
        yield from iter_tags(chunks())
    result = {"resolver": resolver, "raw_tag_source": source or raw_source,
              "tag_source": lambda _: iter_tags((data,)), "sleeper": lambda _: None,
              "offline_confirmation_checks": 1, "media_inspector": lambda _: None}
    return result


def manifest(bridge):
    """Read the durable manifest after every native capture handle has released."""
    return json.loads((Path(bridge.intent.parts_path) / "session.json").read_text())


def contents(root):
    """Capture byte identity for small fixture artifacts, outside capture transactions."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and p.name != ".tikrec-lifecycle.lock"}
