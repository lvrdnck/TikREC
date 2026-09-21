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

### First full-LIVE release soak

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
change, and finalization evidence without exposing a v0.6.0 release blocker in
that run.

### Full-LIVE post-capture 404 evidence

The later preserved `gracie-kf-v060-full-live.parts` session exposed issue #17.
Session `43248309-a69f-45cf-a4e2-f4fc35a82a40`, bound to room
`7687483539771624223`, ran for 10,031.395 wall-clock seconds and retained
1,300,258,942 bytes in six parts while the independent PC service continued with
the owner laptop closed. Its reported `reconnect_count=3` means four allocated
attempts: two successful media reconnects and a final media-free attempt. That
last attempt resolved transport but received HTTP 404 when opening the signed
media URL, after which the historical job failed instead of confirming natural
room end.

The two successful gaps were 1.121 and 2.987 seconds. Their respective components
were 0.007/0.014 local work, 0.939/0.958 resolution, 0.122/1.977 HTTP setup,
0.051/0.035 initial media, 0.001/0.002 write gate, and 0.001/0.001 previous tail.
No retry-timing change is justified. Connection 1 retained parts 1--4,
connection 2 retained part 5, connection 3 retained part 6, and connection 4
retained no media. The fourth allocation explains why the session reports three
reconnects although only two resumed media.

Read-only validation before recovery proved all six FLVs structurally probeable
as H.264/AAC. Part 2 retained four H.264 corrupt-frame reports; parts 2, 4, 5,
and 6 retained packet-DTS warnings that correspond to 16 logged timestamp-replay
records. Parts 1, 3, 4, 5, and 6 decoded cleanly. With no raw-copy evidence, the
part-2 damage cannot be attributed to TikTok transport or TikREC writing and is
preserved as issue #8 evidence rather than hidden by #17 recovery.

Supported manual finalization preserved every retained input and produced
`gracie-kf-v060-full-live.mp4`: 1,560,230,782 bytes, 10,008.064 seconds,
H.264/AAC at 720x1280, SHA-256
`066BC0AF501F4055901AB56A2FEDC4FF5D16A2B2B31722F90E192F30EA8944B5`.
Deep output validation passed with no findings. Retained-session validation
continues to report the historical failed lifecycle and part-2 anomaly honestly;
manual finalization records recovery and completion without rewriting that capture
result. At that point release authorization still required another owner-started
real LIVE to pass naturally through the corrected end path.

### Post-#17 natural-end release gate

Two later owner-started sessions ran through the normal deployed remote service
after #17 commit `b6d1f6f` was loaded. Neither used remote stop, a service
restart, or a manufactured outage. Both completed finalization and retained the
evidence below unchanged.

Session `ba3f26eb-c90b-4559-a60f-7c4cdf48c979` recorded `aishaaa.ts` in room
`7687819052166040350` for 1,771.461 wall-clock seconds. Its manifest is
`completed`, `interrupted=false`, `error=null`, `recovery_performed=false`, and
finalization `completed`; 198,182,914 bytes were retained in 17 FLVs. The later
Gracie job replaced this session in the service's single latest-job store, so
Aishaaa's exact historical `stop_requested` and `recovery_reason` job fields are
no longer available. Its connection log independently proves the terminal path:
three room-status 4 observations record confirmation states false, false, true,
followed by a media-free `offline` attempt. The resulting 195,853,511-byte,
1,697.712-second H.264 High/AAC LC MP4 is 720x1280 and passes normal and deep
validation. MP4 SHA-256 is
`DE6F1A82963E836612A26B785D92834ED633B3E8505B1CA9B865CCB5B3A0F878`;
the connection-log SHA-256 is
`D0DC7C9EAC9941DB5ED6460BF36F8254205662DB982BC40924AB3312BBEF3BED`.

Aishaaa allocated four attempts and reports three reconnects, but only attempts
1--3 retained media. Connections 1 -> 2 and 2 -> 3 are ordinary healthy-close
reconnects with no intervening attempt or recovery boundary. Their respective
component timings in seconds are: previous tail 0.001/0.001, local/backoff
0.008/0.024, resolution 1.287/1.371, HTTP setup 0.187/0.102, initial media
0.037/0.034, write gate 0.006/0.000, and total gap 1.526/1.531. The small local
components agree with removal of the old fixed healthy-close delay. Attempt 4 is
the terminal offline confirmation and is not a successful media reconnect.
There was no transient recovery, media-open failure, stall, source-selection
change, or retained-media attempt failure; every media connection used `hd1`
from `flv_pull_url`.

The Aishaaa source changed width repeatedly between 640 and 720 at constant
1280 height and changed advertised cadence from 25 to 15 fps. Those changes
created part boundaries without extra connections. All 17 FLVs decode. Parts 16
and 17 have four packet-DTS warnings matching four logged replay magnitudes:
part 16 has recovered 1,133-video and 1,110-audio reversals, while part 17 has
unrecovered tail reversals of 1,315 video and 1,280 audio timestamp units. They
occurred within connection 3, not at either reconnect. No raw copy exists, so
source-versus-writer origin remains unproven; this is issue #8 evidence rather
than evidence of a #17 resolver or end-state regression. The deep-valid MP4 and
clean decoder checks keep it non-blocking for this release gate.

Session `ed63dc43-eae5-4b46-a779-97c12d36dade` recorded `gracie.kf` in room
`7687851874133003038` for 1,722.302 wall-clock seconds. Its manifest is
`completed`, `interrupted=false`, `error=null`, `recovery_performed=false`, and
finalization `completed`. The durable service job additionally records state
`completed`, `stop_requested=false`, `recovery_reason=room_ended`, no resume,
and the same session and room identity. Current service health is idle and
available with no active recovery. The session retained 228,298,721 bytes in two
FLVs and finalized a 182,148,512-byte, 1,665.622-second H.264 High/AAC LC
720x1280 MP4. Normal and deep validation pass. MP4 SHA-256 is
`549D082EEC59EB9BC034C615B2FB4CC039BFC85858DA2D229642D4630D17CD2B`;
the connection-log SHA-256 is
`3F423AB3FF346FCC9A19E87E7D5D066C8C2784C1C91A923315BBC870EFE56439`.

Gracie allocated two attempts and reports one reconnect, but connection 1 is the
only media-bearing attempt. It closed normally, after which three room-status 4
observations reached false, false, true confirmation and connection 2 ended
`offline` without resolving or retaining media. The analyzer therefore reports
zero media reconnects. Both FLVs decode and pass packet-DTS checks without a
warning. The source changed from 720 to 640 pixels within connection 1 while
remaining `hd1` from `flv_pull_url`; there was no timestamp replay, stall,
transient recovery, media-open failure, or unexpected source selection.

These real sessions demonstrate that canonical room identity remains usable
across established capture, that same-room reconnect and trustworthy three-
observation offline completion work on the deployed #17 code, and that the
terminal checks are not miscounted as media reconnects. Neither log claims that
a username-page or signed-media 404 occurred in these particular runs. The
focused offline coverage still directly verifies both 404 branches, unchanged
different-room behavior, and fail-closed unverifiable identity; all 67 affected
tests and the full 748-test plus 19-subtest suite pass. No retry, resolver, HTTP,
writer, or finalization regression is evident. The required post-#17 release
gate therefore passed without changing production policy.

## Established-room resolver benchmark

Issue #18 adds a read-only diagnostic for the dominant resolution component of
an ordinary reconnect. It does not change capture, retry, resolver, HTTP, or
room-end behavior. Run it only with an already-established public page and its
canonical room ID:

```console
python scripts/benchmark_bound_resolution.py TIKTOK_LIVE_URL SAVED_ROOM_ID --samples 3
```

`--samples` is bounded to 1--20 and alternates bound/direct order to reduce
first-request and connection-warmup bias. `--json` emits the same safe facts in
structured form. A pair is comparable only when both paths return live results
with the same saved room ID, rendition label, rendition source, and exact signed
transport. Exit status is zero only when at least one such strict pair exists.
The tool never opens media, starts capture, accepts an output/session path,
writes evidence, or prints or persists a signed CDN URL. Rendition label,
source, and exact transport are compared only in memory and emitted as equality
booleans.

The current request sequences are:

1. Initial resolution validates the username LIVE URL, fetches that page, uses
   the public account lookup only when the page has no room identity, then
   fetches room/info for the discovered room and selects an HTTP(S) FLV.
2. Established ordinary reconnect concurrently queries room/info for the saved
   canonical room and the public account lookup. Fresh transport is accepted
   only when room/info proves the saved room live and the account lookup maps to
   that same room. The outer capture binding remains an independent same-room
   check before media opens.
3. Any offline, malformed, conflicting, unavailable, transient, or otherwise
   insufficient fast-path evidence invokes the prior full bound resolver. Its
   page-404 branch rechecks saved-room status and current account identity; a
   live saved room is not accepted when account identity stays unverifiable. A
   different live room preserves `live_changed`, only numeric non-live status
   for the saved room can enter end confirmation, and all uncertainty fails
   closed.
4. Direct known-room refresh calls room/info only for the canonical saved ID.
   It rejects an explicit conflicting room ID, malformed/non-numeric status,
   malformed data, and missing supported transport. A numeric non-live status
   remains typed offline evidence. It does not query the username/account, so a
   direct success alone cannot prove that current different-room semantics are
   equivalent; the benchmark refuses comparison when the bound path reports a
   different room.

Each request timer starts immediately before the injected HTTP opener and ends
after the response body read succeeds or fails. It therefore includes opener,
network, server, and body-read latency but excludes JSON parsing and rendition
selection. Total resolver time surrounds the entire call and includes those
local operations. Media HTTP setup is outside both resolver measurements and
remains separately visible in reconnect-gap evidence.

On 2026-09-21 neither of the two owner-provided creators was live, so no valid
live paired sample was available and the deployed service was not touched.
Read-only one-pair checks returned trustworthy status 4 for each saved room.
For Aishaaa, the pre-#19 bound resolution took 1.258 seconds: 0.307 page, 0.332
public lookup, and 0.616 room/info; direct saved-room room/info took 0.479
seconds. For Gracie, bound took 1.221 seconds: 0.337 page, 0.535 lookup, and
0.346 room/info; direct took 0.378 seconds. The respective 0.779- and
0.842-second differences show that skipped identity-discovery requests can be
material, but these offline/account-lookup paths neither select live transport
nor establish ordinary-reconnect equivalence.

The earlier live Aishaaa reconnects spent 1.287 and 1.371 seconds in fresh
resolution, while HTTP media setup took only 0.187 and 0.102 seconds. Direct
refresh cannot remove the room/info request, and the old logs cannot
retroactively divide their resolver totals by request. A live paired benchmark
is therefore still required before recommending a production fast path. Any
future change must explicitly preserve current different-room handling and
fail-closed identity behavior rather than treating the faster direct result as
automatically interchangeable.

### Live paired evidence

On 2026-09-21 the owner supplied `zoraidajazmine` and `slayyyboo22` specifically
for issue #18. Both initially resolved live through TikREC's normal anonymous
path, with canonical room IDs `7687797603433483038` and
`7687888196419586846`. Slayyyboo22 ended before paired measurement: seven
alternating attempts consistently returned trustworthy status 4 through both
paths and therefore contributed no live or savings sample. No unrelated creator
was probed.

The first Zoraida run exposed a diagnostic-only bug: `comparable` required the
same live room but did not also require its already-reported label, source, and
exact transport equalities. The predicate was corrected before evidence was
accepted, a regression test now rejects a different exact transport, and the
pre-fix summary was discarded. This did not affect production resolution.

Two corrected runs collected 22 alternating live pairs. Every pair returned the
saved room with equal rendition label and source. Ten also returned the same
exact signed transport and are the strict comparable dataset; the other twelve
had a refreshed exact transport and were excluded without exposing either URL.
The strict subset contained eight bound-first and two direct-first pairs. The
two direct-first savings were 0.466 and 0.499 seconds, showing a material result
even when the direct request warmed the later bound requests.

The later 12-pair run supplied six strict pairs and is the primary summary.
Median and range in seconds were:

| Component | Median | Range |
| --- | ---: | ---: |
| Current bound total | 0.942 | 0.759--1.453 |
| Username LIVE page | 0.308 | 0.267--0.357 |
| Public account lookup | 0.259 | 0.183--0.759 |
| Bound room/info | 0.320 | 0.279--0.427 |
| Direct known-room total | 0.351 | 0.275--0.399 |
| Direct room/info | 0.350 | 0.275--0.399 |
| Per-pair time saved | 0.587 | 0.458--1.085 |

All current bound samples invoked the account lookup because the LIVE page did
not yield usable room identity. The earlier corrected ten-pair run added four
strict pairs and independently measured median savings of 0.766 seconds with a
0.499--1.142-second range. Across the two batches, the skipped sequential page
and account requests therefore reduced same-room live resolution materially;
the direct room/info request itself remained unavoidable.

For context, Aishaaa's ordinary reconnects spent 1.287 and 1.371 seconds in
resolution and 1.526 and 1.531 seconds end to end. Substituting the primary
direct median only as an illustration would remove 0.936 and 1.020 seconds from
those resolver components and imply about 0.590/0.511-second total gaps if every
other component and network condition stayed fixed. That cross-session
calculation is not a promised production result; the paired Zoraida savings are
the controlling evidence.

The measurements justified separate implementation/review, tracked in issue #19,
but not a direct-only substitution. Direct room/info proves that the saved room
is live and rejects an explicit conflicting identity, yet it does not prove that
the username/account still maps to that room. A production design must retain a
current account identity check, potentially overlapped with saved-room
room/info; a different account room must still produce existing `live_changed`
behavior. Saved-room offline, malformed/unverifiable evidence, conflicting
identity, account-check failure, or transport failure must fall back to the
full bound resolver and preserve three-observation offline confirmation and
fail-closed recovery. Issue #18 itself made no production change.

### Issue #19 implementation evidence

Issue #19 implements that design only for an established canonical room.
Saved-room room/info and current public-account lookup run concurrently, and a
fast result is accepted only when both prove the saved live room. Any
insufficient result invokes the prior full bound resolver. Initial resolution,
failure/outage retry timing, healthy-close policy, media open, writer/part,
finalization, three-observation room-end confirmation, and rendition ranking
are unchanged. Offline tests additionally ensure a different room's non-live
status cannot become saved-room offline evidence, and no signed transport enters
diagnostics or errors.

The still-live owner-supplied Zoraida room then supplied 12 alternating read-
only pairs against the same canonical room. All 12 matched room, rendition label,
and source; nine also matched exact in-memory transport and formed the strict
dataset. The three rotating transports were excluded without exposure. Strict
median and range in seconds were:

| Component | Median | Range |
| --- | ---: | ---: |
| Identity-safe bound total | 0.366 | 0.297--0.408 |
| Concurrent public account lookup | 0.281 | 0.203--0.367 |
| Concurrent bound room/info | 0.365 | 0.296--0.406 |
| Direct known-room total | 0.324 | 0.275--0.379 |
| Direct room/info | 0.324 | 0.274--0.379 |
| Identity-check overhead versus direct | 0.044 | -0.076--0.104 |

The concurrent bound total tracks the slower of its two requests rather than
their sum. Its 0.366-second median is 0.576 seconds below issue #18's comparable
pre-implementation 0.942-second median, while retaining current account
verification. Slayyyboo22 remained offline and was not sampled further. The
benchmark opens no media and proves resolver behavior only; no natural ordinary
media reconnect occurred, so that required production validation remains
outstanding and issue #19 stays open.

Normal deployment validation ran from `60d55cb` through the existing Scheduled
Task service, without changing service architecture. Zoraida session
`a19f366d-1484-47b2-8eb7-64d26e0a47eb`, room `7687797603433483038`, uses
`C:\Users\Leandro\Videos\zoraidajazmine-v060-issue19-natural-reconnect-validation-20260921.*`.
It reached natural room end after 2,210.858 wall seconds with
`stop_requested=false`, `interrupted=false`, `error=null`, and completed
finalization. Connection 1 retained 288,436,284 bytes, then three numeric status-4
observations reached false, false, and true confirmation. Connection 2 ended
`offline` without resolution, media open, or a retained part. The gap analyzer
therefore reports zero ordinary reconnects: the manifest reconnect count of one
is only the terminal room-end attempt and supplies no #19 timing sample.

The sole FLV passed structure and decoder validation. Its packet-DTS check warned
about a 1,480-unit video reversal and 1,399-unit audio reversal, exactly matching
two recovered timestamp replays recorded inside connection 1; neither occurred
at a reconnect. With no raw copy, their origin remains unproven issue #8 evidence
and is not attributed to #19. Standard and deep validation of the finalized MP4
both passed. FFprobe reports 2,191.564 seconds, 288,187,757 bytes, H.264 High/AAC
HE, 432x864, 25 fps, and 48 kHz stereo. SHA-256 is
`65915E23AFF361B3AC994FAB1F07123555D0FB15A220E4761F9799AB4A7D7A35` for the MP4,
`FEED2FCBD452C240C82053A5A9622E1D9247F33F5F28405562EE56E234037A47` for the FLV,
and `C19A800CA40F283E56123FB897991BA4A74F5F39D88DD7FDA21C04FED776AE2F` for
`connections.jsonl`. No remote stop, service restart, network change, or other
manufactured failure was used. The natural ordinary-reconnect gate remains
outstanding, so issue #19 stays open.

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

For a service-owned validation session, `tikrec remote start --raw-copy` opts in
without accepting an arbitrary remote diagnostic directory. The service writes
the numbered raw and arrival files directly beside the session's retained FLVs,
`connections.jsonl`, and `session.json` in `<stem>.parts`; the finalized MP4
remains at the requested sibling output path. Durable job intent records the
boolean opt-in so a safely resumed capture continues using the same evidence
directory. Without the flag, remote capture performs no raw copy. This is the
issue-#8 workflow and roughly doubles media storage; it does not alter retry,
parser, writer, finalization, or default capture behavior.

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
