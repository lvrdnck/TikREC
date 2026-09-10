# TikREC — a recorder for public TikTok LIVE streams

## Goal

Record a single public TikTok LIVE stream to disk, reliably and completely,
from a URL supplied manually. Stop when the stream ends or when I stop it.

## Scope

In scope:
- Public LIVE streams only
- Recording a stream from the moment I start the tool
- Reconnecting within a recording when the connection drops

Out of scope, deliberately:
- Subscriber-only, private, or otherwise gated streams
- Auth, CAPTCHA, or private request-signing bypass
- Watching a handle and starting automatically
- Predicting when someone will go live
- Transcription, chapters, search, analytics
- Any feature whose purpose is tracking a person rather than
  capturing a stream I chose to record

Some rooms that are visibly live return room-info status code `4003110` and
expose no stream URLs to anonymous page or API requests, while other public
rooms resolve normally. This is TikTok making a session-dependent access
decision, not an offline status. A normal browser User-Agent and Referer were
tested and did not change the response. Recording those rooms would require
authenticating as the user, which is out of scope.

The tool must never wait for a stream to begin. If the room is offline
when invoked, that is an error, not a wait state.

## Commands

    tikrec record <direct-flv-url> --output FILE [--raw-copy DIR]
    tikrec resolve <tiktok-live-page-url>
    tikrec live <tiktok-live-page-url> --output FILE [--raw-copy DIR]
    tikrec finalize PARTS_DIRECTORY --output FILE

`record` takes a direct FLV URL and is the generic path. It must stay
source-agnostic and must not gain TikTok-specific behaviour. Its optional
`--raw-copy DIR` stores the unmodified connection bytes before FLV parsing.
`finalize` stitches a retained parts directory after an interrupted or failed
run. It uses the same finalizer as capture, never changes the parts, and
refuses to overwrite an existing destination.

Exit codes: 0 success, 1 capture or finalization error, 130 interrupted.

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
`iter_tags`, `iter_url_chunks`, `iter_url_tags`, `RawCopy`.

Parses incrementally, never buffers the whole stream. Validates the FLV
header and initial PreviousTagSize. No retries, no TikTok-specific logic.
This is the primitive for exactly one direct FLV connection. When requested,
`RawCopy` tees each received byte chunk to `connection-NNNN.raw` before the
parser consumes it. A raw-copy open, write, or close failure warns and disables
only the copy; capture continues.

### tikrec/finalize.py — stitching
`finalize_parts(parts, output_path, *, ffmpeg, runner)`.

Identical configurations across parts: concat demuxer with `-c copy`.
Differing configurations: filter_complex, reset timestamps, scale and pad
to a common size, re-encode.

Writes a hidden temporary file preserving the output suffix
(`.final.partial.mp4`, not `.final.mp4.partial` — ffmpeg infers the muxer
from the extension). Promotes with `os.replace`. Refuses to overwrite an
existing destination. Never deletes the source parts.

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

### tikrec/live.py — reconnect-capable public LIVE capture
`capture_live(url, *, parts_directory, output_path, ...)` implements the
`tikrec live` path above the generic source, writer, and finalizer layers.

It resolves, connects, records, then re-resolves after every connection
close so that each retry uses a fresh signed CDN URL. It stops when the
room-info response confirms that the room is offline.

- Every reconnect creates a new writer and starts a new part, even when the
  AVC and AAC configurations are identical. A new HTTP connection may reset
  timestamps, so continuing the preceding writer state could create backward
  or zero timestamps.
- Only `TikTokOfflineError`, raised from a successful room-info response
  whose room status is not `2`, means offline. Resolver network, timeout,
  and HTTP failures are transient and retry with backoff.
- Room offline at the first resolve is an error. Room offline after retained
  media is a normal end and triggers optional finalization.
- Part numbering carries forward through the writer's explicit `start_index`;
  it is never inferred by scanning the parts directory.
- As each connection closes, `connections.jsonl` receives and flushes one
  record with wall-clock start/end, its preceding gap, retained part range,
  outcome, error, and optional raw-copy filename. `CaptureResult.connections`
  exposes the same records.
- Defaults stop capture after three consecutive transient failures or three
  consecutive connections retaining no media. Both limits, the clock, and
  sleeper are injectable for offline tests.
- Programming errors, invalid arguments, and malformed FLV data do not retry.
  The first Ctrl-C closes the writer and finalizes retained parts when an
  output was requested, but still exits 130 because capture ended early. A
  second Ctrl-C during finalization terminates FFmpeg; all retained parts
  survive either path.

## Raw-copy storage

`--raw-copy DIR` is off by default. When enabled, it retains the received bytes
of every direct FLV connection before parsing so source behaviour can be
compared directly with TikREC output. The files are named by the connection
number recorded in `connections.jsonl`. This roughly doubles the session's
disk use. A copy failure is a warning, never a capture failure.

## Testing

Unit tests run offline with no network and no live stream. Network
behaviour is tested through injected functions.

Media correctness is not provable by unit tests alone. Any change touching
codec configuration, part boundaries, or finalization must also be checked
against a real recording with the per-part validator:

    python3 scripts/validate_parts.py PARTS_DIRECTORY

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

`scripts/validate_parts.py` performs both checks and prints the available
per-part timing metadata from `connections.jsonl`.

Do not use `ffmpeg -f null -` as a corruption check. Its null-output timestamp
path can resynthesize FLV integer-millisecond timestamps onto a coarser frame
time base, producing non-monotonic-DTS warnings even when the stored DTS is
strictly increasing. These warnings can occur on individual FLV parts as well
as on concatenated output.

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

The interrupted recording investigated in issue #5 also contained a source
timestamp replay: a zero-timestamped script tag preceded a backward video DTS
jump. Parts retain every tag in such a replay; timestamp alone is not enough
to infer that TikTok intended content to be discarded. Each completed replay
is recorded in its part's `timestamp_replays` entry in `connections.jsonl`,
with the one-based retained-tag position, prior and new timestamps, magnitude,
number of replayed tags, and whether the prior point was passed before part
close. Live progress reports the same event. The validator warns, rather than
fails, for backward DTS with its per-stream packet position and magnitude.
Revisit handling only if this source behaviour becomes frequent.

## Roadmap

Not yet scheduled, in rough order:

- Reconnect smoke tests against a real LIVE, including FFmpeg decode checks
- Real multi-configuration capture, verifying each part decodes alone
- Richer session manifest: codecs, reconnect summary, and final status
- Health checks: ffprobe validation, duration sanity, timestamp anomalies
- Logging with a debug mode; never log signed CDN URLs at normal verbosity
- Local library for browsing recordings, stored outside /tmp

## Design principles

- Small modules. Generic FLV logic stays generic.
- One connection is `source`. Resolution is `tiktok`. Reconnect sits above
  both, in orchestration.
- The writer owns what "independently decodable part" means.
- The finalizer owns joining. It never destroys its inputs.
- Never silently overwrite user output.
