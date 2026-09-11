# TikREC roadmap

## Long-term direction

TikREC starts as a reliability-first recorder for a single, manually selected
TikTok LIVE. The longer-term direction is to preserve enough trustworthy
metadata and event context to validate, recover, organize, search, and analyze
recordings, then expose those capabilities through local and remote interfaces.

That growth must not weaken the project's core boundaries. TikREC will not
bypass authentication, CAPTCHA, access controls, or private request signing.
Any future authenticated capture must use a session supplied by the user and
only access streams that account is legitimately allowed to view. Features
should support recordings the user chose to make, not covertly track people.

## Release philosophy

TikREC uses small 0.x releases. Each minor release should deliver one meaningful
capability, or a tightly related set, that can be tested and used on its own.
Dependencies determine the order: durable metadata precedes integrated
validation, validation precedes recovery, and the local library precedes APIs
and user interfaces. Patch releases remain available for focused bug fixes and
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

## Planned releases

### v0.2.0 — Session metadata and manifest

**Goal:** Give every recording one durable, versioned description of what was
requested, captured, and produced.

**Why now:** Later validation, recovery, and library features need a stable
session record instead of reconstructing state from filenames and event lines.

**Likely scope:** A session identifier and schema version; TikREC version; safe
source identity; start, end, duration, and outcome; connection, reconnect, and
part counts; codecs and resolution; retained parts and output paths; and
finalization/interruption state. Existing `connections.jsonl` remains event
evidence; signed CDN URLs and secrets remain excluded.

### v0.3.0 — Recording validation

**Goal:** Make recording health a first-class session result.

**Why now:** The v0.1 validator proves the checks, while the v0.2 manifest gives
their results a durable home.

**Likely scope:** Integrate per-part decode and stored-DTS checks, validate the
final output, add duration and stream sanity checks, and record a concise health
summary. This release does not repair damaged media.

### v0.4.0 — Interrupted recording recovery

**Goal:** Turn retained capture artifacts into a guided, repeatable recovery
workflow.

**Why now:** Recovery can safely choose inputs only after sessions and their
parts have machine-readable identity and validation results.

**Likely scope:** Discover incomplete sessions, assess salvageable parts, resume
or repeat finalization safely, and update recovery outcomes without overwriting
or deleting evidence. It cannot reconstruct media TikTok never delivered.

### v0.5.0 — Configuration and defaults

**Goal:** Move frequently repeated CLI choices into an explicit user
configuration with predictable overrides.

**Why now:** Stable session, validation, and recovery behavior defines which
settings are worth persisting before more subsystems add their own options.

**Likely scope:** Documented config discovery and precedence for recording
locations, file/session naming, capture retry policy, validation, logging, and
similar safe defaults. TikTok credentials and multi-profile account management
are not part of this release.

### v0.6.0 — Chat logging

**Goal:** Preserve time-aligned public LIVE chat and selected LIVE events beside
the recording.

**Why now:** The manifest can identify event artifacts and configuration can
hold opt-in collection and retention choices.

**Likely scope:** Durable, timestamped messages, gifts, joins, and relevant LIVE
events; connection/reconnect state; and clear partial-data reporting. This
release does not add transcription, search, analytics, or authenticated room
access.

### v0.7.0 — Transcription

**Goal:** Produce a time-aligned transcript from recorded audio.

**Why now:** Validated media, stable session metadata, and configuration provide
the inputs and provenance a transcript needs.

**Likely scope:** An explicit post-processing command or stage, timestamped
machine-readable transcripts and subtitle output such as SRT, failure reporting,
and a documented engine boundary. Library-wide indexing and semantic search
come later.

### v0.8.0 — Local library and history

**Goal:** Make completed and recoverable sessions browsable as a coherent local
collection.

**Why now:** Manifests, health results, chat, and transcripts provide useful
records to catalog rather than merely a directory of media files.

**Likely scope:** Local indexing, session history, filtering, video and raw-part
artifact paths, metadata/chat/transcript/diagnostic links, health summaries, and
safe rebuilds from source manifests. No server or browser UI is required here.

### v0.9.0 — Search

**Goal:** Search the local recording library across session metadata and
available text artifacts.

**Why now:** Search needs the normalized catalog introduced in v0.8 rather than
scanning unrelated files ad hoc.

**Likely scope:** CLI-accessible filtering and text search over metadata,
transcripts, and chat, with results linked back to sessions and timestamps.
Remote search and predictive ranking are excluded.

### v0.10.0 — Server and API mode

**Goal:** Expose recording and library operations through a stable service
boundary.

**Why now:** The API can be designed around proven capture, processing,
library, and search workflows instead of guessing at future domain objects.

**Likely scope:** A reusable application/service layer, local API endpoints for
jobs and session data, progress/status reporting, and controlled capture
lifecycle. This is not yet a Web UI or a hardened VPS deployment.

### v0.11.0 — Web UI

**Goal:** Provide a browser interface for the capabilities already exposed by
the API.

**Why now:** Building on v0.10 keeps presentation separate from capture and
avoids a second private control path.

**Likely scope:** Start/stop controls, recording progress, session history,
health, playback links, and search. Multi-user hosting and TikTok account
management are not part of this release.

### v0.12.0 — VPS and headless operation

**Goal:** Run TikREC unattended on a remote or always-on host.

**Why now:** Headless operation depends on stable service controls and an
interface that does not require terminal access.

**Likely scope:** Service lifecycle, Docker and/or systemd deployment guidance,
persistent paths, logging, disk-pressure safeguards, restart behavior, and
secure remote access. This release does not bypass TikTok access controls or
introduce account auth.

### v0.13.0 — TikTok authentication and session management

**Goal:** Manage a user-provided TikTok session safely and transparently.

**Why now:** Credentials should enter only after headless storage, logging,
configuration, and service boundaries can protect and redact them consistently.

**Likely scope:** Explicit sign-in/session import, secure local storage,
expiration and revocation handling, redaction, and clear active-account state.
Authenticated or gated capture itself remains for v0.14.

### v0.14.0 — Authorized authenticated and gated LIVE capture

**Goal:** Record streams the configured TikTok account is legitimately
authorized to view.

**Why now:** Capture must build on the reviewed session-management boundary,
not mix credential handling into the resolver as an incidental feature.

**Likely scope:** Authenticated resolution and media/event access, permission
errors, and provenance in the session manifest. There will be no CAPTCHA,
subscription, entitlement, access-control, or private-signing bypass.

### v0.15.0 — Activity statistics

**Goal:** Derive transparent summary statistics from the user's own recording
library and captured events.

**Why now:** Useful statistics require a substantial, normalized history and
clear provenance for public and authenticated sessions.

**Likely scope:** Start-time and day-of-week distributions, stream frequency and
duration, gaps between recorded streams, recent schedule changes, reconnect and
health trends, and chat/event activity. Aggregates remain traceable to source
sessions; this is not a general-purpose person-tracking or surveillance system.

### v0.16.0 — Predictions

**Goal:** Offer opt-in estimates based on the user's recorded history, with
uncertainty made explicit.

**Why now:** Prediction is meaningful only after enough reliable historical
data and explainable statistics exist.

**Likely scope:** Probable LIVE time windows, confidence values, schedule trends,
changing activity patterns, evaluation against held-out history, and controls
to disable or delete derived data. Transcript-derived schedule hints can wait;
there is no promise of accurate LIVE schedules and no covert monitoring.

## Beyond v0.16

Possible areas, deliberately not assigned versions, include richer Web UI and
remote management, better exports and integrations, deeper analytics and
session comparison, improved search and transcript/chat presentation, storage
and retention management, multi-platform capture adapters, deployment and
packaging improvements, and continued reliability work driven by long
recordings. These ideas should become releases only when a concrete user need
and their dependencies are understood.

## Architectural direction

The existing modules should evolve only when a release needs the separation;
this is not a request for a speculative reorganization.

- **Capture:** resolver, authentication, media source, recorder.
- **Events:** chat, gifts, joins, LIVE state and events.
- **Processing:** finalization, validation, transcription.
- **Library:** sessions, history, search, statistics.
- **Service/API:** shared interface for the CLI, Web UI, and remote operation.
- **Intelligence:** activity analysis and LIVE predictions.
