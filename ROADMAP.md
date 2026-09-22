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

### Planning cadence and target dates

These are planning targets, not release promises. They are based on TikREC's
observed shipping cadence rather than a generic software-project estimate:
v0.1.0, v0.2.0, and v0.3.0 were tagged on 2026-09-11; v0.4.0 followed on
2026-09-15; and v0.5.0 followed on 2026-09-19. The two larger recent releases
therefore took about four days each. For forward planning, an ordinary release
uses roughly a 3--5 day working target and a larger/cross-cutting release roughly
5--8 days, with immediate reforecasting when real use exposes a blocker or when
work finishes materially early.

The baseline schedule assumes conditional v0.6.5 redundant same-LIVE capture is
not needed. If v0.6 evidence justifies v0.6.5, insert it before v0.7 and reforecast
all later dates rather than pretending the original dates still apply.

| Version | Planning target | Primary milestone |
| --- | --- | --- |
| v0.6.0 | 2026-09-22 | Reconnect-gap reduction |
| v0.7.0 | 2026-09-25 | Guided interrupted-session recovery |
| v0.8.0 | 2026-09-28 | Configuration and defaults |
| v0.9.0 | 2026-10-03 | Creator monitoring and automatic recording |
| v0.10.0 | 2026-10-08 | Multiple simultaneous creator recordings |
| v0.11.0 | 2026-10-12 | Smart storage, retention, and disk protection |
| v0.12.0 | 2026-10-15 | Notifications and integrations |
| v0.13.0 | 2026-10-20 | Recording catalog and remote media access |
| v0.14.0 | 2026-10-27 | Web UI, creator pages, playback, watch while recording |
| v0.15.0 | 2026-11-03 | Transcription, captions, and search |
| v0.16.0 | 2026-11-07 | Recording calendar and creator analytics |
| v0.17.0 | 2026-11-12 | LIVE events, chat, and gifts |
| v0.18.0 | 2026-11-16 | Clips/highlights, if adopted |
| v0.19.0 | 2026-11-23 | Authenticated/gated source support, if adopted |
| v0.20.0 | 2026-12-01 | Accounts and multi-user operation, if needed |
| v0.21.0 | 2026-12-11 | Mobile/PWA and public-app readiness, if pursued |

The dates are intentionally aggressive because the current workflow has already
shipped substantial releases in days. They assume regular owner availability for
real-LIVE validation when needed and continued one-task-at-a-time execution. A
rare-evidence blocker, difficult media defect, legal/platform-policy decision, or
conditional v0.6.5 work can move later targets; conversely, finishing a release
early pulls the following work forward.

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
`TikREC v0.4.0` are synchronized. It is a historical released version; v0.9.0
is the current released version.

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

Issue #8 remains open for rare real replay evidence, while issue #9's later
natural final-read/EOF validation completed its incremental raw-arrival work.
Issue #13 is intentionally paused pending an opportunistic distinct-rendition
encounter. Those evidence investigations did not block v0.5 readiness. Patient recovery uses
a 15-minute window and waits of 1, 2, 5, 10, 10, then 30 seconds; reconnect-gap
measurement and reduction were deliberately deferred to v0.6.

Implemented sequence: durable job state, public room identity,
retained-session resume, service startup reconciliation with controller
integration, outage retry policy/recovery status, and interrupted-finalization
reconciliation, and conservative active-writer-partial recovery. Issue #14's
deployed abrupt-restart requirement and the temporary-network-outage validation
are complete; final output validation and v0.5.0 release bookkeeping are also
complete. Reconnect-gap measurement/reduction was selected and completed
separately for the v0.6.0 release candidate described below.

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
At that point v0.6 remained active until a real post-change reconnect verified
the expected gain.

**Post-change verification (2026-09-20):** The retained `ari-dakotaa` session
contains one suitable ordinary reconnect after `dfc5bf1`. Its total retained-media
gap was 1.920 seconds: 0.114 seconds of previous tail, 0.010 local/backoff, 1.480
resolution, 0.220 HTTP setup, 0.096 initial media, and 0.001 at the write gate.
The former 1.004--1.008-second local/backoff component therefore collapsed as
intended. Resolution accounted for about 77% of this sample and resolution plus
HTTP setup for about 89%; those source/network-dependent components remain the
dominant ordinary-gap contributors. The total is below the 2.515--10.883-second
pre-change range, but a single post-change observation does not justify changing
retry, resolver, or HTTP behavior. Full retained-part validation found decoder
errors in earlier parts 1 and 5, while the reconnect-boundary parts 7 and 8 passed;
there were no recorded timestamp replays. The timing evidence remains suitable,
and no additional production change is justified. This completes the planned
v0.6 measurement/reduction behavior; release bookkeeping remains separate.

**Release candidate (2026-09-20):** Package source and release-facing
documentation are prepared for v0.6.0. The release scope is the
read-only reconnect-gap tooling and evidence, removal of the fixed healthy-close
wait, and the verified 1.920-second post-change reconnect with 0.010 seconds of
local/backoff versus the prior 1.004--1.008-second range. Failure/outage backoff,
patient recovery, room-end confirmation, stop behavior, resolver/HTTP policy,
and writer/part safety remain unchanged. At candidate preparation, issues #8,
#9, and #13 were non-blocking evidence work; the later owner decision below makes
#8 release-blocking before v0.6.0 publication. The candidate is untagged and unpublished; v0.5.0
remains the current released version until a separately authorized annotated
tag and GitHub Release are created and verified. Release-candidate checks pass:
79 focused tests, the full 735-test plus 19-subtest suite, CLI version output,
retained reconnect analysis, and wheel metadata all report v0.6.0 consistently.

**First full-LIVE release soak (2026-09-20):** The deployed v0.6.0 service recorded
`aishaaa.ts` for 872.873 seconds through natural room end with no manual stop.
Three allocated attempts comprised two media-bearing connections and the final
offline room-end confirmation. The one natural media reconnect followed an
`IncompleteRead` and was therefore correctly classified as network recovery,
not an ordinary healthy close: 8.494 seconds total, including 5.960 previous
tail, 1.016 unchanged failure backoff, 1.165 resolution, 0.265 HTTP setup, 0.086
initial media, and 0.002 write gate. All three retained parts passed decoder/DTS
validation without warnings, including both sides of the reconnect and the
later in-connection source configuration change; no timestamp replay was logged.
The finalized 831.810-second MP4 passed normal and deep validation. This adds
natural recovery, room-end, and long-session evidence without adding another
ordinary post-change sample or justifying retry/resolver/HTTP policy changes.
No release blocker was found in that run; the candidate remained untagged and
unpublished.

**Release blocker #17 and preserved recovery (2026-09-20):** A later owner-started
`gracie.kf` soak ran independently on the PC for 10,031.395 seconds, retained
1,300,258,942 bytes across six parts, then failed instead of finalizing when its
fourth allocated attempt received HTTP 404 after transport resolution. The fix
keeps initial page-404 behavior fail-closed, but established capture/recovery may
use the retained canonical room ID and direct public room status when the username
LIVE page is 404. Same-room live reconnects, three trustworthy offline observations
end normally, a different live room uses existing identity-change semantics, and
unverifiable status still fails with media retained. An established media-URL 404
only triggers fresh identity resolution after the existing failure backoff; it is
not treated as offline and reconnect timing policy otherwise remains unchanged.

The preserved session was finalized through `tikrec finalize` without changing
any FLV hash. Its 1,560,230,782-byte, 10,008.064-second H.264/AAC MP4 passes deep
validation without findings. Retained-part validation separately exposes issue
#8 evidence: part 2 has H.264 decoder errors and parts 2/4/5/6 have stored-DTS
reversals corresponding to 16 logged replay records; no matching raw copy exists,
so source-versus-writer origin remains unproven. The full offline suite passes 748
tests plus 19 subtests.

**Post-#17 natural-end release gate (2026-09-21):** Two owner-started LIVEs on
the deployed fix completed through the normal three-observation room-end path,
finalized successfully, and passed retained-session plus normal/deep MP4
validation. Aishaaa supplied two ordinary media reconnects at 1.526 and 1.531
seconds, with local/backoff components of 0.008 and 0.024 seconds; Gracie had no
successful media reconnect before its terminal offline attempt. Neither session
recorded a media-open failure, transient outage, stall, resolver/rendition
change, persistent-state recovery, or unexpected termination. The production
evidence confirms retained room identity across established capture and the
three-check natural-end policy; focused tests continue to cover username-page
404, signed-media 404, different-room, and unverifiable-identity branches.

All 19 retained FLVs decode. Aishaaa parts 16 and 17 contain four packet-DTS
warnings exactly matching four logged timestamp-replay records; the replays
occurred within the third established media connection, not at either reconnect,
and the finalized MP4 deep-validates. With no raw copy this remains issue #8
evidence, not a #17 regression or release blocker. The required post-#17 gate has
passed. At that point routine release bookkeeping remained separate from the
feature evidence; v0.6.0 remained untagged and unpublished, and the gate did not
start v0.6.5 or v0.7.

**Established-room resolution experiment (2026-09-21):** The owner paused
v0.6.0 publication because the 1.526/1.531-second ordinary reconnects still
spend 1.287/1.371 seconds in resolution. Issue #18 now owns a read-only
bound-versus-direct known-room benchmark; production resolution remains
unchanged. Offline safety coverage proves conflicting identity rejection,
typed offline evidence, malformed-response failure, preservation of different-
room semantics, safe diagnostics, and capture/session non-mutation.

The first owner-provided rooms were offline, providing directional evidence
only. A later owner-provided Zoraida LIVE completed 22 corrected alternating
pairs. Ten strict pairs matched saved room, rendition label/source, and exact
transport; twelve rotating exact transports were excluded. In the primary six-
pair batch, bound resolution was 0.942 seconds median (0.759--1.453), direct
known-room resolution was 0.351 (0.275--0.399), and median savings were 0.587
(0.458--1.085). Every bound sample used page + account lookup + room/info. A
second supplied creator ended before sampling and contributed no live result.

This material live saving justified issue #19. Its owner-authorized
implementation now overlaps saved-room room/info with current public-account
identity lookup and accepts the fast transport only when both prove the saved
live room. Offline, conflicting, malformed, unverifiable, failed, or otherwise
insufficient evidence uses the prior full bound resolver. Different live rooms,
saved-room-only offline confirmation, fail-closed behavior, initial resolution,
retry/backoff, media, writer, finalization, and rendition policy remain intact.

A 12-pair read-only Zoraida recheck supplied nine strict matches. The identity-
safe bound median was 0.366 seconds (0.297--0.408), direct room/info was 0.324
(0.275--0.379), and median account-verification overhead was 0.044 seconds
(-0.076--0.104). This is 0.576 seconds below issue #18's comparable 0.942-
second pre-implementation bound median. Offline tests pass 774 tests plus 19
subtests. No media was opened and no disconnect was manufactured, so at that
checkpoint a natural ordinary-reconnect validation remained outstanding. v0.6.0
remained untagged/unpublished with no release action authorized.

Commit `60d55cb` is now deployed through the existing Windows Scheduled Task.
The authorized Zoraida validation session
`a19f366d-1484-47b2-8eb7-64d26e0a47eb` later reached natural room end after
2,210.858 seconds. Its one media connection closed normally, three status-4
observations confirmed offline state, and the second allocated attempt retained
no media. Finalization completed without interruption or error; the retained
FLV and 2,191.564-second H.264/AAC MP4 validate, including a passing deep output
decode. Two recovered in-connection timestamp replays produce matching DTS
warnings but no decoder failure and remain separate issue #8 evidence. Because
the run contained zero ordinary media reconnects, it proves deployed capture and
room-end health but did not supply the original issue #19 ordinary-reconnect
sample. No disconnect was manufactured.

The active issue #8 `luhpollisecret` session later supplied a successful
media-bearing connection 1-to-2 recovery on the same deployed code, but it also
does not complete issue #19. The retained analyzer classifies the boundary as
`network_recovery`, not `ordinary`, because connection 1 ended in
`IncompleteRead(0 bytes read)` and an explicit recovery episode began. Media was
retained on both sides with the same canonical room, `hd1`/`flv_pull_url`, and
identical H.264/AAC configuration; the adjacent parts pass decoder/DTS checks.
The 7.758-second total gap included a 5.988-second dying tail, 1.024-second
failure backoff, 0.419-second established resolution, 0.175-second HTTP setup,
0.151-second initial media delivery, and no keyframe gate. The deployed bound
resolver necessarily attempted the identity-safe known-room path, but the
persisted schema cannot prove fast-result acceptance versus full fallback.
Connection 2-to-3 was also classified `network_recovery`: its 7.522-second gap
contained 5.992 seconds of tail, 1.034 seconds of failure backoff, 0.397 seconds
of resolution, 0.070 seconds of HTTP setup, 0.030 seconds of initial media, and
no keyframe gate. The completed analyzer reports two recovery reconnects and zero
ordinary reconnects. They therefore did not meet the original gate wording.

**Media-integrity sequencing decision (2026-09-21):** Issue #19's natural
ordinary-reconnect validation was intentionally paused while issue #8 received
two raw-copy opportunities; its implemented and deployed identity-safe fast path
remains current code. Issue #9's incremental raw-byte preservation, linked
arrival sidecars, and non-fatal diagnostic failure behavior support #8, and the
Promi evidence below completed #9's real-world validation. Issue #13 stays open,
paused/non-blocking, and opportunistic.

The normal remote service previously had no way to request those diagnostics.
It now accepts only a boolean `remote start --raw-copy` opt-in, co-locates raw
connections and arrival sidecars with the retained FLVs and session evidence,
and durably continues that opt-in through safe service recovery. Default remote
capture remains unchanged and avoids doubled diagnostic storage. No suitable
owner-provided public LIVE was available in this task, so the next #8 step is a
normal raw-copy session allowed to run until a natural replay occurs; faults and
replays must not be manufactured. Focused coverage passes 197 tests plus 2
subtests, and the full offline suite passes 785 tests plus 19 subtests. v0.6.0
remains untagged and unpublished.

Current `main` (`0dcdbce`) was deployed through the existing editable
environment on 2026-09-21, and only the existing `TikREC Service` Scheduled Task
was restarted. The task retained its executable, arguments, working directory,
and security architecture. The restarted service is healthy, available, idle,
and free of stale recovery; it loads the current checkout, exposes
`remote start --raw-copy`, and reports `raw_copy_enabled=false` for the prior
completed non-diagnostic job. No recording was started during deployment; the
deployed opt-in was then ready for an owner-provided public LIVE.

The owner-authorized `promi.streams` raw-copy validation started normally on
2026-09-21 as session `e4aa8dc4-532c-42ce-96fa-76596df0a2a9`, room
`7687931142670682901`, and later ended naturally. A source EOF left an incomplete
raw FLV tag, then three status-4 checks confirmed room end and finalization
completed without interruption or service error. The one retained FLV and raw
source contain zero timestamp replays. From the first retained media tag onward,
all 158,062 tag payloads, types, and ordering match the raw source exactly and
timestamps differ only by the expected 2,572,297-unit rebase. Four H.264 decoder
failures occur at matching raw/retained frames and payload hashes, establishing
upstream provenance for this separate non-replay malformed media. The standard
MP4 check passes, while retained-session and deep MP4 validation honestly fail on
those same decoder errors; FLV and MP4 stored DTS remain strictly increasing.

The arrival sidecar contains 79,810 contiguous byte records covering all
435,600,600 raw bytes. It preserved reads from 1 to 16,384 bytes, including the
final 3,799-byte read, then recorded `read_end=eof` seven seconds later. The raw
parser proves an 861-byte incomplete final tag with 192 bytes missing, while
TikREC retained the complete 435,598,545-byte prefix. This natural boundary is
the real-world evidence issue #9 required, so #9 is complete. Issue #8 remains
open because the session supplied no replay to attribute; another natural
raw-copy replay opportunity is still required.

The next owner-authorized opportunity started normally on 2026-09-21 for
`luhpollisecret` as session `c5c070f3-93a3-4c13-be63-f7109fc6e974`, canonical
room `7687950152400816913`. It uses the deployed remote-service `--raw-copy`
path and a new collision-free output/parts pair. The first connection is healthy,
writer/raw/arrival evidence is progressing, and the initial checkpoint has zero
reconnects with no recovery, stop, interruption, or error state. The recording
was left undisturbed for a natural replay or room-end boundary; no fault was
manufactured. Connection 1 later failed naturally and recovered into a productive
connection 2, which subsequently ended after retaining parts 11--20. Its complete
666,852,312-byte raw copy contains 235,300 complete tags and no source-aware
timestamp replay across ten codec configuration epochs. Connection 3 retained
parts 21--22 and its 35,539,119-byte raw copy likewise contains no replay across
12,077 complete tags. Three trustworthy status-4 observations then confirmed room
end; connection 4 retained no media, and finalization completed without error or
interruption. The 1,781,146,349-byte, 6,326.199-second H.264/AAC MP4 passes
standard validation. A later full retained-session check found one H.264 decoder
error in part 22. The untouched connection-3 raw file emits the same error, and
all 924 retained tags from the part's first keyframe preserve raw payloads, types,
and order exactly with only the expected 9,364,937-unit timestamp rebase. The
final MP4 also passes deep validation. No fault was manufactured.

**Issue #8 rare-evidence reassessment (2026-09-21):** Outcome B applies. The issue
remains open for opportunistic replay provenance, but it no longer blocks v0.6.0
or other roadmap work. Historical Gracie replay-associated decoder damage still
lacks raw bytes, and Aishaaa/Zoraida replays likewise cannot establish origin;
no later parser/writer change is assumed to have repaired those cases. Against
that uncertainty, current writer behavior preserves source tag payloads and
ordering, Promi proves exact raw/retained equivalence across 158,062 retained
media-and-later tags, and Luhpol contributes 303,564 complete raw tags across
three media connections and two natural recoveries with zero raw or retained
replays. Both raw-copy sessions independently prove that malformed H.264 can be
present upstream without TikREC divergence. There is no demonstrated current
TikREC-generated corruption, so requiring an increasingly rare natural replay
as a release prerequisite is disproportionate to the remaining risk.

No replay-with-raw-copy sample was captured. A future retained replay absent from
matching raw timestamps/tags, any raw-versus-retained payload/order divergence,
or a reproducible TikREC-only decoder failure would make this a correctness
blocker again. At this reassessment, v0.6.0 remained untagged and unpublished.

**Issue #19 rare-evidence reassessment (2026-09-21):** Outcome C applies and the
issue is complete. No qualifying post-change ordinary reconnect was captured,
and Luhpol's persisted evidence cannot prove fast-result acceptance rather than
fallback. That missing proof is useful for exact end-to-end timing but no longer
represents a meaningful safety or correctness risk. The production resolver
benchmark directly exercised fast acceptance, preserved account verification,
and reduced same-room bound resolution from 0.942 to 0.366 seconds. Comprehensive
offline tests cover same-room success, different-room/live-changed handling,
saved-room-only offline evidence, malformed/conflicting/request-failure fallback,
three-observation confirmation, and fail-closed identity behavior. Zoraida then
proved deployed natural-end/finalization behavior. Luhpol's two natural deployed
network recoveries invoked the same established resolver, successfully reopened
same-room media, measured 0.419/0.397-second resolution consistent with the
optimized path, and produced validated retained/final output without a reconnect
regression. The distinction between those recovery boundaries and `ordinary`
lies in their preceding tail/backoff classification, not a different resolver.

Future evidence should create a new blocker only if it demonstrates an accepted
identity conflict, wrong offline/live-changed decision, unsafe fallback, media-
open/reconnect regression, or recurring material resolver slowdown. With #8
non-blocking and #19 complete, no demonstrated v0.6.0 release-validation blocker
remains. Publication still requires separate owner authorization and the normal
immutable tag/GitHub Release checklist; this reassessment creates neither.

**Release publication (2026-09-21):** v0.6.0 became the current released version.
The immutable annotated `v0.6.0` tag (tag object
`8ee5c90a57d9d6b5da7e00fe9dd3019a7b1d82c4`, peeled release commit
`341de6ea154ec1a767fd89a7994381a1a74d7d78`) and the published non-draft,
non-prerelease GitHub Release `TikREC v0.6.0` are synchronized with package
metadata. Final verification passed 785 tests plus 19 subtests and produced a
verified `tikrec-0.6.0` wheel. Issues #8 and #13 remain open as non-blocking,
opportunistic evidence work. No v0.6.5 or v0.7 implementation began during the
release task.

### v0.6.5 — Redundant simultaneous capture (conditional)

**Goal:** Eliminate reconnect gaps by maintaining more than one concurrent
connection to the same LIVE and filling each gap from whichever connection
had coverage.

**Why conditional:** This is only worth building if v0.6 measurement shows
the remaining gap is large enough to justify doubled bandwidth, doubled
disk, and substantially more complex media assembly. If v0.6 reduces the
per-reconnect loss to a second or two, this release should be dropped.

**Diagnostic dependency on issue #8.** Joining two connections would deliberately
splice encoder outputs and therefore needs explicit media-integrity design and
validation. Current evidence does not demonstrate a TikREC parser/writer defect,
but a future raw-proven retained divergence or a replay-specific finding could
change that assessment before this conditional release is started.

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

**First slice completed (2026-09-21, issue #20):** `tikrec recover ROOT` now
discovers one explicit parts directory or immediate `*.parts` children and
classifies them without mutation. It reports stored session/source/output facts,
retained-part count, lifecycle/finalization state, output availability, evidence
consistency, and a plain-language safe next action, with equivalent `--json`
output. Existing manifest, retained-part, connection, and completed-output rules
drive classification. Active/running, partial, malformed, changing, symlinked,
or conflicting evidence fails closed and remains untouched. This slice does not
run full media validation, finalize, repair, resume, or record a recovery action;
those remain later v0.7 work. v0.7.0 is not released.

**Second slice completed (2026-09-21, issue #21):** Optional
`tikrec recover ROOT --validate` now runs the existing standard session/parts
validator only for consistent `recoverable` or `complete` candidates. Plain and
JSON reports distinguish requested, ran, passed, failed, and skipped validation,
include concise error-first findings, and replace discovery guidance with the
safest validation-aware next action. Active/uncertain and conflicting candidates
are skipped before FFprobe; validator exceptions fail closed. Discovery and
validation remain read-only. Guided repeat finalization and durable recovery-
outcome recording remain future slices; v0.7.0 is not released.

**Third slice completed (2026-09-21, issue #22):** Explicit
`tikrec recover PARTS_DIRECTORY --finalize` now validates and safely repeats
finalization for exactly one named `recoverable` session using its declared
output. Parent roots cannot batch-finalize; active, ambiguous, changed, symlinked,
output-conflicting, partial, or undeclared-output evidence fails closed before
mutation. The action reuses `finalize_parts`, overwrite protections, standard
validation, and existing manifest recovery fields. It records running/completed/
failed/interrupted outcomes, preserves retained FLVs, verifies a regular non-empty
output plus the updated session, and reports plain or structured JSON results.
Discovery and `--validate` remain read-only, and manual `tikrec finalize` remains
supported. The planned v0.7 functionality is implemented but v0.7.0 is not
released.

**Release candidate prepared (2026-09-21):** Package metadata now reports
v0.7.0. Release review found the three completed slices coherent and compatible
with the existing service, `tikrec finalize`, session schema, and validation
paths. Verification passed 181 focused tests, 832 full-suite tests plus 19
subtests, 204 unittest-discovery tests, compilation, CLI parsing/help checks, and
an installed-wheel smoke test. The wheel metadata and `tikrec` entry point are
correct. The issue #22 isolated real-media recovery check remains the applicable
finalization evidence: pre-validation, guided stream-copy finalization, updated-
session validation, and deep output validation all passed without modifying the
source evidence. No release blocker is demonstrated; issues #8 and #13 remain
non-blocking/opportunistic. At this checkpoint v0.7.0 was ready for separately
authorized publication but remained untagged and unpublished, so v0.6.0 was the
current release.

**Release publication (2026-09-21):** v0.7.0 became the current released version.
The immutable annotated `v0.7.0` tag (tag object
`13b0492697d788814ceedcd11017892877be6115`, peeled release commit
`bf3bee32fcd5267a109006883451bf90718ff722`) and the published non-draft,
non-prerelease GitHub Release `TikREC v0.7.0` are synchronized with package
metadata. Final publication verification passed 832 tests, 204 unittest-
discovery tests, compilation, CLI/help checks, and an installed-wheel smoke test;
the issue #22 isolated real-media recovery evidence remains applicable. Issues
#8 and #13 remain open as non-blocking, opportunistic evidence work.

### v0.8.0 ? Configuration and defaults

**Goal:** Persist proven choices for output locations/naming, retry policy,
validation, and logging with documented discovery and CLI override precedence.
This release does not add TikTok credentials or account profiles.

**First slice completed (2026-09-21, issue #23):** TikREC now has strict,
schema-versioned, stdlib-only per-user JSON configuration with deterministic
Windows `%APPDATA%` and POSIX XDG discovery, an explicit `--config FILE`
override, atomic writes, and owner-facing `config show/path/set/unset` commands.
The first persisted setting, `output_directory`, relocates only relative local
`live` and advanced `record` outputs. Absolute local outputs remain authoritative;
missing configuration preserves CWD-relative behavior; and remote, finalize,
recovery, service-state, and retained-session paths remain unchanged. Automatic
output naming plus retry, validation, and logging defaults remain future v0.8
slices. No credentials or account profiles are supported, and v0.8.0 is not yet
a release candidate.

**Second slice completed (2026-09-21, issue #24):** Manually started local
`tikrec live` can now omit `--output` when `output_directory` is configured.
TikREC locally extracts and sanitizes only the public creator handle, combines it
with an injectable local-time `YYYYMMDD-HHMMSS` timestamp, and selects a bounded
deterministic suffix when either the output or matching `.parts` path exists.
Generated paths remain direct children of configured storage and never include
query/signed URL material. Explicit output precedence is unchanged; direct
`record`, remote, finalize, recovery, service, and retained-session behavior is
unchanged. Filename templates plus retry, validation, and logging defaults remain
future v0.8 slices, and v0.8.0 is not yet a release candidate.

**Third slice completed (2026-09-21, issue #25):** Strict schema-1 configuration
now optionally persists `recovery_window_seconds`, bounded to integer values from
60 through 3600. Local `live` and `serve` resolve CLI override, configuration,
then the unchanged 900-second default; explicit overrides avoid configuration I/O
when no other feature needs it. A service snapshots one policy at startup and
uses it for both active LIVE and startup recovery, while status reports that
effective window. Retry classification/math, staged waits, the 30-second cap,
room-end confirmation, direct `record`, remote start/API shape, and existing
output behavior are unchanged. Service restart is required after configuration
changes. Validation and logging defaults remain future v0.8 slices, and v0.8.0
is not yet a release candidate.

**Fourth slice completed (2026-09-21, issue #26):** Strict schema-1 configuration
now optionally persists `validation_mode` as `standard` or `deep` for the
explicit `tikrec validate` command. Mutually exclusive `--deep` and `--standard`
flags override configuration without reading it; otherwise configuration
precedes the built-in standard default. Standard/deep validation semantics and
result reporting are unchanged. Guided `recover --validate` and the pre/post
checks used by `recover --finalize` remain fixed to their standard safety path
and never inherit this preference. Automatic post-recording validation was not
added. Logging defaults remain the next v0.8 configuration slice, and v0.8.0 is
not yet a release candidate.

**Fifth slice completed (2026-09-21):** Strict schema-1 configuration now
optionally persists boolean `debug_tracebacks`, mirroring the existing
unexpected-error `--debug` behavior without introducing a logging framework.
Mutually exclusive `--debug` and `--no-debug` flags override configuration;
otherwise the preference is loaded only after an unexpected exception, with
built-in false preserving existing behavior. Known errors, successful commands,
normal progress/warnings, service request-log suppression, remote/API output,
media behavior, and sensitive-data boundaries are unchanged. This completes the
intended v0.8 configuration/default slices; configurable filename templates are
not required for this release and remain deferred. v0.8.0 still requires normal
release preparation and separate authorization before any tag or GitHub Release.

**Release candidate prepared (2026-09-22):** Package metadata now reports
v0.8.0. Combined review confirms the five slices preserve strict schema-1
validation, explicit CLI precedence, lazy configuration loading, unchanged
no-configuration behavior, and the existing remote/API and media boundaries.
Verification passed 182 focused tests, all 921 offline tests, 215 unittest-
discovery tests, compilation, 14 CLI help paths, CLI version checks, and an
isolated built-wheel/install smoke test. The wheel metadata and `tikrec` entry
point are correct. A first focused attempt hit `WinError 5` while pytest scanned
its shared Windows temp root; focused and full reruns passed in fresh isolated
roots, with no TikREC `os.replace` failure. No new real-media run is required:
v0.8 changes configuration/default selection, not codecs, capture, part
boundaries, or finalization, so existing media validation evidence remains
applicable. Issues #8 and #13 remain non-blocking/opportunistic. v0.8.0 is ready
for separate publication authorization but remains untagged and unpublished;
v0.7.0 remains the current released version.

**Release publication (2026-09-22):** v0.8.0 became the current released version.
The immutable annotated `v0.8.0` tag (tag object
`f97fc91a4af9e95a8ec91363902d1fa8a9cf6091`, peeled release commit
`da0390b502cb7bb51ef4b5097b58d4910017e2df`) and the published non-draft,
non-prerelease GitHub Release `TikREC v0.8.0` are synchronized with package
metadata. Final publication verification passed all 921 offline tests, 215
unittest-discovery tests, compilation, 14 CLI help paths, CLI version checks,
and an installed-wheel smoke test. Existing media evidence remains applicable
because v0.8 changed configuration/default selection rather than media handling.
Issues #8 and #13 remain open as non-blocking, opportunistic evidence work.

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

**First slice completed (2026-09-22):** Schema-1 per-user configuration now
optionally persists an ordered, duplicate-free list of canonical lowercase
public TikTok handles. `tikrec monitor add/remove/list` accepts bare handles,
`@handle`, or a standard public LIVE URL and normalizes locally without network
access. Existing v0.8 settings and atomic-write safety are preserved, and
`output_directory` is not required merely to configure a creator. Persisted
order is deterministic but is not scheduling priority. This slice adds no
polling, LIVE detection loop, automatic recording, disk-space policy,
notifications, or concurrency. The next v0.9 slice is read-only service
monitoring/detection that may observe configured creators but must not start a
recording. Verification passed 139 focused tests, all 960 offline tests, 215
unittest-discovery tests, compilation, CLI/help parsing, source-size checks, and
an isolated configuration smoke. No real-LIVE check applies because this slice
performs no network or recording behavior.

**Second slice completed (2026-09-22):** The persistent service snapshots the
configured creator list at startup and observes it with one independent
read-only worker. It polls promptly, sequentially in configured order, and then
30 seconds after each completed non-overlapping cycle. Observations are
thread-safe, memory-only `pending`/`live`/`offline`/`unknown` state; only an
explicit resolver offline result proves `offline`, while insufficient evidence
stays `unknown` under fixed safe categories. Positive LIVE state retains only
canonical public room ID and immediately discards signed media transport. The
authenticated, browser-origin-rejecting `GET /monitoring` route and `tikrec
remote monitor-status` expose sanitized status and cycle timing. Monitoring
continues independently of the single manual recording slot, changes require a
service restart, and shutdown is cooperative. No recording, output creation,
disk policy, notification, persistence-schema change, or concurrent-recording
behavior was added.
Verification passed 179 focused tests, all 974 offline tests plus 19 subtests,
215 unittest-discovery tests, compilation, CLI/help checks, and source-size
checks. No real-LIVE recording applies because this slice records no media;
resolver outcomes and timing are fully injectable and were tested offline.
**Third slice completed (2026-09-22):** The service now snapshots configured
output storage alongside creators and adds a separate, non-mutating admission
evaluation to each monitoring-status response. A detected LIVE is skipped while
manual capture, recovery, finalization, blocked state, or shutdown owns the
single slot; otherwise it reports fixed blocked reasons for missing/unavailable
storage, less than the built-in 10 GiB free-space floor, or exhausted bounded
name candidates. Ready status uses the existing creator/timestamp and collision-
suffix convention and exposes only safe local candidates/free-byte facts.
Not-yet-created output directories are assessed through their nearest existing
parent without creating files, directories, locks, or reservations. Admission is
recomputed from current state, persists nothing, chooses no winner among
simultaneous LIVEs, and never starts recording. Manual recording/recovery paths
do not inherit the floor. Explicit recovery overrides keep unrelated known
validation/debug preferences lazy while schema and service-needed creator/output
fields remain strict. Verification passes 136 focused tests and all 1,015
offline tests plus 19 subtests; compilation, unittest discovery, CLI/help, and
source-size checks also pass. No real-LIVE/media validation applies because the
slice performs no recording or media change.

**Fourth slice completed (2026-09-22):** After each complete monitor cycle, a
separate service-owned coordinator may attempt exactly one admitted automatic
start. Simultaneous candidates use canonical-handle lexical order rather than
configuration order; admission and collision-safe naming are refreshed before
start, and the recording controller remains authoritative for its slot and path
collisions. The automatic capture must freshly prove the monitored canonical
room before creating session/media artifacts, while manual starts remain
unchanged. Accepted rooms are durably suppressed through completion, failure,
manual stop, and restart until explicit offline or a different room re-arms the
creator. A strict atomic automation state plus pending claim closes the start
crash window; corrupt or ambiguous state disables only automatic starts. The
existing monitoring route now reports safe selection, armed/suppressed, and
fixed block/failure facts. Notifications, concurrent recording, retention, and
v0.10 behavior were not added. Verification passes 99 focused tests, all 1,069
offline tests plus 19 subtests in a clean non-checkout temp root, 215 unittest-
discovery tests, compilation, CLI/help/version checks, diff checks, and source-
size checks.
No suitable owner-authorized public LIVE was identified, so natural deployed
automatic-start/re-arm validation remains outstanding.

**Bounded deployed validation pass (2026-09-22):** Current `main` was installed
into the existing main-pc editable environment only after the deployed service
proved idle with its previous job completed. The established Scheduled Task was
restarted without changing its action or security/network/storage architecture.
It is healthy, available, and idle on package version 0.8.0, and authenticated
monitoring reports an operational coordinator. The per-user configuration is
absent, however, so no owner-authorized monitored creator or output directory was
available and no LIVE was manufactured. Automatic start, identity binding,
output/finalization, durable same-room suppression, restart persistence, and
natural re-arm therefore remain unobserved in deployment. Comprehensive offline
verification still passes, so no correctness blocker is demonstrated, but the
required automatic-start/output/suppression evidence gate is not satisfied and
v0.9.0 is not yet a release-preparation candidate.

**Configured validation continuation (2026-09-22):** The deployed service now
monitors owner-authorized `lilymaye207` with automatic output under
`C:\Users\Leandro\Videos`. The earlier `lilsmaye207` configuration was a typo,
so its five `unknown/unverifiable` cycles provide no evidence about the intended
creator. The typo was replaced through normal TikREC CLI commands, and the
unchanged Scheduled Task is healthy, available, idle, and running the normal
monitor. Three complete corrected-creator cycles returned trustworthy `offline`;
no canonical room, admission candidate, automatic start, new session/output, or
consumed-room state was created. With nothing consumed, this is an offline
baseline rather than a post-consumption re-arm transition. The corrected
configuration remains active for a later natural opportunity, but the primary
deployed gate is still outstanding and v0.9.0 is not yet a release-preparation
candidate.

The corrected `lilymaye207` offline baseline remains valid historical evidence.
The owner later selected `westvlammer` as the sole creator for the primary
automatic-start validation attempt; that configuration change does not invalidate
the earlier trustworthy offline observations.

**Primary deployed gate completed (2026-09-22):** Monitoring owner-authorized
`westvlammer` observed canonical room `7688299000113400608` and automatically
started session `a6b73227-d637-48d5-8ea5-90cd8ea1c806` without a manual start.
The job used matching room identity and collision-safe output
`westvlammer-20260922-152933.mp4` under configured storage. It retained
30,723,109 bytes over 129.406 seconds without error or reconnect before a normal
authenticated stop; finalization produced a 30,750,722-byte MP4 plus one retained
FLV. Retained-session, standard MP4, and deep MP4 validation pass. The same room
was durably consumed and suppressed on a later LIVE cycle with no duplicate.
After an idle Scheduled Task restart, the first natural observation was explicit
offline and reported `rearmed/offline_observed`, which proves the persisted
consumed room was restored and then legitimately cleared; no duplicate output or
session was created. The service remains healthy, idle, and monitoring only
`westvlammer`. Full isolated readiness verification passes all 1,069 offline
tests plus 19 subtests, 215 unittest-discovery tests, compilation, CLI/help/
version, diff, and strict source-size checks. No v0.9 correctness blocker is
demonstrated. The next task is v0.9.0 release preparation; do not begin v0.10.

**Release candidate prepared (2026-09-22):** Package metadata now reports
v0.9.0. Combined review confirms the four creator-automation slices and deployed
gate form one coherent public-only, single-recording-slot release: ordered
configuration, conservative detection, authenticated sanitized status,
collision-safe admission with the 10 GiB floor, room-bound automatic start,
durable same-room suppression, restart persistence, and natural offline re-arm.
Notifications, retention, concurrent creator recording, authentication bypass,
and v0.10 behavior remain outside this release. Verification passes 207 focused
tests, all 1,069 offline pytest tests under isolated configuration/temp roots,
215 unittest-discovery tests, compilation, 24 CLI
help/version paths, strict source-size and diff checks, and an isolated wheel
build/install smoke. Wheel metadata and the `tikrec` console entry point are
correct for `tikrec-0.9.0-py3-none-any.whl` (SHA-256
`7CDFACD9887B2D3D3ADA599F3724202846326EDB5C171849962B875919E450CC`). The
completed `westvlammer` retained/final media evidence remains the applicable real
deployment validation; no ceremonial recording was started. Issues #8 and #13
remain non-blocking/opportunistic. The candidate is untagged and unpublished;
v0.8.0 remains the current release until a separately authorized annotated tag
and GitHub Release are created and verified. Do not begin v0.10.

**Release publication (2026-09-22):** v0.9.0 is the current released version.
The immutable annotated `v0.9.0` tag (tag object
`3e26f06903aad9fffa4f1be2e560d5fba30139fa`, peeled release commit
`9786961d1ecaaed8fddc4c7d10eda85a27b5c968`) and the published non-draft,
non-prerelease GitHub Release `TikREC v0.9.0` are synchronized with package
metadata. Final publication verification passed all 1,069 isolated pytest tests,
215 unittest-discovery tests, compilation, 24 CLI help/version paths, strict
source-size and diff checks, and the recorded wheel metadata/install smoke. The
completed `westvlammer` deployed evidence remains applicable; no service,
configuration, recording, or durable runtime state was changed for publication.
Issues #8 and #13 remain open as non-blocking, opportunistic evidence work.

### v0.10.0 — Multiple simultaneous creator recordings

**Goal:** Record independent LIVEs for multiple configured creators at the same
time with bounded CPU, disk, network, and service ownership. Each session keeps
its own lifecycle, recovery evidence, status, output, and errors.

This follows creator automation quickly so overlapping monitored creators do not
remain a long-term limitation. It is separate from v0.6.5 redundant same-LIVE
capture, whose purpose would be gap filling rather than recording different
creators.

**First bounded implementation slice (2026-09-22):** Current `main` replaces the
service's single controller boundary with a built-in two-slot `RecordingManager`.
The slots retain independent workers, stop events, progress, results, recovery,
finalization, and durable `job.json`/`job-2.json` intent; legacy state needs no
migration, corrupt state blocks only its slot, and colliding interrupted intent
fails closed without rewriting evidence. Aggregate authenticated `/recordings`
and health capacity facts complement compatible singular status, while canonical
session IDs enable targeted stop. The remote CLI adds `recordings` and
`stop --session-id`.

Creator automation now inspects all current jobs, freshly rechecks capacity,
free space, and collision-safe allocation before each start, and sequentially
fills up to two slots in canonical-handle lexical order. Schema-1 retains one
pending claim because each claim is completed or cleared before the next attempt.
Capacity-exhausted creators are reported and reconsidered later; a synchronous
start failure conservatively ends the cycle's remaining attempts. Local `live`
and `record`, the 10 GiB floor, public-only boundary, recovery/finalization,
no-notification/no-retention scope, and v0.9 released behavior are preserved.
Verification passes 134 focused tests, all 1,091 isolated offline pytest tests
plus 19 subtests, 215 unittest-discovery tests, compilation, 25 CLI help/version
paths, strict source-size checks, and diff checks.

The implementation slice itself did not change the real Scheduled Task or start
a LIVE. A separately authorized bounded deployment attempt on 2026-09-22 then
installed `dd00400` into the existing editable environment while idle and
restarted only the unchanged **TikREC Service** task. Deployed health reports
capacity 2 with stable available `slot-1`/`slot-2`; aggregate and legacy singular
status work, authentication rejects an unauthenticated request, and combined
health/recording/monitoring responses contain no bearer token, signed-media
marker, traceback, or unsafe exception text. Host-visible configuration contains
exactly owner-authorized `westvlammer` and `lilymaye207`, with output under
`C:\Users\Leandro\Videos`. Legacy completed `job.json` remained slot 1,
`job-2.json` remained absent/idle without migration, and automation state had no
pending claim or consumed room.

Five bounded complete-cycle checkpoints found both creators naturally offline,
with no selection, automatic start, new session, or output. The healthy service
was left running and monitoring current `main`; no random creator, manual start,
fault, or media was manufactured. This is deployed idle/configuration/status
evidence, not v0.10 release readiness. Genuinely simultaneous independent
recordings, targeted control/finalization isolation, dual retained/final media
validation, automation-capacity behavior under overlap, and idle-restart durable
state validation remain for a later bounded natural opportunity.

**Second deployed validation attempt (2026-09-22):** The owner-authorized pair
was changed through the proven host-visible CLI path to exactly `ranaerose7` and
`moealkaf`, preserving `C:\Users\Leandro\Videos`; the unchanged task definition
was restarted only after both slots were idle. `moealkaf` was naturally LIVE in
canonical room `7688395628493949717` and automation started session
`c7927922-0381-410d-8020-0272aa96f265` in `slot-1` without a manual start. Its
status grew from 1,274,670 to 26,839,748 retained bytes over about 194 seconds
with no reconnect, recovery, stop request, or error. `ranaerose7` remained
`unknown/unverifiable` through seven complete cycles, so no simultaneous overlap
or second session occurred and `slot-2` stayed idle/available. Authentication
and sanitization checks still pass. Read-only durable inspection matches the
active slot-1 session/room/output, leaves `job-2.json` absent/idle, and records
only the independently consumed `moealkaf` room with no pending claim. The useful
automatic recording was left running normally; no restart, stop, manual start,
or fault was manufactured. The simultaneous, targeted-isolation, dual-output,
and idle-restart gates remain outstanding.

**Active-session creator replacement (2026-09-22):** With the legitimate
`moealkaf` session still recording, the owner replaced only non-useful
`ranaerose7` with `phoebelightt`. Normal TikREC CLI operations against the proven
host-visible configuration path persisted exactly `moealkaf`, `phoebelightt` in
that order and preserved `C:\Users\Leandro\Videos`. The running service was not
restarted, so it correctly retains the earlier `ranaerose7`/`moealkaf` startup
snapshot until idle. Three bounded post-change checkpoints showed the unchanged
session healthy in `slot-1`, growing from 126,257,571 to 137,712,136 bytes with
zero reconnects and no recovery, stop, finalization, or error; `slot-2` remained
available. Applying and observing the staged pair is deferred until safe natural
completion. The earlier `ranaerose7` evidence remains historical rather than
being attributed to `phoebelightt`.

**Bounded preserved-session reinspection (2026-09-22):** The unchanged
`moealkaf` session `c7927922-0381-410d-8020-0272aa96f265` remained healthy and
active in `slot-1`. Across the bounded checks, retained bytes grew from
390,912,511 to 406,181,774 and reached about 50.6 minutes elapsed, with zero reconnects
and no recovery, stop request, finalization, or error. Service capacity remained
2 with `slot-2` idle and available; the running service still correctly showed
its earlier `ranaerose7`/`moealkaf` startup snapshot while the persisted
configuration remained staged as `moealkaf`/`phoebelightt`. The task definition
hash remained unchanged. No stop or restart was performed, and applying the
staged pair remains deferred until safe natural completion.

**Natural completion and staged-pair activation (2026-09-22):** Session
`c7927922-0381-410d-8020-0272aa96f265` ended naturally and finalized in
`slot-1` with 788,464,216 retained bytes in one FLV over 5,886.833 seconds,
two allocated connections, one reconnect, `room_ended`, and no recovery,
interruption, stop request, session error, or finalization error. The final
787,935,979-byte MP4 contains 6,250.443 seconds of 640x1280 H.264/AAC media and
passes standard validation. Retained-session and deep MP4 validation both fail
on extensive matching H.264 decoder errors, however. The connection evidence
contains zero timestamp replays and raw copy was disabled, so the source versus
writer origin cannot be established from this session; the media and retained
evidence remain preserved, and issue #8 remains non-blocking/opportunistic.
This session proves automatic single-slot start, binding, natural completion,
and finalization under the v0.10 service, but it is not valid-media evidence for
the outstanding simultaneous gate.

Only after both slots were idle, the unchanged **TikREC Service** task was
restarted once. Its definition hash remained
`54FCCDE50E6B34BDA27A2BA9AB42A0D19B49A4727C450C741543AD05B6B4C443`;
capacity remained 2, the completed slot-1 job did not relaunch, `job-2.json`
remained absent/idle, and automation retained no pending claim or consumed room.
The service loaded exactly `moealkaf` and `phoebelightt`, preserved
`C:\Users\Leandro\Videos`, rejected unauthenticated health, and exposed no
unsafe status marker. Six completed monitoring checkpoints through cycle 7
reported both creators explicitly offline with both slots available, no new
session or output, and no natural overlap. The service remains healthy and
monitoring the staged pair; simultaneous recording, targeted-stop isolation,
dual-media validation, and post-dual-session restart evidence remain outstanding.

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
capabilities should no longer sit in an unversioned "someday" bucket. Reliability,
guided recovery, configuration/defaults, and creator automation through v0.9.0
are released. v0.10.0 multiple simultaneous creator recordings is the active
development target; its first bounded two-slot manager slice is implemented on
`main` and deployed idle/configuration/status checks pass, while simultaneous
recording/isolation validation and later readiness work remain.

The sequence intentionally grows from trustworthy capture into: recovery and
configuration, creator automation, simultaneous creator recording, storage
safety, notifications, a structured recording catalog, a usable web/playback
experience, search/analytics, richer LIVE data, and only then optional
multi-user/public-product capabilities.

## Future commercial/public product direction

This is a deliberately separate product-direction note, not current TikREC
scope, a versioned release commitment, or an active issue. If the product ever
passes the legal and platform-policy gate for broader distribution, a hosted
commercial/public service would likely need:

- hosted accounts, authentication, billing, subscriptions, permissions, and
  tenant administration;
- cloud recording workers that can run jobs independently of an owner's PC;
- durable object storage and a CDN for retained media, playback, and delivery;
- explicit quotas, retention policies, lifecycle controls, and cost protection;
- production operations, observability, incident response, abuse prevention,
  privacy controls, security reviews, and data-governance processes; and
- a documented legal, privacy, copyright, terms-of-service, and platform-policy
  review before public launch or paid service operation.

Current TikREC should only avoid needless future blockers in its boundaries,
data model, and evidence handling. It should not build hosted infrastructure,
commercial account systems, cloud workers, or public-service operations now;
those belong to a separately authorized future product stage.

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
- **Application/service:** bounded independent recording jobs, cooperative
  lifecycle, aggregate/per-session control, and safe status.
- **Interfaces:** existing local CLI, narrow HTTP API, remote CLI; eventual UI.
- **Versioned product layers:** creator automation, concurrent recordings, smart
  storage, notifications/integrations, recording catalog/remote media access,
  web/live viewing, transcripts/search, calendar/analytics, events, and
  conditional multi-user/public-app capabilities.
