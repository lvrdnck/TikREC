"""Explicit public LIVE continuation using the existing reconnect loop."""

import time
from dataclasses import replace

from .live import capture_live
from .live_support import LiveChangedError
from .creator_identity import require_matching_creator
from .session_resume import begin_resume, prepare_resume
from .tiktok import (LiveResolution, _ResolvedLiveUrl,
                     resolve_live, same_live)
from .tiktok_bound import resolve_live_bound


def capture_live_resume(url, *, parts_directory, output_path, session_id, resolution,
                        resolver=resolve_live, bound_resolver=None, **options):
    """Open the proven room on a fresh connection and keep ordinary reconnects."""
    if bound_resolver is None and resolver is resolve_live:
        bound_resolver = resolve_live_bound
    session = prepare_resume(parts_directory, output_path=output_path, session_id=session_id,
                             source_type="tiktok_live", clock=options.get("manifest_clock", time.time),
                             **({"media_inspector": options["media_inspector"]}
                                if "media_inspector" in options else {}))
    saved = session.manifest.snapshot()
    require_matching_creator(saved, url)
    if not same_live(saved.get("room_id"), resolution):
        raise ValueError("resume resolution conflicts with saved session identity")
    first = resolution

    def same_transport(current):
        if not isinstance(current, LiveResolution):
            raise ValueError("reconnect requires structured public LIVE identity")
        if not same_live(resolution.room_id, current):
            # A different LIVE is an end of this session, never a source for the next writer.
            raise LiveChangedError("prior LIVE ended; account has a different room")
        return _ResolvedLiveUrl(current.flv_url, current.room_status, current.rendition_label,
                                current.rendition_source, current.room_id)

    def resolve_same(page):
        nonlocal first
        current = first if first is not None else resolver(page)
        first = None
        return same_transport(current)

    def resolve_same_bound(page, room_id):
        nonlocal first
        current = first if first is not None else bound_resolver(page, room_id)
        first = None
        return same_transport(current)

    begin_resume(session, output_path=output_path, clock=options.get("manifest_clock", time.time))
    result = capture_live(url, parts_directory=parts_directory, output_path=output_path,
                          session_id=session_id, resolver=resolve_same,
                          bound_resolver=resolve_same_bound if bound_resolver is not None else None,
                          _resume_session=session,
                          **options)
    return replace(result, resumed=True, resume_start_index=session.retained.next_index)
