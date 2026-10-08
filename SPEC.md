# TikREC — a recorder for public TikTok LIVE streams

## v0.11.0 published storage scope

Current released version: [**TikREC v0.11.0**](https://github.com/lvrdnck/TikREC/releases/tag/v0.11.0), annotated tag `ef8c5215712d454855a033700116bdc8fc0906a3` at exact approved `2fe6354aa508d53ce3a3452ce08743d97400fe73`; verified [wheel](https://github.com/lvrdnck/TikREC/releases/download/v0.11.0/tikrec-0.11.0-py3-none-any.whl). Publication completed under [owner authorization](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6059131758). [Execution and artifact verification](V0_11_RELEASE_PUBLICATION.md). Historical candidate/preparation statements below describe earlier checkpoints.

The published feature set is storage-only: automatic-admission space checks, conservative planning and one exact-confirmation Windows deletion with age unset/disabled. Later #30/#48/#52 features are excluded. The owner's newer development installation is separate and unchanged; its executable/package metadata is not bumped or installed here. #52 R18–R19 pilot corrections are delivered for PM review under [6060507133](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6060507133); #48 stays OPEN/PAUSED, #51 CLOSED/PASSED, #28 unresolved. [Experimental pilot](ISSUE_52_PILOT.md); B3 and separate natural-LIVE authorization remain outstanding. No default activation, migration, production restart or automatic successor follows publication.


## Experimental pilot capture envelope

The explicit foreground pilot accepts provable positive AVC dimensions with long
edge <=1920 and short edge <=1080, independent of orientation; malformed and
out-of-envelope metadata refuse. No geometry transformation or rendition choice
is introduced. It inherits the existing three-check, 5-second offline confirmation
and 1-second base backoff. Its intentional duration/byte/connection cutoffs remain
interrupted outcomes. [Runbook and corrected evidence](ISSUE_52_PILOT.md).

## Current manifest-completion boundary — 2026-10-06

[PM decision 6012406322](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6012406322) accepts `0ca6144a` publication
and authorizes this single internal slice; earlier accepted foundations remain accepted.
The isolated internal #52 path now completes a schema-1 manifest only after fresh
same-owner publication/output/control proof. Journal schema 8 appends exact
predecessor/successor and observed installation evidence; all original H/input
facts and accounting/pins remain retained. Public CLI/service defaults remain
unchanged. [Contract and limits](ISSUE_52_MANIFEST_COMPLETION.md).

## Historical accepted guarded-publication contract — 2026-10-06

[PM decision 6010639470](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6010639470)
accepts `1e1e1cae` candidate validation, preserving accepted R1–R10/assembly.
The [publication contract/evidence](ISSUE_52_GUARDED_PUBLICATION.md) connects the
original one-shot coordinator and continuously protected candidate to its exact
claimed MP4 destination. Original acquisition narrowly adds candidate DELETE
rights; only publication-capable validation uses read-only inherited seekable
stdin. Assembly-only/validation-only defaults and arbitrary-launch refusal remain.
Schema **7** appends immutable preparation and separate observed-result evidence;
schemas **1–6 are refused/preserved unchanged**, no migration/cutover. Preparation
is not completion; native root-relative no-replace rename has no reopen/replay.
The exact local scratch-to-output successor retains all ownership. Original
assembly/candidate/validation evidence, pending manifests, accounting/claims/pins
and synchronous CLI/service defaults remain. No settlement/refund, retry/adoption,
service/production integration or release. #52 OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED;
#28 unresolved. Earlier checkpoints below are historical within their limits.

## Historical accepted issue #52 internal candidate-validation checkpoint (2026-10-05)

[PM decision 6000035417](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6000035417) accepts `ee884bdc` connected assembly. The new
[validation contract/evidence](ISSUE_52_CANDIDATE_VALIDATION.md) retains original same-attempt scratch/native/input ownership through
three fixed contained media validators and an append-only validation receipt.
The immutable candidate stays `not_checked / unpublished`; separate validation
does not publish, settle/refund, release units/raw/room/path claims or pins, or
authorize retry/adoption. Current isolated journal schema is **6**; schemas 1–5
remain refused/preserved without migration. Media manifest/connection schemas
remain 1, including intentional `finalization: pending`. Applicable candidate
inspection/decode/DTS checks do not use pending publication as a failure reason.
CLI/service behavior remains synchronous and unchanged. No service/API/monitor/
scheduler integration, production access/change/restart or cutover is included.
Full service gates remain outstanding; PM review is next.

## Historical isolated capture handoff boundary (2026-10-04)

[Review 5971119601](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5971119601)
accepted `a96bd6e9` and R1–R3, then approved capture-side integration only.
The [isolated bridge](ISSUE_52_CAPTURE_HANDOFF.md) now reuses real LIVE/writer/raw/
manifest/connection code, verifies native Windows closure and durably transfers
responsibility before journal-backed capture reuse. The finalizer stays unstarted.
Journal schema **3** adds pinned/counted admitted-empty evidence; schemas 1 and 2
are refused/preserved without migration. Media manifest/connection schemas remain 1.

Internal source-ended results preserve requested output and `finalization: pending`;
they never claim MP4 completion. Immutable pending markers bind H to the known
catalog/session/generation/operation/seal. Failed or ambiguous closure remains held.
Production CLI/service defaults and current slot lifecycle remain synchronous;
no production journal, marker, worker, API, cutover or retention change is included.
#52 stays OPEN/SINGLE ACTIVE, #48 OPEN/PAUSED and #28 unresolved. Full service
[A1–A20 gates](ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md) remain outstanding.

## Current implementation goal

Windows is the sole active and planned recording/service runtime under the
owner's 2026-10-01 platform decision. The unreleased Fedora/Linux managed-storage
and Btrfs detour is removed; #53/#54 are superseded with no pending Fedora gate.
Existing portable helpers retain their pre-detour behavior. Windows retention
and lifecycle code matches `0cc59bac`. The public retention CLI independent
review gate and Windows real-media validation are **PASSED**. The project manager
completed #51 on 2026-10-01 after its one ordinary Eliss deletion returned
COMPLETE/0 with exact durable audit and immediate scope verification. The later
Gracie move was an unrelated owner-initiated, hash-checked Drive workflow after
completion and scope proof; the size-only `Unsorted` API discrepancy establishes
no content mutation or retention involvement. No production defect is demonstrated.
Age is restored to its original unset state and the one-deletion authorization
is consumed. All evidence exclusions remain; #51 authorizes no further destructive
validation, retry, repair or second deletion. v0.11.0 is the current published storage
version at its separate approved commit; this development branch is unchanged.
See [ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).

Record public TikTok LIVE streams to disk reliably and completely. Local commands
remain one recording per invocation; the persistent service has a fixed two-job
bound for explicit or opt-in monitored creators. Each stops independently when
its stream ends or when the owner targets it.

## Scope

### Current

- Public LIVE streams only
- Recording a stream from the moment I start the tool
- Reconnecting within a recording when the connection drops
- Up to two independent recordings owned by one persistent service
- An opt-in ordered configuration list of canonical public creator handles
- Read-only service polling with conservative in-memory LIVE observations
- Non-mutating unattended-admission status for detected configured LIVEs
- Capacity-aware durable room-bound automatic starts after a completed cycle

TikREC v0.5.0 established service startup reconciliation, v0.6.0 added evidence-
based reconnect-gap measurement while removing only the fixed healthy-close
wait, v0.7.0 added guided interrupted-session recovery, and v0.8.0 added the
per-user configuration/default behavior documented below. Package version
v0.9.0 added opt-in creator monitoring and durable single-slot automatic starts.
Released v0.10.0 has a two-recording service. A deployed manual second start
passed simultaneous isolation, targeted stops, dual media validation, and idle
restart. Independent reviews found LIVE and pending output/parts ownership
gaps; their corrections passed a final readiness review.
The exact candidate commit was independently reviewed before publication.
Published release records are in PROJECT_STATE.md.
Issue #27 closed after input decode health was preserved; historical Moe source
attribution is non-blocking #28. See [ISSUE_27_FORENSICS.md](ISSUE_27_FORENSICS.md).

### Not implemented yet

- Subscriber-only, private, or otherwise gated streams
- Authentication and session management
- Redundant same-LIVE capture
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
    tikrec monitor raw-copy enable CREATOR
    tikrec monitor raw-copy disable CREATOR
    tikrec monitor raw-copy list
    tikrec monitor remove CREATOR
    tikrec monitor list
    tikrec serve [--host IP] [--port PORT] [--token-file FILE] [--recovery-window-seconds SECONDS]
    tikrec remote health --server URL [--token-file FILE]
    tikrec remote status --server URL [--token-file FILE] [--session-id UUID]
    tikrec remote recordings --server URL [--token-file FILE]
    tikrec remote monitor-status --server URL [--token-file FILE]
    tikrec remote start --server URL PUBLIC_LIVE_URL --output ABSOLUTE_PC_MP4_PATH [--raw-copy] [--token-file FILE]
    tikrec remote stop --server URL [--session-id UUID] [--token-file FILE]
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
prints JSON from health/status/recordings/monitor-status/start/stop. Start/stop
acknowledge asynchronously; responses reporting a failed job and request
failures exit 1. The service can own two active recordings, each with separate
durable intent for startup reconciliation. See
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
Successful re-encoding also classifies recognized H.264 input-decoder errors
into a bounded allowlist of codes and count (capped at 10,000), without saving
stderr, addresses, URLs, or message text. This evidence is `clean` when no
recognized error occurs and `degraded` otherwise, without changing successful
capture/finalization lifecycle. Stream copy records `not_checked`; custom
finalizers without diagnostics record `unknown`. Late-SEI metadata notices
alone do not degrade the result.

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
It stops at the first incomplete tag or framing error and accepts only the
previous parser-proven complete-tag boundary; it never scans forward or repairs
the bad tag. A first/early failure without valid media still blocks. Recovery
intent is persisted before the exact original is atomically moved to a
deterministic evidence-only name. A new copy contains either all bytes or only
that complete prefix and must pass writer
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

The validator reports retained-part media checks, recorded finalization input decode,
final-output inspection, deep output decode, and unproven visual integrity as
separate fields. `not_checked` means that check did not run; old schema-1
manifests without input-decoder evidence report `unknown`. The legacy
`media_integrity` JSON field remains an aggregate checked-media result. A clean
final output cannot override retained-part failure. Therefore an interrupted,
failed, or recording session can pass when its retained parts are healthy even
though no completed output exists.
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

### tikrec/recording_manager.py — bounded service ownership (v0.10 slice 1)

`RecordingManager` owns the built-in capacity of two independent controllers.
Its lock atomically selects a healthy slot for each API or automation start and
rejects active cross-slot output/parts collisions and duplicate normalized LIVE
pages. Page ownership compares creator handle spelling case-insensitively for
both readable current status and session-bound in-memory fallback, including
mixed-case source URLs loaded from durable jobs. Accepted source URLs retain
their spelling. Each controller provides a locked snapshot of only current
session/page/proven-room and accepted local output/parts paths. The manager
refreshes its session-bound cache within allocation, including restored owners
and manual rooms proven later; partial reads retain known facts. Accepted
paths are owned before storage exists. If current identity or required path
ownership remains unknown, allocation fails closed. On an unreadable first
observation, ambiguous recovery health and a failed health read do not prove
emptiness. An invalid current snapshot stays unknown even after an earlier
available-health read. A narrow
`current=false` snapshot can prove an isolated corrupt slot has no current
session, so the other
slot remains usable; recovered reads restore ordinary capacity. An automatic
expected room is also reserved in memory for the current session before its
worker publishes proven room identity; another
current slot cannot claim the same room. A settled or reused session releases its
reservation, and an unreadable status cannot prove release. Neither an unproven
room nor the manager cache is persisted.
Workers, stop Events, durable stores, recovery, byte/reconnect progress, results,
and finalization never cross
slot boundaries. A blocked or recovering slot is unavailable without hiding the
other slot's capacity. Shutdown first closes the manager to new starts, signals
both controllers concurrently, and joins both finalizers.

Stable `slot-1`/`slot-2` identities are service-local; canonical session UUIDs
remain the recording control identity. Aggregate health/status exposes capacity,
active count, available slots, and sanitized per-slot facts. Singular status or
empty stop refuses ambiguity when multiple slots own current work. Explicit stop
validates a session UUID and delegates only to its current owner.

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
or ${XDG_STATE_HOME:-~/.local/state}/TikREC/job.json. The second service slot uses
the deterministic sibling `job-2.json`; missing second-slot state is idle, so
legacy v0.9 state needs no migration. Each controller loads and reconciles only
its store. A malformed store blocks only that slot and remains untouched; two
interrupted stores claiming the same path fail the second closed before recovery.
No state-path CLI option is added. Only the latest job per slot is stored, with
one owning service process/account. This development branch package remains v0.10.0. Current published storage
version is v0.11.0 at the separate approved release commit.

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
in progress. All v0.5 real deployment-validation phases are complete. The
current package version is 0.10.0.

### tikrec/service.py — narrow HTTP adapter

`RecordingHTTPServer` uses the standard-library `ThreadingHTTPServer` with a
custom handler for GET health/recording/recordings/monitoring and POST
recording/start/stop only. Handlers validate bounded JSON and delegate to the
manager. No file serving,
commands, executable paths, accounts, or browser UI. Default `127.0.0.1:8765`;
explicit remote IPs require a token checked in constant time. Raw request logs
and browser-origin requests are disabled; read timeouts bound stalled clients.
This service is for trusted LAN/Tailscale use, not public internet hosting.

### tikrec/monitoring.py — read-only creator observation

`CreatorMonitor` receives the initial ordered creator tuple selected at startup.
In unreleased #30 development, the `serve` CLI also supplies a narrow creator
loader bound to that selected configuration path. Before every cycle it reads
one committed document through `ConfigurationStore.load(missing_ok=False)`,
strictly validates it and returns only `monitored_creators`. A vanished document
cannot silently clear a running list. Invalid/unreadable replacements preserve
the last good tuple; a later valid document is adopted normally. Only creators
are applied, never the output root, reserve, recovery policy or other settings.

One worker starts promptly and remains available even when the configured list
is empty, resolving creators sequentially and waiting 30 seconds after each
completed cycle. Without a loader, explicitly injected static monitors retain
their previous empty-list/no-worker behavior. Reload replaces creator tuple and
observation map together under the snapshot lock; changed lists start with fresh
pending observations. A cycle lock spans reload, observations and the completed
automation callback, preventing overlapping cycles or mixed-list arbitration.
Changes published during that span are adopted on the next cycle. Removal does
not stop active recordings, alter durable jobs or erase consumed-room history.

Each observation is `pending`, `live`, `offline`, or `unknown`. Only
`TikTokOfflineError` proves `offline`; transient transport errors, permanent or
malformed public responses, access restrictions, missing identity, unexpected
failures, and non-structured resolver results remain `unknown` under fixed safe
categories. Positive LIVE results retain only canonical public `room_id`.
Signed transport URLs and arbitrary exception text are discarded immediately.
Reload status adds a fixed `configuration` object to configured monitor snapshots:
`state: ok, reason: null`, or `state: unavailable, reason: configuration_unavailable`.
It contains no raw error text or local paths; a valid read clears the diagnostic.
Config I/O occurs outside the snapshot lock, keeping status and stop responsive.
Shutdown during a read prevents adopting its returned list; shutdown during the
last observation also prevents publishing a completed automatic-start cycle.
Snapshots and cycle timing are protected by a lock, remain memory-only, reset on
restart, and never extend job/session/connection schemas. After publishing a
complete cycle, the monitor invokes one injected notification outside its lock;
partial shutdown cycles never notify. The monitor itself neither consults nor
mutates `RecordingController`. Service shutdown first prevents later automatic
starts, requests monitor stop, shuts down recording, and joins the monitor after
its current bounded resolver call.

### tikrec/admission.py — unattended-recording admission

`RecordingAdmission` is composed by the service but remains separate from the
resolver worker. On each monitoring-status request it evaluates current manager
capacity and storage state for every observation without selecting a winner or
starting a recording. Non-LIVE observations are `not_applicable`. If no slot is
available because of manual capture, startup recovery, finalization,
failure/blocked state, or shutdown, a LIVE is `skipped` with
`recording_slot_unavailable`; it is never queued.

Missing `output_directory` produces `blocked/output_directory_unconfigured` but
does not prevent service startup or read-only monitoring. Admission checks free
space at the configured directory or its nearest existing parent without
creating directories. Failure to inspect storage is
`blocked/storage_unavailable`; fewer than the configured reserve (10 GiB by
default) is `blocked/low_free_space`. This floor applies only to future unattended
recording, never manual local/remote starts, recovery, or finalization.
The read-only storage policy also supplies authenticated `/health` with free,
minimum, and warning byte thresholds and one of `ok`, `warning`, `blocked`,
`unconfigured`, or `unavailable`. Warning starts below the greater of 20 GiB
and twice the minimum; it does not block automatic admission. The minimum is
an optional strict schema-1 integer `minimum_free_space_gib` from 1 to 1024.

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
sequentially attempts ready creators in canonical-handle lexical order until
freshly checked capacity is exhausted, at the global bound of two. It reapplies
admission, free-space checks, and collision-safe allocation immediately before
every start. A duplicate-current-LIVE rejection clears its pending claim without
consuming the room and continues to later eligible creators in the same cycle.
Other synchronous rejections conservatively stop remaining attempts.
Manual, recovery, finalization, blocked, and shutdown ownership wins
through the admission view and the manager/controller authoritative locks.

The selected start carries the monitor's canonical room ID through the internal
controller guard described above. Raw copy defaults OFF; unreleased #48 selects
it from the startup snapshot of `automatic_raw_copy_creators` and passes an
explicit boolean into the existing accepted start/job path. Acceptance consumes
that creator/room even if capture later fails. The same room remains suppressed
through completion, failure, manual stop, and process restart; explicit offline
re-arms it, unknown does not, and a different canonical room is immediately new.
An existing service job with matching creator and room also consumes it.

`automation_state.py` stores schema-1 consumed creator/room pairs and at most one
pending claim in `automation.json` beside service `job.json`. Starts remain
sequential, so that single pending claim is sufficient. A claim contains
only canonical creator/room identity and the newly allocated absolute output and
matching parts candidate, plus the prior safe service job ID when one exists. It
is atomically committed before controller start, then cleared on synchronous
rejection or promoted to consumed after acceptance.
Startup inspects both current jobs: any exact durable match promotes the claim;
the selected slot's unchanged prior session or continued idle state proves an
unaccepted claim; any other result disables automatic starts as ambiguous.
Current jobs are also all inspected to suppress a duplicate when a manual job
already owns the observed creator/room. Corrupt or unwritable state likewise
disables automation without deleting evidence or unnecessarily disabling
monitoring/manual service controls. Signed transports,
cookies, credentials, response bodies, and arbitrary exception text are never
persisted.

`automation_status.py` adds fixed JSON-safe top-level operational/cycle facts,
ordered selected creators, an accepted-recording array, and per-creator armed/
suppressed/result facts. Legacy singular selection/session/output fields are
populated only when exactly one result makes them truthful. Admission fields
remain compatible.

### tikrec/service_configuration.py — service startup snapshot

The service snapshots `output_directory`, the initial `monitored_creators`,
`automatic_raw_copy_creators` (unreleased #48), and the effective
recovery window once at startup. Only the creator list subsequently reloads in
unreleased #30 development, through the cycle-boundary contract above. Other
startup settings remain fixed; existing dynamic retention semantics are unchanged.
Normal startup validates the complete strict
schema. When the recovery window is explicitly overridden, malformed unrelated
known validation/debug preferences stay lazy, while JSON syntax, duplicate and
unknown fields, schema version, output storage, monitored creators, and automatic
raw-copy preferences remain
strict because the running service uses them. Missing output storage is valid.

### tikrec/remote.py and tikrec/control_cli.py — remote client and CLI wiring

`RemoteClient` sends injected/testable standard-library HTTP JSON requests,
refuses redirects and environment proxies, bounds responses, and reports safe
request errors. Optional `RemoteClient.status(session_id)` / `remote status
--session-id UUID` requires `durable_finalization_v1`, then addresses only
that original UUID. Older servers explicitly report unsupported lookup; no latest
slot is substituted. The separately constructed default-OFF isolated HTTP backend
and durable completion semantics are documented in
[ISSUE_52_HTTP_CLIENT.md](ISSUE_52_HTTP_CLIENT.md) and [SERVICE.md](SERVICE.md).
`remote recordings` reads aggregate status and
`remote stop --session-id UUID` targets one current session; legacy singular
status/stop are preserved only where unambiguous. It never automatically retries
an ambiguous start. The CLI
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

Automatic diagnostic capture (unreleased #48) uses a strict optional schema-1
`automatic_raw_copy_creators` ordered list of unique canonical handles. Missing
or empty is OFF; null, non-list, duplicate or noncanonical entries fail loading.
CLI enable/disable/list commands normalize the existing creator input forms and
use locked atomic updates. Preferences are independent of monitoring and survive
removal/re-addition. The startup snapshot governs future accepted automatic
starts only; #30 reloads no raw policy. The durable job flag governs continuation
and recovery despite later policy changes. Evidence stays in the normal matching
`.parts` through existing capture code. Capacity, expected-room guards, consumed
room/rearm, admission, shutdown and manual-start contracts are unchanged.
Owner-authorized deployed policy activation passed with only `gracie.kf` opted
in, Ward OFF, and the monitored tuple unchanged. Natural automatic Gracie raw /
arrival / connection evidence remains outstanding; no further owner action is
pending. Deployment and safe read-only resume: ISSUE_48_DEPLOYED_VALIDATION.md.

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
string `validation_mode` equal to `standard` or `deep`, optional ordered
string list `monitored_creators`, and optional integer
`minimum_free_space_gib` from 1 through 1024, optional ordered
`retention_protected_creators` with canonical unique handles, and optional
integer `retention_max_age_days` from 1 through 3650. Duplicate fields,
missing-version, unknown, incorrectly typed, malformed, or unsupported data is an
error. The optional boolean `debug_tracebacks` controls unexpected CLI traceback
output. Explicitly supplying null for `validation_mode`, `debug_tracebacks`, or
`minimum_free_space_gib`, or `retention_max_age_days` is
invalid. Writes use a flushed same-directory temporary and atomic replacement,
with a parent-directory sync on POSIX. Unsetting all optional settings retains a valid
versioned document. This store must never contain TikTok cookies, credentials,
bearer tokens, or signed media URLs.

Configuration promotion and the internal retention executor's final removal
share a per-configuration OS lock in a persistent sibling
`.CONFIG_FILENAME.retention-policy.lock`. Windows uses a byte-range lock and
POSIX uses `flock`; both are released on process exit. General saves participate,
and the config, monitoring, and protection CLI commands reload and apply their
specific change inside the same transaction so stale reads cannot revert newer
protection. Ordinary configuration reads remain unlocked. Canonical parent,
Windows case, and existing 8.3 filename aliases share authority; retention
refuses a redirected configuration file. The lock covers the final policy/job
recheck and handle removal, not planning or media hashing. An update already
committed blocks old-policy removal; an update racing an already-held removal
boundary waits until that step finishes. Once it applies, every later removal
must recheck the updated policy. Direct external edits do not participate in this
cooperative protocol.

In published v0.11.0 storage scope, `retention protect/unprotect/protected` manages
the independent ordered protection list. `retention plan [ROOT] [--json]` inspects
only immediate `.parts` children of an explicit or configured output directory.
It is read-only and uses durable `ended_at`, never file mtime, for the optional
age threshold (`ended_at <= now - days * 86400`). Only a supported completed
TikTok session with canonical creator, completed finalization, proven regular
output directly beside its `.parts` directory, stable known evidence, and an
unprotected creator can be `eligible`. Unknown, changing, extra, symlinked,
recoverable, and conflicting evidence is not eligible. The local Windows-only
`retention delete SESSION_UUID [ROOT] [--confirm SESSION_UUID]` workflow and
expanded advisory plan are specified in [RETENTION_CLI.md](RETENTION_CLI.md).
They are included in published v0.11.0; no automatic cleanup
exists. Viewing a plan cannot authorize deletion.

The internal retention executor accepts one explicit root and canonical session
UUID, never a saved planner result. Under the owner-approved issue #37 platform
scope, destructive execution is Windows-only. POSIX refuses before creating a
lifecycle lock or audit, or changing any recording artifact; advisory planning
and historical schema-1 journal reading remain supported. POSIX `unlinkat`
still resolves a final filename and cannot provide exact-object removal against
private-name substitution through the available unprivileged interface. There
is no pathname-deletion fallback.
On Windows it takes an exclusive OS-backed root lease,
reloads current configuration, replans the full root, and refuses any target
referenced by either durable service job slot, including a completed job. The
planner's coherent whole-root claim snapshot must still match when authorization
captures artifacts. The same planner runs again after artifact binding, and both
the decision, claim snapshot, and first-pass file byte digests must still match
before audit intent. Destructive planning captures stable byte digests around
media inspection; authorization independently hashes every allowlisted file.
The public read-only planner does not perform this additional full-file hashing.
It reports only stable, singly linked regular-file counts and sizes from
no-follow local-volume observations; unsafe or incomplete inventories remain
unknown rather than zero. The local delete preview does perform full-file
binding and the same fresh authorization checks without holding an exclusive
lease while waiting for confirmation. After confirmation, the executor repeats
authorization under its exclusive lease and compares root identity, all session
claims, policy, and exact artifact identities/bytes against that preview as a
veto only. First-use lifecycle-lock creation may change the root directory
timestamp without changing those claims or root identity.
The private authorization binds root/claim identity, creator and durable end
time, policy, local volume, every file's byte hash, writer-recovery evidence and
referenced-part byte hashes, and exact singly linked artifact fingerprints.
Before each mutation it checks the lease, current policy and job stores,
non-target claims, every still-present authorized file against its bound bytes,
remaining/removed artifacts, and no-follow identity/locality. A referenced
part remains byte-bound even after its writer-recovery evidence file has been
intentionally removed.
It removes retained media and referenced recovery evidence first, then the
connection log, manifest, empty `.parts` directory, and final MP4 last.
Each artifact is opened with Windows read/delete access, no sharing, and
no-follow/reparse inspection. Held identity must match the authorized file or
directory before it can move. `FileRenameInfo` on that handle moves it to the
audited same-directory sibling with `ReplaceIfExists=FALSE`; occupancy is
refused atomically, including a collision after the preliminary check and a
case alias. The exclusive handle prevents source/private-name substitution
through proof and removal. File bytes are hashed through that same held handle.
After the synchronized policy/job/lease recheck, `FileDispositionInfo` marks
that exact object for deletion and closes the handle; no pathname unlink or
rmdir follows. The kernel refuses a nonempty directory even if a child appears
after proof. Sharing conflicts, unsupported filesystem operations, reparse
objects, identity/byte changes, or path reappearance stop the operation. An
unexpected occupant is never cleaned up. Failed proof leaves the original or
quarantined object for inspection, and final MP4 removal remains last.
Preexisting hard links refuse eligibility before audit intent. A deliberately
concurrent external hard-link creation after the final held-identity check can
preserve an alias when the private name is disposed; this is outside the
cooperative-filesystem threat model. Native review covered fixed-drive NTFS,
not every Windows filesystem, and did not test power loss.
Unexpected evidence or failure stops immediately. A later call cannot resume
the stale operation; it must pass fresh authorization, which normally refuses
an incomplete session.

An append-only schema-1 JSONL journal lives beneath the per-user TikREC state
directory's `retention-audit` folder, in a deterministic per-root file. A
synced intent containing the exact order/fingerprints, every file's byte hash,
writer-recovery byte hashes, and deterministic quarantine names precedes all
deletion; synced attempt, deleted,
failed, and completed records
follow. On POSIX, audit ancestors are synced root-to-leaf on every attempt;
each new directory entry is synced before creating its child, and the journal
entry is synced before use. This also covers a visible entry left by a failed
prior sync.
Older POSIX execution synced removals before deleted records; new POSIX
execution is refused. Existing
audit history is checked for complete schema-1 JSONL framing, unique JSON
fields and operation IDs, event-specific fields, this journal's canonical root,
the child/control/directory/final-MP4 destructive order, paired recovery evidence
and parts, platform-correct path spelling, and coherent intent/
attempt/deleted/failed/completed transitions. A later intent permanently freezes
any earlier incomplete operation. A valid intent-only,
unmatched-attempt, or other coherent event-boundary crash tail remains readable
without repair or automatic resume. Malformed or contradictory history blocks
deletion. The journal excludes transport secrets and signed URLs. Issue #35
corrected the plan-to-authorization and audit-history gaps found at `3ff83bc`.
A fresh independent review of `ef8d01b` passed the Windows-only private
executor gate under this cooperative-filesystem boundary. The published local
CLI exposes one explicit Windows-only session deletion through the private
executor; [RETENTION_CLI.md](RETENTION_CLI.md) specifies its confirmation,
status, audit, and exit contract.
Root-level persistent lifecycle locks use
POSIX shared/exclusive `flock` or Windows bounded byte-range leases; process exit
releases a held lock. All TikREC mutators of a recording root take writer leases
while the retention executor takes the exclusive lease. The protocol excludes
TikREC's own writers,
not an arbitrary hostile process deliberately defeating filesystem metadata
guarantees. The executor and its local CLI caller are included in published v0.11.0.
An `attempt` without `deleted` can mean no rename, a preserved quarantine, or
actual removal before the result could be journaled. Process death before
setting disposition leaves the quarantine; death after setting it closes the
handle and may complete removal. `failed` can likewise follow actual removal,
including a failed result write/sync; the existing same-path `deleted` then
`failed` history remains valid. No earlier operation resumes, and no incomplete
operation is reported as completed. Schema 1 and deterministic quarantine names
remain sufficient for audit plus filesystem reconstruction. Native process-exit
tests do not establish Windows power-loss durability; no power-loss claim is made.
Independent review at `d20ed7a` found that ordinary FLV parts and the final
MP4 are only metadata-bound after the closing planner pass; same-size Windows
byte changes with restored metadata can invalidate eligibility without
stopping deletion. The final path check also leaves a check-to-unlink
replacement window. At that reviewed commit, audit validation could reject a
POSIX journal written by the executor for a legal literal-backslash filename
and accept unpaired writer-recovery evidence names. Issue #36 corrected those
gaps; its later review at `5d27dc8` found private-name and policy-revocation
races. Issue #37 supplies the Windows handle protocol and policy synchronization,
with owner-approved POSIX refusal. The fresh independent `ef8d01b` review
passed the private executor gate on native NTFS and WSL POSIX refusal/history;
owner-facing retention execution is now implemented locally on Windows in
published v0.11.0 storage scope; its contract is in
[RETENTION_CLI.md](RETENTION_CLI.md).
The fresh independent public CLI review at `f99528f` found a terminal-output
result-reporting blocker (#40): an output exception or interruption after the
executor returned could label an audited, completed deletion `PARTIAL`/exit 3.
The correction keeps exit 0 once the executor returns and makes a bounded
diagnostic attempt with the output cause and operation context. The NEW fresh
review at `653f5fe` found a narrower successful-intent-`fsync` to progress
callback interruption window and an unhandled broken-stderr path for
after-intent failure reporting (#41). The correction marks intent sync in
progress after the complete write and before the syscall. Faults in that
boundary report `FAILED`/3 with explicit durability uncertainty; faults before
sync retain pre-intent results. Best-effort diagnostics preserve the known exit
result when stderr fails. A NEW independent public CLI review remains required;
no real-media retention deletion has been performed.
That new review at `cc0824d` found a completion-to-return result gap (#42):
an audit close failure or interruption after synced `completed` reports
`PARTIAL`/3 even though the operation is proven complete. The public CLI gate
is NOT READY pending #42 correction and another fresh review. No real media
was deleted in this review.
Issue #42 now publishes proven `completed` sync in caller-owned progress before
audit/lifecycle cleanup. A later cleanup fault retains `COMPLETE`/0 with a
bounded best-effort diagnostic; failed or interrupted completion sync remains
non-complete/3. A NEW independent public CLI review is still required before
real-media retention validation.
The fresh review at `b8ad110` found an after-intent failure-reporting blocker
(#43): a cleanup fault can mask the original execution cause, and a post-intent
`SystemExit` can escape without the required incomplete-result context. The
public CLI gate is NOT READY pending #43 correction and another independent
review. Only disposable synthetic media was used.
Issue #43 now retains the first after-intent operation fault before audit or
lifecycle cleanup and reports any later cleanup fault as secondary when a
diagnostic channel works. Relevant post-intent `BaseException` faults, including
`SystemExit`, produce incomplete exit 3 with operation context. Pre-intent
refusal/interruption and proven completion keep their existing results. A NEW
independent public CLI review remains required before separately authorized
real-media retention validation; v0.11 is unreleased.
The fresh review at `3850d8c` found a post-completion reporting blocker (#44):
after synced `completed`, a later audit/lifecycle cleanup error can mask the
first post-completion interruption or cleanup error. The result stays
`COMPLETE`/0 with operation context, but the original cause is lost. Issue #44
now captures that first fault before later cleanup and reports secondary cleanup
faults separately when diagnostics work. Broken diagnostics cannot change
`COMPLETE`/0. The public CLI gate remains NOT READY pending a NEW independent
review; only disposable synthetic media was used.
The NEW independent public CLI review at `1b38b65` found that a held-artifact
cleanup fault can mask the first post-intent proof/removal failure before
executor progress or the `failed` audit event captures it (#45). The exit
stays incomplete/3 with operation context, but the cause is wrong. The
public CLI gate remains NOT READY pending the bounded #45 correction and
another NEW review before separately authorized real-media validation.
No production code or real media was changed in this review.
Issue #45 now captures the first inner mutation or handle-entry fault before
held-handle or policy cleanup can replace it. The `failed` event retains the
original type, and the public incomplete result retains its cause; later
inner cleanup errors are secondary diagnostics. The public CLI gate remains
NOT READY pending a NEW fresh-context independent review before separately
authorized real-media validation. No real media was deleted.

The NEW independent public CLI review at 2ccf464 found a remaining nested
policy-lock cleanup fault-precedence gap (#46). A first descriptor-close
fault can be replaced by a later condition-notification fault before the
inner mutation boundary captures it; the public PARTIAL/3 reason and durable
failed.error_type then name the wrong cause. An earlier audit cleanup fault
can also be omitted from secondary diagnostics when lifecycle cleanup fails
afterward. The public CLI gate is NOT READY pending #46 correction and
another NEW fresh-context review before separately authorized real-media
validation. No production code or real media was changed in this review.

Issue #46 now preserves the first body or policy-lock cleanup fault at its
origin, before later close/owner/notification faults can replace it. The
first known fault remains the public incomplete reason and the type in a
persisted failed event; later inner cleanup faults are separate diagnostics
in occurrence order. Before completion, audit cleanup is also retained as
secondary evidence when lifecycle cleanup fails later. These reporting
changes do not reauthorize, retry, resume, repair, or add any deletion.
The public CLI gate remains NOT READY pending a NEW fresh-context independent
review before separately authorized real-media retention validation.
No real media was deleted.

The NEW independent review at `75ffb1d` found a remaining audit/lifecycle
teardown fault-precedence and ownership gap (#47). An audit-entry cleanup
fault can replace a first pre-intent validation failure and escape as
`SystemExit` instead of `REFUSED`/1. Lifecycle handle close can replace an
earlier unlock fault; after synced completion `COMPLETE`/0 remains truthful,
but the first diagnostic cause is lost and the in-process registry remains
occupied. Combined mutation faults still preserved the first operation cause
and persisted `failed.error_type`. The public CLI gate is NOT READY pending
#47 correction and another NEW fresh-context review before separately
authorized real-media retention validation. No production code or real media
was changed in this review.

Issue #47 now preserves a first audit-entry or lifecycle teardown fault before
later close faults. It attempts the remaining cleanup actions once and releases
the in-process lifecycle registry and writer slot even when unlock or close
fails. Acquisition rollback also removes partly registered ownership. True
pre-intent refusal/interruption, incomplete uncertainty, and proven completion
retain their established results. The public CLI gate remains NOT READY until
a separate NEW fresh-context independent review passes before separately
authorized real-media validation. No real media was deleted.
The NEW independent review at `72996a7` found a remaining pre-intent public
result gap (#50): a first `SystemExit` from preview stdout or audit-entry
validation escapes instead of reporting `REFUSED`/1, even when later cleanup
faults leave the first cause intact. The gate remains NOT READY pending #50
and another NEW independent review before separately authorized real-media
validation. No production code or real media changed in this review.
Issue #50 now classifies a first pre-intent `SystemExit` as `REFUSED`/1 with
its cause, selected UUID, absolute root, and no-operation notice. Later
audit/lifecycle cleanup faults stay secondary and broken diagnostics do not
change that exit. The public CLI gate remains NOT READY pending a NEW
independent review before separately authorized real-media validation.
No real media was deleted in this correction.
The NEW independent public CLI review of `f3dd917` found no blocker after
corrections #39–#50. Six fresh disposable Windows fault probes passed alongside
native Windows retention/lifecycle/policy/audit, the isolated full offline
suite, and applicable WSL/POSIX read-only/refusal/audit-history coverage. The
public retention CLI gate is PASSED. No real-media deletion occurred in that
review. The later Windows real-media validation #51 is now PASSED under the
2026-10-01 project-manager decision, after reconciliation of the unrelated Gracie
move. Its single authorization is consumed and age is restored to unset; no
further destructive validation is authorized by #51. v0.11 remains unreleased.

Retention planning first discovers safely readable immediate UUID/output claims,
including claims from protected, incomplete, or otherwise rejected sessions.
Unreadable or ambiguous immediate claims prevent a uniqueness proof for the
selected root. Eligibility additionally requires coherent completed capture and
finalization fields, finite consistent elapsed time, and no durable connection,
room-status, resume, service/network, or writer-recovery activity after the
terminal timestamp. `recovery_performed=true` alone is not a contradiction.
The selected local root, `.parts` child, controls, final output, every retained
FLV and writer-recovery evidence must contain no symlink or Windows reparse
redirection and must share a proven local volume. A saved optional LIVE creator is checked
again at fresh resume preflight before any write; legacy absence stays absent.
Planner output is advisory and may become stale. Any future destructive action
needs immediate revalidation and separate approval.

The planner binds each parsed manifest and connection-log read to the exact
control-content fingerprint in an immutable claim snapshot; an observed mismatch
fails closed even if the file later returns to its original contents. It
distinguishes
an explicit null output declaration from a missing or unreadable field. It
compares whole-root snapshots before and after inspection: immediate child
membership, small control-file content identity, artifact metadata, output
identity, and creator/lifecycle changes must remain stable. A changing root
cannot yield eligible sessions.
Each individual root capture also brackets its claim reads with root/child
identity and membership checks. Its closing root identity is read only after
the entire closing child enumeration and child identity scan finish; an
unreadable or unstable capture cannot yield eligibility.
An observed control or evidence mismatch invalidates every candidate in that
planning call even if a later read sees the original bytes again.
`resolver_error` at any connection position can carry only resolver-failure
evidence, with no resolved identity, opened HTTP source, media, or part claim.
Output claims use case-folded in-root names and
available device/inode facts; symlink/reparse aliases, multiply linked outputs,
and unprovable physical ownership fail closed. Roots require local storage
evidence (Windows fixed drive type or known local Linux/macOS filesystem type);
remote, unsupported, and unknown mounts are refused. Retention-only chronology
checks session, numbered-connection, media-milestone, resume, room-status,
service-recovery, network-outage, and writer-recovery timing. The narrow
pre-manifest first-LIVE-resolution exception requires explicit resolution
evidence. Earlier resolver-only failures may precede manifest creation, and the
first successful resolution may cross it, but HTTP opening and media milestones
must follow session initialization. Malformed or stacked mount evidence and a
nested remote/unknown artifact cannot establish eligibility. These checks do
not tighten ordinary schema-1 loading/recovery.
Linux locality additionally requires a coherent visible mount parent chain and
matching artifact device identity where the platform provides it; a lexical
local child hidden under a remote overmount is unproven.

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
retaining a bounded stderr excerpt only for a finalization failure. It does not
enter successful-finalization degraded-health evidence. See
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
make deferred product capabilities permanently prohibited. The architecture
describes released v0.10.0 on current `main` and preserves v0.9.0 boundaries
where historical scope matters. Deployed two-slot isolation, implementation
readiness, and exact-release-commit review passed before publication.

## Design principles

### Proposed #52 capture availability correction (not implemented)

The owner's 2026-10-03 priority correction supersedes the priority-only next task.
Current service capture and finalization remain synchronous: finalizing occupies
a slot and page ownership, so even a free second slot cannot admit that creator's
proven different room. Offline characterization demonstrates the mechanism and
later-cycle retry; it does not attribute a missed production LIVE.

Review proposal: two capture slots plus one tracked Windows-local finalizer,
durable per-session handoff/queue, separate LIVE/artifact claims, guarded restart/
publication, raw/retention preservation, bounded backlog/disk refusal, controlled
shutdown and explicit status compatibility. No codec/quality/timing, runtime,
API/schema or production configuration change is made by the design task.
The design and unexecuted implementation acceptance matrix are in
[ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md](ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md).

### Current principles

- Small modules. Generic FLV logic stays generic.
- One connection is `source`. Resolution is `tiktok`. Reconnect sits above
  both, in orchestration.
- The writer owns what "independently decodable part" means.
- The finalizer owns joining. It never destroys its inputs.
- Never silently overwrite user output.
