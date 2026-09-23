# Issue #27: battle-linked H.264 corruption

2026-09-22 Moe investigation, extended 2026-09-23 with the owner-started Kayla
raw-backed session. **Historical forensic record; finite product blocker #27 closed.** v0.10 simultaneous
validation/readiness is paused. No product code, release, tag, original media,
or durable job/automation evidence was changed by this investigation.

## 2026-09-23 product decision and bounded acceptance

Independent fresh-context review removed raw-backed Moe reproduction from the
v0.10 prerequisite. Historical Moe attribution remains unresolved and is now
non-blocking issue #28. Issue #27 was narrowed to preserving successful
finalization input-decoder health and making validation scope explicit. No
speculative media dropping/reset policy or v0.9.1 corrective release was chosen.

A disposable finalization of copies of Kayla `part-0001.flv` (640x1280) and
`part-0002.flv` (720x1280) reproduced the mixed-configuration path. It
completed and produced a 7,334,499-byte MP4 whose full output decode passed.
The manifest retained `completed` lifecycle and finalization while recording
`degraded` input decode with 21 classified H.264 messages: concealment, intra
prediction, macroblock, and reference. Session validation still fails on the
damaged retained part; automated checks do not prove visual integrity. SHA-256
of both original FLVs was unchanged: part 1
`f7cd07c802ade7afa0bba1c93c6a794ab8b2657d857c49ae68d4f1d2780bd835`,
part 2 `6ab4c090fda7065cdffb44d7e9d87f8766566221b474230968fac8571ec1e13b`.
Disposable output and summary are in the existing diagnostic directory under
`product-check-20260923`.

## Conclusion and limitations

The investigation-state statements below describe the pre-decision forensic
handoff. The product decision and current issue status are recorded above.

### Kayla raw-backed session (owner started after the blocked Codex attempt)

The 2026-09-22 Codex launch attempt was blocked before process creation. The
owner subsequently started the authorized `kaylakreynes` capture through the
normal remote CLI with `raw_copy_enabled=true`. Historical slot state was later
superseded by Phoebe jobs; Kayla's own files establish the outcome. Session
`40173c3c-24f6-47d7-aa49-e054bc999b69`, room
`7688429147089046302`, began in `slot-1`. Its manifest reports natural
`completed` status, no interruption or error, 34 parts, successful finalization,
three allocated connections/two reconnects, `recovery_performed=false`, and
8384.464 s wall elapsed. Connections 1 and 2 contain media and ended at clean
EOF; connection 3 contained no media and confirmed the room offline after three
status-4 observations. The gap before connection 2's first retained media was
0.006633 s. Ten source timestamp replays were recorded in parts 4, 7, 13, 19,
and 26; they were retained, not repaired or suppressed. Final MP4 is
1,044,473,468 bytes, 720x1280 H.264/AAC, with 8150.733 s media duration.

Original output: `C:\Users\Leandro\Videos\kaylakreynes-issue27-raw-20260922-213725.mp4`;
parts directory: same stem plus `.parts`. All 41 original files were SHA-256
hashed before forensic processing and rehashed afterward, with matching values.
The complete hash list, read-only audit scripts/results, decoder logs, and
disposable stills are under
`C:\Users\Leandro\Videos\TikREC-diagnostics\issue-27-kayla-20260923`.
Key original SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| MP4 | `9437d66d42200bd829a2062fc1162e2e635aa523a0ca55c9a2c67983801ff80f` |
| `connection-0001.raw` | `2ec805c4c0bd744ca0b034da81000244073f6dde1117646764cbe283793004d1` |
| `connection-0002.raw` | `68c6f44b37f364eb6826a072937b09b9428bd7fb7fed35dcf76caaa76edff12f` |
| `connections.jsonl` | `9f7b7b8dc95bc85b6cccde51db316b9ecefe008917518e7936bffd22407da95c` |
| `session.json` | `d82a4869b93ef114162731d2c9066b53c8903b965804463f4c83b9b4ec469939` |

The two raw copies have 315,313,991 and 667,212,055 bytes. Their arrival
sidecars record 469,273 and 970,339 byte arrivals respectively, covering every
raw byte contiguously, with one `read_end=eof` each. Both raw files end at
complete FLV tag boundaries. No incomplete tail or pre-keyframe media was
withheld.

**Exhaustive raw versus retained result:** all 331,395 source audio/video media
tags match retained tags one for one, in the same order, with identical FLV
type and payload SHA-256 and exactly expected per-part timestamp rebasing.
There are zero unmatched retained media tags, omitted source media tags, or
timestamp mismatches. All 34 AVC configuration events match the raw order and
payloads; the two distinct configurations alternate with 640x1280 and
720x1280 High/3.1 video. The 640 configuration payload and avcC are byte-for-byte
identical to Moe's sole configuration (`19749999...` and `870a4f92...`). The
original AAC configuration on each connection is copied at each part start;
only the initial pre-part script metadata tag of each connection is omitted.
All 4,151 marked video keyframes contain actual IDRs, all IDRs are marked,
and no in-band SPS/PPS or NAL-length anomaly was found. Source NAL types are
1, 5, and 6. The largest positive video DTS step is 0.997 s on connection 1
and 3.400 s on connection 2, unlike Moe's 387.980 s jump.

Retained-session validation reports complete session evidence but **fails media
integrity** on H.264 decode errors in ten parts. Standard MP4 validation passes.
Deep MP4 validation and a separate single-thread full MP4 decode both pass
without decoder messages: mixed AVC configurations caused normal finalization to
decode and re-encode all 34 parts into one 720x1280 MP4, so the output bitstream
is decodable while preserving already damaged imagery. Full independent decodes
of both untouched raw files log 43 + 58 = **101 H.264 errors** in the same
normalized sequence as all matching retained parts. Raw-source and MP4 stills
near 36.6 s show the same severe vertical-column/smearing image. MP4 deep
validation therefore cannot certify visual integrity in this re-encoded case.

Raw-source error clusters (source PTS seconds; grouping gap 2.5 s):

| Connection | First–last logged PTS | Messages | Following AVC change / IDR |
| --- | --- | ---: | ---: |
| 1 | 3898.701–3899.297 | 12 | 3899.432 |
| 1 | 3925.089–3925.757 | 12 | 3925.888 |
| 1 | 5100.594–5101.236 | 10 | 5101.437 |
| 1 | 5777.006–5777.611 | 9 | 5777.812 |
| 2 | 7233.558 | 1 | 7233.696 |
| 2 | 7944.947–7944.957 | 3 | 7945.666 |
| 2 | 9154.117–9154.895 | 16 | 9155.030 |
| 2 | 9567.483–9568.187 | 14 | 9568.320 |
| 2 | 10426.330–10427.060 | 13 | 10427.194 |
| 2 | 10983.514–10984.085 | 11 | 10984.219 |

These short clusters occur in the 640x1280 source rendition shortly before
source switches to the 720x1280 configuration and a real IDR. The next source
configuration/IDR recovers; TikREC already starts a new part there. Arbitrarily
discarding the preceding damaged source frames would conceal lost media and is
not an accepted mitigation. No deterministic, lossless improvement is proven.

Disposable contact sheets show clear two-person split-screen and occasional
four-person compositions, including samples around MP4 03:00–10:00,
30:00–50:00, and 65:00–90:00. The FLV lacks a visible battle score/timer or
other decisive battle UI in these samples; multi-guest composition alone cannot
establish that a TikTok battle occurred. Treat Kayla as a **corrupt raw-backed
baseline, not confirmed battle acceptance evidence**. Precise battle entry,
duration, and exit cannot be assigned; the earliest visible corruption sample
is about MP4 00:36.6 and recovery follows the next source configuration/IDR.

**Kayla causal classification:** the public raw source itself delivered the
malformed H.264 and matching visible columns; TikREC did not introduce Kayla's
corruption or alter any decodable source media. This is strong supporting
evidence for, but does not prove, source origin in Moe because Moe has no raw
copy. Kayla's short switch-adjacent clusters differ from Moe's long error
regions, single AVC configuration, and large DTS gap. No product-code fix or
v0.9.1 corrective release is implicated by Kayla. Keep #27 open and v0.10
paused pending raw-backed Moe attribution or an explicitly approved source
limitation policy. Issues #8 and #13 remain separate.

Two later Phoebe automatic sessions superseded Kayla in the latest-per-slot
`/recordings` view: `315cb0a9-9c19-44ef-b2f8-d44ef64747e9` in slot 2
(`phoebelightt-20260922-222123`) and
`06803a96-1c26-4117-ba53-a0ade345d327` in slot 1
(`phoebelightt-20260923-030231`). Their own manifests show natural
completion/finalization, their MP4s and parts exist, and standard MP4
validation passes; no deep or simultaneous-readiness claim is made.
Read-only health showed capacity 2, active 0, available 2 on 2026-09-23.
`/recordings` is an operational snapshot, not a durable recording history API;
retained `session.json` and `connections.jsonl` remain the historical evidence.

### Moe findings

**Causal class 5: unresolved without raw source.** Corruption already exists in
the retained FLV, is visibly severe, and survives an independent fresh decoder
at actual IDRs. Finalization is not the origin: all original video NAL bytes and
order, and every AAC packet, are preserved in the MP4. Both full decodes emit
the same 10,352 error messages in the same order after normalizing decoder
addresses. No parser/writer defect or safe decoder-reset rule is yet proven.

The owner reports corruption during every battle. Diagnostic stills independently
confirm the reported vertical columns/smearing, but corrupted imagery alone does
not establish exact battle entry/exit. Match the timeline below against a new
raw-backed battle; do not infer source malformation from retained media alone.

`writer.py`, `flv.py`, and `flv_codec.py` are unchanged from published v0.9.0.
This creates possible shared exposure, not proof of a shared defect. If a defect
in that shared path is proven, recommend a v0.9.1 corrective patch before
resuming v0.10. Do not prepare a release now. Issues #8 (older replay/raw-source
attribution) and #13 remain separate and non-blocking/opportunistic.

## Preserved evidence

Creator `moealkaf`, session `c7927922-0381-410d-8020-0272aa96f265`, canonical
room `7688395628493949717`, `slot-1`. Paths below are under
`C:\Users\Leandro\Videos` unless stated otherwise. SHA-256:

| Artifact | Bytes / SHA-256 |
| --- | --- |
| `moealkaf-20260922-182902.parts/part-0001.flv` | 788,464,216 / `436CE495D57D355A8307B93280FE7A07A18AAEB801601384DE6627E9C14AC1EE` |
| `moealkaf-20260922-182902.mp4` | 787,935,979 / `2851D638042048C526EDF766EC4486744B0D8A44DCFE8D6940545937823B1D6E` |
| sibling `session.json` | `53841FAB8396080ECFC04C970A3135F12AC4CD8B455FB07E15F61D3B991AFBFF` |
| sibling `connections.jsonl` | `2864939FC38E2BD5D27061EFE248F591642B241989D88268D2FF22932603F67A` |
| host `%LOCALAPPDATA%\TikREC\job.json` | `810ACD415D50BAE1C097C34C2A08E2EED4E3CB5433E027E9F65E2815CEA3B684` |
| host `%LOCALAPPDATA%\TikREC\automation.json` | `6410EAA084493D7CD16F834A9B91829CBBA0CB4B2C21B1EA57C556C8EC0F2C39` |

`job-2.json` was absent. Originals were read-only; excerpts/stills and diagnostic
scripts/results live in `C:\Users\Leandro\Videos\TikREC-diagnostics\issue-27-20260922`.
The directory also preserves pre-change configuration and durable-state copies.
Media and verbose local diagnostic output are not committed to GitHub.

Final rehashes of all six artifacts above exactly match the pre-experiment
hashes. The Scheduled Task definition hash also remains unchanged. Fifty focused
offline FLV/codec/writer/validation tests pass with isolated configuration and
temporary roots; `git diff --check` passes. There is no product code change, so
no new regression test or full-suite/fix-acceptance claim is made.

The session completed/finalized naturally without interruption, stop request,
or job/finalization error. Retained-session/deep MP4 validation fails; standard
MP4 structural validation passes (640x1280 H.264, 48 kHz stereo AAC, 6250.443 s).
Manifest elapsed capture time is 5886.833 s; it is not MP4 timeline duration.

**Correction to the earlier record:** there was no startup recovery, but there
was transient network recovery at the end: connection 1 ended with truncated
FLV data (four missing bytes), recovery entered, three status-4 offline checks
confirmed room end, and connection 2 contained no media. The recorded recovery
episode lasted 16.109 s. `recovery_performed=false` does not mean no network
recovery. There were two allocated connections, one reconnect, zero timestamp
replays, and no raw copy.

## Complete decoder map

All 136,368 video frames were decoded, not just sampled. FLV per-output-frame
logs identify 6,539 frames carrying 10,352 error messages, grouped below using
a 2.5-second gap between logged frames. Positions are FLV byte offsets; indices
are zero-based decoder output-frame indices. Times are retained FLV PTS seconds.

| Group | First–last logged PTS | Output indices / packet vicinity | Logged frames / messages | Next log-free IDR PTS |
| --- | --- | --- | --- | --- |
| A | 1503.753–2180.737 | 37548–47700 / 206328890–293037961 | 4266 / 6805 | 2180.937 |
| B | 2568.809–2568.872 | 57351–57352 / 345008578–345044106 | 2 / 3 | 2956.882 |
| C | 2957.415–3287.149 | 57361–62305 / 345112837–387567229 | 2271 / 3544 | 3287.426 |

These are **decoder-log output-frame vicinities**, not an assertion that the
packet attached to each reordered output frame caused its log. H.264 B-frame
reordering prevents that inference. First log: `error while decoding MB 0 1,
bytestream -13`; last: `error while decoding MB 16 30, bytestream -6`.
The MP4 has the identical normalized error sequence; video packet PTS is uniformly
FLV PTS minus 0.020 s. MP4 error-region correspondence follows unchanged NALs,
packet order, that timestamp mapping, and matching full decoder errors.

There is a **387.980 s forward video DTS jump** from 2568.769 to 2956.749
(tag ordinals 117523 to 117529; offsets 345044106 to 345067028), both actual
IDRs. Therefore the B-to-C gap is not hundreds of seconds of clean decoded
video. Two other >1 s video DTS gaps, 1.720 s at 1140.006 and 1.480 s at
2296.961, are outside the logged-error groups. No timestamp replay is inferred.

## Complete configuration and NAL inventory

Every FLV tag was traversed, including all configuration events, not merely
changed configurations. There are 136,369 video tags, all legacy codec ID 7:
one AVCPacketType 0 and 136,368 type 1; no enhanced-video switch or type-2 EOS.
There are 137,368 audio tags, comprising one configuration and 137,367 packets.

The **only AVC sequence header** is tag ordinal 1, byte offset 13, retained
timestamp 0. Connection evidence records original configuration timestamp 0.
Media was rebased by 404156 ms; adding that base to the clamped configuration
timestamp would be incorrect. For retained media, source DTS = retained DTS
+ 404156 ms.

- Full FLV video payload SHA-256:
  `1974999982d412837eaebd62e2c5df64ecd0e07b0b948c3857c70484b0fae799`.
- avcC SHA-256:
  `870a4f92a24b18d64bad87ae74a49a489803f331bc0e61cdcee57c2972c6521e`.
- No preceding header exists, so repeated/identical-to-previous is inapplicable.
- High profile 100, compatibility 0, level 31 (3.1), four-byte NAL lengths;
  SPS ID 0, 640x1280 progressive, 8-bit chroma format 1, four reference frames,
  four-bit frame numbers, POC type 0 with six-bit POC LSB, gaps disallowed.
- SPS: `6764001facd940a00a1a6a0c0e0c8000000300800003e8078c18cb`;
  SHA-256 `db683f461c850c986820d0495653236c5744a3f44a530a1e2591d04081d2f13d`.
- PPS: `68ebecb22c`, PPS ID 0 references SPS 0, CABAC enabled;
  SHA-256 `1df3e2046b09f71e98d1df40ce83bf52980d0360f8526af69abe1c337c1b64b0`.
  avcC trailing extension bytes: `fdf8f800`.

All 3,032 FLV media keyframes contain type-5 IDRs, and all IDRs have the keyframe
flag. No false keyframe or in-band SPS/PPS exists. NAL counts: type 5 = 3,032;
type 1 = 133,336; type 6 = 11,778. No NAL-length parsing anomalies occurred.
All VCL prefixes use PPS 0 and first macroblock 0; slice types are 3,032 I,
34,370 P, and 98,966 B. A bounded reference-frame-number check found no jumps
other than permitted IDR reset/modulo progression. This is **not** a full
MMCO/reference-list or entropy-coded macroblock audit.

The repeated-identical-header hypothesis is rejected for this retained session:
there is no repeated header to correlate with any cluster. The false-FLV-keyframe
hypothesis is also rejected here. There are 340, 2, and 166 IDRs respectively in
the logged packet spans A/B/C; ordinary subsequent IDRs do not immediately heal
the corruption. None of this proves what unretained raw source contained.

## Disposable reset experiments and visible correlation

Excerpts prepend the original AVC/AAC configurations, begin at an actual IDR,
copy source tag payloads/order unchanged, and only rebase timestamps. Each
excerpt was reread to verify payload hashes/order. Five-second excerpts:

| Name | Starting retained DTS | Decoder error lines |
| --- | --- | --- |
| before-first | 1498.729 | 0 |
| first-bad | 1503.637 | 54 |
| next-bad | 1506.281 | 64 |
| middle-first | 1800.809 | 55 |
| after-first | 2183.061 | 0 |
| second-bad | 2568.729 | 0 (only eight tags before timestamp gap) |
| third-bad | 2957.483 | 56 |
| middle-third | 3101.951 | 43 |
| after-third | 3289.698 | 0 |

First-bad starts at ordinal 72773/offset 206328890, source DTS 1907.793 s,
with NAL types `[6,6,6,6,5,6]`. Its still shows the reported colored vertical
columns. Third-bad shows severe black/gray columns. Before/after-first stills
show normal imagery. A direct MP4 still near 1505 s also shows vertical columns.
The short second-bad excerpt is not a clean-source finding: it crosses a large
gap, includes very few packets, and differs in decoder buffering/context.
Fresh decoder + original configuration + real IDR is insufficient to repair A/C;
therefore blindly splitting parts at these IDRs is not an evidence-backed fix.

## Finalization comparison and reproducibility

Packet SHA-256 comparison finds all 137,367 AAC packets identical. Exactly 3,032
whole video packets differ: remux inserts the original SPS/PPS at IDRs. Splitting
length-prefixed NALs proves all 136,368 packets retain every original NAL in
order, with no changed payload or unexpected addition. Every inserted SPS/PPS
matches the sole original configuration. AAC timebase rounding is about 0.5 ms;
video PTS mapping is exactly -0.020 s.

Local scripts and corresponding JSON/text artifacts are named `inventory`,
`slice_map`, `decode_map`, `boundary_report`, `compare_packets`, `nal_compare`,
`experiments`, and `mp4_decode_fallback`; `inventory.jsonl` and `slices.jsonl`
contain all packet neighborhoods, and `flv.errors.json` contains every logged
frame. `boundary-report.json` preserves neighbors around each boundary. Retain
this diagnostic directory alongside the original media for the next comparison.

Full FLV decode command (redirect stdout JSON and stderr separately):

```powershell
ffprobe -v error -threads 1 -select_streams v:0 -show_frames -show_log 16 -show_entries frame=pts_time,pkt_dts_time,best_effort_timestamp_time,pkt_pos,key_frame,pict_type:log -of json FLV
```

Full MP4 decode uses the same command **without `-show_log 16` or `:log`**.
Per-frame MP4 logging made no output/progress in full and two-second probes;
only those diagnostic processes were stopped. Regular full decode completed.
Both decoders return 0 despite errors, so stderr/log inspection is mandatory.
Packet comparison uses `ffprobe -v error -show_packets -show_data_hash sha256
-of json INPUT`. Read payloads at MP4 packet positions and FLV tag position +16,
verify packet hashes, then compare length-prefixed NALs as described above.
No `ffmpeg -f null -` corruption check was used. FFprobe's
[per-frame logging documentation](https://ffmpeg.org/ffprobe.html) defines the
log association, not precise source-packet causality.

## Deployed state and exact next raw-backed opportunity

Only while authenticated health proved both slots idle/available, normal CLI
removed `moealkaf` from the host-visible configuration at
`\\localhost\C$\Users\Leandro\AppData\Roaming\TikREC\config.json`.
`phoebelightt` and `C:\Users\Leandro\Videos` are preserved. The unchanged
**TikREC Service** task was stopped/restarted once while idle to load this
temporary exclusion, preventing automated Moe capture without raw evidence.
Task definition SHA-256 (UTF-16LE export):
`54FCCDE50E6B34BDA27A2BA9AB42A0D19B49A4727C450C741543AD05B6B4C443`.
Token/bind/network/recovery settings and job/automation files were not edited.

Two bounded Moe observations at Unix times 1790104198.728451 and
1790104573.0296533 were explicitly offline. No new recording was started.
Final checkpoint: healthy, capacity 2, active 0, available 2; monitoring cycle 16
completed with only `phoebelightt`, offline, and no pending/consumed room claim.

Next task: inspect health/recordings first and preserve any newly active job.
Do not re-enable Moe automation before raw-backed capture. At the next suitable
owner-authorized Moe LIVE/battle, verify a slot and sufficient free disk exist,
choose a fresh output name with no MP4/parts collision, and use the existing CLI:

```powershell
.venv\Scripts\tikrec.exe remote start --server http://100.123.31.16:8765 --token-file C:\Users\Leandro\.tikrec-service-token --output C:\Users\Leandro\Videos\moealkaf-issue27-raw-YYYYMMDD-HHMMSS.mp4 --raw-copy https://www.tiktok.com/@moealkaf/live
```

Replace the timestamp placeholder with the actual fresh timestamp. Record UUID,
room, slot, output/parts/raw paths, raw and arrival-file growth, and battle
entry/exit times. Preserve source connection bytes/arrival JSONL with retained
parts/manifest/connections/final output. Let useful battle media accrue normally;
finish naturally or use authenticated targeted `remote stop --session-id UUID`.
Never interrupt another slot, manufacture a battle/fault, or wait indefinitely.

Compare raw vs retained tag payload/type/order/configuration around the transition;
decode both independently. Only then choose a bounded fix or a candid malformed-
source policy. Any fix still requires a real battle with visibly clean frames,
passing retained-session and deep MP4 validation; offline tests alone cannot
close #27. Restore the intended Moe/phoebe monitored pair through normal CLI
only after the diagnostic decision, with any snapshot-changing restart strictly
idle. Preserve the original ordered configuration in `config-before.json`; do
not copy/edit that JSON over the live configuration or reset durable state.
