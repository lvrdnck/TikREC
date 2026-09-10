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

The tool must never wait for a stream to begin. If the room is offline
when invoked, that is an error, not a wait state.

## Commands

    tikrec record <direct-flv-url> --output FILE
    tikrec resolve <tiktok-live-page-url>
    tikrec live <tiktok-live-page-url> --output FILE

`record` takes a direct FLV URL and is the generic path. It must stay
source-agnostic and must not gain TikTok-specific behaviour.

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
`iter_tags`, `iter_url_chunks`, `iter_url_tags`.

Parses incrementally, never buffers the whole stream. Validates the FLV
header and initial PreviousTagSize. No retries, no TikTok-specific logic.
This is the primitive for exactly one direct FLV connection.

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
  outcome, and error. `CaptureResult.connections` exposes the same records.
- Defaults stop capture after three consecutive transient failures or three
  consecutive connections retaining no media. Both limits, the clock, and
  sleeper are injectable for offline tests.
- Programming errors, invalid arguments, and malformed FLV data do not retry.
  Ctrl-C closes the writer, preserves completed parts, and exits 130.

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
   strictly increasing within each stream. Missing, malformed, duplicate, or
   decreasing DTS fails the part.

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
