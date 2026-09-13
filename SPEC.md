# TikREC — a recorder for public TikTok LIVE streams

## Goal

Record a single public TikTok LIVE stream to disk, reliably and completely,
from a URL supplied manually. Stop when the stream ends or when I stop it.

## Scope

In scope:
- Public LIVE streams only
- Recording a stream from the moment I start the tool
- Reconnecting within a recording when the connection drops
- One recording owned by an independently launched service, controlled remotely

Out of scope for v0.4.x:
- Subscriber-only, private, or otherwise gated streams
- Authentication and session management
- Watching a handle and starting automatically
- Predicting when someone will go live
- Chat collection, transcription, chapters, search, analytics
- A Web UI, multi-user hosting, and automatic crash/reboot resume

Project-wide security and privacy boundaries:
- No auth, CAPTCHA, entitlement, access-control, or private request-signing
  bypass
- No feature whose purpose is covertly tracking a person rather than
  supporting streams and recordings the user legitimately chose to access

Some rooms that are visibly live return room-info status code `4003110` and
expose no stream URLs to anonymous page or API requests, while other public
rooms resolve normally. This is TikTok making a session-dependent access
decision, not an offline status. A normal browser User-Agent and Referer were
tested and did not change the response. Recording those rooms would require
authenticating as the user, which is out of scope for v0.4.x. A future
authenticated mode may use a session explicitly provided by the user, but must
not bypass TikTok's access controls.

The v0.4.x commands never wait for a stream to begin. If the room is offline
when invoked, that is an error, not a wait state.

## Commands

    tikrec record <direct-flv-url> --output FILE [--raw-copy DIR]
    tikrec resolve <tiktok-live-page-url>
    tikrec live <tiktok-live-page-url> --output FILE [--raw-copy DIR]
    tikrec finalize PARTS_DIRECTORY --output FILE
    tikrec validate TARGET [--deep] [--json]
    tikrec serve [--host IP] [--port PORT] [--token-file FILE]
    tikrec remote health --server URL [--token-file FILE]
    tikrec remote status --server URL [--token-file FILE]
    tikrec remote start --server URL PUBLIC_LIVE_URL --output ABSOLUTE_PC_MP4_PATH [--token-file FILE]
    tikrec remote stop --server URL [--token-file FILE]
    tikrec --version

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

Exit codes: 0 success, 1 capture/finalization/validation failure, 2 invalid CLI
usage, 130 interrupted capture.

`serve` runs a loopback-by-default HTTP service. Explicit non-loopback IP binding
requires a bearer secret; all configured-token endpoints check it. `remote`
prints JSON from health/status/start/stop. Start/stop acknowledge asynchronously;
responses reporting a failed job and request failures exit 1. There is one
active recording and only the latest result is held in memory. See
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
parser consumes it. A raw-copy open, write, or close failure warns and disables
only the copy; capture continues.

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
`resolve_live_url(url, *, opener, timeout)` for a public LIVE page.

Finds the room ID from public page state, falls back to the public
api-live user/room lookup. Queries webcast room/info. Live means room
status equals 2. Picks a rendition by deterministic quality preference.
Returns only http(s) URLs ending in `.flv`.

`rtmp_pull_url` may contain an HTTPS FLV URL despite its name, so it is also
considered after `flv_pull_url`; the latter wins equal-quality ties. An actual
`rtmp://` URL is not supported. `hls_pull_url` may also be present, but HLS
capture is not supported.

No cookies, no login, no private signing, no yt-dlp.

### tikrec/capture.py — orchestration
`capture_tags`, `capture_url`, `CaptureResult`, `CaptureError`.

Prepares the session directory once, refuses to reuse an existing one,
preserves completed parts on error or interrupt, finalizes on clean EOF.

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
  whose room status is not `2`, means offline. Resolver network, timeout,
  and HTTP failures are transient and retry with backoff. A live response
  during confirmation cancels the sequence and capture resumes; a later
  non-live response starts a new sequence at one.
- An open CDN response that delivers no bytes for 30 seconds raises
  `SourceStallError`. Live capture records the connection outcome as `stalled`,
  preserves any completed part, and retries it as a transient failure under the
  existing backoff and consecutive-failure limit.
- Room offline at the first resolve is an error. Room offline after retained
  media and successful confirmation is a normal end and triggers optional
  finalization.
- Part numbering carries forward through the writer's explicit `start_index`;
  it is never inferred by scanning the parts directory.
- As each connection closes, `connections.jsonl` receives and flushes one
  record with wall-clock start/end, its preceding gap, retained part range,
  outcome, error, and optional raw-copy filename. `CaptureResult.connections`
  exposes the same connection records. End confirmation also appends and
  flushes one `room_status` event per checked response. Each event contains
  `timestamp`, the raw `status` value, and `confirmation_reached`; a live
  response that cancels confirmation is included as evidence.
- `session.json` is initialized only after resolution creates a real session,
  then its part and connection counts are updated as attempts close. Initial
  offline or unresolved rooms still leave no session directory.
- Defaults stop capture after three consecutive transient failures or three
  consecutive connections retaining no media. Non-live confirmation defaults
  to three checks spaced five seconds apart. All three limits, confirmation
  spacing, the clock, and sleeper are injectable for offline tests.
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

### tikrec/service.py — narrow HTTP adapter

`RecordingHTTPServer` uses the standard-library `ThreadingHTTPServer` with a
custom handler for GET health/recording and POST recording/start/stop only.
Handlers validate bounded JSON and delegate to the controller. No file serving,
commands, executable paths, accounts, or browser UI. Default `127.0.0.1:8765`;
explicit remote IPs require a token checked in constant time. Raw request logs
and browser-origin requests are disabled; read timeouts bound stalled clients.
This service is for trusted LAN/Tailscale use, not public internet hosting.

### tikrec/remote.py and tikrec/control_cli.py — remote client and CLI wiring

`RemoteClient` sends injected/testable standard-library HTTP JSON requests,
refuses redirects and environment proxies, bounds responses, and reports safe
request errors. It never automatically retries an ambiguous start. The CLI
loads `--token-file` or `TIKREC_TOKEN` without printing the value; tokens do not
reach capture or session metadata. Existing local commands are unchanged.

Implementation order for the v0.4 addition: capture_control with LIVE/source
integration, recording controller, service handler, remote client, control_cli
and existing CLI wiring. Each layer has offline tests before the next layer.
Service-crash/reboot recovery, persisted job history, and resume policy remain
v0.5 scope. Windows Task Scheduler launch, rather than a detached recording
subprocess, provides independence from SSH/VS Code in this release.

## Raw-copy storage

`--raw-copy DIR` is off by default. When enabled, it retains the received bytes
of every direct FLV connection before parsing so source behaviour can be
compared directly with TikREC output. The files are named by the connection
number recorded in `connections.jsonl`. This roughly doubles the session's
disk use. A copy failure is a warning, never a capture failure.

## Recording storage

TikREC has no implicit recording root. `--output` is the authoritative path,
and a relative local CLI path is relative to the process working directory.
Remote start requires an absolute .mp4 path on the service machine. Recordings
should normally use a dedicated directory outside a source checkout. During
development in this repository, `runs/` is the conventional local destination;
the repository ignores `runs/`, `*.parts/`, common recorded-media extensions,
and partial outputs. The `*.parts/` rule covers `session.json` and
`connections.jsonl` inside deterministic session directories.

TikREC does not warn merely because an output is inside a Git working tree. A
checkout may intentionally contain an ignored recording directory, and Git
repository detection is not evidence of a capture error. The command instead
honors the explicit path while this repository's ignore rules prevent its normal
artifacts from being staged accidentally. User-selected raw-copy directories
outside ignored paths remain the user's storage responsibility.

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

The writer's independently-decodable-part guarantee does not currently hold
across a timestamp replay. Retaining replayed tags is containment that
preserves evidence for finalization and investigation; the failure is
unresolved, not accepted as valid part output. Raw-copy comparison must decide
whether a lossless writer fix is possible before replay handling changes.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the dependency-ordered release plan. Features
listed there remain out of scope until their release is implemented; the
architecture in this specification describes v0.4.x as it exists today.

## Design principles

- Small modules. Generic FLV logic stays generic.
- One connection is `source`. Resolution is `tiktok`. Reconnect sits above
  both, in orchestration.
- The writer owns what "independently decodable part" means.
- The finalizer owns joining. It never destroys its inputs.
- Never silently overwrite user output.
