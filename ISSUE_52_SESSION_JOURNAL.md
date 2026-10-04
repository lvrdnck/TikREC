# Issue #52 — isolated durable journal checkpoint

## Current durable ownership extension - 2026-10-04

[PM review 5982869804](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5982869804)
approves minimal schema **4** for held local attempt/child authority. New tables
retain owner, original H, attempt-time marker observation and permanent sequential
launch intent/native identity/whole-job exit/diagnostics/cleanup with phase receipts.
FIFO claiming shares existing rules; capture bindings, eight-unit accounting,
immutable H/room/raw/path claims and DELETE/EXTRA/FK/1000-ms settings remain.
Schemas 1/2/3 are retained/refused byte-identically, no migration/recreation.
Existing failure/retry/hold/settlement callbacks refuse owned attempts; successful
readers do not complete/refund/clear pins. Reopen grants inspection only, no local
launch authority, adoption or PID-only absence inference. Audits stay bounded to
current owners/latest children, with paged history. See the
[internal protocol, tests and limits](ISSUE_52_DURABLE_LAUNCH.md).

## Historical capture-side bridge checkpoint — 2026-10-04

[Project-manager review 5971119601](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5971119601)
accepted `a96bd6e9` and R1–R3. The approved isolated capture-side bridge is now
implemented for review; [actual scope, Windows evidence and remaining gates](ISSUE_52_CAPTURE_HANDOFF.md).
Its native adapter supplies real closure inputs to H; production remains synchronous.
Explicit schema **3** adds `evidence` units and typed empty closure for admitted
zero-media captures: no task, released binding, retained counted artifact/room pins.
Unadmitted no-writer settlement remains separate. Failed/ambiguous captures stay held.
Schemas 1 and 2 are preserved/refused without migration or empty recreation.
The following schema-2/1 checkpoints and test results remain historical.

## Historical review correction pass — 2026-10-03 (accepted by 5971119601)

Evidence checkpoint: **2026-10-03 16:16:31 UTC**.

[Review 5970692341](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5970692341)
approves only focused journal corrections, not integration. #52 remains SINGLE
ACTIVE/OPEN; #48 OPEN/PAUSED. The review was a source review, not an independent
rerun of the historical Windows results below.

Added regressions before changing package code: against `58939620`, **13 failed,
four passed in 1.20 s**. Reproduced committed stop/latest-revision admission,
mutually contradictory owners and missing/inconsistent automatic provenance,
acceptance-based queue order and retry overtaking. These are unwired journal
findings, not production recording/missed-LIVE or media-mutation claims.

Implemented corrections:

- R1: fresh admission refuses saved stop inside the guarded transaction. Historical
  reserve/admit receipts remain idempotent evidence; they are not permission to
  launch a writer after a later stop. Reconcile unknown acknowledgement, then
  revalidate current UUID/binding/generation/revision/stop under the eventual
  native launch boundary. No writer/launch adapter is implemented here.
- R2: admission/audit share bounded pairwise owner rules. Two current captures
  cannot own the same creator; room and native subtree conflicts fail closed.
  Same creator/different known rooms with closed-task ownership remains valid.
  Mandatory automatic receipt/claim/session/immutable-intent binding is checked
  for outstanding sessions and when addressed historical evidence is used.
  Logical-corruption fixtures insert individually constrained rows directly in
  disposable databases; no production schema constraint/trigger is disabled.
- R3: journal schema **2** adds immutable queue-entry history, task queue-order FK,
  and indexed immutable accepted automatic-claim identity. H assigns queue order
  atomically. Explicit failed retry appends at the tail. Replay finds the existing
  operation receipt and neither appends nor moves its queue entry. FIFO eligibility
  uses task queue entry, while session history keeps its independent acceptance
  sequence. Queued/running/failed/blocked tasks still retain one unit and pins.

Schema 1 is explicitly unsupported by this implementation: reopen refuses it,
initialize refuses its existing path, and no migration/recreation is performed.
The frozen reviewed schema-1 fixture preserves real state for refusal tests;
all prior disposable roots, including the failing baseline fixtures, remain.
DELETE/EXTRA/FK/1000 ms, two bindings, one finalizer, eight units, immutable raw/
identity/seals and guarded accounting remain unchanged.

### Actual correction-pass verification

- Baseline on `58939620`: **13 failed / four passed**, 1.20 s, before package edits.
- Expanded focused journal suite: **136 passed**, 17.19 s (initial corrected run:
  113 passed, 12.76 s). Stop-before-admission/latest revision/reopen, both serialized
  stop/admission orders, competing callbacks, admission/stop lost acknowledgements,
  historical receipt replay versus fresh permission and unchanged durable records.
- Ownership/provenance: contradictory creator/subtree fixtures are refused on
  reopen, status and mutation without changing database bytes/unrelated records;
  valid same-creator/distinct-room task+capture retains each raw policy. Missing,
  wrong-session and wrong-hash automatic provenance is rejected; addressed
  historical claim/operation/session validation does not scan all completed history.
- FIFO: reverse acceptance/H, retry-tail/replay/reopen and competing claims;
  12 H/retry fault cases including queue-entry writes and lost acknowledgement.
  Three additional retry subprocess deaths complement the prior nine acceptance/
  H/settlement cases; dirty-page spill exposes rollback journals before commit.
  Durable operation identity resolves outcomes without double entry or unit release.
- Related ownership/worker/job/automation/retention: **633 passed / four platform
  skips**, 54.97 s; includes unchanged synchronous characterizations. Disposable
  retention fixtures only; no production retention action.
- Full isolated result: **1,932 passed / seven skips / 19 subtests passed**,
  183.24 s.
- Windows Python **3.12.10**, linked **SQLite 3.49.1**. Source ID:
  `2025-02-18 13:38:58 873d4e274b4988d260ba8354a9718324a1c26187a4ab4c1cc0227c03d0f10e70`.
  Reopened a current disposable file-backed journal to verify delete / synchronous
  3 / FK 1 / busy 1000. No upgrade or production-engine assertion.
- Evidence/config/database roots: `C:\Users\Leandro\TikREC-tests\issue52-journal-review-20261003`.
  Logs: `baseline-regressions.log`, `focused-1.log`, `focused-2.log`,
  `related-final.log`, `full-final.log`. Every invocation uses a distinct basetemp;
  related/full child APPDATA/LOCALAPPDATA/XDG config/state are redirected there.
  Existing old roots and all 42 unrelated worktree artifacts are preserved.
  New package modules stay under 300 lines; public API docstrings/diff checked.

Native proof, power-loss guarantees and all A1–A20 service gates remain
outstanding. No service/API/worker/marker/database deployment,
config/media/runtime change, restart, LIVE, production retention, #48 polling,
priority benchmark, dependency, remote worker, release or tag occurred.

Next at that checkpoint: review the focused correction commit; this was fulfilled
by review 5971119601. Current resume authority is the bridge report/PROJECT_STATE.

## Initial journal checkpoint — 58939620 (historical)

2026-10-03, evidence checkpoint **15:25:56 UTC**.
Authority: [approved review 5970143137](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5970143137),
following design/reproduction `9d6299d9`. **Journal slice complete for review;
#52 remains OPEN / SINGLE ACTIVE.** #48 OPEN/PAUSED; Gracie-only raw policy,
Ward OFF and monitored order `wardsimons`, `gracie.kf` are preserved. Production
was not inspected or changed by this isolated slice; prior runtime facts are
historical, not a fresh health assertion. #28 remains unresolved.

## Implemented, deliberately unused by production

| Module | Complete internal responsibility |
| --- | --- |
| `session_journal_types.py` | Frozen identity/raw intent, canonical native keys, bounded typed closure/disposition/exit/publication inputs. |
| `session_journal_schema.py` | Version 1 STRICT tables, FK/check/immutable-history constraints, eight-unit trigger, unique running task, indexes and exact schema signature. |
| `session_journal_store.py` | Explicit fresh initialize versus reopen, known catalog/application/version/file checks, verified pragmas, short transactions and durable operation reconciliation. |
| `session_journal_checks.py` | Bounded outstanding-ownership/accounting, room/artifact/seal and task/attempt consistency checks. |
| `session_journal_capture.py` | Atomic acceptance/reservation, room admission, revision/generation-bound stop/recovery/closing intent, H, proven unadmitted-reservation settlement. |
| `session_journal_tasks.py` | One finalizer claim, permanent attempt tokens, held uncertain exit, failure/requeue/block transitions and guarded exact-once completion. |
| `session_journal.py` | Internal facade; stable UUID lookup, accepted automatic claim receipt, bounded capture/task status and paged history. |

No existing service/controller, automation, retention, assembly, CLI or HTTP
module imports this journal. There is no default database path, import-time
database creation, migration, recording-root marker, worker loop or production
catalog. The old synchronous service still retains its slot during finalization;
the existing five characterization tests remain accurate and unchanged.

## Operation and ownership contract

- `initialize(explicit_path, catalog_UUID)` requires an existing deliberate parent
  and exclusive new file. Failure preserves that file for investigation; it does
  not remove/recreate it. `SessionJournal(path, known_catalog_UUID)` opens `mode=rw`
  only, verifies the schema/application/catalog identity and integrity, and never
  creates missing state. Unexpected mode, redirected/reparse parents, multiply
  linked files and replacement of a live instance's file are refused. Native
  path pinning/volume verification and scheduler exclusivity still need integration.
- Every appropriate connection verifies DELETE, EXTRA (`3`), foreign keys (`1`)
  and a **1000 ms** busy timeout. Mutations use explicit `BEGIN IMMEDIATE` and
  short commit/rollback boundaries; readers use short snapshots. No media/network
  work occurs inside them. Query results are bounded (two bindings, eight units/
  outstanding tasks, one keyed session/receipt, history pages 1–100). Reopen does
  an integrity check; this is intentionally additional work, not a per-row media scan.
- `reserve` atomically stores immutable UUID/creator/expected-room/display paths/
  native keys/root/raw/start identity, increments one slot generation, reserves a
  unit, claims output and the entire parts subtree, and commits an automatic claim
  receipt when applicable. Expected room is a reservation, not source proof.
  `admit` records the caller-proven matching room before writing may begin.
- Only two bindings exist. Each binds at most one session; a current page owner
  prevents another capture even when another slot is free. After H, a proved
  different room and disjoint paths may be admitted for that creator. Old room
  and artifact claims remain until proven settlement; room aliases, shared paths
  and ancestor/subtree conflicts are refused. Unknown identity never establishes
  disjointness. Native alias proof is supplied by the caller, not by string paths.
- `capture_intent` guards UUID/generation/revision, preserves stop once requested
  and preserves recovery reason when no successor is supplied. H requires closing
  phase, matching immutable fields and caller-supplied typed inventory/control
  digests. Its one transaction seals a queued task, transfers the existing unit,
  releases the binding and preserves old-room/artifact claims. It allocates no
  second unit, including when all eight units are already reserved.
- UUID records, original slot/generation, raw choice, seal, automatic receipt and
  completed metadata survive reuse. Replayed acceptance resolves to the original
  session, not today's slot occupant. No history or evidence is evicted for capacity.
- `claim_next` claims oldest queued work with a permanent unique attempt token.
  A unique index and serialized transaction enforce one running task globally.
  Uncertain child exit stays running/pinned and prevents another finalizer, while
  independent captures below genuine bounds remain admissible. Proven failed or
  blocked work keeps its unit and pins. Explicit failed requeue requires matching
  revision/attempt/token/exit proof; there is no automatic retry loop.
- Successful task settlement requires matching session/revision/attempt/token,
  input seal and output identity plus typed caller-proven publication/exit fields.
  It records proof and completion and releases exactly that unit/pins atomically.
  Replay of the same operation returns its durable receipt; a fresh stale callback
  cannot refund again. Releasing an unadmitted reservation requires a typed bound
  no-writer proof. Admitted empty/failed capture disposition is a later closure
  integration requirement, not something inferred from a missing thread.

### Uncertain result protocol

Every mutation takes a canonical durable operation UUID. Its kind, argument
digest and result receipt commit in the **same transaction** as state changes.
Reusing that UUID with different arguments is refused. Automatic acceptance also
has its independently durable claim UUID, bound to the immutable intent.

Before-COMMIT injected failures roll back all partial rows, bindings, units and
receipts. Any COMMIT or acknowledgement exception is `JournalUncertain`, including
a real reader-induced COMMIT lock timeout. This is not permission to refund or
retry with a new identity. Reopen verified authority and query `operation(UUID)`;
replay the **same operation and arguments** under the serialized transaction.
That transaction finds a committed receipt or executes once after resolving
absence. A missing/busy/corrupt authority is not evidence of rollback. No failed
operation can authorize deleting a potentially hot rollback journal.

## Stored evidence versus actual proof

The typed inputs validate field types, canonical IDs/keys, bounded sizes, hashes,
known evidence names, policy and session/generation/room/path binding. H retains
ordered FLV/raw/arrival/control observations and warnings under the old UUID.
It does **not** open files, inspect arrival ranges, hash media, close writers,
prove child exit or validate publication. Test keys/stamps/proofs are synthetic.
A future trusted native adapter must establish those facts before supplying them.
Likewise, accepted automatic receipts prove journal acceptance; they do not prove
that a source started or that requested raw bytes were successfully captured.

Unimplemented integration: native storage/alias/handle lifetime, writer unwind/
flush/closure, child Job Object control, publication receipt ordering, guarded
empty-capture settlement, phase-aware stall deadlines, low-disk reservation
yield/reconciliation, explicit backlog recovery, migration/downgrade refusal,
retention pin readers and older-executor marker protection, automation projection,
public status/API compatibility and deployment. No journal result passes the full
[A1–A20 service acceptance matrix](ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md).
No real-media `tikrec validate` or power-loss/storage-fault certification occurred.

## Actual engine and verification

Windows test interpreter: **Python 3.12.10, 64 bit**. Linked SQLite **3.49.1**:

```text
2025-02-18 13:38:58 873d4e274b4988d260ba8354a9718324a1c26187a4ab4c1cc0227c03d0f10e70
```

File-backed diagnostics verified `delete`, synchronous `3`, foreign keys `1`,
busy timeout `1000`. No runtime/dependency upgrade. DELETE/EXTRA follows the
review; no WAL exposure or production linked-engine claim is inferred.
Durability remains subject to SQLite/OS/filesystem/storage guarantees.

All databases, redirected test configuration and logs are under the disposable
external root `C:\Users\Leandro\TikREC-tests\issue52-journal-20261003`.
No production media, configuration or credentials were read or copied into Git.
The schema signature uses an ephemeral in-memory schema only; all tested authority,
rollback, reopen, contention and crash operations use real file-backed databases.

- Focused final journal checks: **95 passed in 14.33 s** after matching test-module layout; prior final run
  **95 passed in 11.76 s**.
- Related ownership/worker/job/automation/retention checks: **633 passed, four
  platform skips, 55.60 s**. Retention tests use disposable fixtures; no production
  retention operation was executed.
- Full isolated suite: first pass **1,891 passed, seven skipped, 19 subtests
  passed, 89.69 s**. Final post-hardening rerun: **1,891 passed, seven skipped,
  19 subtests passed, 97.38 s**.
- Failures injected at 24 acceptance/H/settlement transaction boundaries include
  every partial-write stage and successful COMMIT followed by lost acknowledgement.
  Nine bounded subprocess-death cases cover pre/post commit for acceptance, H and
  settlement; forced dirty-page spill leaves rollback journals for SQLite recovery.
  Durable rows and unrelated-session preservation are checked, then the same
  operation is reconciled/replayed. These are **process death**, not power loss.
- Coverage also includes raw ON/OFF reuse, surviving receipts, new-room admission,
  duplicate room/alias/subtree refusal, two queued tasks plus two new captures,
  eight-unit transfer, failed units plus unadmitted reservations, stale callbacks,
  competing admissions/claims/settlements, unique attempt history, lock timeout,
  missing/corrupt/wrong-catalog/schema/mode/replaced/multiply-linked state and
  cross-table inconsistencies. Refusals assert durable rows/zero unwanted changes.
- Development runs: 82 then 92 focused checks passed. A stronger evidence-name
  guard exposed one malformed test arrangement (`part.flv`); the outside-volume
  test now uses valid `part-0001.flv` to exercise the intended path refusal.
  Final focused run passes; no product validation was weakened.

### Reproduce the isolated checks

Use fresh external basetemp children and redirect APPDATA/LOCALAPPDATA plus XDG
configuration/state locations to disposable directories before launching pytest.
No default service state is read by these commands. In the runs above, a bounded
Python subprocess wrapper supplied that child environment and captured logs.

```powershell
@'
import os, subprocess, sys
from pathlib import Path
root = Path(r"C:\Users\Leandro\TikREC-tests\issue52-journal-REVIEW-FRESH")
root.mkdir(exist_ok=False)  # choose a fresh root; never clear previous evidence
child_env = dict(os.environ)
for key in ("APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
    location = root / key
    location.mkdir()
    child_env[key] = str(location)
journal_tests = sorted(str(p) for p in Path("tests").glob("test_session_journal*.py"))
for name, files in (("focused", journal_tests), ("full", [])):
    subprocess.run([sys.executable, "-m", "pytest", *files, "--basetemp",
                    str(root / name), "-q", "-p", "no:cacheprovider"],
                   env=child_env, check=True, timeout=600)
'@ | .\.venv\Scripts\python.exe -
```

Final static inspection: every new package module is under 300 lines and public
functions have docstrings; journal references in `tikrec/` occur only in these
new internal modules. Existing current-behavior characterizations are unchanged.

## Safe next action

Project management reviews the committed journal, its proof boundary and test
results, then selects the next bounded integration slice under a new MODEL GATE.
Do not wire or deploy this component automatically. #52 stays open; #48 stays
paused with all natural-evidence criteria preserved. No priority benchmark,
remote worker, other issue, release or tag is started.
