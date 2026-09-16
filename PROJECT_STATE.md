# TikREC current state

Last reviewed: 2026-09-16. This is a short handoff record, not a replacement
for [ROADMAP.md](ROADMAP.md), [SPEC.md](SPEC.md), [SERVICE.md](SERVICE.md),
[SESSION_MANIFEST.md](SESSION_MANIFEST.md), or
[CONNECTION_LOG.md](CONNECTION_LOG.md).

## Coordination

- **Active issue/task:** Issue #14, recover the active FLV writer partial after
  abrupt service death. It blocks v0.5 release readiness.
- **Status:** Real deployment validation stopped in phase B. Restart preserved
  the original job/session/media but startup reconciliation rejected the normal
  active `.part-0001.flv.partial` as ambiguous and did not resume.
- **Paused, non-blocking issue:** Issue #13 remains open, but active random-LIVE
  screening has stopped. Resume it opportunistically only when normal use
  exposes genuinely distinct simultaneous public source media.
- **Open evidence issues:** Issues #9 and #8 retain their real stall-boundary
  and timestamp-replay completion criteria. Collect that rare evidence during
  suitable future recordings; neither issue blocks ordinary v0.5 readiness.
- **Pending owner action:** None. Preserve the failed-validation artifacts and
  durable job state; no release action is authorized.
- **Next queued task:** Implement issue #14 conservatively, then repeat the
  abrupt restart, network-outage, graceful-stop, and deep-validation phases.

GitHub issues and this file are authoritative for active/pending work. Reconcile
this file, ROADMAP.md, relevant open issues, and repository state before choosing
new work; calendar entries are reminders only.

## Released version and development target

- **Package version:** v0.4.0, from `tikrec.__version__`/packaging metadata.
- **Tagged version:** annotated `v0.4.0`, which peels to
  `9f8e4104f8bc24f439a3e927ca72da29257c41fa`.
- **GitHub Release:** published `TikREC v0.4.0` for `v0.4.0`.
- **Current released version:** v0.4.0; its package version, tag, and GitHub
  Release are synchronized. Historical GitHub Releases for v0.3.0 and v0.3.1
  are also published from their existing tags.
- **Development target:** v0.5.0 environment survival/resumability. It is
  unfinished and must not be described as released or tagged.

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
- **Implementation gap:** `discover_parts()` rejects every `.partial` artifact
  before establishing whether the proven writer-owned active part is safely
  recoverable. Issue #14 must define evidence-preserving clean/truncated partial
  handling without weakening ambiguity checks.
- **Validation still required after #14:** repeat abrupt restart and prove
  same-session continuation, then exercise a real temporary network outage,
  graceful stop/finalization, retained-session validation, and deep output
  validation. No outage or completed-output claim was attempted in the failed run.
- **Release bookkeeping after validation:** synchronize the v0.5.0 package and
  release documentation, rerun required checks, review the exact release commit,
  then create the annotated tag and published GitHub Release in a separately
  authorized release action. No version, tag, or release changed here.
- **Optional non-blocking evidence:** issue #9's real raw-copy stall-boundary
  check, issue #8's replay with matching raw bytes, and issue #13's distinct
  rendition comparison remain open for opportunistic collection.

## Durable decisions and risks

- TikREC supports one manually supplied public LIVE; creator monitoring,
  future-LIVE automatic recording, and authentication remain deferred.
- Automatic resume requires the same canonical room ID and valid retained
  evidence. Active writer partials currently remain preserved and blocked even
  when structurally complete; issue #14 owns that release blocker.
- Raw-copy diagnostics are best-effort and record local processing boundaries,
  not provable source-byte arrival.
