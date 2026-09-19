# TikREC roadmap

## Long-term direction

TikREC starts as a reliability-first recorder for a single, manually selected
TikTok LIVE and initially targets a single-owner setup. The longer-term product
direction is a broader livestream recording platform: user-configured creator
automation, concurrent recording, a library, playback, web interfaces, events,
transcripts, search, analytics, integrations, and storage workflows built on
trustworthy capture and recovery evidence. A later public/distributed app is a
possible product stage, not an assumption; it requires separate legal, privacy,
platform-policy, security, and product review before that scope is adopted.

That growth must not weaken the project's core boundaries. TikREC will not
bypass authentication, CAPTCHA, entitlements, access controls, or private request
signing. Any future authenticated mode must use authorization/session material
explicitly supplied by the user and respect platform controls. Automation must
act on creators the user deliberately configured, not enable covert surveillance.

## How to read scope

- **Current:** implemented and supported by the present CLI/service and described
  in README.md and SPEC.md.
- **Planned / future product:** deliberately deferred while reliability work has
  priority, but expected to be reconsidered and rebuilt.
- **Versioned future:** intended product capabilities now have directional
  release slots even when their exact requirements may change before work begins.
- **Conditional candidate:** a version slot may be reserved for a useful idea
  without committing to implementation until earlier evidence justifies it.
- **Permanent boundary:** unsafe or unwanted methods and behavior that TikREC
  must not adopt, regardless of feature sequence.

Deferred does not mean prohibited. The predecessor is a product-capability
reference, not implementation authority; future features should be redesigned
around the new repository's evidence, lifecycle, privacy, and security model.

## Release philosophy

TikREC uses small 0.x releases. Each minor release should deliver one meaningful
capability, or a tightly related set, that can be tested and used on its own.
Actual use determines the order: remote recording control comes before
environment survival, gap reduction, guided recovery, and configuration.
Patch releases remain available for focused bug fixes and
reliability improvements between roadmap milestones.

### Release terminology and completion

The **package version** comes from packaging metadata. A **tagged version** is
an immutable annotated Git tag at a reviewed historical commit. A **GitHub
Release** is the published GitHub release object for that tag. The **current
released version** is the latest version for which those records and the
documentation are synchronized; the **development target** is unfinished work
and is not a release. See AGENTS.md for the mandatory release-completion
checklist.

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
Document Windows Task Scheduler deployment. This release adds neither a browser
UI nor crash-resume.

**Implementation:** v0.4.0 adds these controls with offline coverage. Deployment
through Task Scheduler/Tailscale on main-pc has been validated: recording
survived SSH/VS Code disconnection, remote stop finalized successfully, and
retained-session and deep output validation passed.

**Release record:** package version v0.4.0, annotated `v0.4.0` tag at
`9f8e4104f8bc24f439a3e927ca72da29257c41fa`, and the published GitHub Release
`TikREC v0.4.0` are synchronized. It is a historical released version; v0.5.0 is the current released version.

### v0.5.0 ? Environment survival / resumability

**Goal:** Make service crashes, PC reboots, network loss, and disk/environment
failures recoverable. Establish restart/session reconciliation and explicit
resume policy without overwriting retained evidence or claiming missing media
was captured. An independent service launch in v0.4 solves SSH lifetime only.

**Implementation:** Atomic service job intent, canonical public room identity, explicit
session continuation, and service startup reconciliation/controller persistence
are implemented. Startup validates retained storage before new-job acceptance,
resumes only the prior explicitly-started same room, and safely finalizes ended/
offline/different-room or stopped/finalizing sessions when output is absent.
Patient transient DNS/network recovery now uses one shared bounded policy for
active capture and startup identity resolution. Health/status remain responsive,
stop/shutdown wake waits, and meaningful transitions preserve durable intent.
Exhaustion retains unfinalized parts, reports outage_timeout, and releases the
service slot without auto-relaunching the job. Partial/ambiguous output cases
remain blocked. This startup-recovery path never monitors an account for its
next LIVE. Signed transport stays out of persistence/status. Interrupted FFmpeg
finalization reconciliation is also implemented: a partial is recoverable only
with matching durable finalization-in-progress evidence, is preserved under a
collision-safe evidence name, and all retained parts are re-finalized. Ambiguous
artifacts remain untouched and block automatic recovery.

**Release-readiness evidence:** The 2026-09-15 offline audit found no missing
slice; 707 tests plus 19 subtests pass, and the real-media finalization-recovery
smoke decoded cleanly. The first deployed abrupt-restart test on 2026-09-16 then
exposed issue #14: a normal active `.part-0001.flv.partial` survived the Task
Scheduler stop, but startup recovery classified storage as `ambiguous_state` and
did not resume the still-live same room. The 11,789,861-byte partial ended at a
clean FLV tag boundary and passed decoder/DTS checks, so this is a recovery-policy
gap rather than damaged-media evidence.

**Issue #14 implementation:** Startup-only recovery now requires matching durable
recording intent, manifest identity/lifecycle/paths/counts, safe output state,
canonical next-index ownership, unambiguous regular artifacts, parser-proven FLV
framing, and decoder/DTS validation. It preserves the exact crash file under a
session/index evidence name and publishes a separately copied complete prefix;
an incomplete trailing tag is excluded only from that copy. Optional manifest
evidence records source SHA-256 and original/recovered/discarded byte counts.
Generic completed-part
discovery remains strict. The 728-test plus 19-subtest suite covers clean and torn
tails, interrupted recovery, correct next allocation, and fail-closed conflicts.

**Release-blocking validation:** The repeat abrupt process-death/Task Scheduler
restart passed on 2026-09-19 against `lilymaye207`. Startup preserved the exact
7,874,881-byte crash artifact (SHA-256
`AC27A60670479A99A179AA53CEC838361A2EF85734752FF69EDF480FD0D44CB1`), admitted
the equal complete prefix with zero discarded bytes, retained the same session and
room, and resumed through connection 3 into fresh `part-0002.flv`. The recovered
and first resumed parts passed decoder/DTS checks with independent near-zero media
starts. A later short 640x1280 source-configuration part alone had H.264 decoder
errors between clean 720x1280 parts; its evidence is preserved and no recovery-code
change is justified from that source interval. The real network-outage phase also
passed on 2026-09-19: a loopback proxy interruption held session/room/bytes fixed
in patient recovery, staged retries remained remotely observable, and restoring
the proxy automatically opened a fresh same-room connection and growing next part
without a new start. Closed pre-outage media and actively growing post-reconnect
media passed decoder/DTS checks. The final graceful-stop/retained-session/deep-
output phase then passed on the preserved session: graceful remote stop retained
four coherent parts, closed the recovery episode as an explicit user-stop boundary,
completed finalization, and produced a 1,200.636-second H.264/AAC MP4 that passed
deep validation without findings. All retained FLVs passed decoder/DTS checks,
and their evidence leaves the measured outage absent from captured media.

**Release record:** v0.5.0 package and documentation reflect the completed
environment-survival/resumability work. Annotated tag `v0.5.0` (tag object
`173d25f4736a2b900ffb381d98e218aaae31770c`) peels to release commit
`7e65248bb4061cf74e84986314db0b6b16d5fc02`; the non-draft, non-prerelease
GitHub Release `TikREC v0.5.0` was published on 2026-09-19.

Issues #9 and #8 remain open for rare real stall/replay evidence, and issue #13
is intentionally paused pending an opportunistic distinct-rendition encounter.
Those evidence investigations do not block v0.5 readiness. Patient recovery uses
a 15-minute window and waits of 1, 2, 5, 10, 10, then 30 seconds; successful
reconnect-gap measurement and reduction remain v0.6 work.

Implemented sequence: durable job state, public room identity,
retained-session resume, service startup reconciliation with controller
integration, outage retry policy/recovery status, and interrupted-finalization
reconciliation, and conservative active-writer-partial recovery. Issue #14's
deployed abrupt-restart requirement and the temporary-network-outage validation
are complete; final output validation and v0.5.0 release bookkeeping are also
complete. Successful reconnect-gap measurement/reduction remains v0.6 and must
be selected separately from this completed release.

### v0.6.0 ? Reconnect-gap reduction

**Goal:** Use connection milestones and real recordings to reduce avoidable
reconnect gaps. Improve bounded retry/read behavior only with evidence, while
preserving codec configuration, part safety, and conservative room-end checks.

**Diagnostic foundation:** Opt-in raw-copy sessions now preserve local HTTP-read
byte ranges and monotonic timing beside the byte-exact source. This supports
source-versus-writer replay investigation and later gap measurement; it does not
itself reduce reconnect gaps or enable simultaneous capture.

**Phase 1 baseline (2026-09-19):** A read-only analyzer now derives the full
retained-media gap and its existing milestone components from `connections.jsonl`,
keeps missing values unknown, exposes intervening/coalesced failed attempts, and
separates ordinary reconnects from outage, restart/resume, room-end, and other
recovery boundaries. Six retained real logs yielded one usable ordinary reconnect:
10.883 seconds total, comprising 0.001 seconds of dying tail, 1.004 seconds of
local/backoff time, 7.107 seconds resolving, 2.691 seconds opening HTTP, 0.080
seconds to first parsed media, and less than 0.001 seconds at the write gate.
Resolution and HTTP open dominated this single observation; the fixed healthy-
close wait is visible but is not supported by multiple samples, so production
reconnect behavior remains unchanged. The deliberate v0.5 outage remains separate
at 103.366 seconds. v0.6 remains active: gather multiple ordinary reconnects and
then reassess the healthy-close delay before considering broader policy changes.

**Healthy-close optimization (2026-09-19):** The validated `vibecrewkrista`
session added two suitable ordinary reconnects, bringing the baseline to three
samples across two sessions. Total gap median/range is 3.997/2.515--10.883 seconds;
healthy local/backoff is 1.005/1.004--1.008, resolution is
1.288/1.087--7.107, HTTP setup is 1.410/0.247--2.691, initial media is
0.107/0.080--0.118, and the write gate is 0.001/0.000--0.001. The repeated fixed
wait is TikREC-controlled, so a healthy media-bearing close now proceeds directly
to fresh resolution. Transient/failure backoff, patient recovery, room-end checks,
stop behavior, and fresh writer/URL safety are unchanged. This should reduce each
ordinary gap by about one second; resolution and HTTP setup remain dominant.
v0.6 stays active until a real post-change reconnect verifies the expected gain.

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
This release does not add TikTok credentials or account profiles.

### v0.9.0 — Creator monitoring and automatic recording

**Goal:** Let the owner explicitly configure public creators to monitor. Detect
when those creators go LIVE, start recording automatically, finish safely, and
re-arm for the creator's next LIVE, with manual overrides.

This is the first release aimed directly at the "record it while I am asleep or
away" use case. Initial automation may still be limited by the service's current
single-active-recording model; overlapping monitored LIVEs must have explicit,
honest behavior rather than silently pretending both were captured.

Because unattended recording can consume disk without the owner present, this
release must include a basic free-space safety floor and must fail safely when
storage is insufficient. Full retention policy belongs to v0.11.

This is opt-in creator automation, not covert monitoring, and it does not change
the current one-shot recording or same-room crash-resume semantics.

### v0.10.0 — Multiple simultaneous creator recordings

**Goal:** Record independent LIVEs for multiple configured creators at the same
time with bounded CPU, disk, network, and service ownership. Each session keeps
its own lifecycle, recovery evidence, status, output, and errors.

This follows creator automation quickly so overlapping monitored creators do not
remain a long-term limitation. It is separate from v0.6.5 redundant same-LIVE
capture, whose purpose would be gap filling rather than recording different
creators.

### v0.11.0 — Smart storage, retention, and disk protection

**Goal:** Make unattended recording libraries safe to operate without manual disk
housekeeping. Add retention rules, low-disk warnings/protection, cleanup of
eligible temporary/recovery artifacts after safe validation, and local/network/
cloud storage or publishing workflows where justified.

Retention must support explicit per-creator protection so selected creators can
be configured as **never automatically delete** even when general recordings use
age/space-based cleanup. Destructive cleanup must remain auditable and must never
silently remove protected recordings or retained evidence needed for recovery.

### v0.12.0 — Notifications and integrations

**Goal:** Tell the owner when unattended behavior matters: creator LIVE detected,
recording started, completed, skipped because of a limit, failed/needs attention,
and low disk space. Add webhooks, exports, and external adapters only around
demonstrated workflows so notifications remain useful rather than noisy.

### v0.13.0 — Recording catalog, library foundation, and remote media access

**Goal:** Turn recordings into a structured catalog instead of only a folder of
files. Index sessions and artifacts, recording health/history, creator identity,
basic thumbnails/storyboards, and the information later UI pages will need.

This release is deliberately **not** the polished browser UI. The catalog can be
used through service/API/CLI boundaries and can expose trusted tailnet playback
or one-click download primitives. A Mac should be able to access a recording
stored on main-pc without manual SCP, while explicit download/copy remains
available when a local file is wanted.

### v0.14.0 — Web interface, home screen, creator pages, and playback

**Goal:** Put the v0.13 catalog and existing recording controls behind a proper
browser experience. Add a home screen showing service health, active recordings,
recent recordings, storage status, warnings, and monitored creators.

Add creator pages using the catalog, normal playback and downloads, browser-based
recording controls, and **watch while recording** for active recordings stored on
main-pc. Live viewing must remain separate from capture correctness: playback
failure must never stop or damage recording.

### v0.15.0 — Transcription, captions, and search inside recordings

**Goal:** Post-process recorded audio into timed transcripts/captions with clear
engine provenance. Add search across transcripts and available recording/event
metadata, with results linking directly to the relevant playback timestamp.

This is the release where queries such as finding where a creator discussed a
specific topic should become practical.

### v0.16.0 — Recording calendar and creator analytics

**Goal:** Add a creator-oriented timeline/calendar of observed LIVEs and recorded
sessions, plus explainable recording, reconnect, event, and creator-history
statistics. Creator pages can grow from the v0.14 presentation into richer
schedule/history views here.

Possible schedule prediction may use only the owner's retained history and should
be presented as an estimate, not a guarantee.

### v0.17.0 — LIVE events, chat, and gifts

**Goal:** Optionally retain timestamped public chat, gifts, joins, and other
available LIVE events, then align them with recording playback. Missing or partial
event data must be shown honestly rather than implied to be complete.

### v0.18.0 — Clips and highlights (conditional candidate)

**Goal if adopted:** Create a new clip from a selected time range without changing
the original recording, preserving source quality where practical. This version
slot is intentionally conditional: build it only after library/playback workflows
show that clipping is genuinely useful. Automatic highlight generation is not
committed scope.

### v0.19.0 — Authenticated or gated source support (conditional)

**Goal if adopted:** Support legitimate access that requires user-supplied
authorization/session material, but only after a separate security/privacy design
and review of applicable platform rules. TikREC must not bypass authentication,
CAPTCHA, entitlements, access controls, or private signing.

### v0.20.0 — Accounts, multi-user operation, and administration

**Goal if product direction requires it:** Move beyond the initial single-owner
deployment with accounts, permissions, multi-user administration, resource
limits, and auditable controls. This is not required for the personal/local
product and should begin only when an actual multi-user use case exists.

### v0.21.0 — Mobile/PWA and public-app readiness (conditional)

**Goal if TikREC expands beyond personal use:** Provide a mobile/PWA experience
and prepare the product for broader distribution or public/editorial workflows.
This release is gated on explicit legal, privacy, security, platform-policy, and
product decisions; the roadmap does not assume that public release is permitted
or desirable.

## Versioned future product sequence

The releases above are directional slots rather than fixed promises or dates.
Requirements may move when real use exposes dependencies, but future product
capabilities should no longer sit in an unversioned "someday" bucket. Reliability
and the active v0.6 work still take precedence over later product work.

The sequence intentionally grows from trustworthy capture into: recovery and
configuration, creator automation, simultaneous creator recording, storage
safety, notifications, a structured recording catalog, a usable web/playback
experience, search/analytics, richer LIVE data, and only then optional
multi-user/public-product capabilities.

### Permanent boundaries

- No authentication, CAPTCHA, entitlement, access-control, or private-signing
  bypass; future authorization support must not circumvent platform decisions.
- No covert monitoring or surveillance. Creator automation must be explicitly
  configured by the user for legitimate recording purposes.
- No silent overwrite/destruction of recordings, retained evidence, or user data.
- No assumption that predecessor architecture is suitable for this rebuild.

## Architectural direction

Evolve separation only when a release needs it; do not scaffold future systems.

- **Capture:** public resolver, one HTTP media source, writer, LIVE orchestration.
- **Processing:** retained-part finalization and read-only validation.
- **Application/service:** one recording job, cooperative lifecycle, safe status.
- **Interfaces:** existing local CLI, narrow HTTP API, remote CLI; eventual UI.
- **Versioned product layers:** creator automation, concurrent recordings, smart
  storage, notifications/integrations, recording catalog/remote media access,
  web/live viewing, transcripts/search, calendar/analytics, events, and
  conditional multi-user/public-app capabilities.
