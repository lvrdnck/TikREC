"""Explicit public LIVE continuation using the existing reconnect loop."""

import time
from dataclasses import replace

from .live import capture_live
from .live_support import LiveChangedError
from .session_resume import begin_resume, prepare_resume
from .tiktok import (LiveResolution, _ResolvedLiveUrl,
                     resolve_live, same_live)


def capture_live_resume(url, *, parts_directory, output_path, session_id, resolution,
                        resolver=resolve_live, **options):
    """Open the proven room on a fresh connection and keep ordinary reconnects."""
    session = prepare_resume(parts_directory, output_path=output_path, session_id=session_id,
                             source_type="tiktok_live", clock=options.get("manifest_clock", time.time),
                             **({"media_inspector": options["media_inspector"]}
                                if "media_inspector" in options else {}))
    if not same_live(session.manifest.snapshot().get("room_id"), resolution):
        raise ValueError("resume resolution conflicts with saved session identity")
    first = resolution

    def resolve_same(page):
        nonlocal first
        current = first if first is not None else resolver(page)
        first = None
        if not isinstance(current, LiveResolution):
            raise ValueError("reconnect requires structured public LIVE identity")
        if not same_live(resolution.room_id, current):
            # A different LIVE is an end of this session, never a source for the next writer.
            raise LiveChangedError("prior LIVE ended; account has a different room")
        return _ResolvedLiveUrl(current.flv_url, current.room_status, current.rendition_label,
                                current.rendition_source, current.room_id)

    begin_resume(session, output_path=output_path, clock=options.get("manifest_clock", time.time))
    result = capture_live(url, parts_directory=parts_directory, output_path=output_path,
                          session_id=session_id, resolver=resolve_same, _resume_session=session,
                          **options)
    return replace(result, resumed=True, resume_start_index=session.retained.next_index)
