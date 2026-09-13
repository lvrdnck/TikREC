# Connection evidence

`tikrec live` appends and flushes each closed capture/resolution attempt to
`connections.jsonl` in the parts directory. Existing fields and `room_status`
events remain unchanged. Older recordings remain readable; they do not acquire
new evidence retroactively.

## Connection milestones

All wall-clock fields are Unix timestamps in seconds. The new optional fields
are `null` when the milestone was not reached or an injected implementation
cannot observe it.

| Field | Meaning |
|---|---|
| `started_at` | Attempt starts, before room resolution. Existing field. |
| `resolved_at` | A successful resolver call returns its selected URL. |
| `http_opened_at` | The HTTP response opens, before reading its body. |
| `first_media_tag_at` | The first complete audio/video media tag is parsed, even if the writer discards it before a keyframe. |
| `first_retained_media_at` | The writer finishes writing its first media tag. |
| `last_retained_media_at` | The writer finishes writing its last media tag, including retained timestamp replays. |
| `ended_at` | Attempt closes after writer/raw-copy cleanup. Existing field. |

Sequence headers and script metadata do not advance retained-media timestamps.
Connections that never write media have `null` first/last retained timestamps.
The observation clock is injectable independently of the reconnect-policy clock.

For adjacent successful live-capture connections, the measurable breakdown is:

- Dying-connection tail: previous `ended_at - last_retained_media_at`.
- Backoff/local bookkeeping: current `started_at -` previous `ended_at`.
- Resolution: current `resolved_at - started_at`.
- HTTP/local setup: current `http_opened_at - resolved_at`.
- Initial media delivery/parsing: current `first_media_tag_at - http_opened_at`.
- Initial keyframe gate/writing: current `first_retained_media_at - first_media_tag_at`.

An intervening failed attempt contributes its own duration and backoff. These
are processing timestamps, not exact socket-byte arrival times: HTTP buffering,
parser work, file writes and cleanup are included. They diagnose elapsed capture
gaps, but do not prove how much missing source media was recoverable. Clock
adjustments or laptop sleep also affect wall-clock intervals.

Custom sources without an HTTP-open hook leave `http_opened_at` unknown; custom
writers without the retained-media hook leave retained-media times unknown.
Direct-FLV raw-copy records also contain observed media times, but have no room
resolution or selected rendition. Their existing attempt interval includes
optional finalization, unlike live-capture connection intervals.

## Rendition and part facts

Each live connection records `rendition_label` (the selection's normalized,
lowercase label) and `rendition_source` (`flv_pull_url` or `rtmp_pull_url`). These
carry the already-selected rendition; ranking and reconnect behavior do not
change. Plain-string custom resolvers leave both fields `null`. Signed CDN URLs
are not added to the log.

Each entry in `part_timings` additionally records:

- `width` and `height`: displayed dimensions from the part's AVC SPS, not from
  the padded/scaled final output.
- `nominal_frame_rate`: a positive rational string, such as `15/1` or
  `30000/1001`; unknown rates are `null`.
- `nominal_frame_rate_source`: `onMetaData`, `sps_vui`, or `null`.

The positive `onMetaData.framerate` associated with the part at its first
keyframe takes precedence; metadata preceding its configuration is cached.
While waiting for that keyframe, the latest positive advertisement wins. If no
rate was known at startup, the first later positive advertisement fills it.
Once known for a started part, subsequent advertisements are cached for the
next part rather than relabeling retained media: metadata can announce an
upcoming configuration change before that change closes the current part.
Otherwise, fixed-rate SPS VUI timing supplies `time_scale / (2*num_units_in_tick)`.
Non-fixed VUI timing is not used: TikTok may advertise a 1000 Hz timestamp grid
rather than the picture cadence. Missing, unsupported or damaged diagnostic
metadata stays unknown and never rejects media. No FFprobe process is added to
the reconnect path.

Nominal rate is not a measured average or a promise of constant-rate timestamps.
These fields do not feed resolution selection or encoder settings. Comparing
labels and actual part facts can expose changes, but a label alone does not
guarantee stable dimensions: an upstream encoder can change within one rendition.

## Explicit capture-resume boundary

Internal explicit resume appends one event before consuming the supplied new
connection. It does not replace existing connection or room-status evidence:

```json
{"event":"capture_resume","reason":"explicit_resume","timestamp":1789300000.0,"session_id":"a738109c-a387-423f-a20b-969ecf656c4b","previous_status":"interrupted","connection":3,"next_part_index":3}
```

`connection` allocates the upcoming attempt; `next_part_index` forces its new
writer part. The new connection's closed record follows and contains only new
parts, while manifest/result part counts cover old plus new parts. Connection
allocation continues above the greatest manifest/log/resume-event allocation;
a process can die after allocation but before its closed record is written.
Historical closed connection numbers must increase and part ranges cannot
overlap. Incomplete JSONL tails and conflicting/missing part references block
resume instead of being truncated or repaired. Numeric part gaps and abandoned
partial files also block resume. New error summaries redact transport URLs.

The event records explicit library-level continuation, not proof of a service
restart or Windows reboot. Those decisions/evidence belong to the later service
reconciliation module. No signed FLV URL is included, no media is appended to an
old FLV, and each new part starts in its own rebased timestamp domain.
