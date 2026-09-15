# TikREC roadmap

## Long-term direction

TikREC starts as a reliability-first recorder for a single, manually selected
TikTok LIVE. The longer-term direction is to preserve enough trustworthy
metadata and event context to validate, recover, organize, search, and analyze
recordings, then expose those capabilities through local and remote interfaces.

That growth must not weaken the project's core boundaries. TikREC will not
bypass authentication, CAPTCHA, access controls, or private request signing.
Private/gated access, future-start monitoring, and schedule prediction remain
outside the current plan. Features
should support recordings the user chose to make, not covertly track people.

## Release philosophy

TikREC uses small 0.x releases. Each minor release should deliver one meaningful
capability, or a tightly related set, that can be tested and used on its own.
Actual use determines the order: remote recording control comes before
environment survival, gap reduction, guided recovery, and configuration.
Patch releases remain available for focused bug fixes and
reliability improvements between roadmap milestones.

This roadmap is directional rather than a promise of exact scope or dates. It
will evolve when implementation and real recordings reveal new dependencies.

## Completed

### v0.1.0 — Reliable public LIVE recording

The first stable checkpoint established the capture foundation:

- CLI commands to resolve public LIVE pages, record TikTok or direct FLV
  sources, and finalize retained parts.
- Reconnect-capable capture using a freshly resolved signed CDN URL for every
  connection, with bounded retries and conservative room-end confirmation.
- Independently decodable, timestamp-rebased FLV parts that preserve AAC/AVC
  configuration changes and survive errors or interruption.
- MP4 finalization that stream-copies matching parts and re-encodes differing
  video configurations without deleting source parts.
- Durable `connections.jsonl` evidence for connections, room-status checks,
  keyframe gating, and timestamp replays, plus optional byte-exact raw copies.
- Terminal progress, clean interrupt handling, manual retained-part recovery,
  and a standalone FFprobe-based per-part validation tool.
- 123 offline tests in the tagged release, with real-recording validation notes
  retained in `SPEC.md`.

### v0.2.0 — Session metadata and manifest

TikREC now writes an atomically updated `session.json` beside retained parts.
Schema version 1 records a session ID, TikREC version, source type, lifecycle
timestamps, result, paths, part/connection/reconnect counts, interruption and
manual recovery state, finalization result, a redacted failure reason, and
optional FFprobe codec/resolution facts. It complements rather than replaces
`connections.jsonl`. `tikrec --version` reports the package version from the
same source used by packaging.

### v0.3.0 — Recording validation

TikREC now supports `tikrec validate TARGET` for completed outputs, retained
parts directories, and v0.2+ sessions. It reuses the proven decoder and stored
DTS checks, adds stream/container/duration checks, and compares manifests with
actual parts, output, finalization state, and available media metadata. Results
collect concise errors and warnings in human or JSON form while keeping media,
parts, and manifests read-only. Legacy directories remain supported, and
interrupted session completeness is reported separately from media integrity.
An optional deep mode fully decodes the completed output when the additional
time and CPU cost is warranted.

## Current release and planned releases

The priority is to reliably record public LIVE streams on an always-on PC,
control recordings remotely, preserve/finalize media safely, and make failures
recoverable. The proven setup is Mac -> Tailscale -> main-pc -> TikREC service
-> files stored on main-pc. Closing SSH or VS Code must not end a recording.

### v0.4.0 ? Remote service and recording control

**Goal:** Run capture under an independently launched service with one active
recording, health/status/start/graceful-stop HTTP controls, and a small remote
CLI. Reuse the LIVE loop and finalizer through an application layer. Default to
loopback; require a bearer secret for explicit trusted LAN/Tailscale binding.
Document Windows Task Scheduler deployment. No browser UI or crash-resume.

**Implementation:** v0.4.0 adds these controls with offline coverage. Deployment
through Task Scheduler/Tailscale on main-pc has been validated: recording
survived SSH/VS Code disconnection, remote stop finalized successfully, and
retained-session and deep output validation passed.

### v0.5.0 ? Environment survival / resumability

**Goal:** Make service crashes, PC reboots, network loss, and disk/environment
failures recoverable. Establish restart/session reconciliation and explicit
resume policy without overwriting retained evidence or claiming missing media
was captured. An independent service launch in v0.4 solves SSH lifetime only.

**Progress:** Atomic service job intent, canonical public room identity, explicit
session continuation, and service startup reconciliation/controller persistence
are implemented. Startup validates retained storage before new-job acceptance,
resumes only the prior explicitly-started same room, and safely finalizes ended/
offline/different-room or stopped/finalizing sessions when output is absent.
Patient transient DNS/network recovery now uses one shared bounded policy for
active capture and startup identity resolution. Health/status remain responsive,
stop/shutdown wake waits, and meaningful transitions preserve durable intent.
Exhaustion retains unfinalized parts, reports outage_timeout, and releases the
service slot without auto-relaunching the job. Partial/ambiguous output cases remain blocked. This never monitors
an account for its next LIVE. Signed transport stays out of persistence/status.

The suite passes 693 offline tests plus 17 subtests. Real resumed-media and
crash/reboot/outage deployment checks, deeper finalization reconciliation, and
release tagging remain pending. The package remains 0.4.0; v0.5 is not complete.
The next module is deeper finalization reconciliation. Patient recovery uses a
15-minute window and waits of 1, 2, 5, 10, 10, then 30 seconds; normal successful
reconnect-gap measurement and reduction remain v0.6 work.

Implementation order: durable job state, public room identity, retained-session
resume, service startup reconciliation with controller integration, outage retry
policy, recovery status, then release documentation/version.
Each module gets offline tests before the
next begins. Successful reconnect-gap measurement/reduction remains v0.6.

### v0.6.0 ? Reconnect-gap reduction

**Goal:** Use connection milestones and real recordings to reduce avoidable
reconnect gaps. Improve bounded retry/read behavior only with evidence, while
preserving codec configuration, part safety, and conservative room-end checks.

**Diagnostic foundation:** Opt-in raw-copy sessions now preserve local HTTP-read
byte ranges and monotonic timing beside the byte-exact source. This supports
source-versus-writer replay investigation and later gap measurement; it does not
itself reduce reconnect gaps or enable simultaneous capture.

### v0.6.5 — Redundant simultaneous capture (conditional)

**Goal:** Eliminate reconnect gaps by maintaining more than one concurrent
connection to the same LIVE and filling each gap from whichever connection
had coverage.

**Why conditional:** This is only worth building if v0.6 measurement shows
the remaining gap is large enough to justify doubled bandwidth, doubled
disk, and substantially more complex media assembly. If v0.6 reduces the
per-reconnect loss to a second or two, this release should be dropped.

**Hard dependency on issue #8.** Joining two connections means deliberately
splicing two encoder outputs together. That is exactly the operation that
currently produces malformed H.264 at CDN replay boundaries. Building
redundant capture before understanding why a splice fails would make the
core operation of this release the project's one known unsolved defect.

**Likely scope:**
- Two or more concurrent connections per session, independently resolved.
- Alignment on FLV media timestamps, which originate from TikTok's encoder
  and are shared across connections. Wall-clock arrival time is not used;
  no external time source is required or useful.
- Gap filling only at clean random-access points, never mid-GOP.
- Evidence recording which connection supplied each region.
- A validation path proving the joined output decodes across every seam.

**Explicitly not in scope:** better video quality. Concurrent connections
deliver the same rendition TikTok is already serving. Redundancy improves
completeness, not resolution, bitrate, or frame rate.

**Open risks:** TikTok may rate-limit or refuse concurrent connections from
one address; each additional connection is a second chance to hit the
replay defect rather than a mitigation of it.

### v0.7.0 ? Guided interrupted-session recovery

**Goal:** Discover incomplete sessions, validate salvageable parts, guide safe
repeat finalization, and record outcomes. Keep manual `tikrec finalize` available
throughout. Recovery cannot reconstruct media TikTok never delivered.

### v0.8.0 ? Configuration and defaults

**Goal:** Persist proven choices for output locations/naming, retry policy,
validation, and logging with documented discovery and CLI override precedence.
No TikTok credentials or account profiles.

### v0.9+ ? Library, playback, and UI based on proven use

**Goal:** Catalog sessions and artifacts, browse history/health, and provide
playback and eventual UI controls when actual use establishes the requirements.
Build presentation on the existing service boundary; text/analytics artifacts
are optional and are not dependencies for recording control or a library.

## Later / backlog (not current priorities)

These ideas are preserved without promised versions or implementation order:

- **Chat logging:** opt-in timestamped public chat, gifts, joins, LIVE events,
  reconnect evidence, and clear partial-data reporting beside a session.
- **Transcription:** explicit post-processing of recorded audio into timestamped
  transcripts/subtitles with engine provenance and failure reporting.
- **Search:** metadata and available transcript/chat search linked to sessions
  and timestamps, after a useful library exists.
- **Statistics and analytics:** explainable summaries of the user's recordings,
  including duration, reconnect health, event activity, and session comparison.
- **Prediction ideas:** retained for reconsideration only; future-start
  monitoring and schedule prediction are outside the current project scope.
- **Deployment/integrations:** additional headless packaging, exports, storage
  and retention tools, and multi-platform adapters driven by demonstrated use.
- **Authentication/gated-access ideas:** retained as historical possibilities,
  outside the public-only plan; no credentials, private/gated capture, auth,
  CAPTCHA, entitlement, or private-signing bypass is authorized.

## Architectural direction

Evolve separation only when a release needs it; do not scaffold future systems.

- **Capture:** public resolver, one HTTP media source, writer, LIVE orchestration.
- **Processing:** retained-part finalization and read-only validation.
- **Application/service:** one recording job, cooperative lifecycle, safe status.
- **Interfaces:** existing local CLI, narrow HTTP API, remote CLI; eventual UI.
- **Later optional layers:** library, events, transcripts, search, analytics.
