# TikREC — a recorder for public TikTok LIVE streams

## Current implementation goal

Record one public TikTok LIVE stream at a time to disk, reliably and completely,
from either an explicit URL or an opt-in monitored creator. Stop when the stream
ends or when I stop it.

## Scope

### Current

- Public LIVE streams only
- Recording a stream from the moment I start the tool
- Reconnecting within a recording when the connection drops
- One recording owned by an independently launched service, controlled remotely
- An opt-in ordered configuration list of canonical public creator handles
- Read-only service polling with conservative in-memory LIVE observations
- Non-mutating unattended-admission status for detected configured LIVEs
- One durable room-bound automatic start after a completed monitoring cycle

TikREC v0.5.0 established service startup reconciliation, v0.6.0 added evidence-
based reconnect-gap measurement while removing only the fixed healthy-close
wait, and v0.7.0 added guided interrupted-session recovery. Package version
v0.8.0 adds the per-user configuration/default behavior documented below;
published release records are maintained in PROJECT_STATE.md.

### Not implemented yet

- Subscriber-only, private, or otherwise gated streams
- Authentication and session management
- Multiple simultaneous creator recordings or redundant same-LIVE capture
- Schedule prediction from recording history
- Chat collection, transcription, chapters, search, analytics
- A recording library, browser playback/downloads, or Web/PWA interface
- Notifications, cloud publishing/storage, accounts, or multi-user/mobile operation

These are release/product scope statements, not permanent prohibitions.
Library/history/playback and a web interface are also part of the product
direction. Other items remain possible later. ROADMAP.md owns sequencing and
capability status; this specification remains authoritative for behavior that
exists in the current checkout.

### Permanent security and privacy boundaries

- No auth, CAPTCHA, entitlement, access-control, or private request-signing
  bypass
- No feature whose purpose is covertly tracking a person rather than
  supporting streams and recordings the user legitimately chose to access
- No silent destruction or overwrite of recordings, retained evidence, or user
  data

Some rooms that are visibly live return room-info status code `4003110` and
expose no stream URLs to anonymous page or API requests, while other public
rooms resolve normally. This is TikTok making a session-dependent access
decision, not an offline status. A normal browser User-Agent and Referer were
tested and did not change the response. Recording those rooms would require
authenticating as the user, which the current checkout does not implement. A future
authenticated mode may use a session explicitly provided by the user, but must
not bypass TikTok's access controls.

The current commands never wait for a stream to begin. If the room is offline
when invoked, that is an error, not a wait state.

## Commands

    tikrec record <direct-flv-url> --output FILE [--raw-copy DIR]
    tikrec resolve <tiktok-live-page-url>
    tikrec live <tiktok-live-page-url> [--output FILE] [--raw-copy DIR] [--recovery-window-seconds SECONDS]
    tikrec finalize PARTS_DIRECTORY --output FILE
    tikrec recover ROOT [--validate] [--finalize] [--json]
    tikrec validate TARGET [--deep | --standard] [--json]
    tikrec config show [--json]
    tikrec config path
    tikrec config set output-directory DIRECTORY
    tikrec config unset output-directory
    tikrec config set recovery-window-seconds SECONDS
    tikrec config unset recovery-window-seconds
    tikrec config set validation-mode standard|deep
    tikrec config unset validation-mode
    tikrec config set debug-tracebacks true|false
    tikrec config unset debug-tracebacks
    tikrec monitor add CREATOR
    tikrec monitor remove CREATOR
    tikrec monitor list
    tikrec serve [--host IP] [--port PORT] [--token-file FILE] [--recovery-window-seconds SECONDS]
    tikrec remote health --server URL [--token-file FILE]
    tikrec remote status --server URL [--token-file FILE]
    tikrec remote monitor-status --server URL [--token-file FILE]
    tikrec remote start --server URL PUBLIC_LIVE_URL --output ABSOLUTE_PC_MP4_PATH [--raw-copy] [--token-file FILE]
    tikrec remote stop --server URL [--token-file FILE]
    tikrec --version

Global `--debug` and `--no-debug` are mutually exclusive; local command parsers
also accept them after the subcommand. They explicitly enable or suppress Python
tracebacks for unexpected CLI exceptions. Known capture, resolution, remote,
configuration, filesystem, validation, and interruption outcomes retain their
concise existing handling and never gain tracebacks from this preference.

`record` takes a direct FLV URL and is the generic path. It must stay
source-agnostic and must not gain TikTok-specific behaviour. Its optional
`--raw-copy DIR` stores the unmodified connection bytes before FLV parsing.
`finalize` stitches a retained parts directory after an interrupted or failed
run. It uses the same finalizer as capture, never changes the parts, and
refuses to overwrite an existing destination.
`validate` performs a read-only structural and media health check on an output
file, parts directory, or session manifest/directory. It does not finalize,
repair, or recover recordings. Standard validation fully decodes retained
parts but uses bounded stream/container/duration inspection for a completed
output. `--deep` also decodes the complete output; its cost grows with recording
length and session validation then decodes both the parts and final artifact.
The explicit `--deep` and `--standard` flags are mutually exclusive. Without
one, the command uses configured `validation_mode`, then built-in `standard`.
An explicit flag bypasses configuration loading for this preference; an
implicit mode fails if configuration is malformed.

Exit codes: 0 success, 1 capture/finalization/validation failure, 2 invalid CLI
usage, 130 interrupted capture.

`serve` runs a loopback-by-default HTTP service. Explicit non-loopback IP binding
requires a bearer secret; all configured-token endpoints check it. `remote`
prints JSON from health/status/monitor-status/start/stop. Start/stop acknowledge asynchronously;
responses reporting a failed job and request failures exit 1. There is one
active recording; latest explicit intent is persisted for startup reconciliation. See
[SERVICE.md](SERVICE.md) for the exact API and independent Windows deployment.

## Modules

Layered so that generic FLV handling never becomes TikTok-specific.

### tikrec/flv.py — format
Bytes in, structured data out. No network, no subprocess.

`FlvTag`, `read_tag`, `sps_dimensions`, `avc_configuration_dimensions`,
`FlvFormatError`. Configuration tags are `payload[1] == 0`, media tags
are `payload[1] == 1`.

### tikrec/writer.py — parts on disk
Consumes an iterable of tags, writes numbered FLV parts.

- Waits for a video keyframe before writing media into a part
- Rebases timestamps per part
- Writes AVC configuration, then AAC configuration, then first keyframe
- Rolls to a new part only on a real AVCDecoderConfigurationRecord change
- Writes `.partial`, promotes atomically with `os.replace`
- Deletes parts retaining zero media tags
- Accepts an explicit `start_index` so numbering can carry across sessions

The AAC configuration must be cached and emitted even when it arrives
before the first video keyframe. Dropping it produces an FLV that looks
valid and decodes at a ~99% audio error rate.

A visual layout change on TikTok does not imply a codec configuration
change. Roll on the codec, not on appearance.

### tikrec/source.py — one HTTP connection
`iter_tags`, `iter_url_chunks`, `iter_url_tags`, `RawCopy`, `SourceStallError`.

Parses incrementally, never buffers the whole stream. Validates the FLV
header and initial PreviousTagSize. No retries, no TikTok-specific logic.
This is the primitive for exactly one direct FLV connection. When requested,
`RawCopy` tees each received byte chunk to `connection-NNNN.raw` before the
parser consumes it. It also records local HTTP-read boundaries in a best-effort
`connection-NNNN.arrivals.jsonl` sidecar and links that file from the numbered
connection's `raw_arrivals` field. A raw-copy or arrival-log open, write, flush,
or close failure warns and disables only the affected diagnostic; capture
continues. Existing diagnostic paths are never overwritten.

HTTP responses use `read1()` when available so a single underlying buffered
read can return bytes already available before a later stall; sources without it
retain the `read()` fallback. Arrival timestamps are sampled after that call and
before raw writing, stop handling, parsing, or writer retention. They describe
this process's local HTTP-library boundary, not TCP/TLS packets, exact socket or
server timing, FLV tags, or proof that missing media was recoverable. See
[CONNECTION_LOG.md](CONNECTION_LOG.md) for the persistent record contract.

HTTP source operations default to a 30-second timeout. A timeout after the
response has opened is raised as `SourceStallError`, distinguishing an open
connection that stopped delivering bytes from an ordinary close or other HTTP
failure. Callers may inject a different positive timeout, or explicitly use
`None`, but the recording paths use the bounded default.

### tikrec/finalize.py — stitching
`finalize_parts(parts, output_path, *, ffmpeg, runner, progress, frame_rate_inspector)`.

Identical configurations across parts: concat demuxer with `-c copy`.
Differing configurations: filter_complex, reset timestamps, scale and pad
to a common size, re-encode.

Re-encoding probes each part's video frame rate with FFprobe, preferring a
positive `avg_frame_rate` and falling back to a positive `r_frame_rate` when
the average is unavailable. The average is preferred because `r_frame_rate`
can describe a timestamp-grid estimate rather than the actual cadence. The
encoder's nominal rate is the maximum of these per-part rates, not a
duration-weighted session average: a long slow segment must not dilute the
nominal rate needed for a faster segment. Missing usable rates fail clearly
rather than falling back to an arbitrary constant.
`tikrec/frame_rate.py` owns this bounded FFprobe inspection and rational rate
selection; the probe runner and finalizer's rate inspector are injectable for
offline tests.

This rational rate is supplied only through x264's `fps` parameter. Output
uses timestamp passthrough and the concat filter's microsecond encoder time
base; no output `-r` or `fps` filter forces constant-rate sampling. Existing
per-part timestamp resets remain, but variable intervals within each part are
preserved. x264 selects its H.264 level automatically; no level is hardcoded.
This prevents mixed-rate concat's unknown frame rate from being mistaken for
the inverse microsecond time base (1,000,000 fps), which previously made
`prinske-01` incorrectly declare level 6.2 despite 15/25 fps, 720x1280 media.
Re-finalization verified automatic level 3.1, a passing full decode, all
18,935 video frames retained, and exactly preserved within-part video PTS
intervals. Audio packet payloads and timing matched the original output.

Writes a hidden temporary file preserving the output suffix
(`.final.partial.mp4`, not `.final.mp4.partial` — ffmpeg infers the muxer
from the extension). Promotes with `os.replace`. Refuses to overwrite an
existing destination. Never deletes the source parts.

Before FFmpeg starts, progress states whether finalization will stream-copy or
re-encode. Re-encoding warns that it may take several minutes or longer.
Structured FFmpeg output time is reported as encoding progress; other progress
fields are suppressed, while real diagnostics remain available for failures.

### tikrec/tiktok.py — resolution
`resolve_live(url, *, opener, timeout) -> LiveResolution` for a public LIVE page.
`resolve_live_url(...) -> str` remains the compatibility wrapper, including raw
room status and rendition observation attributes; it now also carries room_id.

Finds the room ID from public page state, falls back to the public
api-live user/room lookup. Queries webcast room/info. Live means room
status equals 2. Picks a rendition by deterministic label preference.
The structured result contains room_id, flv_url, raw room_status, rendition_label,
and rendition_source. Its transport URL remains HTTP(S) with a `.flv` path.

The accepted `flv_pull_url` and `rtmp_pull_url` values provide a rendition label,
source field, and transport URL to TikREC. The resolver has no validated
per-candidate dimensions, native cadence, bitrate, codec, or reliability facts.
`_quality_score` is therefore a conservative label heuristic, not measured media
quality: known label families form tiers, then source field, normalized label,
and URL provide deterministic tie-breaks. Unrecognized labels remain below known
tiers rather than having arbitrary numbers or adjectives interpreted as facts.
The presence of `hls_pull_url` does not alter FLV selection because TikREC does
not currently support HLS capture. No sibling or embedded SDK field may affect
production ranking until its meaning is verified against delivered media.

Selected label/source evidence is recorded for each connection. After capture,
part evidence supplies displayed SPS dimensions and an optional advertised or
fixed-VUI nominal cadence; the completed manifest supplies output codec and
dimensions. These observations explain what the selected stream delivered, not
why another candidate would have been better. A real `hd1` service session
validated successfully at 640x1280 H.264, 25 fps, and about 1.07 Mbit/s overall,
which demonstrates that a label alone is not a resolution or bitrate guarantee.

Before changing the default policy, a bounded developer-only comparison must
hold signed URLs in memory and identify samples only by non-sensitive source
field, normalized label, and protocol. Capture short same-window samples from
every legitimately exposed public FLV/HLS candidate where practical; compare
codec, dimensions, packet cadence, duration, delivered bitrate, startup, and
manual visual quality. Then compare longer same-window samples for stalls,
disconnects, recovery, truncation, timestamp replays, configuration changes,
decoder/validation errors, and finalization behavior. Repeat on multiple public
LIVEs before inferring a global transport policy. This investigation does not
add a public CLI or make normal recording multi-rendition.

`tikrec/tiktok_identity.py` owns public identity discovery, `LiveResolution`,
`canonical_room_id`, and `same_live` (also exposed from `tiktok`). Room IDs are
positive ASCII decimal strings with leading zeros removed; large IDs retain
their digits without narrowing to a fixed integer width. Empty, zero,
malformed, duplicate JSON fields, or conflicting public identities fail safely.
Repeated numerically equivalent IDs are accepted. Discovery considers all room
IDs in recognized page state instead of guessing from traversal order. A page
with no identity falls back to the public lookup; a malformed or conflicting
identity is an error. Room-info's explicit id/id_str/roomId/room_id must agree
with the queried ID; nested account-owner IDs are not LIVE identities.

`same_live(saved_room_id, resolution)` compares canonical room IDs only. Equal
IDs are eligible for consideration as the same LIVE; different IDs or missing/
unprovable identity return false. Username identifies an account, not one LIVE.
Signed FLV URLs, CDN hostnames, timestamps, and media similarity prove nothing
about identity. When room-info omits its ID, the result retains the ID used in
the successful public room-info query. This is the strongest public identity
available to TikREC, not a documented TikTok guarantee against future ID reuse.
Automatic resume must remain conservative if identity cannot be established.

Both resolver APIs make a single resolution attempt and preserve typed failures;
the separate service monitor schedules repeated calls. A valid numeric room status other than 2
raises `TikTokOfflineError` carrying raw status and queried room_id. Missing or
nonnumeric status, malformed room data, and conflicting identity raise
`TikTokResolutionError`. Classified transport failures and HTTP 408/425/429/5xx
raise `TikTokResolutionTransientError`, carrying a safe failure kind and optional
Retry-After hint. Permanent HTTP/local failures cannot enter patient retry.
Offline confirmation is unchanged; the shared outage policy below governs retries.

The frozen structured result excludes signed URLs and untrusted rendition
metadata from repr/str. `safe_diagnostics()` contains only room_id and live=true.
Its flv_url is internal transport data: generic dataclass `asdict` serialization
still includes it and must never be used for status or persistence. The legacy
URL wrapper intentionally remains the actual URL for source/CLI compatibility.
Network-error messages redact HTTP(S) URLs. Durable jobs store only room_id,
never the resolution object or its URL. Job-state validation shares the
canonical identity helper without a resolver-to-service dependency.

`rtmp_pull_url` may contain an HTTPS FLV URL despite its name, so it is also
considered after `flv_pull_url`; the latter wins equal-quality ties. An actual
`rtmp://` URL is not supported. `hls_pull_url` may also be present, but HLS
capture is not supported.

The current resolver uses no cookies, login, private signing, or yt-dlp.

### tikrec/capture.py — orchestration
`capture_tags`, `capture_url`, `CaptureResult`, `CaptureError`.

Prepares the session directory once, refuses to reuse an existing one,
preserves completed parts on error or interrupt, finalizes on clean EOF.

`_capture_session` shares writer unwind and finalization behavior with explicit
resume. `CaptureResult` adds optional `resumed` (default false) and
`resume_start_index` (default null); existing callers keep their behavior.

### tikrec/session_parts.py, session_resume.py, and capture_resume.py - explicit continuation

`discover_parts(directory)` returns numerically ordered completed parts plus
the next writer index. Names must exactly match `part-{index:04d}.flv` for
positive ASCII decimal indexes; four digits are a minimum, so part 10000 follows
9999. Parts must be regular files, contiguous from one. Gaps fail even if a log
could suggest a missing part: this module does not repair or skip evidence.
Part-looking names, other FLV files, and any `.partial` artifact inside the
directory fail preflight. Unrelated non-FLV/non-part/non-partial files are
ignored because they cannot claim a writer index. Symlink parts are refused.
This generic rule remains unchanged. Service startup uses a separate recovery
planner for the exact canonical active writer partial only.

Checks read bounded chunks through the existing FLV parser: writer header,
complete tags and PreviousTagSize, own AVC sequence header, first media at a
zero-based video keyframe, AAC configuration before audio media, and no changed
AVC record inside one part. This scans framing without FFmpeg/FFprobe or codec
decoding; cost grows with retained bytes and does not prove media health.

`writer_recovery.py` admits that partial only when durable job and manifest both
prove active recording ownership, UUID/source/room/output/parts paths and counts
agree, prior parts are contiguous, output/finalizer temp are absent, and no second,
wrong-index, same-index, unowned, colliding, symlink, or nonregular artifact exists.
It finds the last complete tag with the existing parser; malformed framing before
a merely incomplete trailing tag blocks. Recovery intent is persisted before the
exact original is atomically moved to a deterministic evidence-only name. A new
copy contains either all bytes or only that complete prefix and must pass writer
structure, FFprobe decoding/DTS, and recognizable-video inspection before atomic
publication. Evidence bytes are never changed. Optional schema-1 manifest records
make preservation/publication retryable and bind part/evidence names plus source
SHA-256, original/recovered, and discarded byte counts. Resume then uses a fresh
connection and next part; no timestamps, duration, or counts claim the downtime
was captured.

`prepare_resume` validates a supported schema-1 manifest and connection evidence
without writing. Status must be recording/interrupted/failed; finalization must
be pending/not_started/not_requested. Finalizing, finalized, or cleanly completed
sessions require finalization reconciliation instead of capture continuation. It verifies the UUID,
source type, times/counts/flags, matching parts-directory path, optional expected
session ID/source type, and canonical room identity when present. A recording
manifest may lag completed parts; a closed manifest must match their count.
Recording manifests may also lag flushed connection evidence; closed manifests
must not predate newer connection records. The next connection is
one above the greatest manifest/log/resume-boundary allocation, so a crashed
unclosed attempt is not reused. Truncated/malformed logs, duplicate fields,
backward/duplicate connection numbers, overlapping part ownership, and missing
part references fail safely. Relative manifest paths use the original working
directory; relocated sessions with conflicting paths are not guessed into use.

`capture_tags_resume(tags, *, parts_directory, output_path=None, ...)` and
`capture_url_resume(direct_flv_url, *, parts_directory, output_path=None, ...)`
are explicit internal APIs. Callers must own the session and ensure the previous
writer has exited. A supplied direct URL opens exactly one connection: no
TikTok resolution, identity decision, reconnect policy, or future-LIVE polling.
Optional injections cover source/writer/finalizer, clocks, media inspection,
stop event, expected identity/source, progress, and heartbeat. The session must
already exist with completed parts and a valid manifest; legacy manifest-free
directories can still use manual finalize but cannot resume capture.

Preflight finishes before consuming a source. Resume preserves original session
ID, source type, start time, room identity and other stored facts; it atomically
reopens recording lifecycle, updates counts and recovery_performed, then appends
a capture_resume event before the new connection. There is no new manifest
schema or media resume counter; the service job owns resume_count.
The returned connection tuple describes this attempt; older evidence remains
in connections.jsonl. A new writer always starts at the next index, even with
identical AVC/AAC bytes. It obtains its own headers/keyframe and never appends
old media, reuses prior timestamp bases, or offsets DTS across parts.

No output argument means capture-only continuation: the previous output
declaration is retained, but this attempt marks finalization not_requested.
An explicit output must match a prior declaration (or establish one if null).
Existing declared/requested outputs or finalizer temporary artifacts block
resume even when output finalization is omitted. Requested finalization uses
all old and new parts in numeric order. Failures retain every part; first
Ctrl-C/cooperative stop uses the same close/retain/finalize path as fresh capture,
and a second finalization interrupt retains the existing finalizer semantics.
Service startup now uses this session continuation through `live_resume.py`.
There is no resume CLI/remote endpoint. LIVE continuation uses the patient outage
policy below; generic direct/tag resume remains one connection. The v0.6 healthy-
close optimization is limited to immediate fresh resolution after a normal media-
bearing close and does not change this resume policy.
Real-recording part decoder/DTS validation passed during the completed v0.5
deployment validation.

### tikrec/manifest.py and tikrec/media.py — session metadata

`SessionManifest` owns the versioned `session.json` lifecycle and atomic file
replacement. `inspect_media` obtains stream codecs, video dimensions, container
name, and duration from one shared FFprobe path. Manifest capture treats those
facts as optional; validation applies the stricter requirements appropriate to
an explicit health check. See [SESSION_MANIFEST.md](SESSION_MANIFEST.md) for the
schema.

### tikrec/part_validation.py, tikrec/validation.py, and validation_report.py

`part_validation` owns decoder and stored-packet-DTS checks for one retained
FLV part. `validation` discovers supported targets, checks readable non-empty
media, calls the shared part/media probes, and compares v0.2+ manifests with
disk state. `validation_report` defines the collected result/finding model and
human rendering; the same model produces `--json` output.

Validation requires recognizable video. Missing audio is a warning because a
video-only source may be valid. A completed output must additionally expose a
container and a positive finite duration. For a manifest session, declared
non-null codec/resolution facts must agree with FFprobe, part counts must agree
with disk, and completed finalization requires an existing output. Missing
optional manifest media fields do not fail.

The validator reports media integrity, session completeness, and output
availability separately. Therefore an interrupted/failed/recording session can
pass when its retained parts are healthy even though no completed output exists.
It never mutates a manifest or recording. The standalone validation script is a
compatibility wrapper over this shared implementation.

Validation began as a standalone developer script because v0.1 had only one
diagnostic operation over retained parts and did not promise a stable user
interface. It became a `tikrec` subcommand in v0.3 because validation now covers
multiple user-owned target types, has documented exit behavior and JSON output,
and is a supported recording workflow rather than a development probe. Keeping
the script as the primary interface would either hide that status or duplicate
target discovery and reporting. The script remains only as a thin wrapper over
the same reusable implementation.

### tikrec/live.py — reconnect-capable public LIVE capture
`capture_live(url, *, parts_directory, output_path, ...)` implements the
`tikrec live` path above the generic source, writer, and finalizer layers.

It resolves, connects, records, then re-resolves after every connection
close so that each retry uses a fresh signed CDN URL. It does not poll room
status while an FLV connection is open. After retained media exists, it stops
only after three consecutive non-live room-info responses, with five seconds
between responses. Thus the default confirmation window spans about ten
seconds from its first response to its third.

Initial resolution still requires the public username LIVE page or its normal
page-200 lookup fallback; HTTP 404 cannot invent a room or a successful session.
Once a canonical room ID is durably established, bound resolution concurrently
refreshes public room-info for that exact ID and queries the public account's
current room identity. It accepts the refreshed transport only when the saved
room is live and the account lookup identifies that same room. Offline,
malformed, conflicting, unavailable, or failed fast-path evidence falls back to
the prior full page/account/room resolver. A proven different current live room
ends the prior session under the existing identity rule; a saved-room numeric
non-live status enters the existing confirmation window. A different room's
non-live status and all unprovable identity fail closed rather than becoming
saved-room offline evidence. Initial resolution is unchanged.

Confirmation begins only after the preceding FLV response has ended or failed;
no media connection remains open during the checks. If a later check returns
live, capture resumes but may have missed up to about ten seconds of media that
was available through a new connection, in addition to the ordinary reconnect
backoff and request latency. If all three responses are falsely non-live,
TikREC ends the recording and may miss the room's entire remaining stream. It
never discards bytes still arriving on an open FLV connection.

- Every reconnect creates a new writer and starts a new part, even when the
  AVC and AAC configurations are identical. A new HTTP connection may reset
  timestamps, so continuing the preceding writer state could create backward
  or zero timestamps.
- Only `TikTokOfflineError`, raised from a successful room-info response
  whose room status is not `2`, means offline. Classified resolver network,
  timeout, and temporary HTTP failures retry with the patient policy. A live response
  during confirmation cancels the sequence and capture resumes; a later
  non-live response starts a new sequence at one.
- An open CDN response that delivers no bytes for 30 seconds raises
  `SourceStallError`. Live capture records the connection outcome as `stalled`,
  preserves any completed part, and retries it as a transient failure under the
  shared bounded patient policy once a canonical LIVE identity is anchored.
- HTTP 404 while opening an established room's freshly resolved media transport
  requests another identity/status resolution after the existing failure backoff.
  It is not classified as offline; before retained media and canonical identity
  exist, the same source response remains a terminal failure.
- Room offline at the first resolve is an error. Room offline after retained
  media and successful confirmation is a normal end and triggers optional
  finalization.
- Part numbering carries forward through the writer's explicit `start_index`;
  it is never inferred by scanning the parts directory.
- As each connection closes, `connections.jsonl` receives and flushes one
  record with wall-clock start/end, its preceding gap, retained part range,
  outcome, error, and optional raw-copy filename. `CaptureResult.connections`
  exposes every attempt. Repeated resolver-only failures during an outage coalesce
  disk evidence into network_recovery summaries, so persisted connection numbers
  may have monotonic gaps. End confirmation also appends and
  flushes one `room_status` event per checked response. Each event contains
  `timestamp`, the raw `status` value, and `confirmation_reached`; a live
  response that cancels confirmation is included as evidence.
- `session.json` is initialized only after resolution creates a real session,
  then its part and connection counts are updated as attempts close. Initial
  offline or unresolved rooms still leave no session directory.
- An anchored LIVE uses the shared 15-minute patient transient window below.
  Initial unresolved capture and legacy injected resolvers without room identity
  retain the three-failure limit. Three clean connections retaining no media still
  fail. A healthy media-bearing EOF reconnects immediately through fresh resolution;
  non-live confirmation remains
  three checks spaced five seconds apart. Policy, limits, clocks and waits are injectable.
- Programming errors, invalid arguments, and malformed FLV data do not retry.
  The first Ctrl-C closes the writer and finalizes retained parts when an
  output was requested, but still exits 130 because capture ended early. A
  second Ctrl-C during finalization terminates FFmpeg; all retained parts
  survive either path.

### tikrec/capture_control.py — cooperative stop

`CaptureControl` checks an optional `threading.Event` around resolver calls,
between complete tags, and during interruptible retry/confirmation waits.
`source` also accepts a stop check between chunks, including while parsing a
large incomplete tag. Sources close deterministically when capture unwinds.
`CaptureStopped` follows the same writer-close/retain/finalize/manifest path as
first Ctrl-C. The event never enters finalization. Existing bounded HTTP reads
can delay stop until their operation finishes or times out. No subprocess is
killed for a remote stop. Retry waits are inside the first-interrupt handler.

`capture_live` also accepts a state observer and optional session ID. It reports
resolving/recording/reconnecting/finalizing without signed URLs, and supplies the
application job's ID to the existing schema-1 manifest. Local CLI defaults and
interrupt exit codes remain unchanged; no capture algorithm is duplicated.

### tikrec/recording.py — application job ownership

`RecordingController` reserves one slot under a lock, launches a non-daemon
worker that invokes `capture_live`, and uses its Event for stop. The slot stays
busy through finalization. Snapshots expose idle or the current/latest job,
normalized public source, paths, lifecycle times, retained-part count, existing
writer byte heartbeat, reconnect attempts, interruption, and a bounded redacted
error. Successful stop is completed/interrupted; capture/finalizer errors are
failed. Requested output and actual final output are distinct fields. Shutdown
rejects new starts, requests stop, and joins the worker outside the lock.
Automatic callers may additionally pass one internal canonical expected room
ID. Only that path wraps the initial and bound resolvers so fresh structured
identity must match before capture creates a session or opens media. The HTTP
start schema cannot supply this value, and manual starts remain unchanged.

### tikrec/job_state.py - durable service intent (v0.5.0)

`JobState` and `JobStateStore` provide validated, atomic storage for the latest
explicitly started service job. Intent exists independently of `session.json`
because the service must persist acceptance before resolution creates media
storage. The job record owns the public page URL, requested paths, job identity,
lifecycle, stop flag, finalization-completed flag, optional public room ID,
resume count, and fixed recovery reason. The manifest continues to own media
facts and connection counts. See [SERVICE.md](SERVICE.md) for job schema 1.

Non-terminal intent needs reconciliation unless finalization is complete.
Capture resume additionally requires a saved room ID, no stop request, and a
capture lifecycle state; callers must still verify that the current room ID
matches. Finalizing jobs may only reconcile finalization. Malformed, duplicate,
missing, or unknown fields fail safely without modifying stored evidence.

The controller now persists explicit starts before workers, room identity before
media opens, stop intent before signalling, and lifecycle/result changes. Default
state lives outside the checkout at %LOCALAPPDATA%\TikREC\job.json (Windows),
or ${XDG_STATE_HOME:-~/.local/state}/TikREC/job.json. No state-path CLI option
is added. Only the latest job is stored, with one owning service process/account.
Package version is v0.8.0.

### Patient outage policy and transport classification

`network_errors.py` classifies terminal LIVE evidence, user stop, transient
transport, malformed response, and local/programming failures. DNS, timeout,
reset/abort/refusal, network-unreachable, incomplete reads/EOF errors and matching
urllib causes retry. HTTP 408/425/429 and 500–599 retry; permanent HTTP, malformed
payloads, disk/permission errors and programming errors fail conservatively.
Bare OSError with no errno is accepted only at known transport boundaries for
legacy injected sources; exception text is never used to infer retryability.

`retry_policy.py` provides one immutable injectable RetryPolicy and monotonic
OutageRecovery shared by active LIVE and startup. Default waits are 1, 2, 5, 10,
10, then 30 seconds, capped at 30; Retry-After seconds/HTTP dates can increase
waits up to that cap. The window is 900 seconds from the first transient error,
with waits clamped to remaining time and no new attempt at expiry. Existing
bounded HTTP calls may finish after the deadline. Stop wins over expiry.

`live_recovery.py` binds every established reconnect to the chosen room ID and
adapts the shared policy to capture. A same-room resolve alone cannot reset a
persistently failing CDN episode; useful retained media closes it. `live_source.py`
marks only source creation/read failures, leaving writer errors nonretryable.
`startup_network.py` retries identity resolution after storage preflight, inside
the existing service worker. `network_evidence.py` appends strict coalesced entry/
outcome summaries; `live_session.py` owns capture completion/failure and connection
closure. Timestamp, codec and keyframe algorithms are unchanged.

Stop/shutdown uses Event.wait to wake retry waits and finalize retained media.
Timeout instead fails capture without finalizing or claiming offline, leaves all
parts intact and finalization not_started, and persists terminal failed/outage_timeout.
The service releases its slot; that job never auto-relaunches. A process death
during non-terminal recovering_network preserves explicit identity/intent; restart
reconciles the same room with a fresh window. No deadline is persisted. Only
meaningful transitions are saved; safe API counters/countdowns are computed in
memory. Job schema remains 1 with extended state/reason enums, media schema stays 1.
This remains the v0.5 outage-survival policy. The v0.6 optimization removes only
the fixed healthy-close delay; failure/outage waits and safety behavior remain
unchanged.

### tikrec/reconciliation.py - service startup decisions

`StartupReconciler` loads durable intent and inspects owned storage independently
of HTTP. The controller reserves an unresolved job before accepting new starts;
its worker exposes reconciling/recovering/resuming. Missing intent is idle and
terminal/completed intent is never relaunched. Maintenance restart while idle
stays idle; pre-integration recordings without intent are never inferred.

`recovery_session.py` checks supported manifest, matching UUID/source/room/paths,
contiguous completed parts and connection evidence. Capture resume also passes
strict `prepare_resume` checks and requires manifest room_id equal to durable
room_id. Only an interrupted capture-phase explicitly-started job with no user
stop and a missing final output can proceed to public identity resolution.

Patient bound-resolution attempts prove the same saved room ID before resume and
can use direct room-info if the username LIVE page is HTTP 404. Different LIVE or
explicit offline means the prior LIVE ended during downtime and safely
finalizes retained parts. It never monitors a username for the next LIVE. Stop
intent outranks identity; stopped/finalizing jobs skip TikTok and only assess
finalization. Existing output needs committed manifest completion and bounded
matching codec/container/positive-duration evidence; ambiguity blocks recovery
without overwriting it. Finalization retries only with absent output. A nonempty
encoder temporary is recoverable only when durable job state is `finalizing` and
manifest finalization is `running`; it is atomically preserved under a
collision-safe session evidence name before every retained part is re-finalized.
Empty/nonregular/unproven temporaries, evidence-name collisions, and coexisting
output/temporary artifacts remain untouched and block. Failures retain media,
preserved evidence, and a finalizing job for a later retry.

The service injects the shared patient policy; transient failures save
recovering_network/network_outage and retry in-process without repeating storage
preflight. GET health/status work and POST start returns 409 while unresolved.
Timeout returns an unblocked exhausted result and terminal failed/outage_timeout
job. The direct reconcile API without a policy retains its single-attempt typed
DeferredReconciliationResult contract. Malformed public data/storage or programming
failures produce fixed safe failure diagnostics and never count as offline.

### tikrec/live_resume.py and recovery_evidence.py - service continuation

`capture_live_resume` shares explicit preflight/begin-resume with generic resume,
then seeds the existing LIVE loop with old parts and the proven first resolution.
It preserves session ID/start/room identity, opens a new direct connection, starts
the next numeric part, and resets timestamps/codec/keyframe state. Later ordinary
reconnects use the shared patient policy and must match saved room ID; a different
LIVE is never connected. `live_source.py` retains per-connection source/raw-copy
selection with a source-error classification boundary. CLI interfaces stay unchanged.

The job's resuming phase and incremented resume_count are atomically saved before
media continuation; concurrent remote stop cannot be overwritten by that decision.
`service_recovery` events append observed restart/decision/finalization evidence,
followed by `capture_resume` and new numbered connections. No exact crash time is
invented, and no signed URL enters persistence or status. Media manifest schema
stays 1 with optional room_id; old manifests retain validation/manual-finalize
compatibility. Automatic capture resume requires proven persisted identity.

Interrupted-FFmpeg finalization and active-writer-partial reconciliation are
implemented. Issue #14's repeat process-death deployment validation passed on
2026-09-19 with exact crash-evidence preservation, validated-prefix publication,
and same-session/same-room continuation into a fresh connection and part. The
temporary-network-outage deployment validation also passed on 2026-09-19: while
TikTok resolution and media were isolated behind a terminated loopback proxy, the
service retained one session/room, fixed media counts, responsive control, and
patient retry state; restoring the proxy automatically resumed the same room in a
fresh growing part without a new start. Pre-outage and active post-reconnect media
both passed decoder/DTS checks. At that point final completed-media validation
remained outstanding. No future-LIVE monitoring or Task Scheduler modification
is implemented.

The preserved outage session then passed final deployment validation. A normal
remote stop closed its successful post-outage connection as interrupted, closed
the open recovery summary with phase `user_stop`, retained four coherent FLVs,
and completed finalization. All retained parts passed decoder/DTS checks; the
1,200.636-second H.264/AAC MP4 passed deep validation without findings. The
103.366-second observed retained-media gap across the outage is absent from the
output rather than represented as capture. After proxy retirement and an idle
service restart, status also restores the completed manifest's reconnect count;
active capture avoids reading the manifest while its atomic replacement may be
in progress. All v0.5 real deployment-validation phases are complete. Package
version is 0.8.0.

### tikrec/service.py — narrow HTTP adapter

`RecordingHTTPServer` uses the standard-library `ThreadingHTTPServer` with a
custom handler for GET health/recording/monitoring and POST recording/start/stop only.
Handlers validate bounded JSON and delegate to the controller. No file serving,
commands, executable paths, accounts, or browser UI. Default `127.0.0.1:8765`;
explicit remote IPs require a token checked in constant time. Raw request logs
and browser-origin requests are disabled; read timeouts bound stalled clients.
This service is for trusted LAN/Tailscale use, not public internet hosting.

### tikrec/monitoring.py — read-only creator observation

`CreatorMonitor` receives the immutable ordered creator tuple selected at service
startup. An empty tuple starts no worker. Otherwise one worker begins a cycle
promptly, resolves creators sequentially in configured order, then waits 30
seconds after the completed cycle before starting another. The single worker
prevents overlap; each creator failure is contained so later creators are still
checked. Configuration changes take effect only after service restart.

Each observation is `pending`, `live`, `offline`, or `unknown`. Only
`TikTokOfflineError` proves `offline`; transient transport errors, permanent or
malformed public responses, access restrictions, missing identity, unexpected
failures, and non-structured resolver results remain `unknown` under fixed safe
categories. Positive LIVE results retain only canonical public `room_id`.
Signed transport URLs and arbitrary exception text are discarded immediately.
Snapshots and cycle timing are protected by a lock, remain memory-only, reset on
restart, and never extend job/session/connection schemas. After publishing a
complete cycle, the monitor invokes one injected notification outside its lock;
partial shutdown cycles never notify. The monitor itself neither consults nor
mutates `RecordingController`. Service shutdown first prevents later automatic
starts, requests monitor stop, shuts down recording, and joins the monitor after
its current bounded resolver call.

### tikrec/admission.py — unattended-recording admission

`RecordingAdmission` is composed by the service but remains separate from the
resolver worker. On each monitoring-status request it evaluates the current
controller health and storage state for every observation without selecting a
winner or calling `RecordingController.start()`. Non-LIVE observations are
`not_applicable`. If the single slot is unavailable because of manual capture,
startup recovery, finalization, failure/blocked state, or shutdown, a LIVE is
`skipped` with `recording_slot_unavailable`; it is never queued.

Missing `output_directory` produces `blocked/output_directory_unconfigured` but
does not prevent service startup or read-only monitoring. Admission checks free
space at the configured directory or its nearest existing parent without
creating directories. Failure to inspect storage is
`blocked/storage_unavailable`; fewer than `10 * 1024**3` free bytes is
`blocked/low_free_space`. This built-in floor applies only to future unattended
recording, never manual local/remote starts, recovery, or finalization.

With storage available, admission reuses the creator/local-time
`creator-YYYYMMDD-HHMMSS.mp4` convention and bounded `-2` through `-1000`
collision search. Both output and matching `.parts` paths must be unoccupied;
inspection failure is storage unavailable and exhaustion is
`output_name_unavailable`. A `ready` result may expose those candidate local
paths plus observed/required free bytes because the authenticated recording API
already exposes local paths. Candidate allocation creates no file, directory,
lock, reservation, or persisted decision. The automation coordinator allocates
again immediately before starting, and controller collision checks remain
authoritative. Fixed reasons prevent exception text or signed transport from
reaching status.

### tikrec/automation.py — automatic selection and durable re-arm

`AutomationCoordinator` consumes only published complete-cycle snapshots and
makes at most one start attempt per cycle. It reapplies admission immediately
before start, chooses simultaneous ready creators by canonical-handle lexical
order, and does not try a second creator after synchronous rejection. Manual,
recovery, finalization, blocked, and shutdown ownership continues to win through
the admission view and the controller's authoritative lock/collision checks.

The selected start carries the monitor's canonical room ID through the internal
controller guard described above and never enables raw copy. Acceptance consumes
that creator/room even if capture later fails. The same room remains suppressed
through completion, failure, manual stop, and process restart; explicit offline
re-arms it, unknown does not, and a different canonical room is immediately new.
An existing service job with matching creator and room also consumes it.

`automation_state.py` stores schema-1 consumed creator/room pairs and at most one
pending claim in `automation.json` beside service `job.json`. A claim contains
only canonical creator/room identity and the newly allocated absolute output and
matching parts candidate, plus the prior safe service job ID when one exists. It
is atomically committed before controller start, then cleared on synchronous
rejection or promoted to consumed after acceptance.
Startup promotes a claim whose durable job matches, clears it only when the job
store is idle, and otherwise disables automatic starts as ambiguous. Corrupt or
unwritable state likewise disables automation without deleting evidence or
unnecessarily disabling monitoring/manual service controls. Signed transports,
cookies, credentials, response bodies, and arbitrary exception text are never
persisted.

`automation_status.py` adds fixed JSON-safe top-level operational, cycle,
selection, session, and output facts plus per-creator armed/suppressed/result
facts to the existing monitoring response. Admission fields remain compatible.

### tikrec/service_configuration.py — service startup snapshot

The service snapshots `output_directory`, `monitored_creators`, and the effective
recovery window once at startup. Normal startup validates the complete strict
schema. When the recovery window is explicitly overridden, malformed unrelated
known validation/debug preferences stay lazy, while JSON syntax, duplicate and
unknown fields, schema version, output storage, and monitored creators remain
strict because the running service uses them. Missing output storage is valid.

### tikrec/remote.py and tikrec/control_cli.py — remote client and CLI wiring

`RemoteClient` sends injected/testable standard-library HTTP JSON requests,
refuses redirects and environment proxies, bounds responses, and reports safe
request errors. It never automatically retries an ambiguous start. The CLI
loads `--token-file` or `TIKREC_TOKEN` without printing the value; tokens do not
reach capture or session metadata. Existing local commands are unchanged.

Implementation order for the v0.4 addition: capture_control with LIVE/source
integration, recording controller, service handler, remote client, control_cli
and existing CLI wiring. Each layer has offline tests before the next layer.
Startup resume and interrupted-finalization reconciliation cover the conservative
v0.5 cases above. No job history is added. Windows Task Scheduler launch, rather
than a detached recording subprocess, provides independence from SSH/VS Code in
this release.

## Raw-copy storage

`--raw-copy DIR` is off by default. When enabled, it retains the received bytes
of every direct FLV connection before parsing so source behaviour can be
compared directly with TikREC output. The files are named by the connection
number recorded in `connections.jsonl`. This roughly doubles the session's
disk use. A matching arrival sidecar records the local timing and byte range of
each successful HTTP body read plus the observed read end. Both diagnostics are
best-effort; their failure is a warning, never a capture failure. Arrival logs
add small variable storage and per-read JSON/flush work only when raw copying is
explicitly enabled.

Remote diagnostic capture uses the boolean `remote start --raw-copy` opt-in
rather than accepting an arbitrary diagnostic path. The service co-locates raw
files and arrival sidecars inside the deterministic `<stem>.parts` directory,
persists the opt-in in durable job intent, and passes that same location to a
safe resumed capture. Normal remote starts omit the field and remain unchanged.

## Configuration and recording storage

Schema-1 per-user configuration is strict JSON stored outside the checkout at
`%APPDATA%\TikREC\config.json` on Windows or
`${XDG_CONFIG_HOME:-~/.config}/TikREC/config.json` elsewhere. `--config FILE`,
when placed before the subcommand, selects one deterministic explicit file.
TikREC never scans for alternatives. The schema permits integer
`schema_version: 1`, optional absolute string `output_directory`, and optional
integer `recovery_window_seconds` from 60 through 3600 inclusive, and optional
string `validation_mode` equal to `standard` or `deep`, and optional ordered
string list `monitored_creators`; duplicate,
missing-version, unknown, incorrectly typed, malformed, or unsupported data is an
error. The optional boolean `debug_tracebacks` controls unexpected CLI traceback
output. Explicitly supplying null for `validation_mode` or `debug_tracebacks` is
invalid. Writes use a flushed same-directory temporary and atomic replacement,
with a parent-directory sync on POSIX. Unsetting all optional settings retains a valid
versioned document. This store must never contain TikTok cookies, credentials,
bearer tokens, or signed media URLs.

Each `monitored_creators` entry is a unique lowercase TikTok handle of 1 through
24 ASCII letters, digits, underscores, or internal periods. List order is
preserved deterministically but does not define scheduling priority. TikREC
stores no cookies, credentials, room IDs, media URLs, signed URLs, or other
creator access material in an entry.

`monitor add CREATOR` accepts a bare handle, `@handle`, or exact public
`https://www.tiktok.com/@handle/live` URL, normalizes it without network access,
and rejects duplicates. `monitor remove CREATOR` applies the same normalization
and fails if the creator is absent. `monitor list` preserves configured order and
reports an empty list without creating a missing configuration file. These
commands use the existing atomic configuration replacement and preserve every
v0.8 setting. They do not require `output_directory`, contact TikTok, start
recordings, or perform admission themselves. The separately launched service
snapshots this list and `output_directory` at startup, performs the read-only
polling specified above, evaluates admission for status and completed-cycle
decisions, and owns the automatic coordinator described above.

`config path` does not need to parse the file. `config show [--json]` reports the
path, existence, configured values, and effective values/sources. `config set
output-directory DIRECTORY` resolves a relative CLI value to an absolute path
without creating the recording directory, while `config unset output-directory`
removes only that setting. `config set recovery-window-seconds SECONDS` persists
the bounded integer and its matching `unset` restores the built-in default.
`config set validation-mode standard|deep` persists the standalone validation
default and its matching `unset` restores built-in standard. An explicitly
persisted `standard` remains distinguishable from an absent setting in `show`.
`config set debug-tracebacks true|false` persists the unexpected-error diagnostic
default; its matching `unset` restores built-in false. Persisted false remains
distinguishable from absence. Explicit `--debug`/`--no-debug` overrides it
without reading configuration. With neither flag, the CLI loads this preference
only after an unexpected exception; malformed configuration is then reported
clearly without hiding the original concise unexpected-error line. Normal command
execution, known error handling, help, and version output do not consult this
setting. HTTP request logging remains suppressed because request targets can
contain secrets or signed URLs.
Invalid existing configuration is never silently overwritten by a mutation.

`--output` is optional only for local `live`. When supplied, an absolute path is
authoritative and does not consult the configured output directory. A relative explicit path is
resolved beneath configured `output_directory`, with lexical or resolved escapes
rejected; without the setting it remains relative to the process working
directory. Advanced local `record` still requires explicit output and never
derives names from direct or signed media URLs.

When local `live` omits output, a configured `output_directory` is mandatory.
The CLI validates the supplied public TikTok LIVE-page URL locally, uses only its
creator segment, strips `@`, percent-decodes that segment, replaces non-portable
characters with `-`, collapses separator runs, trims unsafe boundary characters,
and bounds the result to 64 characters. Empty or nonstandard identities fail
before capture or network resolution. Query strings, fragments, credentials,
tokens, signed URLs, and other path segments never enter the filename.

The default is `creator-YYYYMMDD-HHMMSS.mp4`, using local system time with
one-second precision and an injectable clock for deterministic tests. Both it
and the matching `.parts` path are direct children of the configured directory.
If either candidate exists, including as a symlink, suffixes `-2` through `-1000`
are checked deterministically; exhaustion fails without deleting or reusing any
artifact. Capture's existing session/output checks add another refusal layer
before session creation and finalization. Explicit output is never renamed by
this logic.

Remote start still requires and preserves an absolute .mp4 path on the service
machine. Manual `finalize --output`, guided recovery stored paths, service state,
and existing retained sessions do not consult automatic naming or the unattended
10 GiB admission floor. No customizable filename template exists yet. Admission
may report a candidate but does not reserve it or imply automatic recording.

Local `live` and `serve` resolve the recovery window as CLI override, then
configuration, then the built-in 900 seconds. An explicit override avoids reading
configuration solely for retry policy; output-path resolution may still require
it independently. `serve` snapshots the effective policy at process startup and
must be restarted after configuration changes. The same selected `RetryPolicy`
governs active media recovery and startup reconciliation. Direct `record`, remote
start, and the HTTP start body do not expose this option. Schema 1 remains
compatible because the new field is optional and old documents retain 900.

Recordings should normally use a dedicated directory outside a source checkout.
During development in this repository, `runs/` is the conventional local
destination; the repository ignores `runs/`, `*.parts/`, common recorded-media
extensions, and partial outputs. The `*.parts/` rule covers `session.json` and
`connections.jsonl` inside deterministic session directories.

TikREC does not warn merely because an output is inside a Git working tree. A
checkout may intentionally contain an ignored recording directory, and Git
repository detection is not evidence of a capture error. The command instead
honors the explicit path while this repository's ignore rules prevent its normal
artifacts from being staged accidentally. User-selected raw-copy directories
outside ignored paths remain the user's storage responsibility.

### tikrec/recovery_discovery.py - guided recovery discovery

The first v0.7 slice adds `tikrec recover ROOT` as a read-only classification
step. Because TikREC has no global recording root, callers must name one parts
directory or a bounded recording root; only immediate `*.parts` children are
considered and discovery never recurses. The classifier reuses schema-1 manifest,
contiguous completed-part/framing, connection-log, declared-output, and completed-
output media invariants. It reports safe stored identity only: source type and
canonical room ID where present, never a guessed creator or signed transport URL.

Completed output, safely repeatable manual finalization, possibly active work,
and incomplete/conflicting evidence are distinct results. A recording/finalizing
state is never presumed stale. Writer/encoder partials, missing or malformed
manifests, path/count/log conflicts, symlinks, output-state contradictions, and
evidence that changes during inspection remain untouched and receive no recovery
action. The command does not run FFmpeg, decode every retained part, modify a
manifest, resume capture, repair media, or perform finalization. Structured JSON
contains the same facts as the plain-language report. The validation and explicit
single-session finalization slices build on this conservative discovery boundary.

The second v0.7 slice adds optional `--validate` without changing that discovery
boundary. Only `recoverable` and `complete` candidates with consistent evidence
are passed as their parts-directory/session target to the existing standard
`validate_target` implementation. Active/uncertain and needs-attention candidates
are skipped before FFprobe. Results distinguish requested, ran, passed, failed,
and skipped; retain the validator's media/session/output summaries; and include
at most five error-first findings plus an omitted count. Failed or skipped
candidates make validation mode exit nonzero, while no candidates is a successful
bounded scan. Validation exceptions become redacted fail-closed findings. Plain
discovery retains its prior output/JSON shape and performs no validation. Neither
mode persists validation history or invokes finalization.
Recovery validation always passes `deep=False` and does not consult the standalone
`validation_mode` preference, even when that preference is `deep`.

The third v0.7 slice adds explicit `tikrec recover PARTS_DIRECTORY --finalize`.
`--finalize` implies standard validation and is accepted only when the named
scope itself is exactly one consistently classified `recoverable` session. A
parent root is refused even when it currently contains only one candidate, so
the command cannot become accidental batch recovery. Active/uncertain sessions,
conflicting evidence, missing declared output, an existing output, an encoder
partial, a missing output parent, or symlinked session/output paths are refused
without mutation.

Guided finalization snapshots the manifest and immediate artifact metadata before
validation, then rediscovers and compares the session immediately before its
first write. It uses the declared output path, existing `finalize_parts`
implementation, overwrite/temporary-output protections, and schema-1
`mark_recovery`/`finish_recovery` transitions rather than a second finalizer or
manifest schema. Running, completed, failed, and interrupted attempts retain the
existing recovery fields and safe errors. Success requires a regular non-empty
output plus a passing standard validation of the updated session. Failures and
interruptions retain all FLV parts; no writer repair, capture resume, deletion,
or recursive scanning is performed. Plain and JSON output report the guided
outcome. Manual `tikrec finalize PARTS_DIRECTORY --output FILE` remains unchanged.
Both guided pre-finalization and post-finalization checks remain standard and do
not inherit the standalone validation preference.

## Testing

Unit tests run offline with no network and no live stream. Network
behaviour is tested through injected functions.

Media correctness is not provable by unit tests alone. Any change touching
codec configuration, part boundaries, or finalization must also be checked
against a real recording with the per-part validator:

    tikrec validate PARTS_DIRECTORY

It checks decoder output and the stored packet timestamps separately.

## Validation notes

Validate each retained FLV part in two independent ways:

1. Decode it with `ffprobe -show_frames`, with frame output discarded and
   decoder errors captured. A non-zero exit or decoder error output fails the
   part.
2. Read stored packet DTS with `ffprobe -show_packets` and verify that DTS is
   strictly increasing within each stream. Missing, malformed, or duplicate
   DTS fails the part. A decreasing DTS is reported with its packet position
   and magnitude as a warning because it is known TikTok source behaviour.

`tikrec validate` performs both checks and includes their collected findings in
the validation report. `scripts/validate_parts.py` remains a thin wrapper for
older developer workflows.

Do not use `ffmpeg -f null -` as a corruption check. Its null-output timestamp
path can resynthesize FLV integer-millisecond timestamps onto a coarser frame
time base, producing non-monotonic-DTS warnings even when the stored DTS is
strictly increasing. These warnings can occur on individual FLV parts as well
as on concatenated output.

The four-part `vibecrewkrista` recording validated this distinction on
2026-09-19. Every retained FLV passed full decoding and per-stream stored-DTS
checks, and the 604,991,710-byte stream-copy MP4 passed deep decoding plus a
separate strict packet-DTS check. During muxing, FFmpeg corrected two video DTS
values at the part-0002 to part-0003 concat boundary (`49321296` and `49359744`
after previous `49369008/49369009`). Part 0003 itself starts at nonzero video/audio
timestamps of 3.003/6.108 seconds. The completed MP4 stores the corrected boundary
as strictly increasing DTS `49369008`, `49369009`, `49369010` on its 1/16000 video
time base and decodes cleanly. The messages therefore describe valid concat/muxer
timestamp correction around unusual retained source timing, not media corruption
or a TikREC finalization defect.

TikTok H.264 can also make FFmpeg repeatedly print `Late SEI is not implemented`
during decoding or re-encoding. FFmpeg's H.264 decoder deliberately skips SEI
NAL units that arrive after picture setup; the message describes unsupported
handling of that supplemental metadata, not a TikREC-generated A/V error. Late
SEI ordering can still be a source-stream quirk or standards violation, and the
skipped SEI may contain ancillary metadata, so investigate only if it coincides
with a decoder failure or missing required metadata. By itself, it does not
invalidate otherwise cleanly decoded TikTok media. During finalization TikREC
shows the notice once and suppresses repeats from terminal progress while
retaining FFmpeg's original stderr for a finalization failure. See
[FFmpeg change `f7dd408d`](https://ffmpeg.org/pipermail/ffmpeg-cvslog/2022-July/133020.html),
“avcodec/h264dec: Skip late SEI.”

The AAC configuration bug found on 2026-09-09 was different: it caused genuine
AAC decoder failures and is still detected by the first check. That distinction
is why the old null-output command appeared to be a useful validation check.

The six-part reconnect recording validated on 2026-09-10 ran for about
20 minutes. All packets were present and ordered, A/V was within 21 ms at
the investigated boundaries, and finalization added 267 ms of duration drift.

The 78-minute reconnect-4 recording validated on 2026-09-10 had one
connection, 14 parts, and ended with Ctrl-C. Its 4,703.083 s wall-clock
duration exceeded the 4,702.768 s media span by 315 ms. The 13 inter-part
gaps totalled 474 ms (7--142 ms each; 36 ms mean), consistent with the
33 ms video cadence.

`keyframe_gate_duration` was zero for every part: each configuration,
first-media, and first-keyframe timestamp was identical at every configuration
roll. TikTok therefore emits the new AVC configuration with an IDR keyframe,
and the gate discarded no tags. In part 0001 the configuration timestamp was
zero while media began at 1,710,552 ms, confirming the zero-stamped-header
quirk and the decision to measure the gate from first media instead. This also
rules out gate cost as the explanation for reconnect-2 connection 2's 7.65 s
loss; its `IncompleteRead` indicates a stalled socket tail before the error.

The interrupted recording investigated in issue #5 also contained source
timestamp replays: a zero-timestamped script tag preceded backward audio and
video DTS jumps. Parts retain every tag in such a replay; timestamp alone is
not enough to infer that TikTok intended content to be discarded. Each
completed replay is recorded in its part's `timestamp_replays` entry in
`connections.jsonl`, with the one-based retained-tag position, prior and new
timestamps, magnitude, number of replayed tags, and whether the prior point was
passed before part close. Live progress warns that the affected part may not
validate. The validator warns, rather than fails, for the backward DTS itself.

Deep validation later found genuine H.264 decoder errors around two replay
intervals in `part-0005.flv`; the four timestamp-replay records represented
overlapping audio and video jumps at those two locations. Errors were confined
to 218.831--222.221 seconds and 229.419--229.939 seconds rather than spread
through the roughly 231-second part. Removing every backward-clock audio and
video tag until each stream passed its previous timestamp did not repair the
part: both decoder-error clusters remained. Frames after the removed ranges can
still depend on reference state established inside them, so dropping only the
detected replay is neither lossless nor sufficient.

A second experiment split a temporary copy at both replay starts, initialized
each new part with the cached codec configuration, and began each replay part
at its H.264 IDR frame. The pre-replay part decoded cleanly, but each freshly
initialized replay part retained its corresponding decoder-error cluster.
Rolling a part at the backward jump therefore does not repair this recording,
and duplicate frames entering one continuous decoder session are not a
sufficient explanation. Without a simultaneous raw copy, the evidence cannot
distinguish malformed CDN bytes from corruption introduced while parsing or
writing them.

The 2026-09-21 Promi raw-copy validation supplied a complete comparison but no
timestamp replay. Its raw source and retained FLV both contain zero replay
events. From the first retained media tag onward, all 158,062 payloads, tag
types, and ordering are identical; timestamps differ only by the writer's
2,572,297-unit base subtraction, and the raw AVC/AAC configuration payloads are
the retained configurations. Four H.264 decoder failures reproduce in the raw
source at the exact corresponding payload hashes and at timestamps 2,572.297
seconds above the retained timeline. TikREC therefore did not introduce this
separate non-replay malformed media. The source's final incomplete tag produces
additional raw-only tail errors and is correctly absent from the retained FLV.
This proves that upstream corruption can occur without a replay, but it does not
answer the replay-specific source-attribution question, which remains open.

The completed Luhpol raw-copy validation added 303,564 complete source tags
across three media connections, two natural network recoveries, and 22 retained
parts without a source or retained timestamp replay. Full retained validation
found one H.264 decoder error in part 22, but the untouched connection-3 raw file
emits the same error. All 924 retained tags from that part's first keyframe match
the raw payloads, types, and order exactly; timestamps differ only by the expected
9,364,937-unit part rebase. The finalized MP4 deep-validates. Together Promi and
Luhpol cover 461,629 complete raw tags and independently establish upstream
malformed H.264 without a TikREC writer divergence.

No replay-with-raw-copy sample has occurred, so the historical replay-specific
source-attribution question remains unresolved. Under the rare-evidence rule it
is now non-blocking and opportunistic: current evidence demonstrates no active
TikREC replay-corruption defect, and requiring a random replay as a release gate
would not be proportionate to the residual uncertainty. The writer's
independently-decodable-part guarantee remains qualified across a future replay;
retaining replayed tags preserves evidence rather than claiming repair. A
retained-only replay, any raw-versus-retained payload/order divergence, or a
reproducible decoder failure absent from matching raw media must restore the
investigation as a correctness blocker before replay handling changes.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the dependency-ordered release plan. Features
listed there are unavailable until their release is implemented; that does not
make deferred product capabilities permanently prohibited. The
architecture describes the released v0.8.0 package.

## Design principles

- Small modules. Generic FLV logic stays generic.
- One connection is `source`. Resolution is `tiktok`. Reconnect sits above
  both, in orchestration.
- The writer owns what "independently decodable part" means.
- The finalizer owns joining. It never destroys its inputs.
- Never silently overwrite user output.
