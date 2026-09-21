# TikREC current state

Last reviewed: 2026-09-21. This is a short handoff record, not a replacement
for [ROADMAP.md](ROADMAP.md), [SPEC.md](SPEC.md), [SERVICE.md](SERVICE.md),
[SESSION_MANIFEST.md](SESSION_MANIFEST.md), or
[CONNECTION_LOG.md](CONNECTION_LOG.md).

## Coordination

- **Active issue/task:** Issue #18 is the single active task: a read-only
  experiment comparing current established bound resolution with direct known-
  room transport refresh. Issue #16 remains open but is owner-paused/blocked
  pending this evidence because reconnect performance is not yet satisfactory.
  Issue #17 remains completed and closed by `b6d1f6f`; v0.6.0 remains untagged
  and unpublished, and no release action is authorized.
- **Completed blocker fix:** Established capture and startup recovery now retain
  the canonical room ID as an independent resolution anchor. A username
  LIVE-page 404 can use direct public status for that room and the public account
  lookup: the same live room reconnects, trustworthy offline status retains the
  three-observation end policy, a different live room uses existing live-changed
  semantics, and unverifiable state fails closed. Initial page 404 remains a
  permanent safe failure. An established media-URL 404 requests fresh identity
  resolution after the existing failure backoff; the 404 itself is never an
  offline claim.
  Focused resolver/LIVE/service/recovery coverage passes 308 tests and the full
  offline suite passes 748 tests plus 19 subtests.
- **Post-#17 release validation:** Sessions
  `ba3f26eb-c90b-4559-a60f-7c4cdf48c979` (`aishaaa.ts`, room
  `7687819052166040350`) and `ed63dc43-eae5-4b46-a779-97c12d36dade`
  (`gracie.kf`, room `7687851874133003038`) both ran through the normal remote
  service path and ended through three trustworthy offline observations. Both
  manifests are completed, uninterrupted, error-free, and finalized; the
  current Gracie job additionally records `stop_requested=false` and
  `recovery_reason=room_ended`. Aishaaa had two ordinary media reconnects at
  1.526 and 1.531 seconds, with only 0.008 and 0.024 seconds of local/backoff;
  Gracie had no media reconnect. Terminal offline attempts retained no media
  and are not counted as successful reconnects. Both MP4s pass normal and deep
  validation, and all 19 FLVs decode successfully.
- **Issue #18 diagnostic state:** A read-only benchmark now separates username
  LIVE-page, optional public-account lookup, room/info, and total timings while
  comparing room/rendition/source/transport only through safe facts. It cannot
  open media or mutate capture/session state. Both owner-provided rooms were
  offline during the bounded 2026-09-21 check: direct saved-room room/info was
  0.779 seconds faster for Aishaaa and 0.842 seconds faster for Gracie, but the
  bound paths invoked account lookup and no live transport equivalence was
  available. These are directional observations, not production evidence.
- **Preserved soak recovery:** Session `43248309-a69f-45cf-a4e2-f4fc35a82a40`,
  room `7687483539771624223`, retained 1,300,258,942 bytes in six unchanged FLVs
  across 10,031.395 wall seconds. Four allocated attempts produced three reported
  reconnects, but only two were successful media reconnects: 1.121 and 2.987
  seconds. Attempt 4 resolved a transport, then received HTTP 404 while opening
  the signed media URL and retained nothing. Supported manual finalization produced a
  1,560,230,782-byte, 10,008.064-second H.264/AAC 720x1280 MP4 with SHA-256
  `066BC0AF501F4055901AB56A2FEDC4FF5D16A2B2B31722F90E192F30EA8944B5`;
  deep output validation passes without findings. Retained validation remains
  honestly failed: part 2 has H.264 decoder errors and parts 2/4/5/6 contain
  stored-DTS reversals already represented by 16 replay records. This is
  additional issue #8 evidence without a matching raw copy, not caused by #17.
- **Completed release task:** Issue #15 is closed. The annotated v0.5.0 tag and
  published non-draft GitHub Release remain synchronized and unchanged.
- **Paused, non-blocking issue:** Issue #13 remains open, but active random-LIVE
  screening has stopped. Resume it opportunistically only when normal use
  exposes genuinely distinct simultaneous public source media.
- **Open evidence issues:** Issue #8 retains the raw-copy requirement needed to
  locate timestamp-replay corruption. The historical pre-#17 Gracie run still
  contributes its decoder/replay evidence without raw bytes. The new Aishaaa
  session separately recorded two recovered replays in part 16 and two
  unrecovered tail replays in part 17; their four packet-DTS warnings exactly
  match the recorded magnitudes, all parts decode, and the finalized MP4 deep-
  validates. With no raw copy, this is additional issue #8 evidence and is not
  attributed to #17. Issue #9 and paused issue #13 remain unchanged.
- **Pending owner action:** None immediately. v0.6.0 publication is paused; do
  not create its tag or GitHub Release. A future already-known public LIVE is
  needed for issue #18's paired live comparison.
- **Next queued task:** Run issue #18's safe paired benchmark when a suitable
  owner-known room is live, then decide whether a separately reviewed
  production fast path is justified. Keep issue #16 blocked and do not start
  v0.6.5 or v0.7.

GitHub issues and this file are authoritative for active/pending work. Reconcile
this file, ROADMAP.md, relevant open issues, and repository state before choosing
new work; calendar entries are reminders only.

## Released version and development target

- **Package version:** v0.6.0 release candidate, from `tikrec.__version__` and
  packaging metadata.
- **Tagged version:** annotated `v0.5.0`, whose tag object is
  `173d25f4736a2b900ffb381d98e218aaae31770c` and which peels to release commit
  `7e65248bb4061cf74e84986314db0b6b16d5fc02`.
- **GitHub Release:** published non-draft, non-prerelease `TikREC v0.5.0` for
  `v0.5.0` on 2026-09-19.
- **Current released version:** v0.5.0; its release-commit package metadata,
  immutable annotated tag, and GitHub Release remain synchronized. Historical
  v0.3.0, v0.3.1, and v0.4.0 releases remain published from their existing tags.
- **Release candidate:** v0.6.0 reconnect-gap measurement/reduction is prepared
  but remains untagged and unpublished; it is not yet the current released version.

## Issue #13 rendition investigation

- Owner sequencing decision on 2026-09-15: issue #13 is intentionally paused
  and non-blocking. Do not actively hunt random public LIVEs; resume only when
  normal use reveals potentially distinct simultaneous sources. TikREC still
  aims for the highest genuine public source quality and native FPS, without
  upscaling or synthesized frames. Escalate a measured quality/FPS conflict.
- Current production selection remains unchanged: known rendition labels form
  heuristic tiers, with deterministic source/label/URL tie-breaks. The public
  response evidence audited so far does not validate per-candidate resolution,
  native FPS, bitrate, codec, or reliability metadata.
- Current logs already retain selected label/source, per-part SPS dimensions and
  optional nominal cadence, plus completed-output codec/dimensions. Explaining a
  future stronger choice additionally needs a safe candidate inventory,
  selection-policy identifier, and verified metadata provenance without URLs.
- A prior real `hd1` service recording passes TikREC validation and measures
  640x1280 H.264 at 25 fps and about 1.07 Mbit/s overall. It proves delivered
  facts can be compared with a label, but it contains no alternative candidates.
- On 2026-09-15, `ninika_live` anonymously resolved through TikREC's existing
  public path. The room exposed `hd1` through `flv_pull_url` and `default`
  through `rtmp_pull_url`, both as HTTPS FLV, with no public HLS candidate.
  Aligned 30-second and three-minute samples showed that the two labels carried
  identical H.264/AAC media payloads. The longer samples delivered 720x1280
  H.264 High video at a measured 29.983 fps and about 1.999 Mbit/s average;
  startup was 0.406 seconds, the longest observed output-growth pause was 1.407
  seconds, and neither candidate disconnected, changed configuration, replayed
  timestamps, or failed decoder/DTS checks. Both stream-copy finalizations also
  passed deep output validation.
- A second anonymous comparison on `noahdksl` exposed the same two source/label
  candidates and no public HLS. The aligned 30-second files were byte-identical,
  including all 740 video and 704 audio payloads. Both delivered 640x1280 H.264
  High/AAC at a 40 ms median packet interval (nominal 25 fps), measured 24.631
  packets/s across the sample, and about 0.626 Mbit/s average. Both started in
  about 1.4 seconds and passed FLV structure, decoder, and DTS checks with one
  unchanged audio/video configuration and no timestamp replay. Representative
  stream-copy finalization produced a 30.037-second MP4 that passed deep output
  validation.
- A third anonymous comparison on `theo_fitness1` exposed the same alias FLVs
  plus the first public HLS choice. FLV and HLS carried matching H.264/AAC source
  content at 720x1280 and 15 fps in the short sample. Over the longer matched
  window, 3,894 video frames and 3,775 normalized AAC payloads agreed; both
  transports had the same cadence gaps and passed decoding/timestamp checks.
  HLS started in 2.813 seconds versus FLV's 0.610 seconds and was 18.964 seconds
  farther from the live edge. Neither disconnected, while maximum observed
  output-growth pauses were 10.828 seconds for HLS and 6.422 for FLV.
- The source changed configurations repeatedly within the selected `hd1` FLV:
  640x1280, 320x640, 432x864, and 720x1280 all appeared. TikREC stream-copy
  finalization preserved every configuration and passed deep output validation;
  a diagnostic HLS stream copy also passed.
- A fourth anonymous comparison on `sbomberbomp1` again exposed only alias
  `hd1`/`default` FLVs and no public HLS. The aligned 30-second files were
  byte-identical, including all 451 video and 703 audio payloads. Both delivered
  stable 720x1280 H.264 High/AAC at measured 15 fps and about 0.992 Mbit/s,
  started in 1.266 seconds, and passed structure, decoder, DTS, configuration,
  and timestamp checks. Representative stream-copy finalization produced a
  30.061-second MP4 that passed deep validation. Room metadata advertised
  `HD1` as 720p but supplied zero dimensions; earlier `hd1` media was 640 pixels
  wide, so the label claim remains unsuitable as verified quality evidence.
- A later attempt on `vandaelesir` found that the supplied LIVE had ended before
  comparison. The normal anonymous resolver and two short rechecks returned the
  same room with status 3; no candidates, transport URLs, media, or dataset from
  that attempt were collected.
- A fifth anonymous comparison on `brycebennet1` exposed only `hd1` through
  `flv_pull_url` and `default` through `rtmp_pull_url`, both as HTTPS FLV, with
  no public HLS. The aligned 30-second files were byte-identical, including all
  451 video and 704 audio payloads. Both delivered stable 720x1280 H.264
  High/AAC at measured 15 fps and about 0.922 Mbit/s, started delivering output
  in 2.984 seconds, and passed structure, decoder, DTS, configuration, and
  timestamp checks. Representative stream-copy finalization produced a
  30.059-second MP4 that passed deep validation. The conclusive alias result did
  not justify a longer duplicate-media comparison.
- A subsequent ordered screening pass checked six owner-supplied public LIVE
  pages without capturing routine inventories. `lxkt16`, `thorben1891`, and
  `thethomb` were live but each exposed only the familiar HTTPS FLV
  `hd1`/`default` pair, no HLS, and no additional quality tier. `wukiyampi`,
  `tim_tokii`, and `imullaa` did not yield a current room ID through TikREC's
  anonymous public path. No promising room, media capture, signed-URL artifact,
  or sixth dataset resulted from this screening.
- All five datasets show alias labels, and the same labels carry materially
  different dimensions, cadence, and bitrate across rooms. Dataset three
  supports the existing FLV choice for equal fidelity with lower latency, but
  one FLV/HLS run cannot establish global transport reliability. Production
  selection remains unchanged. Resume #13 opportunistically when normal use
  exposes genuinely distinct simultaneous source media; escalate if resolution,
  cadence, bitrate, codec, or reliability goals conflict.

## v0.5 and diagnostic handoff

- Durable service job intent, canonical public room identity, retained-session
  continuation, startup reconciliation, bounded network recovery, and safe
  interrupted-FFmpeg finalization reconciliation are committed in `b6f190b`
  through `a384dd3`.
- The opt-in raw-arrival diagnostic slice is separately complete: raw copies can
  record HTTP-read byte ranges/timing in `connection-NNNN.arrivals.jsonl` without
  interrupting capture. It supports issue #8 investigation but does not reduce
  reconnect gaps or alter resume/finalization policy.
- The 2026-09-15 offline audit found no missing slice and the full suite passed
  707 tests plus 19 subtests, but the 2026-09-16 real deployment run exposed
  issue #14 at the first abrupt-process-death boundary.
- **Failed phase-B evidence:** Task Scheduler stopped the actively recording
  deployed service without graceful cleanup. Restart kept session
  `41dd234c-3d8c-42c3-ba36-742de92367d7`, room `7685987454411344653`, durable
  `recording` intent, and the original 11,789,861-byte writer partial, but health
  reported `failed`/`ambiguous_state` and no new part or connection opened while
  the same room remained live. The partial ends at a clean FLV tag boundary,
  contains 3,765 media tags through 86.653 seconds, and passes decoder/DTS checks.
  It remains ignored/local under `runs/v05-deployment-allynwd04-20260916.parts/`.
- **Implemented #14 policy:** generic `discover_parts()` remains strict. Startup
  alone may recover the canonical next writer partial when durable recording job,
  manifest identity/lifecycle/paths/counts, connection evidence, output absence,
  artifact inventory, FLV structure, and FFprobe decoder/DTS checks all agree.
  It durably marks recovery first, atomically preserves the exact original under
  a session/index evidence name, admits only a separately copied complete prefix,
  and records its SHA-256 plus byte counts/discarded tail in manifest evidence.
  Clean and torn-tail cases resume at a fresh connection/next part; arbitrary,
  empty, malformed, unowned, conflicting, colliding, or nonregular artifacts block.
- **Offline verification:** 728 tests plus 19 subtests pass, including byte-exact
  preservation, truncated-tail salvage, recovery-restart idempotence, count/timing
  honesty, correct next part/connection allocation, and the fail-closed matrix.
- **Repeat abrupt-restart validation passed:** On 2026-09-19 the deployed service
  recorded `lilymaye207` as session `c3d05742-242e-4093-b8cb-69297f967e39`, room
  `7687184860712225537`. `Stop-ScheduledTask` left a 7,874,881-byte writer partial
  with SHA-256 `AC27A60670479A99A179AA53CEC838361A2EF85734752FF69EDF480FD0D44CB1`.
  Restart exposed `recovering/writer_partial_recovery`, preserved the exact bytes
  under the deterministic evidence name, published an equal 7,874,881-byte clean
  prefix with zero discarded bytes, and resumed the same session/room with
  `resume_count=1`, connection 3, and fresh `part-0002.flv`. The recovered part and
  resumed part both passed FFprobe decoder/DTS checks and began near timestamp zero,
  while status/media continued growing without ambiguous or failed recovery.
- **Preserved validation anomaly:** The resumed source later changed 720x1280 to
  640x1280 and back within connection 3. The short middle `part-0003.flv` has valid
  FLV framing, a source-marked keyframe start, and clean DTS but FFprobe reports H.264
  decoder errors; surrounding `part-0002.flv` and `part-0004.flv` decode cleanly.
  TikREC copies source payloads unchanged, so this run does not justify a recovery
  code change. A normal remote stop was used only to freeze evidence after the
  finding; its completed output was not deep-validated or claimed as the deferred
  graceful-finalization phase.
- **Temporary-network-outage validation passed:** On 2026-09-19 a new deployed
  `lilymaye207` session `73675685-5c7c-4310-b94f-dd749e2bc5b8`, canonical room
  `7687184860712225537`, was routed through a loopback HTTPS CONNECT proxy that
  covered both TikTok resolution and the selected media CDN while remote control
  stayed direct over Tailscale. Killing only that proxy closed a 6,293,414-byte
  `part-0001.flv`, entered durable `recovering_network/network_outage`, and held
  retained bytes and identity fixed through staged retries. Restoring the proxy
  produced an automatic same-room reconnect without a new start; connection
  allocation advanced to 8 (`reconnect_count=7`) and fresh `part-0002` grew from
  650,080 to more than 43 MB. Part 1 and a read-only probe of the actively
  growing part 2 both passed FFprobe decoder/DTS checks with near-zero rebased
  starts. The proxy was unavailable for about 93 seconds; the next CDN tunnel
  opened about 102.6 seconds after part 1's last retained-media observation, so
  that interval is an observed capture gap, not recorded media.
- **Final deployment validation passed:** The same session was remotely stopped
  through TikREC after more than 1,150 seconds of useful post-outage capture.
  Connection 8 closed as interrupted with completed `part-0002.flv` through
  `part-0004.flv`; the coalesced recovery boundary closed honestly as `user_stop`
  with retry attempt 7 rather than inventing source EOF. Its connection record
  proves successful same-room media from `1789820978.7953813` through
  `1789822129.9061882`. Manifest/job state retained the original session and room,
  4 parts, 8 allocated connections, 7 reconnects, completed finalization, and
  intentional interruption. All four FLVs passed decoder/DTS validation without
  warnings. The 159,231,842-byte H.264/AAC MP4 (720x1280, 1,200.636 seconds,
  SHA-256 `9B6C75049EFE5E7708938345B2642D0B1DDED8216D93EEFD8B4CF9204B701B3E`)
  passed deep validation without findings. The 103.366-second interval between
  pre- and post-outage retained media remains absent from the output timeline.
- **Validation-discovered fix:** Restarting the idle service initially exposed
  `reconnect_count=0` even though the completed manifest retained 7. Inactive
  status now restores that durable count without reading the manifest while active
  capture may atomically replace it on Windows. Focused tests and the full 729-test
  suite pass. The validation proxy was retired, user-level `HTTPS_PROXY` remains
  absent, and the Scheduled Task was restarted healthy/available in its normal
  environment.
- **Release finalization:** v0.5.0 tag `173d25f4736a2b900ffb381d98e218aaae31770c`
  was pushed and peels to `7e65248bb4061cf74e84986314db0b6b16d5fc02`; the verified
  non-draft GitHub Release is published. Issue #15 is ready to close.
- **Optional non-blocking evidence:** issue #9's real raw-copy stall-boundary
  check, issue #8's replay with matching raw bytes, and issue #13's distinct
  rendition comparison remain open for opportunistic collection.

## Durable decisions and risks

- TikREC supports one manually supplied public LIVE; creator monitoring,
  future-LIVE automatic recording, and authentication remain deferred.
- Automatic resume requires the same canonical room ID and valid retained
  evidence. Only the exact proven active writer partial is recoverable; all
  unowned or conflicting partials remain preserved and blocked.
- Raw-copy diagnostics are best-effort and record local processing boundaries,
  not provable source-byte arrival.
