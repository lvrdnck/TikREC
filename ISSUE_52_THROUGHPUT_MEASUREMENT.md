# #52 offline ingestion throughput measurement — INCONCLUSIVE

2026-10-09; execution `throughput-20261009-a7ad`; [PM assignment](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6077338031)
and [sole-owner checkpoint](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6077853483).
Measurement-specific GPT-6.1 Sol — High MODEL GATE/PROCEED preceded execution.

**PARTIAL / INCONCLUSIVE; experiment STOPPED, original fixture supervisor retained.**
One instrumented ordinary control completed. The first instrumented operational
capture received the entire source with growing lag, then an external fixture
resolver error prevented normal end confirmation/H. Its truthful incomplete
shutdown stops the experiment under the PM boundary. No operational timings were
persisted, no uninstrumented repetition or two-capture case ran. This cannot
establish a located product bottleneck, a local throughput pass, or past LIVE
attribution. The accepted continuity diagnosis, R20 and overlap remain accepted;
rollout HOLD and both LIVE permissions CLOSED.

## Identity and preserved work

Exact worktree: `C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC`,
branch `codex/capture-journal-handoff`. Clean base/own upstream verified, then
`git pull --rebase --autostash` returned up to date before project reads.
Execution revision `a7ad0f2e25bfcef2b0ddd3720cfc59bca4b02591`; accepted executable
`aefeebe597933b963e24c641cd3dca317f5db539`; actual CLI package fingerprint:
`6a92803377040eb8ce8553b3f90c8ceaf437883c37d25776600e890215d70151`.
All 536 source/test/packaging hashes and 180 historical evidence hashes match
before/after. No product/test edits, historical media parsing, service-state
reopening, old validation repeats, production access or LIVE occurred.

External evidence root:
`C:\Users\Leandro\TikREC-tests\throughput-measurement-20261009-a7ad`.
Prospective records include `plan.json`, generation commands/stdout/stderr/results,
per-case init/producer/receiver launch argv/cwd, lifecycle stdout/stderr, manual
start intents/UUID acknowledgements, original native handles/creation identity,
normal raw/arrival/parts, shutdown intent/receipt and `NEEDS-ATTENTION.json`.
`analysis.json`, per-case `derived.json`, before/after hashes,
`stable-generated-artifacts.json` and `retained-owner-check.json` are derived
separately. No private identities/media or tokens were uploaded.

Native Windows Python 3.11.15 / SQLite 3.53.1; launcher
`C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`.
Existing FFmpeg/FFprobe `N-124716-g054dffd133-20260531` binaries were checked by
normal CLI startup; their SHA-256 values are respectively
`b241596c846107ef85fe5a6fb9c11146e256cbe193378c86788e0462b6ad1081` and
`171a9102fe291870ee4fa62e8a6814366e65247d692d5177cb2ca73567c2f3d5`.

## Predeclared envelope and seams

48 finite cases: four profiles × ordinary/operational-one/operational-two ×
instrumented-1, uninstrumented-1, uninstrumented-2, instrumented-2. Sources are
32-second generated testsrc2 AVC/AAC FLV, 850-kbit/s video target, 48-kbit/s mono
24-kHz AAC; 720×1280 at 15 fps and 640×1280 at 25 fps. Small fragmentation sends
11-byte tag headers, payload fragments up to 2,048 bytes and four-byte tails;
the larger control batches 200 ms; headroom is explicitly 1.2× the 25-fps source.
Saved aggregate historical read/tag statistics informed fragmentation, not replay.
The 15-fps profile is a lower-cadence control; it does not replicate every saved
25-fps layout/rate. Only its first two cases actually ran.

Finite file/case budgets 16/32 MiB; observation 120 s/case, matrix 4,800 s;
actual physical floor 15 GiB; normal configuration reserve 10 GiB and unchanged
operational margins/check cadence. Initial free space 50.91 GiB; measured initial
case floors exceeded 50.6 GiB. No pressure injection or second supervisor.

Lag criteria declared before launch: warmup 3 s; growing slope >0.01 s/s,
late-minus-early >0.25 s, late lag/drain >0.5 s. Producer p95/max lateness limits
25/100 ms; profiler lag difference 100 ms, relative local-time effect 10%; stage
resolution target 10 ms. Lag grid 100 ms; normal HTTP status observer 500 ms.
Python monotonic uses GetTickCount64, reported resolution 15.625 ms; stage spans
use QueryPerformanceCounter, resolution 100 ns. Sub-tick send durations reported
as zero are unresolved, not proof of zero work.

Independent producer process preserves one fixed media-time deadline schedule,
chunked loopback HTTP, TCP_NODELAY and 131,072-byte socket send buffer. A
two-capture barrier was prepared but never exercised. Send completion means
application/socket-buffer acceptance, not wire arrival. No in-process file/chunks
substitution: actual urllib HTTPResponse.read1 feeds the normal parser/writer.

Operational receiver runs normal `tikrec.cli serve --journal-home` via runpy,
with fresh explicit config/home/catalog/token/tools, normal supervisor/logging,
storage checks, fences, SQLite and raw/arrival/retained writes. Empty monitored
creator configuration disables real discovery while leaving the normal monitor
worker active. Manual selectors `fixture.s0`/`fixture.s1` map only through the
trusted resolver seam to disjoint synthetic rooms and 127.0.0.1 HTTP URLs.
The receiver rejects nonloopback source HTTP before opening it.

Selected timing wrappers preserve calls/returns/exceptions and context lifetimes.
Per-thread nested spans record call counts, cumulative and exclusive nanoseconds;
exclusive time subtracts selected child spans, avoiding nested double counting.
Read/tag events are memory-buffered, capped at 100,000 per stream/stage, with
overflow counts. No per-read profiler file writes. The product's synchronous
raw-arrival flush remains active. Profiler/bookkeeping overhead is not calibrated
because uninstrumented comparisons did not run.

## Actual measurements

Both cases sent/read exactly 3,661,002 source bytes (SHA-256
`5c4d505de71b00e97bf81744810a06b2ad3752191483496f3974041dbe0eeb42`).
Each retained 1,230 of 1,231 complete media tags, matching input payload/order
exactly after the accepted leading one-AAC-tag keyframe gate. Read offsets are
contiguous and EOF recorded. This is bounded payload preservation, not MP4 or
deep-validation evidence. Operational H/finalization never completed.

| Measure | Ordinary, instrumented-1 | Operational one, instrumented-1 |
| --- | ---: | ---: |
| Actual nonempty read returns | 5,210 | 5,551 |
| Read length median / p95 / max, bytes | 226 / 2,048 / 2,048 | 246 / 2,048 / 2,048 |
| Complete-media arrival lag early / late median, s | 0.008 / 0.008 | 4.8545 / 25.287 |
| Arrival lag maximum, s | 0.015 | 27.187 |
| Production-window wall-grid early / late lag, s | 0.024 / 0.024 | 2.726 / 13.724 |
| Wall-grid lag slope, s per wall second | 0.000026 | 0.465171 |
| Receive drain after nominal last-media deadline, s | 0.000 | 27.187 |
| Raw drain after actual last socket send, s | 0.000 | 5.125 |
| Producer p95 / maximum lateness, s | 0.015 / 0.015 | 21.485 / 22.551 |
| Sum / maximum socket-send duration, s | below tick / below tick | 49.047 / 1.359 |
| Normal finalization / confirmed complete retirement | n/a / yes | no / no |

Wall-grid uses the latest complete received A/V prefix at each 100-ms tick
between warmup and nominal production end; it does not add overlapping A/V
warnings. Per-tag arrival lag follows each source media timestamp to the first
raw-arrival record covering its complete tag. The fixed production schedule is
not shifted to hide blocked sends. Operational raw EOF arrived about 60.281 s
after its raw clock reference; final byte equality after that drain is not
real-time ingestion. Producer failure of the predeclared pacing limits also
prevents treating this case as a clean sustained-rate test.

Ordinary actual stage costs, seconds; cumulative columns must not be summed:

| Selected scope | Calls | Cumulative | Exclusive |
| --- | ---: | ---: | ---: |
| HTTP read1, including paced waiting | 5,211 | 32.702011 | 32.702011 |
| Raw arrival serialize/write/flush | 5,212 | 0.103137 | 0.103137 |
| Raw write | 5,210 | 0.143499 | 0.040449 |
| Parser exact reads | 3,706 | 31.922623 | 0.081494 |
| Parser tags | 1,236 | 31.948518 | 0.025896 |
| Retained tag write | 1,233 | 0.022109 | 0.022109 |

Selected ordinary local exclusive total **0.273084 s**; observed receiver span
33.531 s. The remainder is not assigned to a guessed stage. Operational policy,
path/free-space, fence/owner, SQLite, parsing/raw/writer spans were instrumented
in memory, but the receiver saves them only after the original CLI returns.
It has not returned. Those costs and parsed/retained event timing are **unavailable**,
not zero; normal raw-arrival records permit the partial lag analysis above.

## Fixture failure and exact owners

The external resolver supplied one live result, one same-room offline exception,
then raised StopIteration when the normal three-check offline confirmation
requested another observation after five seconds. This is my fixture defect;
it is not evidence of an operational product regression. Saved connections record
one clean transport EOF, a status-4 observation with confirmation false, then
`capture_error`; normal session evidence records capture failure. The bridge
held the original post-writer pre-H capture in `closing`, with no task/output.

Driver submitted one prospective local shutdown nonce. Actual receipt:
`complete:false`, captures/finalizer/HTTP requests/monitor joined true,
authority released false, reason `ownership_or_cleanup_unconfirmed`, two bounded
diagnostics, none dropped. Last UUID status preserved binding/closing/needs-attention;
no successful handoff, unit refund, output completion or retry was fabricated.
No MP4 or finalizer load is claimed. Later catalog accounting was not reopened.

Original supervisor **PID 31084**, wrapper **18656**, creation FILETIME
**134360110830474802**, session **0023ccbd-71c5-4314-aa5f-b915f5305533** remains
reachable. Original driver retains its process/native handle objects and waits;
its attention guard prevents another matrix case even if eventual retirement
occurs. Supplemental same-creation native check confirms WAIT_TIMEOUT / STILL_ACTIVE
(258/259), not retirement. Producer PID 7500, same saved creation identity,
is confirmed exited 0. Ordinary receiver PID 71368 and producer PID 54480 have
original-handle confirmed exits 0 and wrapper exits 0.

Documented original-thread local control remains at:
`C:\Users\Leandro\TikREC-tests\throughput-measurement-20261009-a7ad\cases\small15-operational1-i1\home\control.json`.
No fresh cleanup nonce was submitted: supported refusal retirement explicitly
requires zero writer openings (`service_runtime_refusal.retire_refusal`), whereas
this fixture retained a written part. A blind retry cannot establish that proof.
No process kill, state repair/reopen, alternate owner or broader recovery was used.

## Reproducibility and next action

External `prepare.py`, `producer.py`, `receiver.py`, `metrics.py`, `native.py` and
`driver.py` preserve the as-launched fixture; generation and each real CLI command
are in their prospective JSON records. `analyze.py` parses only the new generated
source/parts and buffered arrival/producer evidence; assertions verify bytes,
offsets, EOF and retained payload order. `close_evidence.py` compares historical
and source hashes read-only and verifies original fixture identity without
opening its catalog. Final analysis/preservation checks exit 0. No historical
validation, full suite, B3, product tests or additional capture was repeated.

Safe read-only reproduction of the saved derived measurements:

```powershell
& 'C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe' 'C:\Users\Leandro\TikREC-tests\throughput-measurement-20261009-a7ad\analyze.py'
```

Do not rerun prepare/driver or recreate this home. **One next action: PM disposition
of the retained original post-writer fixture owner and this incomplete measurement.**
A later authorized continuation would first need confirmed owner retirement,
then an external resolver that returns the same-room offline observation for all
normal confirmation calls, followed by the missing matched/repeated/uninstrumented
matrix. No product optimization is proposed from this incomplete evidence.
#52 remains open; #48 paused; #51/v0.11.0 complete; #28 separate/non-blocking.
