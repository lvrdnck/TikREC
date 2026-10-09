# Issue #52 — written pre-H failure shutdown correction

**2026-10-09: PARTIAL delivery; implementation committed, final verification STOPPED
for insufficient physical headroom. Focused PM disposition next; rollout HOLD.**
[Complete PM task 6080770655](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6080770655),
sole `post-writer-shutdown-20261009-ae7b` / [checkpoint 6081297903](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6081297903).
New Complex / GPT-6.1 Sol — High gate and task-specific PROCEED recorded. No delegation.
Prior shortened trial accepted within scope; its consumed allocation remains closed.

## Exact candidate and execution boundary

Verified designated Windows worktree/root/origin/branch/common Git directory,
preserved changes, pulled own upstream before reading project files.
Base `ae7b172227a9f73c372d2dfc9cec88542bbe1a3f`; accepted baseline executable
`e78db2da7feb03411f20f54a4b4ad468e590360e`, fingerprint
`9da7cc3c5c9358abcb3b127c3a30d0755decd6c0c892eb775133c85d7aeaf8ad`.

First executable/test candidate `72f5ab087a42fa8cca6e179f10517b731205af77`, fingerprint
`7720fdf2f519fdf77d413e2e8cd43748fb12e9e414540f056f4db6ec211483db`.
Final receipt-compatible executable/test candidate **`249ce32fb99b3368dafb83097a5f5e3aa0408cc5`**;
normalized package fingerprint **`b517def2c3e8305a16b8aff6a15d2e215edde7a7b516318203673418b7094d4f`**.
**542 frozen source/test/packaging files; 220 package modules.** First manifest
unchanged throughout its actual test run; final manifest differs in only
`service_runtime_refusal.py` and the two matching new regression modules.
Final AST/line-limit and Git diff checks pass. **Final native/media tests have
not run; this fingerprint is not a completed safety/performance acceptance.**
Documentation follows separately; no old fingerprint-bound home is converted.

No production watcher/service/task/config/media access/change, LIVE, installation,
migration, retention, broader recovery, force termination, main merge, release or
#52 closure. Historical reports/homes and the consumed 57426 test intervention
are preserved; its old `complete:false` remains unchanged.

## Implemented narrow correction

Preserve the explicit zero-writer branch and historical `writer_openings` count.
An additional written-failure proof uses a single-use original capture-thread
scope and UUID/generation-bound part/control writer ledger. Built-in part,
manifest-temporary and connection/room/outage JSONL streams register original
ownership before first write; existing `NativeCloseGuard` compares exact kernel
objects/CRT descriptors. Confirmed closures discard objects and become counters;
live/uncertain originals remain reachable. Writer secondary errors are bounded at
32; overflow/unknown acquisition refuses retirement. No per-read/per-tag cadence,
disk queries, storage thresholds, raw/retry/media behavior or schema change.
Ordinary streams outside the guarded capture scope keep normal semantics.

Existing shutdown fences admission, joins source/capture/finalizer/request/monitor
owners and retires SQLite on its original threads. The added proof requires no
active writer/in-flight callback; completed original writer execution; matching
part-opening counts; confirmed source/raw/arrival/part/control native closure;
exact UUID/generation/bridge/lease/intent/binding/unit; no H operation/marker,
pending handoff, queued/finalizing task, output or competing authority.
Only known writer-close diagnostics can be resolved by explicit guarded retry;
unknown source/close/commit identity stays incomplete. `capture_uncertain`,
authoritative post-H handling and the full shutdown algorithm are unchanged.

This closes local OS resources, not the failed recording: preserve failed/closing
row, media/control, immutable raw policy, unit, binding and claims. No H/output,
settlement/refund, retry/resume/adoption or deferred finalization. Normal attention
exit is 3 after confirmed retirement. Same-code reopen of a NEW test home preserves
occupied needs-attention accounting and permits idle cleanup of fresh local owners.

## Baseline and first frozen results — actual, not final acceptance

**Unchanged reviewed code: 3 expected baseline failures** at `shutdown.complete`
after tiny generated useful media, raw on/off, exhausted resolver and observer
failure. Independent same-process disposable fixture teardown actually joined
and retired its exact test resources separately. No uncontrolled retained CLI or
force-kill. Actual `baseline.txt` exit/failures remain saved.

**Development/pre-freeze: 18 new regressions passed.** First frozen run at
`72f5ab08`: **156 passed / 1 failed, 1032.28 s**. The existing pilot witness tried
to JSON-encode a local retirement proof containing the new writer-owner object.
The serialization failure is recorded, not waived or concealed. All **301 tracked
original Popen processes** have actual image/creation-FILETIME/original-handle
exit proof and are exited; the failing pilot also exited, no retained current owner.
Test `kill`/`terminate` fallbacks were disabled.

Final follow-up `249ce32f` pins the exact writer object in a separate private entry
field, leaving the retirement receipt JSON-compatible. The sealed retry still
requires that exact owner reference; it does not rely only on an integer/Python
closed flag. A new assertion covers serialization. The generated CLI teardown
guard now selects fresh `cleanup` after an incomplete shutdown, instead of a
second ignored `shutdown`. **These final changes have AST/diff checks only.**

Before that failure, frozen checks passed writer/source/control lifetime/refusal,
unknown source/acquisition, active-writer/unjoined-callback, stale UUID/generation,
writer-generation/pending/marker ambiguity, native part/control/catalog close
protection, SQLite thread-affinity faults, explicit safe retry/repeated sealed
cleanup, disjoint failed/healthy sessions, capture/post-H/native/shutdown/finalizer/
capacity checks, actual operational CLI, storage pressure, restart and R20.
Existing ten-success and 121-second/70-MiB assertions passed on first frozen bytes;
healthy copy/configuration-change finalization and their saved new deep verdicts
remain preserved. They are not relabelled as final-candidate results.

## Actual headless CLI proof at first candidate

The generated wrapper exercises real `tikrec.cli` parsing and accepted
`serve --journal-home` composition, fresh explicit home/config/catalog/token/tools,
real parser/raw/writer and source observations only. It replaces no shutdown,
H, finalizer or success. Witnesses persist after capture independently of CLI return.

| New case | Original UUID | Native PID / creation FILETIME | Cleanup | Exit | Preserved artifact hashes |
|---|---|---|---|---:|---:|
| test_actual_written_failure_at0 | `01789d8c-6a6a-4400-98d3-cac603d5d071` | 52128 / 134360260064615390 | true → true | 3 | 5 |
| test_actual_written_native_fau0 | `2233d40a-bd26-4f2b-af48-eda38cb657fd` | 55576 / 134360260112218671 | false → true | 3 | 5 |

The exhausted-resolver failure retires and exits 3 normally. The protected native
part case reports incomplete first and holds the SAME supervisor/bridge/exact
failure/resources, without periodic retry. Only exact test-handle protection
removal plus a fresh original-thread local `cleanup` nonce completes exit 3.
Witnesses confirm admission fenced, capture/worker/request/monitor joined,
native lease/raw/arrival/writer closure, SQLite ownership absent and state pins
retired. Before/after rows/status/hashes remain identical; no H/output/refund.
The normal case reopens its NEW same-code first-candidate home, preserves unit/
binding/needs-attention and hashes, then idle owned shutdown exits 0. Binding
occupancy does not mean a local writer was relaunched.

Native main PIDs match direct CPython launch, avoiding launcher-child ambiguity.
Python 3.11.15 / SQLite 3.53.1; existing venv pytest read through PYTHONPATH without
installation. Selected existing FFmpeg/FFprobe N-124716-g054dffd133 paths/hashes
appear in prospective startup receipts. `focused-command.json`, actual image/
FILETIME launch records and original-handle exit records provide provenance.

Reproduction shape (use only another NEW bounded generated fixture, never LIVE):
`python -m pytest tests/test_operational_written_shutdown.py` from the designated
checkout with checked tools first in PATH. The actual CLI argv is
`python -m tikrec.cli --config CONFIG serve --journal-home HOME --journal-catalog-id UUID
--token-file TOKEN --port 0 --ffmpeg FFMPEG --ffprobe FFPROBE --journal-init`,
then the same argv without `--journal-init`, behind the generated source wrapper.
[Normal commands/local nonce policy](SERVICE.md#opt-in-operational-windows-service)
remain unchanged. This is a reproduction prescription, not a new launch authorization.

## Storage stop and exact unrun checks

Predeclared total new fixture/evidence budget **1 GiB**; physical safety floor
**16 GiB**. Free space checked before batches and every first-frozen test setup.
Minimum recorded pre-test free **16.324 GiB**.
Before final setup the floor assertion failed; subsequent metadata-only observation
recorded **12.989 GiB free**, versus floor 16 GiB and
normal reserve-10 admission floor 14 GiB. Task evidence only
**363.951 MiB**. Host decline materially exceeds task
growth; cause unestablished. No unrelated scan, deletion/archive, reserve reduction
or production interference was attempted.

Final continuation preparation stopped BEFORE sources/home/catalog/service
initialization. A subsequent harness invocation failed at missing `native` import
because preparation had stopped; no product owner launched. Its failed attempt is
preserved and grants no test success. All first-run owners already retired.

**Unrun on final candidate:** the planned final native/refusal/operational/pilot/
R20/affected-safety run (including pilot serialization and matching regressions);
compact paced loopback smoke plus two alternating ordinary/operational-one pairs;
final NEW successful-control generated deep checks. The first run stopped at
pilot refusal before later selected pilot/native/HTTP/storage/writer/manifest/
connection/live tests. `focused-command.json` plus last `focused-headroom.json`
entry identifies the exact attempted ordering. No final ingestion verdict,
stage costs, lag measurements or final deep-validation pass is claimed.

The compact plan and corrected accepted loopback helpers are staged only: same
3,661,002-byte 32.043-s 720x1280/15-fps generated AVC/AAC, header/2,048-byte payload/
trailer fragments, raw enabled, 1.0× pace, comparable path depth, uninstrumented
ordinary → operational-one → operational-one → ordinary. Existing lag/drain/
producer scheduling criteria stay unchanged; no 48-case expansion or optimization.
No case in that plan actually ran in this execution.

## Durable evidence and safe next action

Private generated root: `C:\Users\Leandro\TikREC-tests\post-writer-shutdown-20261009-ae7b`. Preserve baseline/development/first-frozen homes,
source/manifest hashes, `focused-command.json`, `focused-headroom.json`,
`focused-launches.json`, `focused-original-exits.json`, `focused-result.json`,
logs/witnesses/validation receipts, `storage-stop.json`, and staged `final` helpers.
Final freeze is `final/frozen-source-hashes.json` / `final/frozen-candidate.json`;
542 hashes, new fingerprint above. Old histories and no-longer-matching homes
remain excluded from reopening. No historical missing logs are reconstructed.

**One next action:** PM disposition of this PARTIAL candidate and bounded final
verification after stable adequate storage. A subsequent assigned executor must
verify/reconcile exact bytes and allocation, check actual headroom against
unchanged floors plus finite remaining fixture budget, then use a NEW directory
and fresh final-fingerprint homes; do not reuse/reinitialize any existing home.
Do not automatically resume the staged helpers, new LIVE or rollout here.

Remaining limits: final serialization/safety/performance evidence outstanding;
unknown acquisition/source/close/H/task/output ambiguity intentionally stays
incomplete; broader recovery and old-home upgrades excluded. Stable storage and
sustained-operation/installation/rollout authorization remain separate prerequisites.
#52 OPEN, #48 PAUSED, #28 separate/non-blocking, #51/v0.11.0 complete.
