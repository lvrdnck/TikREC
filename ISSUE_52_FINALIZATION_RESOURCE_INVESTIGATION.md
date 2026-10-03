# Issue #52 — bounded Windows finalization priority investigation

## Status and scope

Recorded 2026-10-03, 13:16 UTC. **Stage 1 investigation complete; #52 remains
OPEN and the single active issue for its next bounded slice.** #48 is OPEN /
PAUSED by owner decision, with all natural-recording criteria preserved. Its
approved policy remains raw-copy only for `gracie.kf`, monitored order
`wardsimons`, `gracie.kf`, Ward OFF. No #48 evidence search was performed here.
#28's corruption investigation remains unresolved. No release is authorized.

Source checkpoint: `ce24d0be20621f02d76cb126145547e4b6a4c901`, after the committed
coordination transition. Production modules, task, configuration and media were
not changed. All experiment inputs were generated synthetic fixtures; no LIVE,
retained recording or forensic artifact was used. The historical GPU incident
was already attributed to old TikREC's NVENC FFmpeg PID 62580 / parent 14876 in
`Desktop\antigravity\TikREC`, with `h264_nvenc -preset p6 -tune hq -rc vbr
-cq 18 -b:v 0`. That attribution remains intact; this CPU experiment does not
repeat or reinterpret it. See [the attribution comment](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5907805556).

## Current finalization and ownership

| Path / owner | Current behavior at the source checkpoint |
| --- | --- |
| `tikrec/finalize.py:26`, same AVC configuration bytes | Concat demuxer, `-map 0 -c copy -movflags +faststart`; no video encode. |
| Same function, differing configuration | Scale/pad to the maximum dimensions, reset each input's starting video/audio timestamps, filter concat, CPU `libx264` / AAC, faststart. Highest nominal input frame rate is supplied to x264; `-fps_mode:v passthrough -enc_time_base:v filter` preserves filter timing. |
| `tikrec/finalize.py:97` / Popen at line 120 | Shared synchronous FFmpeg launch/wait; no explicit priority class or thread cap. Bounded stderr diagnostics; owned child termination on exceptional unwind. Progress reporting adds FFmpeg progress/logging options when a callback exists. |
| `tikrec/capture.py:102` | Mark manifest finalizing, wait for finalizer, record input decode health, then mark terminal result. |
| `tikrec/recording.py:190`, `recording_worker.py:11` | Root writer lease covers capture and finalization. Durable job and `_active` ownership remain until completion/failure is persisted. That service slot remains unavailable during finalization; the other slot/HTTP handling are independent. |

CLI/manual recording, service automatic recording and recovery use the shared
finalizer. A temporary `.OUTPUT.partial.mp4` is published only after successful
FFmpeg completion and absent-destination checks. Retained parts remain in place.
There is no independent post-processing queue or ASR pipeline in current TikREC.
Lower scheduling priority can therefore extend slot and writer-lease occupancy;
it does not free capture capacity while the existing worker is finalizing.

### Actual deployed scheduling context

Read-only observation found Scheduled Task priority **7**, service PID **16480**
WMI base priority **6**. Microsoft maps task priority 7 to **Below Normal**.
Windows normally lets a child inherit a Below Normal parent when no class is
specified. The present Popen therefore already has an expected Below Normal
launch context under this task. This is an inference: direct native service
priority-class query was denied (`WinError 5`), and no production FFmpeg child
was active to measure. [Task priority mapping](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-priority),
[Windows priority inheritance](https://learn.microsoft.com/en-us/windows/win32/procthread/scheduling-priorities).

The explicit **Normal** experiment is a controlled alternative launch context,
not an observed baseline for the deployed service. Do not describe these results
as proving an improvement over its current scheduling behavior.

## Environment and reproducible method

- Windows 11 Home 10.0.26200; Ryzen 9 7950X3D, 16 cores / 32 logical CPUs;
  32,669,096 KiB usable RAM, initially 12,470,092 KiB free. No affinity changes.
- Python 3.12.10; existing FFmpeg/FFprobe
  `N-124716-g054dffd133-20260531`, GCC 15.2.0, x264 core 165, Windows GPL build
  from the existing WinGet yt-dlp.FFmpeg installation. Full version/configuration
  text is retained locally. No dependency installation or NVENC experiment.
- Workspace: `C:\Users\Leandro\TikREC-tests\issue52-priority-20261003\experiment`.
  Outputs, commands, owned PIDs/parent PIDs, native class samples, full stderr,
  fixture hashes, probe records, resource samples and validation reports remain
  outside Git and outside the production recording root.
- Two 16-second lavfi `testsrc2` / 440-Hz AAC FLVs: 1280x720 and 1920x1080 at
  30 fps, yuv420p, libx264 default quality/settings. Copy case uses two copies of
  the first part; encode case uses both. Source files are hashed before/after.
- Run current `finalize_parts` through its existing runner injection. Only the
  disposable FFmpeg child's explicit creation class differs: Normal `0x20` or
  Below Normal `0x4000`. Commands match within each path after substituting output
  and temporary concat-manifest filenames. No quality/filter/timing/thread
  changes. Encode logs confirm default CRF 23, 34 x264 threads, 5 lookahead
  threads for every encode trial. The injected runner writes full stderr and
  does not exercise the service's progress-callback logging wrapper.
- Three pairs per path, all sequential: pair 1 Normal then Below; pair 2 Below
  then Normal; pair 3 Normal then Below. Encode pairs precede copy pairs. Each
  trial has eight test-owned Normal-priority sequential PBKDF2 CPU contenders,
  one Normal-priority 60-Hz probe and one-second warmup.
- Probe: absolute scheduled wake, then fixed 20,000 integer iterations. Response
  is scheduled time to completion; wake latency is recorded separately. Include
  only samples wholly within the FFmpeg interval. Interpolate quantiles. Count
  completions beyond 16.667 ms; skip accumulated backlog. This is a scheduler /
  CPU-work proxy, with no rendering, GPU, game engine or input latency measurement.
- Sample native process CPU/lifetime logical I/O, working set/private memory and
  machine CPU / PDH `_Total` physical-disk counters every 50 ms. CPU percent uses
  lifetime CPU seconds divided by elapsed time and 32 logical CPUs. Process
  transfers include cache and are not physical-disk attribution. PDH includes all
  workloads and drives; background I/O cannot be assigned to FFmpeg.
- Limits: each fixture-generation FFmpeg <=60 s, trial FFmpeg <=60 s, load/probe
  <=90 s, each validation FFprobe <=30 s; abort trial on available physical RAM
  below 4 GiB or FFmpeg sampled private memory above 2 GiB. Cleanup only owned
  Popen children. No guard triggered; no test processes remained afterward.

Replay with a **fresh** absolute directory under `C:\Users\Leandro\TikREC-tests`:

```powershell
.\.venv\Scripts\python.exe -m tests.diagnostics.issue52_priority prepare --root C:\Users\Leandro\TikREC-tests\FRESH-52 --duration 16
.\.venv\Scripts\python.exe -m tests.diagnostics.issue52_priority run --root C:\Users\Leandro\TikREC-tests\FRESH-52 --case encode --priority normal --trial 1 --contenders 8
```

Repeat `run` for the remaining explicit case/priority/trial combinations in the
order above. Preparation and each trial refuse an existing destination. This
diagnostic is not installed or invoked by the production service.

## Results

| Case / pair | Normal FFmpeg PID / seconds / proxy p95 ms | Below Normal PID / seconds / proxy p95 ms |
| --- | --- | --- |
| Encode 1 | 35900 / 3.2237 / 2.5821 | 26408 / 3.2753 / 2.2977 |
| Encode 2 | 42388 / 3.2730 / 2.5702 | 22608 / 3.4267 / 2.4071 |
| Encode 3 | 55452 / 3.3346 / 2.7600 | 5788 / 3.3251 / 2.4331 |
| Copy 1 | 35752 / 0.1147 / 1.6004 | 42112 / 0.1104 / 1.6856 |
| Copy 2 | 40192 / 0.1112 / 1.6727 | 42228 / 0.1122 / 1.8510 |
| Copy 3 | 46632 / 0.1107 / 1.5800 | 51044 / 0.1116 / 1.4949 |

| Aggregate (medians unless labelled maximum) | Encode Normal | Encode Below | Copy Normal | Copy Below |
| --- | ---: | ---: | ---: | ---: |
| FFmpeg elapsed, s | 3.2730 | 3.3251 | 0.11124 | 0.11164 |
| Whole finalizer elapsed, s | 3.6047 | 3.6169 | 0.3241 | 0.3181 |
| FFmpeg CPU, s | 44.2813 | 43.3281 | 0.0625 | 0.0469 |
| FFmpeg mean share of machine CPU, % | 42.03 | 41.02 | 1.76 | 1.33 |
| Maximum observed peak working set, MiB | 1274.90 | 1274.89 | 27.19 | 26.95 |
| Maximum sampled private memory, MiB | 1520.81 | 1520.53 | 25.25 | 23.99 |
| Process logical read, MiB | 38.272 | 38.404 | 24.427 | 24.427 |
| Process logical write, MiB | 39.582 | 39.582 | 24.428 | 24.428 |
| Per-trial response p95 median, ms | 2.5821 | 2.4071 | 1.6004 | 1.6856 |
| Per-trial wake p95 median, ms | 0.5441 | 0.5313 | 0.4721 | 0.4377 |
| Included probe samples, total | 589 | 603 | 20 | 20 |
| Probe 16.667-ms misses, total | 0 | 0 | 0 | 0 |

Below Normal's encode proxy p95 median was 0.175 ms (6.8%) lower, while FFmpeg
elapsed median was 1.6% longer. Paired elapsed changes ranged -0.3% to +4.7%;
paired proxy changes were -11.0%, -6.3%, -11.8%. Three short pairs provide no
confidence interval or actual gaming proof. Whole-finalizer overhead includes
configuration/frame-rate inspection; FFmpeg elapsed includes up to one 50-ms
completion-detection interval. Copy trials only contain 6–7 probe observations
each: their tail quantiles and timing differences are too small/undersampled for
a scheduling-benefit claim.

System CPU mean during encode was approximately 71–78%, with sampled peaks
92–99%, including contenders and unrelated programs. Encode system-disk trial
mean read rates ranged 0–0.757 MiB/s at Normal and 0.272–135.176 MiB/s Below;
mean writes 3.938–5.974 and 1.758–6.735 MiB/s respectively. One Below trial had
a system read peak about 822 MiB/s. Copy trials also had a Below system-write
spike (trial mean 121.742 MiB/s). These aggregate short-window/cache/background
measurements do **not** establish priority-dependent disk impact. Logical child
I/O and memory were essentially unchanged. CPU priority is scheduling policy,
not a memory/CPU-usage/disk budget; background resource modes were not tested.
[Windows priority-class documentation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setpriorityclass).

## Media checks and retained diagnostics

Both synthetic input directories passed existing `validate_target(deep=True)`
decoder checks and part packet-DTS checks. Only `manifest_missing` warnings
occurred, expected for synthetic parts without recording manifests; no session
completeness claim is made. All 12 MP4s passed deep decoding and packet-DTS
checks, with no output warnings. Encode input-decode classification was clean;
stream-copy classification is correctly `not_checked` because it does not decode.
All source hashes stayed identical; all six outputs within each path were
byte-identical, with equal probe metadata/frame counts across priorities.

- 720p fixture SHA256: `003b5463396f593984a9f8e2ea152c394794eef837a7187bdc6e0686037b0484`.
- 1080p fixture SHA256: `e11565188d5e9385a91af33b17115e6bf3eaee29ff50095d6d8b59fc865f1c24`.
- Copy output SHA256: `93511042e0437a366373f3951e928077340ef39bb08851e70d0a287d8229819e`.
- Encode output SHA256: `5262b74a07e3bad4f456289c9988482696031a00266dd47015526d28e2886254`.
- Each output: 960 H.264 video frames, 1382 AAC frames. Copy: 1280x720,
  video start/duration 0.023 / 32.067 s, audio 0 / 32.111565 s. Encode:
  1920x1080, video 0 / 32.044785 s, audio 0 / 32.089002 s. Small AAC/concat
  boundary differences between paths are identical across priority treatments;
  no timing semantics were changed to force an idealized 32-second result.

Focused final checks: **29 passed in 0.51 s** (`test_priority_diagnostics.py`,
`test_finalize.py`, `test_decode_diagnostics.py`), including native class metrics
on only disposable FFmpeg children, stop escalation, fixed probe behavior,
validation deadlines and rejection of a production root. New diagnostic modules
are each below 300 lines. Full offline suite was not rerun; production code is
unchanged. Local `analysis.json`, version/environment/priority JSON, fixture and
per-trial reports/logs/probes are preserved; `evidence-index.json` records their
SHA256 values without adding media or credentials to Git.
Index SHA256: `bebeaff42e93d274125b8d553f9b45f4a9dc78ab41feb484ad771715864a24a7`.

## Production preservation and limitations

Before 12:46:47.5570435 UTC / after 13:06:04.7905686 UTC: service **PID 16480**,
creation **2026-10-02T12:32:54.1650210Z**, unchanged. Health/storage OK, two
available slots, no active worker; no test children left. Proven service-visible
config `\\localhost\C$\Users\Leandro\AppData\Roaming\TikREC\config.json` SHA256
unchanged: `1E24D284AF2B9ABB15D37A3DD378F60DEB72AF3322F49A839E68C423F42FF1D2`.
No configuration write, task change, restart, manual recording, recovery,
retention, media transfer or old-project modification occurred. Service checks
were aggregate health/identity/hash protection, not another #48 evidence pass.

No real game, long LIVE finalization, concurrent capture/finalization, saturated
disk workload, thread cap, alternative encoder or dedicated worker was tested.
The actual Task-7 child class remains inferred, not directly verified. This
investigation cannot satisfy #52's eventual material gaming-improvement criterion
or #48/#28's media-evidence gates.

## Recommendation and safe next slice

The smallest supported implementation candidate is **explicit Windows Below
Normal only for the differing-configuration CPU re-encode FFmpeg child**. It
would make direct CLI / Normal-parent launches consistent with the expected
current Scheduled Task behavior. Keep stream-copy launch behavior, parent/task
priority, codecs, quality, filters, timing and thread selection unchanged, with
normal portable behavior off Windows. Add focused launch-policy/cleanup coverage
and repeat suitable bounded media validation when implementing that slice.

This is scheduling consistency, with a small measured synthetic proxy benefit;
it is **not** a demonstrated improvement for the already-Below-Normal service.
Do not advertise it as a gaming fix. If project management requires a material
gaming benefit before any policy change, representative measurement is the next
gate and current production should remain as it is. Priority alone did not
reduce observed memory or logical I/O; do not choose an arbitrary thread cap from
these results. Slower completion under higher-priority competing work may retain
a service slot/writer lease longer; the short paired cost here does not bound
that cost under real games. Queue/worker architecture remains a separate future
#52 stage, with no setup or transfer authorized by this investigation.

Continue only that bounded #52 slice after the next MODEL GATE. #48 remains
paused for qualifying natural evidence or credible missed-LIVE investigation;
#13/#28/#8 and release/tag work are separate and unstarted here.
