# #52 path-check correction — NOT REPRODUCED IN TESTED ENVELOPE

2026-10-09; code correction and safety/performance verification COMPLETE for focused
PM review under [complete assignment 6079130341](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6079130341).
New Complex / GPT-6.1 Sol — High MODEL GATE and PROCEED recorded; sole implementation
owner `path-check-20261009-a490`, [checkpoint 6079429067](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6079429067).
The prior measurement checkpoint stays CLOSED. No parallel executor.

**Safety: PASS within available native privileges. Connected performance: NOT REPRODUCED IN TESTED ENVELOPE.**
Three corrected uninstrumented single-capture repetitions pass unchanged lag criteria.
Compact two-capture/larger-fragment/modest-headroom results are individually recorded
below; no sustained deployment, upstream completeness or historical LIVE attribution.
Rollout HOLD; old fingerprint-bound homes remain incompatible and preserved.

## Exact frozen executable and bounded correction

Verified designated root/origin/branch/common Git directory, clean base
`a4907b1050ac2eda04a569fe1ede5db6b7ad7a46`; own-upstream pull was up to date.
Code/test candidate **`e78db2da7feb03411f20f54a4b4ad468e590360e`**, normalized 219-module fingerprint
**`9da7cc3c5c9358abcb3b127c3a30d0755decd6c0c892eb775133c85d7aeaf8ad`**. Complete raw-byte manifest: **537**
product/test/packaging files, `frozen-source-hashes.json`. Relative to the prior
536-file executable manifest, only `tikrec/pilot_identity.py` changed and
`tests/test_pilot_identity_local.py` was added. All verification used these frozen
bytes before the later documentation delivery commit. No version change.

`local` obtains one fresh no-follow lstat per observation and derives type,
symlink/reparse and hardlink facts from it. It still visits the target and EVERY
ancestor, then obtains a separate fresh known-target observation after traversal.
Actual state/media path probes: **37 → 10 metadata queries**; final MP4 path:
41 → 11; absent leaf: 37 → 10. This is within-invocation query coalescing, no
cross-call cache or reduced checking cadence. Separate caller checks and native
pins remain unchanged. Namespace checks are cooperative, not an atomic snapshot.

Narrow intended-refusal strengthening characterized before implementation:
the old helper accepted an absent leaf beneath a regular-file ancestor and a
dangling junction as an absent new leaf. Both now refuse. Other metadata errors
remain refusal and become sanitized `pilot path metadata unavailable`, without
private pathname/error text. Existing paths and absent FINAL leaf with an intact
directory ancestry retain return semantics. Known-state missing targets refuse.
The final fresh known-target observation also validates its type/link attributes.

All per-read/per-tag invocations, both state/media checks and BOTH physical-space
queries remain. Profile counts confirm two path checks/two disk queries per
snapshot. Different actual HTTP read aggregation explains different invocation totals;
the offered fragmentation is unchanged.
for both baseline/corrected captures, policy checks equal
`3 * (nonempty raw reads + 1) + 1235`. SQLite/media/raw/retry/shutdown/schema 10,
reserves/margins and normal/pilot defaults are unchanged.

## Tests first and frozen safety verification

Unchanged-code baseline, saved `baseline-tests.log`: **7 failed, 10 passed,
4 skipped**, 0.40 s. Failures expose the two acceptance holes, redundant queries
and unsanitized access/I/O/sharing errors. No baseline failure was relabelled as
success. Development helper: 17 passed/4 skips; broader pre-freeze check:
50 passed/6 skips, 98.47 s. Added fresh-success and Windows-error-code assertions
were included in the final frozen candidate.

Final affected regression selection: **252 passed, 6 skipped in 1193.82s (0:19:53)**. Exact selection, Python,
frozen candidate, prospective launch records and launcher/tool original-handle outcomes are in
`focused-command.json`, `focused-launches.json`, `focused-original-exits.json` and
`focused-result.json`; 419 tracked subprocess originals all exited.
Existing fixture force-termination fallbacks were disabled by the external runner;
unknown retirement would retain original handles and stop expansion.

Coverage: acceptance/refusal/query counts; missing/non-directory ancestry; native
hardlinks and intact/dangling Windows junctions; reparse and symlink metadata;
access/sharing/I/O uncertainty; missing/replaced target/ancestor between calls;
fresh queries on consecutive successes and post-traversal known-target deletion.
Native file/directory symlink creation has privilege error 1314; four helper cases
skip, with independent sealed-input privilege skips reported by pytest. Mocked
metadata cases supplement these limits, not replace native pins. Independent
native pin/sharing/close tests preserve original handle identity and explicit
safe retries. Low/unknown storage and cooperative in-flight stop, UUID/accounting,
ten completed recordings and the generated 121-second/70-MiB source assertions,
R20 combined reporting failures/retained SQLite/native cleanup, ordinary service
defaults, restricted-pilot compatibility, HTTP/automation/finalizer/shutdown pass.
No full suite, B3, historical validator or LIVE rerun.

## Prospective connected verification and measured improvement

New external root: `C:\Users\Leandro\TikREC-tests\path-check-correction-20261009-a490`. Corrected prior harness copied with
`reused-harness-hashes.json`; old helpers/homes/receipts remain byte-identical.
Same volume/path DEPTH (nine target/ancestor observations for state/media),
interpreter/checked tools, 0.5-second HTTP observer, raw enabled, source schedule
and fragmentation. No directory relocation or product seam beyond the same
loopback resolver injection. All sources are finite GENERATED media, not TikTok.
Python 3.11.15 / SQLite 3.53.1; actual launch/import/tool identities saved per
operational startup. FFmpeg/FFprobe N-124716-g054dffd133-20260531 hashes match the
accepted baseline. Fresh separate catalog/config/token/home for every case.

Healthy two-second smoke precedes all timed work. Normal three terminal same-room
observations at five-second spacing remain; exact H/assembly markers, completed
UUIDs, separate finalization state and original-owner receipts were checked.
Buffered metrics still export at capture completion/failure independently of CLI
return. External failure-export regression preserves the exact primary exception
without whole-CLI return; zero product starts. Profile export took
0.025010 s outside ingestion.

Matched order: ordinary-u1 → operational-u1 → operational-u2 → ordinary-u2 →
ordinary-u3 → operational-u3; lighter operational-i1 → ordinary-i1; then one
two-disjoint-captures runtime, larger-fragment ordinary/operational pair and
25-fps at 1.2× pace ordinary/operational pair. 14 cases including smoke;
no 48-case campaign or second concurrent supervisor. Minimum observed free space
32.072 GiB; normal reserve 10 GiB and physical
fixture floor 15 GiB unchanged. Host activity/available-space variation is not
controlled and was not investigated through production access.

Accepted before-correction uninstrumented baseline: EOF spans
42.719 / 38.860 / 51.656 s, late medians 10.192 / 6.522 / 16.432 s, wall slopes
0.235033 / 0.164639 / 0.259979 s/s; ordinary EOF 32.000 s and late medians
0.003 / 0.006 / 0.008 s. That historical evidence was reused, not rerun.

Current matching metrics (EOF span excludes offline confirmation/finalization;
drain columns are after nominal source end / actual final socket send):

| Case / stream | Raw EOF s | Late median / max lag s | Wall slope s/s | Late − early s | Drain nominal / send s | Blocked sends s | Fresh schedule p95 / max ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| headroom25-operational1-u1 / s0 | 26.704 | 0.013 / 0.050 | -0.000048 | -0.000 | 0.019 / 0.032 | 0.123 | 0.437 / 0.891 |
| headroom25-ordinary-u1 / s0 | 26.672 | -0.004 / 0.004 | -0.000019 | -0.000 | 0.003 / 0.000 | 0.124 | 0.434 / 0.651 |
| large15-operational1-u1 / s0 | 32.015 | 0.106 / 0.210 | -0.000051 | -0.003 | 0.204 / 0.000 | 0.013 | 0.512 / 0.586 |
| large15-ordinary-u1 / s0 | 32.000 | 0.102 / 0.215 | -0.000039 | 0.000 | 0.203 / 0.000 | 0.013 | 0.520 / 0.595 |
| small15-operational1-i1 / s0 | 32.047 | 0.016 / 0.093 | 0.000481 | 0.006 | 0.015 / 0.031 | 0.114 | 0.448 / 0.654 |
| small15-operational1-u1 / s0 | 32.031 | 0.012 / 0.081 | 0.000040 | -0.001 | 0.000 / 0.015 | 0.120 | 0.430 / 0.700 |
| small15-operational1-u2 / s0 | 32.047 | 0.012 / 0.067 | 0.000042 | 0.000 | 0.031 / 0.047 | 0.121 | 0.434 / 0.602 |
| small15-operational1-u3 / s0 | 32.031 | 0.012 / 0.082 | 0.000066 | 0.002 | 0.000 / 0.015 | 0.125 | 0.436 / 0.750 |
| small15-operational2-u1 / s0 | 32.015 | 0.020 / 0.090 | 0.000049 | 0.000 | 0.016 / 0.031 | 0.129 | 0.432 / 0.645 |
| small15-operational2-u1 / s1 | 32.015 | 0.020 / 0.090 | -0.000020 | -0.001 | 0.016 / 0.031 | 0.131 | 0.427 / 0.635 |
| small15-ordinary-i1 / s0 | 32.000 | -0.005 / 0.003 | -0.000047 | 0.000 | 0.000 / 0.000 | 0.117 | 0.433 / 0.651 |
| small15-ordinary-u1 / s0 | 32.000 | 0.005 / 0.013 | 0.000026 | 0.000 | 0.000 / 0.000 | 0.138 | 0.437 / 0.692 |
| small15-ordinary-u2 / s0 | 32.000 | 0.002 / 0.010 | 0.000004 | 0.000 | 0.000 / 0.000 | 0.126 | 0.434 / 0.706 |
| small15-ordinary-u3 / s0 | 32.000 | 0.000 / 0.008 | -0.000020 | 0.000 | 0.000 / 0.000 | 0.134 | 0.438 / 0.632 |

Original criteria retained: warmup 3 s; growing wall slope >0.01 s/s,
late-minus-early >0.25 s, late median/drain >0.5 s are failures. Monotonic Windows
resolution 15.625 ms; 100-ms frontier grid, QPC 100 ns. Small/negative millisecond
values are not precision claims. `lag-verdicts.json` records every stream result.
Socket-send completion is not a wire timestamp; fresh producer scheduling and
blocked-send/inherited-backpressure intervals are separated, never summed as loss.

Lighter profile actual exclusive capture-thread costs, same sampler as baseline:

| Category | Baseline / corrected calls | Baseline / corrected exclusive wall s |
| --- | ---: | ---: |
| sqlite_session | 7 / 7 | 0.026518 / 0.024576 |
| sqlite_status | 1242 / 1242 | 4.145171 / 4.323530 |
| arrival_write_flush | 5553 / 5205 | 0.189351 / 0.134856 |
| path_identity | 35782 / 33694 | 35.793039 / 14.064544 |
| free_space_query | 35782 / 33694 | 0.940203 / 1.076637 |
| policy_snapshot | 17891 / 16847 | 0.453593 / 0.458457 |
| policy_check | 17891 / 16847 | 0.065474 / 0.065074 |
| http_read_blocking | 5552 / 5204 | 1.069081 / 11.928823 |
| raw_write | 5551 / 5203 | 0.057021 / 0.040303 |
| parser_tag | 1236 / 1236 | 0.188663 / 0.139198 |
| retained_write | 1233 / 1233 | 0.029196 / 0.021106 |

Selected local exclusive wall time **41.888228 →
20.348282 s**. Path cost per invocation
**1.000308 →
0.417420 ms**.
Parent cumulative scopes include these children and are not added again.
HTTP waiting rises as the receiver keeps up with paced delivery. SQLite remains
secondary and unchanged; no further optimization was made.
Light profile late median is 0.016 s versus 0.012 s uninstrumented; EOF 32.047 s
versus 32.031–32.047 s. These observable differences are below the existing 0.1-s
lag criterion; they do not precisely bound instrumentation CPU/exclusive-cost
overhead. Historical full-profile amplification remains in the preserved report.
Repeated uninstrumented passes independently establish the connected improvement.

## Generated payload/output and original-owner evidence

Exact source inventory: `{"smoke.flv": {"bytes": 258377, "sha256": "c2f2380494b01de00f110e99fbf4d96f870531b469db4568af07be9965dc90f5"}, "v15.flv": {"bytes": 3661002, "sha256": "5c4d505de71b00e97bf81744810a06b2ad3752191483496f3974041dbe0eeb42"}, "v25.flv": {"bytes": 3661493, "sha256": "182810b6e0a742d5ea11b501865cf27ca8f2ba13e3323c111fb7246f099afbeb"}}`.
Every timed source byte is offered/sent/read exactly; contiguous raw-arrival
records terminate with EOF. Every retained media payload/order matches the exact
source suffix after the existing leading AAC keyframe gate; no media/retry change.
Actual read-size distributions, not requested 64 KiB, are preserved:

| Case / stream | Offered B | Sent B | Raw-read B | Retained / offered media tags | Reads | Median / p95 / max B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| headroom25-operational1-u1 / s0 | 3661493 | 3661493 | 3661493 | 1550 / 1551 | 5930 | 11 / 2048 / 2048 |
| headroom25-ordinary-u1 / s0 | 3661493 | 3661493 | 3661493 | 1550 / 1551 | 5928 | 11 / 2048 / 2048 |
| large15-operational1-u1 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 322 | 8186 / 17962 / 65536 |
| large15-ordinary-u1 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 322 | 8186 / 17962 / 65536 |
| small15-operational1-i1 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5203 | 226 / 2048 / 2048 |
| small15-operational1-u1 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5200 | 227 / 2048 / 2048 |
| small15-operational1-u2 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5200 | 226 / 2048 / 2048 |
| small15-operational1-u3 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5202 | 228 / 2048 / 2048 |
| small15-operational2-u1 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5195 | 230 / 2048 / 2048 |
| small15-operational2-u1 / s1 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5195 | 230 / 2048 / 2048 |
| small15-ordinary-i1 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5194 | 230 / 2048 / 2048 |
| small15-ordinary-u1 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5182 | 234 / 2048 / 2048 |
| small15-ordinary-u2 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5183 | 234 / 2048 / 2048 |
| small15-ordinary-u3 / s0 | 3661002 | 3661002 | 3661002 | 1230 / 1231 | 5176 | 235 / 2048 / 2048 |

4 new generated deep checks exit 0 (single retained parts/MP4 and both
two-capture MP4s), original artifact hashes unchanged. `new-generated-deep-checks.json`
contains actual commands/stdout/stderr and before/after proof. No historical-media
validation, repair, remux or re-encode. All new producer/receiver originals and
separately observed wrappers exit 0; operational shutdown is complete with
authority released, zero diagnostics, zero units and two available slots.
Two disjoint UUIDs/rooms have independent H/finalization evidence in one supervisor.
No process disappearance inference, hidden retry or forced intervention.

Eight operational cases complete nine recordings. In the larger-fragment case,
the last health snapshot still showed one running task; the next UUID poll saw
completion. That earlier snapshot is preserved. Read-only inspection of only
the NEW catalogs after confirmed original exit independently proves zero units,
no bound captures and completed tasks, with catalog/sidecar hashes unchanged.
Per-case `*-post-exit-accounting.json` records the observation boundary; no earlier
snapshot was rewritten or historical state reopened.

All 180 historical trial hashes and 718
saved old-measurement files remain unchanged; no old state was reopened. Old failed
fixture exit 57426 and `complete:false` remain historical test intervention,
not product retirement. Unsupported post-writer cleanup is STILL a rollout risk.

Reproduce saved derived measurements read-only with:

```powershell
& 'C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe' 'C:\Users\Leandro\TikREC-tests\path-check-correction-20261009-a490\analyze.py'
```

Fresh-launch stages are recorded in `plan.json`/`driver.py` and per-case launch
argv; existing case directories are never reused. Timings, native exits, UUID
states, H markers, source/package manifests and generated hashes are prospective.
Credentials/media are external and not uploaded.

**One next action:** focused PM review of this exact correction and its bounded
safety/performance evidence. Larger-rate/long sustained deployment, real-source
continuity and unsupported post-writer cleanup remain unproven; no next
optimization, recovery implementation, rollout or new trial is authorized.
#52 OPEN, #48 PAUSED, #28 separate/non-blocking, #51/published v0.11.0 complete.
No production watcher/service/Scheduled Task access/change, LIVE, installation,
migration/retention, dependency upgrade, force-kill, main merge, release or closure.
Refs #52.

---

Historical accepted measurement and stopped attempt follow VERBATIM.

# #52 throughput continuation — LOCAL BOTTLENECK REPRODUCED

2026-10-09; **same measurement `throughput-20261009-a7ad` COMPLETE for PM review**
under [complete disposition 6078321058](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6078321058).
Reused this measurement's GPT-6.1 Sol — High MODEL GATE/PROCEED and reactivated
the [same sole-owner checkpoint](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6077853483).
The previous INCONCLUSIVE delivery remains historical evidence below.

**Fixture disposition: TEST-HARNESS INTERVENTION, actual supervisor/wrapper exits
57426 (`0xE052`); never product cleanup or exit-0 success.** Corrected continuation:
one healthy smoke and twelve timed cases, all new original native and wrapper
exits 0, seven operational outputs completed with normal H/finalization/shutdown.
No retained new owner or further case. Product/test/packaging bytes unchanged.
Rollout HOLD; no historical LIVE/network/interference attribution follows.

## Exact failed-fixture disposition

Before checkout-changing Git operations, verified PID **31084**, creation FILETIME
**134360110830474802**, wrapper **18656**, session
**0023ccbd-71c5-4314-aa5f-b915f5305533**, exact failed home and catalog selection
against the original launch/startup/UUID records and original driver's attention
guard. Narrow queries covered only these identified test processes, producer
7500, driver 23660 and direct supervisor children. Producer had exited 0; no child
remained; saved capture/finalizer/request/monitor joins were true. Generated raw
bytes equalled the prospectively generated fixture; media inventory contained
only its known files. No machine-wide watcher/task census.

Preserved old helpers/plan/identity/shutdown records and readable failed home,
catalog/sidecars and media before action; stable hashes remained equal across a
quiescence interval. Two existing lifecycle locks were unreadable until exit.
The native image resolved the recorded uv Python 3.11 directory junction to
3.11.15; same-file identity was proved before action. Initial literal-path check
stopped without action until that alias was resolved.

Obtained a terminate-capable native handle, revalidated creation/executable and
retained **that same handle** through TerminateProcess and wait. Actual wait/exit
confirmed 57426; wrapper was observed separately and also exited 57426. The old
driver's **original retained-handle** receipt independently confirmed the same
creation/exit; its existing guard ended the attempt with exit 1, without another
case. No PID/name/tree kill or living-process code injection occurred.

Every readable pre-action artifact remained byte-identical afterward. Existing
locked files became readable; the original driver added its actual exit receipt.
Final full failed-case copy/hash inventory preserves the catalog and sidecar set
without SQLite opening/checkpointing, accounting mutation, repair or media change.
Old helpers remain unchanged; failed home permanently excluded from reuse.
`complete:false` remains false; volatile operational timings were lost and were
not reconstructed. Durable post-writer pre-H accounting was not refunded or H
fabricated. This unsupported shutdown limitation remains an operational risk;
the one-time exception grants no future forced cleanup.

After confirmed disposition, own-upstream `git pull --rebase --autostash` was up
to date at documentation base `8dc8b49f6041e0d8feb32a60d92264d183b2618a` in
`C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC`, branch
`codex/capture-journal-handoff`. Accepted executable remains
`aefeebe597933b963e24c641cd3dca317f5db539`, actual startup fingerprint
`6a92803377040eb8ce8553b3f90c8ceaf437883c37d25776600e890215d70151`.

## Corrected harness and staged execution

New root `C:\Users\Leandro\TikREC-tests\throughput-continuation-20261009-8dc8`.
Linked PM/provenance, preservation/action/exit records, old as-launched copies,
revised plans, per-case launch argv/stdio/harness hashes, buffered timings and
generated media stay external. No private media/token uploads.

Resolver supplies one generated live URL, then the same-room terminal status-4
exception on **every** later observation. Existing three confirmation checks,
five-second spacing, retries, storage/fences and CLI are unchanged. Two-second
generated smoke proves false/false/true end confirmation, assembly H marker,
completed UUID/output, zero outstanding units/two free capture slots, complete
owned shutdown with zero diagnostics, and original native/wrapper exits 0.

Each instrumented capture exports its own bounded buffered metrics after the
original run_capture unwinds, independently of whole-CLI return, including the
failure path. Exports took 0.020561–0.027284 s, outside ingestion, and preceded
CLI retirement. Final shutdown also saves the whole metrics snapshot. No per-read
profiling file writes; normal synchronous arrival flush remains enabled.
An isolated regression executes the frozen external checkpoint wrapper with a
failing stand-in call: real buffered export survives failure without whole-CLI
return and preserves the exact exception; zero product processes/state started.

First uninstrumented order: ordinary-u1 → operational-u1 → operational-u2 →
ordinary-u2. Then full buffered profiles in the same/reversed pairs. Full profiling
amplified observed duration, so prospectively added **one** focused cost check:
ordinary-u3 → operational-u3 → lighter operational-i3 → lighter ordinary-i3.
Preserved full as-launched helper bytes before adding lower-allocation wrappers.
The lighter sampler retains actual policy/path/free-space/SQLite/read/raw/parser/
retained calls; full profiles provide separate fence/owner scopes.

Same 3,661,002 generated bytes, 32-second 15-fps 720×1280 AVC / mono 24-kHz AAC,
small tag fragments ≤2,048 bytes, raw enabled; actual real loopback HTTP/read1,
fresh separate homes/catalogs/config/token, unchanged normal policy/supervision.
All timed raw files exactly equal source; contiguous arrivals/EOF; each retains
the exact expected 1,230-media-tag suffix after one leading AAC keyframe-gate tag.
Ordinary actual read returns 5,196–5,198; operational 5,551; operational median
246 bytes, p95/max 2,048. Requested 64 KiB is not the actual return size.

Original 16/32-MiB file/case, 120-s observation, 4,800-s campaign and 15-GiB
physical-floor ceilings remained maximum budgets. Minimum observed free space
**24.410 GiB**; normal reserve 10 GiB/margins unchanged; no pressure injection.
Thirteen cases, not the original 48-case target. No two-supervisor/finalizer-load
expansion. Larger-chunk, 25-fps/headroom and two-capture cases omitted under the
PM stop rule after the single-capture failure was located; no verdict beyond
this actual envelope or sustained/long-recording performance claim.

## Actual connected measurements

EOF span is first raw byte to raw EOF, excluding later confirmation/finalization.
Arrival lag follows a complete media tag's source deadline to the raw record
covering its final byte. Late median uses the last five source seconds; max uses
all complete tags. Wall slope uses the same 100-ms frontier grid/warmup as before.
All are matching statistics across paths; A/V frontiers are not summed.

| Case, in actual order | Raw EOF span s | Arrival late median / max s | Wall lag slope s/s | Blocked sends s | Scheduling p95 / max ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| ordinary-u1 | 32.000 | 0.003 / 0.011 | 0.000017 | 0.163 | 0.430 / 0.706 |
| operational-u1 | 42.719 | 10.192 / 10.703 | 0.235033 | 34.181 | 0.006 / 0.613 |
| operational-u2 | 38.860 | 6.522 / 6.837 | 0.164639 | 21.765 | 0.288 / 0.819 |
| ordinary-u2 | 32.000 | 0.006 / 0.014 | -0.000010 | 0.154 | 0.444 / 0.776 |
| ordinary-i1, full | 32.000 | 0.006 / 0.014 | -0.000016 | 0.162 | 0.447 / 0.821 |
| operational-i1, full | 55.204 | 21.287 / 23.172 | 0.407428 | 45.180 | 0.006 / 0.694 |
| operational-i2, full | 45.734 | 13.120 / 13.727 | 0.338777 | 33.990 | 0.111 / 0.666 |
| ordinary-i2, full | 32.000 | -0.001 / 0.007 | -0.000035 | 0.155 | 0.435 / 0.705 |
| ordinary-u3 | 32.000 | 0.008 / 0.016 | 0.000027 | 0.114 | 0.427 / 0.594 |
| operational-u3 | 51.656 | 16.432 / 19.609 | 0.259979 | 31.197 | 0.298 / 0.638 |
| operational-i3, light | 42.328 | 9.370 / 10.313 | 0.241092 | 27.152 | 0.225 / 0.661 |
| ordinary-i3, light | 32.000 | -0.003 / 0.005 | -0.000045 | 0.131 | 0.433 / 0.670 |

Producer QPC timestamps split accumulated lateness into inherited delay from the
previous send and fresh scheduling lateness relative to max(deadline, previous
send completion). Blocking sums are sequential send durations, not missing media
or wire-arrival time. Independent fixed offer deadlines are never shifted after
backpressure. Sub-ms fresh scheduling delays contrast with repeated long blocked
sends: the receiver cannot keep up; a late backpressured producer is not evidence
that its independent scheduler caused the backlog. All transports reached EOF;
no timeout or source recovery occurred before the normal terminal observations.

Uninstrumented operational drain after nominal media end was 6.829–19.609 s;
after actual last socket send 3.031–6.312 s. Light profile drains 10.313/4.125 s.
Final byte equality after those drains is not real-time ingestion. Light-profile
read/raw/parsed/retained late medians all 9.370 s and maxima all 10.313 s within
the 15.625-ms monotonic resolution; backlog is already present at HTTP read.

## Measured location, overhead and smallest proposed remedy

Capture-thread wall times below; selected child time is subtracted from parents.
**Do not sum cumulative columns.** Light profile:

| Scope | Calls | Cumulative s | Exclusive s |
| --- | ---: | ---: | ---: |
| Policy reason | 17,891 | 37.252309 | 0.065474 |
| Policy snapshot | 17,891 | 37.186835 | 0.453593 |
| Path identity | 35,782 | 35.793039 | 35.793039 |
| Physical free-space query | 35,782 | 0.940203 | 0.940203 |
| SQLite status | 1,242 | 4.145171 | 4.145171 |
| SQLite session | 7 | 0.026518 | 0.026518 |
| HTTP read1 including initial wait | 5,552 | 1.069081 | 1.069081 |
| Raw write | 5,551 | 0.246269 | 0.057021 |
| Arrival serialize/write/flush | 5,553 | 0.189351 | 0.189351 |
| Parser tag | 1,236 | 35.155911 | 0.188663 |
| Retained tag write | 1,233 | 0.029196 | 0.029196 |

Selected light local exclusive total **41.888228 s**; path identity alone
**35.793039 s**, 85.45% of that total, exceeds the offered 32-second source.
Ordinary light local total 0.199348 s; HTTP waiting 32.775961 s, raw/arrival
0.027101/0.088573 s, parser 0.063029 s, retained 0.020646 s. The operational
HTTP wait mostly contains the initial one-second producer barrier, so prolonged
transport waits are not the dominant observed receiver cost.

Both full profiles agree on location: path identity 38.143471–45.898815 s,
SQLite status 4.435924–5.224075 s, free-space 1.045772–1.270422 s. They separate
owner callback exclusive 0.560352–0.913272 s and fence scope exclusive
0.107101–0.129200 s; cumulative fence/parser times include children/reads.
These are wall costs including OS/scheduling delay, not CPU-cycle attribution.

Profiler effects were measured, **not waived**: initial full EOF mean 50.469 s
versus uninstrumented 40.7895 s (+23.73%), outside the 10%/100-ms negligible-effect
criteria. Do not treat full-profile magnitudes as calibrated baseline estimates.
The later uninstrumented run itself took 51.656 s; light took 42.328 s, within
the observed uninstrumented range and +3.77% versus the initial uninstrumented
mean. Variation prevents a precise causal whole-pipeline overhead estimate or a
100-ms equivalence claim. Five 100,000-call pure external calibration trials give
median wrapper overhead 1.762 µs full / 0.641 µs light (about 0.248/0.082 s at
observed call counts), excluding buffered callbacks and host interactions; these
are not subtracted from measurements or treated as a bound. Full and light
profiles locate the same dominant original function, while **three runs without
either profiler independently reproduce the failure**. The result is a bounded
local bottleneck finding, not a precise capacity/speedup estimate.

Location: `operational_source.source_options.check` repeatedly calls
`OperatingPolicy.reason → snapshot`, which calls `pilot_identity.local` for both
state and media on three checks per read plus parsed tags. `local` repeatedly
queries exists/lstat/is_symlink/is_dir and parents. Normal freshness checks are
retained; raw/arrival writes are materially smaller in this measurement.

**Smallest proposed remedy, not implemented:** assess coalescing redundant
metadata queries inside each fresh `pilot_identity.local` call, deriving existence,
type/link/reparse facts from one fresh lstat per component. Preserve every
per-read/per-tag policy call, every ancestor/reparse/hardlink refusal, native
identity/pins, both fresh physical-space queries, admission fencing and exact
shutdown. No persistent identity cache, relaxed cadence or threshold change.
Safety/equivalent-refusal tests and the same uninstrumented paced reproduction
must precede any performance-success claim; no source optimization was authorized.

## Verification, reproducibility and one next action

`final-verification.json`: 13 cases (smoke + 12 timed), seven operational normal
end/H/finalization outcomes with three status-4 observations and five-second
spacing, zero units/free slots/confirmed complete owner shutdown; all 26 new
producer/receiver originals and their wrappers exit 0. Export checkpoints precede
whole-CLI return. Source-byte/read-offset/retained-payload-order assertions pass;
536 product/test/packaging hashes and 180 historical hashes unchanged. No old
catalog reopen, historical packet/frame/validator/B3/full-suite repeat, LIVE,
production/watcher/task access, installation, recovery implementation or rollout.

`analysis.json`, case `derived.json`, `wrapper-calibration.json`,
`frozen-generated-hashes.json`, failed preservation/identity/intervention/exit
records and all prospective commands/receipts support reproduction. Per-case
`harness-hashes.json` and saved full helpers distinguish instrumentation versions.
Read-only derivation of the saved new generated measurements:

```powershell
& 'C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe' 'C:\Users\Leandro\TikREC-tests\throughput-continuation-20261009-8dc8\analyze.py'
```

Do not relaunch a campaign or reopen any existing home automatically. **One next
action: PM review of this measurement and the narrowly proposed fresh-metadata
query correction.** #52 remains open; #48 paused; #51/v0.11.0 complete;
#28 separate/non-blocking. Original engineering/R20/continuity/overlap acceptances
stand; post-writer unsupported cleanup remains a risk; rollout HOLD.

---

## Historical first attempt — accepted PARTIAL, superseded by continuation above


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
