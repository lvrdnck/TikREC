# Issue #27: battle-linked H.264 corruption

2026-09-22 investigation, based on `a46f1b3`. **PARTIAL; blocker remains open.**
v0.10 simultaneous validation/readiness is paused. No product code, release,
tag, original media, or durable job/automation evidence was changed.

## Conclusion and limitations

### Supplemental Kayla attempt (2026-09-22, approximately 21:34 +02:00)

The owner authorized `kaylakreynes` for a manual `remote start --raw-copy`
investigation, without adding her to monitoring or replacing the future Moe
reproduction. Preflight found both slots safely available, 49,544,634,368 free
bytes, the preserved completed Moe job in slot 1, and idle slot 2. Monitoring
still contained only offline `phoebelightt`; no service restart was requested.

The execution tool rejected the capture command before process creation with
`blocked by policy`. The command would have selected a fresh timestamped output,
preserved pre-start durable-state copies, and invoked normal authenticated
raw-backed start. None of that command executed. A subsequent authenticated
recordings check confirmed active count 0 and the unchanged completed Moe job.
No bypass or alternate execution path was attempted.

**PARTIAL: no Kayla recording or media evidence was obtained.** Whether Kayla
was LIVE or battling, visible corruption, raw/retained decode, and payload/order
comparison were not established. There is no new causal classification or
v0.9.1 implication. Continue only when execution policy permits the authorized
capture; recheck slots/storage and use the requested normal raw-copy CLI path
with a fresh `kaylakreynes-issue27-raw-YYYYMMDD-HHMMSS.mp4` output. Preserve all
other sessions and monitoring, and do not restart the service. The Moe analysis
below and future raw-backed Moe reproduction remain applicable; #27 stays open
and v0.10 stays paused.

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
