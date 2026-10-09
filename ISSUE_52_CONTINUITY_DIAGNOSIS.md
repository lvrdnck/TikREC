# #52 — Offline continuity attribution and concurrent-run reconciliation

Completed 2026-10-09 for [PM task 6071249155](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6071249155). Sole assigned executor: the conversation delivering `7377d8c1`; analysis ID `continuity-20261009-7377`, [prospective owner checkpoint 6076897875](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6076897875). No parallel executor was recorded before that checkpoint. Both trial permissions are closed. **Offline diagnosis complete; operational coverage remains PARTIAL and rollout HOLD.** Engineering, restricted overlap and R20 acceptances remain unchanged.

## Conclusion and one recommended next action

**Received complete media is preserved through retention in both runs; their received coverage differs. No capture/retention or finalization content-loss defect is demonstrated.** Every complete AVC/AAC raw media tag matches a retained tag in payload, occurrence order and rebased DTS. Both outputs have exactly the retained video packet count and that many decoded video frames. The main duration differences already exist between arrival elapsed time and retained source-clock spans; the finalizer does not remove another 110/174 seconds. Partial access units at four transport failures cannot be counted as complete received media. Saved validation verdicts remain PASS, interrupted, visual not checked.

The causal classification is **mixed/unresolved before retention**: source-clock progression, buffered/repeated source delivery and missing received coverage at reconnect boundaries are measured. Network/CDN pacing versus local synchronous checks/I/O and concurrent-run interference are not separable from these records. The smaller MP4 durations do not establish 109.619/173.522 seconds of unique lost content. They also do not prove that upstream never produced content absent from both runs.

**Recommended next action:** PM commission one narrowly scoped, offline Windows throughput attribution of the accepted operational read/check path using a paced generated source. Measure read-return, policy/fence/SQLite checks, raw-sidecar writes and tag delivery separately against the normal transport path before choosing any correction. This is a recommendation for a separately assigned task, not execution or LIVE permission. No speculative timeout, retry, codec, storage-policy or pipeline change is proposed here.

## Evidence identity, ownership and coordination

Historical reports are preserved byte-for-byte: [A / e8f85c17](ISSUE_52_OPERATIONAL_SERVICE.md#supervised-operational-service-trial), [B / 7377d8c1](ISSUE_52_OPERATIONAL_TRIAL.md). Private manifests verify the **same actual creator and room**, not merely the public `example.creator` alias; all connections report rendition `hd1` / `flv_pull_url`. Two matching AVC configurations cover 720×1280 and 640×1280; matching AAC configuration and content anchors further establish shared delivered content. This does not prove identical delivery schedules or constitute a controlled A/B experiment.

| Saved identity | A | B |
|---|---|---|
| Catalog | `81d2421e-3bd1-4a7b-8f98-0a0032aa4bec` | `7e56c7c7-c98e-44ed-b4ee-098207fe823d` |
| Session | `1b3972c4-c613-4534-8007-d87fd133298c` | `dce63e94-3575-4a58-8edc-437fea917ad7` |
| Native / wrapper PID | 61464 / 39952 | 65844 / 40244 |
| Port | 18771 | 49155 |
| Native creation UTC | 2026-10-08 22:55:50.190124, saved pre-shutdown identity | 2026-10-08 23:02:04.0151244, prospective original handle / FILETIME `134359741240151244` |
| Admission / task / terminal accounting | One automatic receipt/session/task; zero units | One automatic receipt/session/task; zero units |
| Native exit provenance | Product complete retirement and exit-0 receipts; standalone process snapshot reports exited but native/wrapper exit codes **null** | Original native handle signalled/exit 0; wrapper Popen exit 0, independent confirmation at 23:32:09.607383 |

Both startup records identify actual launch `7458a5edf9582a80ee5a8af8e33f00037114d52e`, accepted executable `aefeebe597933b963e24c641cd3dca317f5db539`, fingerprint `6a92803377040eb8ce8553b3f90c8ceaf437883c37d25776600e890215d70151`. Source/test/packaging bytes remain unchanged. Neither documentation successor changes executable code. Current branch remains `codex/capture-journal-handoff`, diagnosis starts at `7377d8c121d67c6f04c91e4e7b5dbe0d1311d89c`.

B's actual private home was recovered from this execution's saved `launch.json` argv, then corroborated with `native-identity.json`, its catalog/session and `process-exit.json`. `<PRIVATE_TRIAL_ROOT>` was never used as a filesystem path. Both exact roots are recorded privately in the derived `identified-roots.json`; no disk-wide or unrelated-chat search was used. Complete saved retirement receipts were checked before read-only/immutable catalog examination; neither service was reopened.

All timeline dates below are 2026-10-08 UTC (local Brussels time is UTC+2, hence 2026-10-09 locally). UTC is explicit to avoid a date/zone ambiguity.

| Time UTC | Saved event / limit |
|---|---|
| 22:38:15 | Accepted R20 delivery `7458a5ed` commit |
| 22:54:19.817 | A setup records requested selected URL and new private home |
| 22:55:50.174 | A saved service launch; startup/ready corroborate source/PIDs/catalog |
| 22:55:53.291 | A capture manifest begins |
| 23:02:03.994 | B prospective service launch, wrapper acquisition immediately after |
| 23:02:07.866 | B capture manifest begins |
| 23:02:10.625 | B acquires original native handle and creation identity |
| 23:15:28.173 | A normal creator removal recorded; subsequent reload confirmation |
| 23:15:52.375 | A capture ends; original UUID stop receipt saved at 23:15:52.383 (receipt time is not proven send time) |
| 23:17:10.699 | A log first records completed finalization phase |
| 23:21:15.946 | A original-home shutdown intent; complete retirement at 23:21:16.038 and product exit 0 at 23:21:16.042 |
| 23:21:17.970 | A standalone process snapshot reports original processes exited, exit codes null |
| 23:22:09.502 | B creator-removal command completed; reload confirmed 23:22:25.188 |
| 23:22:25.190 / .264 | B single original-UUID stop request / acknowledgement |
| 23:22:25.277 | B capture ends |
| 23:23:30.257 | B log first records completed finalization phase |
| 23:24:54 | A documentation commit `e8f85c17`, while B supervisor still owns its window |
| 23:32:04.479 | B one original-home shutdown nonce; complete retirement at 23:32:04.560, product exit 0 at .562 |
| 23:32:09.607 | B prospective original native/wrapper exit-0 confirmation; confirmation is not kernel exit time |
| 23:37:32 / 23:38:27 | B documentation commit `7377d8c1` / delivery comment 6071187950 |

Capture overlap is **824.508597 s** (13:44.509). Native creation to A product exit overlaps B for about **1,152.027 s**; A's independent exit-code limit above still applies. Shared content sometimes arrives materially apart: the first common source video anchor arrives in B at 23:02:08.258, in A at 23:02:36.913, about 28.656 s later. Service lifetime, capture wall overlap and shared content arrival are distinct measurements.

The owner request in this conversation and B's saved `accepted-pm.json` establish the single bounded decision 6070585346 available here. A's setup/launch, B's prospective launch/control records and each durable automatic admission exist. No shared prelaunch authorization-consumption record is present in these evidence sets or the reconciled prelaunch coordination. An independently saved owner instruction/consumption claim explaining A's concurrent launch is **UNKNOWN** here; unrelated chats were not searched. Separate homes, per-catalog automatic claims and a clean Git tree provide no cross-chat permission lock. Catalogs establish one accepted start each; logs named `stop` are three lifecycle observations each, not three control sends. B records one stop request/ack and one shutdown nonce; A saves one stop command result and one shutdown intent. A's complete HTTP request/send history is unavailable.

The prior A Scheduled Task inspection is a **known scope deviation**. Its saved 206-task inventory and nine absent baseline Python PIDs do not identify those processes' purposes or exit causes. No fresh watcher/task/process inventory or control was performed. Do not transfer A's inventory claims to B.

Smallest future procedural correction: before any separately authorized operational trial, PM designates one executor, and that executor records one shared authorization-consumption checkpoint with decision/run ID before launch, visible across chats/homes. A fresh home does not create another allowance. No scheduler/locking subsystem or new trial permission is added.

## Per-connection transport and raw clocks

Times are seconds relative to each **capture manifest start**, not service launch. Initial connection start is earlier because resolution precedes manifest activation. Resolver duration is `resolved-started`. Retained first/last wall measurements are saved connection callbacks; detailed arrival algebra below instead uses the arrival sidecar's full-tag EOF boundary. HTTP-open callback is null in the injected operational source, so resolver completion to first media cannot be divided into HTTP-open, server buffering and local work. No resolver-only/no-media attempt appears; every connection has retained media. All raw arrival offsets cover each file contiguously to EOF.

| Connection | Start | Resolver | Retained wall first–last | End | Source DTS first–last V / A (s) | Raw bytes / arrival records | Outcome |
|---|---:|---:|---|---:|---|---|---|
| A1 | -1.001 | 0.977 | 0.447–761.060 | 761.084 | 2338.231–3060.182 / 2338.259–3060.219 | 81,095,742 / 120,033 | connection_error |
| A2 | 762.106 | 0.467 | 763.119–918.729 | 918.736 | 3102.250–3252.254 / 3102.289–3252.219 | 16,811,025 / 24,976 | closed |
| A3 | 918.745 | 0.471 | 919.593–945.838 | 945.846 | 3258.254–3280.255 / 3258.279–3280.209 | 2,778,248 / 4,014 | closed |
| A4 | 945.853 | 0.548 | 946.929–949.893 | 949.899 | 3278.255–3280.255 / 3278.289–3280.209 | 280,331 / 354 | closed |
| A5 | 949.908 | 0.350 | 950.569–953.462 | 953.468 | 3278.255–3280.255 / 3278.289–3280.209 | 280,331 / 354 | closed |
| A6 | 953.475 | 0.375 | 955.495–1095.998 | 1096.020 | 3292.255–3385.180 / 3294.289–3385.217 | 11,017,917 / 16,817 | connection_error |
| A7 | 1097.038 | 0.433 | 1098.688–1199.042 | 1199.075 | 3438.287–3536.423 / 3438.318–3536.458 | 10,361,427 / 16,210 | interrupted |
| B1 | -1.037 | 1.009 | 0.389–598.513 | 598.519 | 2714.240–3280.255 / 2714.279–3280.209 | 64,098,320 / 95,138 | closed |
| B2 | 598.528 | 0.371 | 599.262–723.454 | 723.477 | 3312.256–3385.980 / 3312.289–3386.017 | 9,120,098 / 13,998 | connection_error |
| B3 | 724.498 | 0.427 | 725.212–1044.254 | 1044.286 | 3438.287–3705.227 / 3438.318–3705.288 | 28,315,291 / 44,088 | connection_error |
| B4 | 1045.318 | 0.394 | 1047.106–1217.376 | 1217.399 | 3760.295–3897.165 / 3760.328–3897.158 | 14,987,430 / 22,748 | interrupted |

A1/A6 and B2/B3 fail with `IncompleteRead(0 bytes read)`. A2–A5 and B1 end cleanly; final A7/B4 are interrupted by the original UUID stop. A4 and A5 each redeliver the same 3278.255–3280.255 s source range: identical ordered VCL picture/DTS and AAC payload/DTS sequences (31 pictures / 46 AAC packets each). Their 280,331-byte raw files differ in non-VCL content; equal sizes do not establish byte identity. These are repeated snapshots, not fresh advancing two-second content. Last raw suffixes are retained untouched:

| Failed connection | Partial video source DTS (s) | Payload expected / received / missing bytes | Raw suffix incl. tag header | Peer evidence |
|---|---:|---|---:|---|
| A1 | 3060.249 | 41,277 / 3,685 / 37,592 | 3,696 | Exact prefix of complete B1 packet |
| A6 | 3385.220 | 12,694 / 568 / 12,126 | 579 | Exact prefix of complete B2 packet |
| B2 | 3386.020 | 36,156 / 17,701 / 18,455 | 17,712 | No peer complete packet in preserved common evidence |
| B3 | 3705.294 | 2,236 / 1,895 / 341 | 1,906 | Outside verified common-content range |

Each also lacks its four-byte PreviousTagSize. These incomplete access units never become complete parsed/retained tags; no synthetic completion or repair was performed. In particular, A's two truncated packets demonstrate a received transport boundary against a complete peer packet, not a writer dropping an already complete packet.

The recovery episode labels include useful recording. A's 157.657 s episode includes almost the whole A2 connection; its second 103.047 s episode includes A7 recording. B's 320.813 s episode includes B3 recording; the subsequent 173.109 s episode includes B4. `live.py` closes a recovery episode when a connection finishes with useful parts, including just before entering the next failure episode. These are **not missing-media durations**. Actual error-end to next connection-start is about 1.022/1.018 s in A and 1.021/1.032 s in B; resolver and first-media waits are separate table intervals. Clean EOF reconnects generally resolve immediately.

No within-connection gap between consecutive **complete media tag raw-copy arrivals** reaches one second. This excludes a hidden long complete-media arrival stall in these files, not local/network pacing below that threshold, a tag spanning a failure or missing upstream production. Absolute wall-minus-monotonic reference offsets vary only 0.010128 s in A / 0.007535 s in B. A large local wall-clock step is unsupported; source encoder clock accuracy and read-to-disk timing are not independently measured.

## Raw → retained → finalizer → MP4

Matching uses `(stream, SHA256(full media payload), source DTS)` in occurrence order **within each connection**, allowing only the executed writer's DTS rebase. All 13 retained parts match; every complete raw media occurrence is consumed exactly once. Metadata, cached/repeated codec headers, FLV headers/PreviousTagSize and incomplete tails explain container byte differences; payload equality/order, not file size, establishes retention. AAC/AVC configuration caching and unsigned timestamp clamping are handled separately. Every recorded IDR gate duration is zero and no complete media tag is excluded by a gate in these trials.

| Run/part / connection | FLV bytes | Geometry | Source base–max DTS (s) | Arrival wall span | Source span | Wall−source | V / A packets | Output frame PTS ordinal bracket (s) |
|---|---:|---|---|---:|---:|---:|---|---|
| A 0001 / C1 | 81,090,630 | 720×1280 | 2338.231–3060.219 | 760.609 | 721.988 | 38.621 | 10,830 / 16,922 | 0.000000–721.952000 |
| A 0002 / C2 | 16,809,614 | 720×1280 | 3102.250–3252.254 | 155.609 | 150.004 | 5.605 | 2,251 / 3,515 | 722.018668–872.022668 |
| A 0003 / C3 | 2,776,836 | 720×1280 | 3258.254–3280.255 | 26.250 | 22.001 | 4.249 | 362 / 561 | 872.089336–894.089336 |
| A 0004 / C4 | 278,917 | 720×1280 | 3278.255–3280.255 | 2.968 | 2.000 | 0.968 | 31 / 46 | 894.150278–896.150278 |
| A 0005 / C5 | 278,917 | 720×1280 | 3278.255–3280.255 | 2.890 | 2.000 | 0.890 | 31 / 46 | 896.216945–898.216945 |
| A 0006 / C6 | 5,330,124 | 720×1280 | 3292.255–3342.149 | 65.734 | 49.894 | 15.840 | 720 / 1,123 | 898.283612–948.152612 |
| A 0007 / C6 | 5,685,835 | 640×1280 | 3342.187–3385.217 | 74.625 | 43.030 | 31.595 | 1,055 / 1,010 | 948.221971–991.214971 |
| A 0008 / C7 | 10,360,012 | 720×1280 | 3438.287–3536.458 | 100.360 | 98.171 | 2.189 | 1,473 / 2,301 | 991.282638–1089.552638 |
| B 0001 / C1 | 64,096,904 | 720×1280 | 2714.240–3280.255 | 598.125 | 566.015 | 32.110 | 8,584 / 13,405 | 0.000000–566.015000 |
| B 0002 / C2 | 3,317,467 | 720×1280 | 3312.256–3342.149 | 49.157 | 29.893 | 19.264 | 449 / 701 | 566.080946–595.948946 |
| B 0003 / C2 | 5,783,540 | 640×1280 | 3342.187–3386.017 | 74.922 | 43.830 | 31.092 | 1,075 / 1,029 | 596.015616–639.808616 |
| B 0004 / C3 | 28,311,970 | 720×1280 | 3438.287–3705.288 | 319.047 | 267.001 | 52.046 | 4,005 / 6,258 | 639.876283–906.950283 |
| B 0005 / C4 | 14,986,014 | 720×1280 | 3760.295–3897.165 | 170.266 | 136.870 | 33.396 | 2,054 / 3,208 | 907.016985–1044.087985 |

Arrival span is first-to-last complete media full-tag EOF arrival. Source span is maximum retained A/V DTS relative to the part's video base, not a sum of audio and video durations. Output brackets partition decoded frame metadata by cumulative input video count; they corroborate timing/count boundaries but **do not prove pixel identity or independently identify every boundary picture** after re-encoding.

At the shared geometry boundary source DTS 3342.187 s, A6 and B2 roll into 640×1280; later reconnects return to 720×1280. All complete media across these switches matches raw. Nominal onMetaData is 25/1; saved finalizer argv uses x264 `fps=1000/1`, selected by its input-rate plan, and explicitly `-fps_mode:v passthrough -enc_time_base:v filter`. That rate parameter controls encoder nominal-rate/level selection, not a CFR playback acceleration. The shared concat filter scales/pads, resets each input's video/audio PTS to STARTPTS and joins segments; it does not preserve periods in which a disconnected connection supplied no media. Source audio/video initial offsets are reset independently (A part 6 audio begins at 2.034 s); this is an observed normalization, not a newly attributed content-loss cause.

| Part boundary | Actual arrival wall gap (s) | Source next base − prior max (s) |
|---|---:|---:|
| A 0001→0002 | 2.056638 | 42.031 |
| A 0002→0003 | 0.869128 | 6.000 |
| A 0003→0004 | 1.077126 | -2.000 |
| A 0004→0005 | 0.684299 | -2.000 |
| A 0005→0006 | 2.035164 | 12.000 |
| A 0006→0007 | 0.141000 | 0.038 |
| A 0007→0008 | 2.680549 | 53.070 |
| B 0001→0002 | 0.747892 | 32.001 |
| B 0002→0003 | 0.109000 | 0.038 |
| B 0003→0004 | 1.757535 | 52.270 |
| B 0004→0005 | 2.853979 | 55.007 |

Positive source jumps are absent from the joined output timeline; negative jumps represent repeated source ranges. Neither is elapsed retry time. A's source jumps net to 109.139 s; B's net to 139.316 s. This is the timestamp discontinuity at raw/part boundaries, not deletion of packets already received.

Saved assembly intents prove actual argv, `libx264`/AAC re-encoding and candidate caps 22,519,803,904 bytes (A) / 21,913,690,112 (B), far above actual output. Both writers have confirmed exit-0/cleanup records. Diagnostics streamed completely to the accepted decoder-health collector, whose recorded input decode is clean. **Only 16,384 stderr bytes are preserved as prefix:** A 259,291 total / 242,907 omitted, B 291,697 / 275,313 omitted. These omitted-byte counters are not dropped-frame counters. Final FFmpeg `dup`/`drop` summaries are unavailable; no zero-drop summary is fabricated. Ordinary progress text and unsupported late-SEI notices occur in the prefix; structured terminal progress was not saved.

New bounded packet/frame metadata inspection: A 16,753 retained video packets → 16,753 MP4 video packets → 16,753 decoded output frames; B 16,167 → 16,167 → 16,167. No **net** output video frame loss is supported. AAC is re-encoded, so input/output AAC packet counts are not conservation units. Output audio is 51,164 / 49,216 packets; sample padding, encoder delay, resampling/concat and per-part normalization prevent compressed-byte or packet-count identity claims. Unique audio-sample identity and all rendered pixels have not been exhaustively compared.

Replay warnings describe overlapping streams: A's two warnings describe one approximately two-second source replay; B's six describe three approximately two-second replay boundaries, with two referring to the same source range. Exact full-payload/DTS extra occurrences are A V=89/A=138 and B V=89/A=140; do not add stream durations or treat six warnings as six outages. Decoded output frame metadata still has 15 PTS backsteps within A part 3's ordinal bracket and 45 within B part 1, with some one-microsecond positive intervals, although output packet DTS is monotonic. This is observed replay/mux timing behavior; count preservation and saved decode PASS do not prove ideal presentation or visual integrity. No 110/174-second finalizer shortening follows from it.

These raw-backed, decoder-clean replay samples are relevant to #8's evidence method, but do not resolve its historical malformed-replay cause. #28 visual corruption/quality work remains separate and non-blocking.

## Duration attribution and residual uncertainty

For each part `W = last full media arrival − first full media arrival`, `S = max retained A/V DTS − video base`. Let `L` be manifest elapsed capture and `M` saved MP4 format duration. The disjoint arithmetic ledger is `(L−ΣW) + (ΣW−ΣS) − (M−ΣS) = L−M`. It uses arrival clock references, complete-tag EOF offsets and source clocks; timestamp/audio/video overlaps are never added as independent losses.

| Stage/measurement (seconds) | A | B |
|---|---:|---:|
| Capture wall L | 1199.083745 | 1217.410649 |
| Sum first–last arrival spans ΣW | 1189.045000 | 1211.517000 |
| Outside those spans: initial/final edges + all part boundaries L−ΣW | 10.038745 | 5.893649 |
| Sum retained source spans ΣS | 1089.088000 | 1043.609000 |
| Within-part arrival/source divergence ΣW−ΣS | 99.957000 | 167.908000 |
| MP4 format M | 1089.465000 | 1043.889000 |
| Final normalization/container duration correction M−ΣS | +0.377000 | +0.280000 |
| Measured wall−MP4 gap | **109.618745** | **173.521649** |
| Arithmetic residual | <0.000001 | <0.000001 |

Of the outside-span totals, inter-part arrival gaps sum to 9.543904 / 5.468406 s; initial/final edges account for 0.494841 / 0.425243 s. Resolver/backoff timing overlaps these boundary gaps and is not added again. The frame endpoints and MP4 format/edit/codec durations differ by fractions of a second, not hundreds: last decoded PTS 1089.552638 / 1044.087985 versus format 1089.465 / 1043.889. Probe `format.duration=0` on replay-bearing FLVs is unreliable; the parser's tag clocks and packet/frame endpoints are used instead.

An independent source-clock ledger agrees: A's first-base to final source max is 1198.227 s, B's 1182.925 s. Relative to wall these leave 0.856745 / 34.485649 s; subtracting net inter-part source jumps 109.139 / 139.316 s and applying output corrections yields the same totals. These are alternate views of the same intervals, not additional loss terms.

Arithmetic closure below one microsecond is a numerical identity, not measurement accuracy. Saved monotonic arrivals are quantized to milliseconds; paired wall/monotonic references vary by roughly 10 ms / 8 ms across A/B connections. Boundary timing carries that clock-pair uncertainty; source timestamp intervals do not calibrate upstream real time.

**Causal residual is not zero just because arithmetic closes.** The 99.957/167.908 s within-part divergence cannot be uniquely split among encoder-clock pace, network buffering, local processing/I/O and concurrent execution. The raw-copy boundary is after a synchronous HTTP read and checks; it is not a packet-capture wire timestamp. There is no saved independent clock calibration, HTTP read-duration trace, local work profile or resource/interference trace. Unique content absent from both runs is explicitly **unquantifiable**. Thus all measured durations are localized by stage, while root-cause allocation and upstream completeness remain unresolved.

## Verified common content only

Shared exact full media payload+DTS keys: **26,835**, comprising 10,684 video and 16,151 AAC keys, across source DTS 2714.240–3536.458 s. Some IDR packets carry differing supplemental NAL data despite the same coded picture. A second pass parses AVC length-prefixed NALs under each saved configuration and hashes length-delimited VCL NALs (types 1/5), separately from SEI/configuration. It verifies **10,749 common coded-picture/DTS keys**, source bracket 2714.240–3536.423 s. Consecutive VCL anchors establish common rendition/content, not just equal timestamp numbers.

Inside that verified source bracket, A lacks **739** coded pictures present in B: 630 at 3060.249–3102.183 s (41.934 s first/last missing-picture span), 89 at 3252.321–3258.187 (5.866 s), and 20 at 3385.220–3385.980 (0.760 s). B lacks **271** coded pictures present in A: source 3292.255 and 3294.255–3312.189 (270 pictures; 17.934 s first/last span). These are bounded peer-observed received-coverage differences, not entire elapsed outages or an A/B quality score. Single-picture intervals have zero first/last span but nonzero material; do not turn these spans into exact playback-loss durations or add them to the duration ledger.

AAC full-payload/DTS comparison in the shared exact-payload bracket finds 1,145 peer keys absent from A and 422 absent from B. This corroborates asymmetry but is not added to video spans. A1/A6 incomplete video prefixes match the complete B packets initiating two of A's missing ranges. The 3386.017→3438.287 s source-clock jump (52.270 s) is absent from both raw media sets; so is the 3280.255→3292.255 s range (12.000 s). These clock brackets do not quantify unique unseen content and cannot be attributed to upstream nonproduction. Repeated source pictures are retained, not silently deduplicated. Arrival lag changes across shared anchors, so these runs are not a synchronized controlled experiment; same-room/rendition does not establish no interference.

## Exact executed code inspected; no correction implemented

Trace-directed review uses the unchanged launch bytes: `operational_source.py` (bounded read/tag and fresh storage checks), `operational_policy.py` (both-scope free-space/native-path checks), `source.py` (HTTP `read1`, raw-copy/sidecar write boundary), `live_source.py` / `live.py` / `live_recovery.py` (shared room-bound transport/recovery), `writer.py` / `flv.py` (configuration/IDR/rebase), `finalize_media.py` / `journal_assembly.py` / `assembly_diagnostics.py` (actual normalization and diagnostic retention).

Ordinary transport defaults to 30 s timeout and timestamps raw chunks immediately after read return. Operational transport explicitly uses 5 s timeout, synchronous storage/path checks before reads, after reads/before raw writes and per tag, plus original capture fencing. Operational `http_opened_at` is not supplied. Recovery policy/room binding and writer semantics are reused; the trace contains no timeout failures and no gated complete-media discard. Static synchronous overhead is a candidate for measurement, **not a demonstrated performance defect**; neither timeout nor retry changes are justified. The retention comparison demonstrates no smallest correction to implement. If a later paced offline reproduction proves the critical path cannot sustain the offered rate, propose the smallest correction at that measured location while retaining the accepted storage/ownership guarantees.

## Reproduction, preservation and delivery boundaries

New external derived directory: `C:\Users\Leandro\TikREC-tests\continuity-analysis-20261009-7377`. Originals stay in their prior private homes. `identified-roots.json` resolves A/B; `originals-before.json` and `originals-after.json` cover **107 A files / 73 B files** (388,872,122 / 372,584,212 bytes), including catalog, markers, control, media and all saved trial evidence. Every size/hash is unchanged. **536 executable/test/packaging raw hashes** before/after are unchanged and match B's saved prelaunch baseline after normalizing path separators; accepted package fingerprint is unchanged. Historical trial reports are unchanged. No existing watcher/task/configuration/user recording was accessed.

Derived reproduction records: `analyze.py` / `timelines.json` (strict FLV PreviousTagSize parsing, exact raw/retained occurrence checks, sidecar offset coverage and read-only immutable catalog exports); `content.py` / `vcl-comparison.json` / `arrival-stalls.json` (AVC VCL anchors, complete-media arrival gaps); `attribute.py` / `attribution.json` / `common-content-comparison.json` (two ledgers and raw-key comparisons); `details.py` / `partial-boundaries.json` / `coordination-timeline-private.json`; `probe.py` / `probe-summary.json` / `saved-assembly.json`; `frames.py` / `frame-summary.json`; `preserve.py` / `preservation.json`. The private files retain exact paths/commands and identities; tracked prose retains privacy aliases. Helpers import only the standard library, not service/runtime state.

After substituting the saved local Python/tool paths, reproduce derived reads (do **not** rerun `bootstrap.py`, which creates the owner-state checkpoint):

```powershell
$analysis = 'C:\Users\Leandro\TikREC-tests\continuity-analysis-20261009-7377'
$python = 'C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe'
& $python (Join-Path $analysis 'analyze.py')
& $python (Join-Path $analysis 'probe.py')
& $python (Join-Path $analysis 'attribute.py')
& $python (Join-Path $analysis 'content.py')
& $python (Join-Path $analysis 'frames.py')
& $python (Join-Path $analysis 'details.py')
& $python (Join-Path $analysis 'preserve.py')
```

FFprobe executable SHA256 `171a9102fe291870ee4fa62e8a6814366e65247d692d5177cb2ca73567c2f3d5`, version N-124716-g054dffd133-20260531. **15 packet/stream/format inspections + two bounded output video frame-metadata inspections exit 0**, with exact argv/outputs recorded. Packet inspection selects only stream/PTS/DTS/duration/position/size/flags plus stream/container metadata. Frame inspection selects only video frame PTS/DTS/duration/type/geometry. No media was generated, repaired, remuxed or re-encoded. Saved deep verdicts reused; no validation/full-suite/B3/pilot rerun. Helpers assert complete-tag match/order, contiguous raw coverage, output frame counts and ledger closure.

Derived-file hashes and command provenance are in local `analysis-index.json`; this report plus concise PROJECT_STATE/ROADMAP/#52 and the normal vault are the only task-owned documentation updates. #52 stays OPEN, #48 paused, #51/v0.11.0 complete, #28 separate/non-blocking. No source/test/schema/storage/media/default changes, service reopen, LIVE, monitoring, installation, migration, retention, source-media upload, main/release changes or issue closure. Stop for focused PM review; no automatic successor.
