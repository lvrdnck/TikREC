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
- Total observed retained-media gap: current `first_retained_media_at -` previous
  `last_retained_media_at`.

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

## Read-only reconnect-gap analyzer

This analyzer and the evidence-backed healthy-close timing change documented
below are the complete reconnect-specific scope of TikREC v0.6.0.

Run the checkout-local diagnostic against one or more retained logs:

```console
python scripts/analyze_reconnect_gaps.py PATH/TO/connections.jsonl [...]
```

Add `--json` for structured output. The analyzer never writes recording artifacts.
It reports unknown milestones as `unknown`, lists recorded intervening attempts,
flags connection-number allocations whose individual resolver attempts were
coalesced, and classifies explicit outage, service-restart, capture-resume, and
room-status boundaries separately from ordinary reconnects. A wall-clock retained-
media gap is diagnostic elapsed time, not exact missing source-media duration.

The 2026-09-19 Phase 1 audit inspected the six retained non-test datasets under
`runs/`: `gracie-kf-2026-09-15.parts`, `gracie-kf-2026-09-15_1.parts`,
`recording.parts`, `v05-deployment-allynwd04-20260916.parts`,
`v05-issue14-abrupt-lilymaye207-20260919T0200.parts`, and
`v05-network-outage-lilymaye207-20260919T1425.parts`. Only `recording.parts`
contained a usable ordinary in-process reconnect. Its connection 1 to 2 breakdown
was 0.001 seconds dying tail, 1.004 local/backoff, 7.107 resolution, 2.691
HTTP/local setup, 0.080 initial media delivery/parsing, less than 0.001 keyframe/
write gate, and 10.883 total.
With `n=1`, the median and range are the same. Resolution plus HTTP open accounted
for about 90% of the observed gap and is substantially source/network dependent.
The approximately one-second configured healthy-close wait is TikREC-controlled;
tail cleanup, parsing, and the write gate include TikREC-local work but contributed
only about 0.081 seconds here. One ordinary sample is insufficient to change that
production delay.

The deliberate v0.5 network-outage validation is excluded from the ordinary
baseline. Its connection 1 to 8 gap was 103.366 seconds: 0.150 dying tail, 100.280
between attempts/outage waits, 2.125 resolution, 0.459 HTTP/local setup, 0.351
initial media delivery/parsing, and 0.001 write gate. Its recovery event and six
coalesced resolver-only allocations identify it as outage evidence. The other
retained logs contain single connections, terminal room-end confirmation, or
service/process-restart and explicit-resume boundaries without two comparable
media-bearing connection records, so they do not contribute ordinary samples.

### Healthy-close evidence and optimization

The later `vibecrewkrista.parts` session passed retained-session validation for
all four FLVs and contributed two ordinary reconnects. Connection 1 to 2 measured
2.515 seconds total: 0.069 tail, 1.005 local/backoff, 1.087 resolution, 0.247 HTTP
setup, 0.107 initial media, and 0.001 write gate. Connection 2 to 3 is excluded as
transient network recovery: it measured 9.494 seconds total, including a 5.982-
second dying tail after `IncompleteRead`. The `network_recovery:recovered` event
after connection 3 closes the prior episode; it does not taint connection 3 to 4,
which is ordinary and measured 3.997 seconds total: 0.172 tail, 1.008 local/
backoff, 1.288 resolution, 1.410 HTTP setup, 0.118 initial media, and 0.001 gate.

Combined with `recording.parts`, the ordinary baseline is three reconnects across
two sessions. Median/range in seconds is: total 3.997/2.515--10.883, previous tail
0.069/0.001--0.172, healthy local/backoff 1.005/1.004--1.008, resolution
1.288/1.087--7.107, HTTP setup 1.410/0.247--2.691, initial media
0.107/0.080--0.118, and keyframe/write gate 0.001/0.000--0.001. This repeated
approximately one-second TikREC-controlled wait justified removing it only for a
normal media-bearing close. A healthy close now begins fresh resolution without
that sleep. Network/transient waits, failure backoff, patient recovery, room-end
confirmation, stop checks, new writer/part state, and fresh URL resolution retain
their prior behavior. The expected reduction is about one second per ordinary
reconnect; a post-change real reconnect was still necessary to measure it directly.

### Post-change verification

The retained `ari-dakotaa-postchange.parts` session supplied one suitable ordinary
reconnect after `dfc5bf1`. Connection 1 closed normally after retained media, and
connection 2 resumed without an intervening failed attempt or recovery boundary.
The measured gap was 1.920 seconds total: 0.114 seconds of previous tail, 0.010
local/backoff, 1.480 resolution, 0.220 HTTP setup, 0.096 initial media, and 0.001
at the keyframe/write gate.

Compared with the three-sample pre-change baseline, local/backoff fell from a
1.005-second median and 1.004--1.008 range to 0.010 seconds. This verifies that
the fixed healthy-close wait collapsed as intended. Resolution accounted for
about 77% of the observed gap and resolution plus HTTP setup for about 89%.
The 1.480-second resolution remained within the prior 1.087--7.107 range; the
0.220-second HTTP setup was just below the prior 0.247--2.691 range; and initial
media plus the write gate remained within their prior ranges. The total is below
the prior 2.515--10.883-second range, but resolver and HTTP timings vary with the
source and network; one post-change sample does not justify changing those
policies.

The session is complete and contains ten retained parts. Validation found H.264
decoder errors in earlier parts 1 and 5; both the last pre-reconnect part 7 and
first post-reconnect part 8 passed, and the log records no timestamp replay. The
earlier media findings therefore do not disqualify the wall-clock reconnect sample
or justify a production change from this evidence. The retained artifacts remain
unchanged.

### Full-LIVE release soak

The retained `aishaaa-ts-v060-full-live.parts` session recorded through the
deployed v0.6.0 service from remote start until natural room end, without a manual
stop or manufactured failure. Session `3d0016f5-bf1b-4df1-80c2-d4e7de87149d`
ran for 872.873 seconds, retained 92,267,458 bytes in three parts, and finalized a
75,853,434-byte H.264/AAC MP4 with 831.810 seconds of media. It completed without
an error, interruption, or recovery of persistent state.

The log has three allocated connection attempts: two media-bearing connections
and a final media-free offline attempt that completed the normal three-observation
room-end confirmation. There was one natural media reconnect, from connection 1
to 2. Connection 1 ended with `IncompleteRead(0 bytes read)`, so the analyzer
correctly classifies the boundary as `network_recovery`, not as an ordinary
healthy-close sample. Its 8.494-second retained-media gap comprises 5.960 seconds
of previous tail, 1.016 local/failure backoff, 1.165 resolution, 0.265 HTTP setup,
0.086 initial media, and 0.002 at the keyframe/write gate. There were no
intervening or unrecorded attempts.

The approximately one-second local component is expected for the unchanged
transient-failure path and is not evidence that the removed healthy-close wait
returned. This boundary is therefore not comparable as an ordinary sample with
the pre-change 1.004--1.008-second healthy-close baseline. The existing ordinary
post-change verification remains 1.920 seconds total with 0.010 local/backoff.
For this recovery gap the dying tail dominated, followed by resolution and the
preserved failure backoff; one observation does not justify retry, resolver, or
HTTP changes.

Connection 2 later changed source width from 720 to 640 pixels and opened part 3
without another reconnect. All three FLVs passed decoder and packet-DTS validation
without warnings, including part 1 to 2 across the reconnect and part 2 to 3
across that configuration change. No connection recorded timestamp replay or a
stall. Normal and deep validation of the finalized MP4 also passed without
findings. The soak therefore adds natural recovery, room-end confirmation, source-
change, and finalization evidence without exposing a v0.6.0 release blocker.

## Raw copy and byte-arrival evidence

When `--raw-copy DIR` successfully opens both diagnostics, each connection has
`connection-NNNN.raw` and `connection-NNNN.arrivals.jsonl`. Its closed numbered
record in `connections.jsonl` names them in `raw_copy` and `raw_arrivals`.
Either field is `null` when that diagnostic was disabled or failed. Older
records omit `raw_arrivals` or read it as unknown; the session manifest schema
does not change.

The arrival sidecar is UTF-8 JSON Lines. Records are emitted in this order:

1. One `clock_reference` record has `connection`, Unix `wall_time`, process-local
   `monotonic_time`, and `boundary="raw_copy_write"`.
2. Each successful HTTP body read has a `byte_arrival` record with `connection`,
   zero-based raw-file `offset`, positive byte `count`, process-local
   `monotonic_time`, and `elapsed_seconds` from the clock reference. The byte
   range is `[offset, offset + count)` and successful ranges are contiguous.
3. A clean EOF or observed read failure may end with a `read_end` record. Its
   `reason` is `eof`, `timeout`, or `error`, with the same monotonic fields.

The byte timestamp is sampled immediately after Python's HTTP `read1()` returns
and before raw-file writing, cooperative-stop handling, FLV parsing, or writer
retention. `read1()` makes at most one underlying buffered read, allowing bytes
already available to be returned before a later stall. Sources without `read1()`
use the compatible `read()` fallback. Injected custom raw sources may write raw
bytes without producing a `read_end` boundary.

These observations show when this TikREC process received each returned byte
range at its HTTP-library boundary. They do **not** identify TCP/TLS packet
boundaries, exact socket arrival or server-send time, FLV tag boundaries, or
media that could have been recovered after a disconnect. OS, TLS, socket, and
Python buffering can combine data, while scheduling and disk work add local
delay. Monotonic values are comparable only within the connection; `wall_time`
is an approximate bridge to `connections.jsonl`, not a conversion guarantee.

Like the raw byte copy, the sidecar is diagnostic and best-effort. Lines are
flushed but not fsynced per body read, so a process or machine crash may leave a
missing or incomplete tail. Any open/write/flush/close failure warns, disables
that diagnostic, and never interrupts recording. Existing files are never
overwritten; a sidecar collision disables only the sidecar while the raw copy
may continue. Partial or unreferenced diagnostic files remain evidence.

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
The current evidence also cannot compare candidates that were not selected.
Doing that safely requires a non-sensitive candidate inventory, an explicit
selection-policy identifier, and the provenance of any verified metadata; those
fields are not added until public response semantics and real media agree.

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
restart or Windows reboot. The service now appends separate recovery evidence. No signed FLV URL is included, no media is appended to an
old FLV, and each new part starts in its own rebased timestamp domain.

## Service recovery observations

Startup reconciliation appends fixed, non-secret boundaries to valid existing
logs. A service_recovery event never allocates a connection or replaces evidence:

```json
{"event":"service_recovery","timestamp":1789300000.0,"session_id":"a738109c-a387-423f-a20b-969ecf656c4b","reason":"process_restart","resume_count":1}
```

Fields are exactly event, timestamp, session_id, reason, resume_count. Reasons
include process_restart, room_ended, live_changed, user_stop, recovery_finalization,
existing_output, identity_unavailable, ambiguous_state, and failed_resume. A
process_restart observation before resolution carries the prior counter; a second
one after committed same-room resume carries the incremented counter. The ensuing
capture_resume records the concrete connection/part allocation before media opens.
Closed numbered connection records and existing room_status evidence then continue
in order. In-process reconnects retain ordinary numbered connection evidence.

room_ended/live_changed record observed reconciliation decisions, not exact room
end during downtime. New room ID and signed CDN URL are never written into these
boundaries. The internal single-attempt reconciliation API can still append
identity_unavailable and return deferred. The service's default patient worker
uses the outage boundaries below. Malformed storage/logs are preserved rather than appended
to or repaired; safe failure diagnostics remain available through service status.
Timestamp is when TikREC actually observed recovery, never an inferred crash time
or proof of a PC reboot. Existing logs without these events remain compatible;
preflight validates new boundaries before any future continuation.

A resumed recording's later reconnect that proves a different room closes its
numbered attempt with outcome=live_changed and finalizes the prior session. It
never invents an offline room_status response for the account's new ongoing LIVE.

## Patient network recovery observations

One `network_recovery` boundary records outage entry; another summarizes recovery,
exhaustion, proven end, stop, or nonretryable failure. These append to the existing
log and never allocate a connection or include transport URLs/error reprs:

```json
{"event":"network_recovery","timestamp":1789300030.0,"session_id":"a738109c-a387-423f-a20b-969ecf656c4b","phase":"exhausted","retry_attempt":7,"outage_elapsed_seconds":900.0,"failure_kind":"dns"}
```

Fields are exactly those shown. Phases are entered, recovered, exhausted, offline,
live_changed, user_stop, failed; kinds are dns, timeout, connection, http, network.
retry_attempt counts classified failures in the episode; elapsed uses monotonic
time and timestamp is the observed wall clock. Startup `recovered` means valid
identity resolution returned; service_recovery then records the same/different-room
decision. During active capture, useful retained media ends the episode; merely
resolving the same room does not reset a persistently failing CDN's window.

Waits and repeated resolver-only failures inside an outage do not append individual
records or rewrite the manifest. Their counts appear in the closing summary.
The first resolver failure and actual source attempts retain ordinary numbered
records; connection numbers can therefore have monotonic gaps. In-memory capture
records keep all attempts, and the manifest flushes total allocations on capture
completion/failure. Strict resume preflight validates these event fields and
session identity; malformed evidence is preserved and blocks continuation.
