# Issue #52 — successful owned-attempt settlement and safe release

## Managed isolated orchestration successor — 2026-10-07

Normal successful settlement remains accepted; corrected prepared-success
recovery at `2d542164` is accepted by
[PM 6030581435](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6030581435).
The [explicit runtime](ISSUE_52_SERVICE_RUNTIME.md) automatically invokes this
original full success adapter for FIFO queued work. It does not reconstruct live
capabilities, alter cleanup/accounting guards or activate default service/CLI.
Incomplete cleanup remains owned and terminal accounting survives local errors.
Runtime integration at `90156913` is not yet accepted; [PM R14–R15](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6037046559)
requires dispatch/retirement correction. A default-no-op acquired-input hook
lets this runtime protect the exact finalizer lifecycle lease with existing
native close references. Failed registry owners, original-thread SQLite cleanup
and committed terminal results remain supervised independently of `current`.
Original settlement/preparation/cleanup evidence and this one-shot accounting
protocol remain unchanged; runtime verification is recorded in its report.

## Narrow prepared-success recovery successor — 2026-10-06

[PM decision 6017389662](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6017389662)
accepts `0665b5e8` as the successful local settlement foundation and authorizes
the single follow-up described in [prepared-success recovery](ISSUE_52_RELEASE_RECOVERY.md).
That decision supersedes this report's earlier blanket no-restart statement only
for an explicitly addressed attempt with durable successful release preparation.
No accepted foundation is reopened for review. Earlier incomplete media/control
phases, attempts without preparation, and all service/deployment integration stay
outside this exception. Recovery uses schema 10; schemas 1–9 remain
refused/preserved without migration.

[PM R12–R13 correction](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6024429330)
keeps this accepted normal success lifecycle intact. Recovery's exact primary
errors and retained native/lease/SQLite resources now block unsafe teardown or
another generation without blocking unrelated capture admission during proof.
Its already committed terminal accounting remains authoritative if later cleanup
or acknowledgement fails. Schema 10 stays unchanged; full correction evidence is
in the linked recovery report. Recovery acceptance and service integration remain
separate review gates.

## Authority and delivery boundary

[PM decision 6014913888](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6014913888)
accepts `df954dd2760e57fc682a0fb17d2bd4dc9a8e8b44`: R11 and manifest completion
as corrected. Accepted R1–R10, assembly, validation and publication stay accepted.
This single task completes the internal successful local lifecycle. #52 remains
OPEN / SINGLE ACTIVE; #48 OPEN / PAUSED; #28 unresolved. Owner decisions: None.
Isolated Windows `codex/capture-journal-handoff` was pulled before inspection;
Complex / GPT-6.1 Sol — High MODEL GATE and PROCEED preceded edits.

Implementation is complete and verified for PM review. Actual final results and
delivery state are recorded below; no successor task is automatically authorized.
This is not service integration, production cutover or v0.11 release readiness.

## Explicit connected success contract

`JournalSettlement` explicitly creates the original `JournalManifest` before
acquisition, opts into this narrow settlement capability, and runs at most one
sealed FIFO session. It connects accepted assembly, validation, publication and
manifest completion to actual cleanup and terminal settlement. Existing
`JournalManifest`, assembly/validation/publication-only adapters and synchronous
CLI/service defaults retain their earlier lifetime behavior.

`OwnedSettlement` requires this invocation's original successful manifest adapter,
coordinator and continuously held input/output/control objects. It cannot be
constructed from reopened paths or historical receipts. The internal journal
continuation checks the exact live capability, current call/arguments and SQLite
calling thread. A copied adapter, competing thread, missing/failed completion,
revoked execution or arbitrary generic `SettlementProof` grants no release.
The generic `settle_task` owned-attempt prohibition remains unchanged.

Fresh proof checks original session/attempt/H/input seal/marker, immutable
assembly/validation/publication and installed/flushed manifest records, exact
original/successor control bytes, output native identity/size/stamp/hash and all
applicable input/scratch inventories. Each original local child must match its
durable identity/exit and complete diagnostics hash, with all native job/process/
thread/pipe handles confirmed closed. A retained R11 reader, prior cleanup error
or unknown lifetime prevents success authority.

Before closing protection, immutable release preparation binds that proof, exact
unit/room/path claims, task revision and original resource scope. Its same
transaction irreversibly revokes execution. The task remains running/countable
and excludes a competing finalizer. Preparation means **cleanup pending**.
Only the already-authorized cleanup/accounting continuation remains possible;
capture/media/publication/control mutations are refused after preparation.

Held proof is checked again after preparation acknowledgement/reconciliation and
before the first release. This release-only observation does not restore execution
authority. Changes during/after preparation, including bytes changed with a
restored native stamp, cannot inherit earlier proof. Scans/hashes and SQLite
transactions are separate cooperative boundaries, not an atomic filesystem/SQLite
snapshot. No held-handle proof is attempted after protection has been closed.

## Exact cleanup and terminal accounting

Cleanup captures the original objects, then independently attempts each exact
native close and attempt writer-lease release once. It includes input pins,
marker/control/history pins, installed successor, scratch workspace/helpers and
published candidate's original owner. Shared catalog/media-root authority and
other capture/attempt objects are excluded. There is no media/control/helper/
history/marker deletion, reopen, encode, rename replay or repair.

Failure of one close does not skip other safe closes. Each resource has an explicit
confirmed/unconfirmed result; unconfirmed exact owners stay reachable. A thrown
close after an actual release still records uncertainty rather than claiming
success. First errors remain primary; secondary errors use the existing bounded
32-diagnostic/dropped-count convention. Writer-lease secondary faults are included.
Unknown cleanup keeps the durable unit and active claims outstanding.

The release-specific SQLite transaction helper preserves exact entry/body errors,
independently rolls back/closes and explicitly retains any unconfirmed connection.
SQLite thread affinity is unchanged. Wrong-thread cleanup stays unconfirmed;
only the original thread can confirm release of that exact connection. Earlier
manifest R11 plumbing and all generic journal transaction defaults remain intact.

A separate immutable cleanup observation distinguishes confirmed from incomplete
cleanup. Preparation and confirmed cleanup still retain capacity/finalizer ownership.
Only after the required proof and cleanup are confirmed does one transaction record
the terminal settlement receipt, task/attempt/session completion and removal of
exactly this session's one unit and active task-lifetime room/path claims together.
Immutable H, seals, ownership, child diagnostics, operation/automatic-start receipts
and every media/control/history file remain intact. No current retention eligibility,
forensic/raw policy release or permission to overwrite existing artifacts is granted.

Cancellation before preparation cannot create settlement authority. After its
commit, cancellation can only fence native work; the prepared cleanup/accounting
continuation can finish. Each lost acknowledgement allows one addressed lookup of
the exact operation/hash, without repeating a release/decrement/native action.
Unavailable lookup leaves explicit uncertainty. A confirmed/reconciled terminal
commit remains authoritative through later reporting or transaction-close failure:
no rollback to running, duplicate refund, re-pin or mutation of a replacement
capture binding. Post-commit retained SQLite ownership is reported separately.

### Inspectable durable states

| Journal settlement state | Original resource cleanup | Unit and active claims / finalizer |
| --- | --- | --- |
| No release preparation | No success release authorized | Retained |
| `cleanup_pending` | Not confirmed; preparation alone proves no close | Retained |
| `cleanup_incomplete` | Explicit unconfirmed results/errors | Retained |
| `cleanup_confirmed` | Required original resources confirmed closed | Retained until terminal transaction |
| `released` | Confirmed cleanup precedes immutable terminal receipt | Exactly one unit and this task's claims returned |

Post-terminal SQLite notification/close uncertainty is reported separately and
cannot reverse an already confirmed terminal accounting result.

## Schema 9 and bounded history

Schema **9** appends immutable `release_preparations`, `release_cleanups` and
`release_results`, bounded active indexes and irreversible owned terminal records.
Schemas **1–8 are refused/preserved unchanged**. The schema-8 fixture freezes
accepted `df954dd2` definitions; no migration, catalog recreation or cutover exists.

Active audits start from the at-most-eight outstanding units and indexed task/
session views. Completed owner history does not count toward admission capacity
and is not scanned wholesale on each admission. Addressed terminal inspection
checks the original complete evidence chain plus exact release/cleanup receipts.
Only that proven terminal history uses historical publication validation without
requiring its released active claim. Active publication checks stay strict, and
newer claims do not invalidate older immutable receipts. Each addressed attempt's
child inspection is bounded by the existing 4096-artifact seal limit: at most one
frame-rate probe per FLV, one writer and three fixed validators. Diagnostics are
bound by hash without copying every historical stream prefix into preparation.

Reopen exposes committed preparation/cleanup/terminal facts only. Supervisor death
after partial/full native cleanup cannot imply a cleanup receipt or refund. No
restart adoption, retry, failure repair or admitted-empty settlement is implemented.
This invocation is single-use; incomplete success release remains conservatively
outstanding for a later separately authorized recovery design.

## Baseline and development record

Evidence root: `C:\Users\Leandro\TikREC-tests\issue52-settlement`.
An initial baseline invocation failed to create a basetemp because its parent was
absent; that setup error is preserved outside the root as `settlement-baseline.log`.
After creating the deliberate disposable parent, the four new connected tests
generated sealed fixtures and failed on the unchanged accepted base because the
success adapter did not exist (`baseline.log`). No product code had been changed.

Development runs are diagnostic, not final-tree acceptance:

- `dev1`: four positive tests passed, including copy/libx264/interrupted and ten
  sequential successes (71.05 seconds).
- `dev2`: one failure exposed use of the cancellation-fenced validation hash after
  preparation. The release-only held-object proof now uses the existing scratch
  hash primitive; validator execution semantics remain unchanged.
- `dev3`: 39 passed (266.25 seconds).
- `dev4`: 85 passed / 17 failed (648.28 seconds). Source/schema edits while this
  development parent was running made its schema fingerprint differ from freshly
  launched death probes. All seventeen failures were `unexpected journal schema`
  on reopen. This sequencing error is preserved; no refusal/assertion was weakened.
- `dev5`: 50 passed (375.22 seconds).
- `dev6`: 40 passed (244.08 seconds), including all seventeen actual supervisor
  deaths on consistent definitions, ten sequential successes, file-backed SQLite
  errors and competing/historical authority checks. Final suites include subsequent
  terminal-immutability and indexed-plan assertions.
- The initial external final-suite runner had an escaped-newline syntax error before
  any suite/configuration began. Its script was corrected outside Git; source/test
  hashes were unchanged. These setup failures are not labelled test-suite results.

## First frozen verification and fixture corrections

All first-snapshot suites completed on unchanged 427-file hashes. They reported
exactly the same three new drift-test failures and one fixture teardown error:

| First frozen suite | Actual result | Seconds |
| --- | --- | --- |
| Focused (15 modules) | 279 passed / 3 failed / 1 error | 1532.45 |
| Related (94 modules) | 1,042 passed / 3 failed / 2 skipped / 1 error / 17 subtests passed | 2099.58 |
| Full (`tests`) | 2,803 passed / 3 failed / 9 skipped / 1 error / 19 subtests passed | 2372.85 |

The three restored-stamp drift tests reopened the still-protected output for their
final hash assertion and received Windows `PermissionError`. They now use the
same retained descriptor and require the exact `prepared output bytes changed`
error. Native sharing/protection is unchanged. The teardown error read
`session.json` after deliberately failed pre-install control work. Teardown now
requires exact complete staged successor bytes, immutable original history,
`staged`/`preserved` receipts and confirmed staging flush when installation has
not happened. Installed successors keep exact-byte checks; both cases verify all
unchanged capture fields. This is not permission for a missing installed manifest.

A separate frozen reproduction recorded **2 passed / 1 teardown error**, 14.67
seconds, confirming the original missing-path fixture assumption. The first
correction check recorded **5 passed / 1 teardown error**, 27.17 seconds: its new
assertion used the nonexistent durable phase `written`. That assertion was
corrected to the existing `staged`/`preserved` protocol with required flush proof.
The fresh five-case correction run passed **5 tests**, 24.36 seconds.
Only two new test/helper files changed; all runtime bytes stayed unchanged.
Complete failed logs and each snapshot/hash index remain preserved. No source/test
edit occurred while any suite on the preceding snapshot was still running.

## Final verification

All final isolated suites passed on the same **427-file frozen source/test tree**:

| Corrected final suite | Actual result | Seconds |
| --- | --- | --- |
| Focused (15 modules) | 282 passed | 1321.46 |
| Related (94 modules) | 1,045 passed / 2 skipped / 17 subtests passed | 1826.12 |
| Full (`tests`) | 2,806 passed / 9 skipped / 19 subtests passed | 2076.65 |

The final staged whitespace check reports one extra blank line at EOF in
`tests/test_journal_settlement_lifetime.py:94`. This formatting-only note is
recorded; the exact tested source/test bytes are preserved without post-suite edits.

No final failures. All **110 new settlement regressions**, the new schema-8 refusal
case and selected accepted R1–R11/assembly/validation/publication/manifest/native/
synchronous regressions pass. Each runner verified all 427 source/test hashes before
and after execution, with no added files; `final-tree-verification.json` rechecks the
delivered tree. Runtime modules remain below 300 lines. Schema-8 definitions still
match accepted `df954dd2` exactly; schemas 1–8 remain refused without byte changes.

Each suite used a fresh `*-corrected-final` basetemp and independent
`*-corrected-final-config` APPDATA, LOCALAPPDATA, XDG_CONFIG_HOME and XDG_STATE_HOME,
explicit isolated-worktree PYTHONPATH and the unchanged installed Hermes Python
3.11/SQLite 3.53.1 runtime. Existing Windows FFmpeg/FFprobe/.NET fixture tools were
reused without upgrades. Earlier basetemps/configurations/evidence were preserved.
The related/full selections overlap focused only in source, with independently
isolated catalogs, native events, jobs, media and configuration.

Complete `*-corrected-final.log`, frozen-check JSON, module lists,
`source-test-hashes-corrected-final.json`, failed/development logs, prior snapshots,
`schema-and-frozen-verification.json`, `final-tree-verification.json` and native
fixture evidence remain at the evidence root. Earlier accepted reports/results
remain historical in their original documents/roots. Normal task-owned `Refs #52`
commit/push; **PM review next, no automatic successor**.

## Connected generated-media and death evidence

`final-connected-evidence.json` records seven completed positive fixtures /
**19 successful sessions per suite**, and all **17 new supervisor-death boundaries
per suite**. Read-only collection preserved the SQLite catalog bytes and verified
exact original/successor manifest bytes, capture fields, marker hashes, output
size/hash against immutable native-candidate evidence, confirmed cleanup resources and terminal returned-unit
facts. The tests additionally assert before/after source/FLV/raw/arrival/connection/
control/unrelated hashes and original H/seal identity; fixture cleanup is independent
of product settlement. Positive cases include ten sequential successes, capture
binding generation 10, disjoint captures plus subsequent explicit FIFO processing,
reused room claims, old addressed receipts and degraded/interrupted capture truth.

| New connected output | Bytes | Owned inspection facts | SHA-256 |
| --- | --- | --- | --- |
| Two-part stream copy | 17,883 | H.264/AAC, 64×64; input decode `not_checked` | `564dc75486b06c55dfe12ab6acaeccd3eeaaba46f1d53374943323a8f9ee24af` |
| Differing-config libx264 | 16,855 | H.264/AAC, 80×64; input decode `clean` | `675817cf334dbce51ee8efd41559f3ec1ead86ca9deb9648caa7363734326d6c` |
| Interrupted one-part capture | 9,635 | H.264/AAC, 64×64; capture remains interrupted | `3e58d102d463d6fdaf6dfd498b937144a7fc6b2f9eb61bfad6703bf387d1838c` |

The two-part hashes equal the accepted assembly/validation/publication foundations.
The initial immutable scratch candidate retains its original `unpublished` /
`not_checked` fields; successful validation/publication are their separate accepted
records, and the requested final output is present unchanged after settlement.
Clean validated output retains an injected degraded-input classification rather
than rewriting it to clean. Original manifest/H evidence stays immutable.

Actual `TerminateProcess` evidence distinguishes: two deaths without release
preparation; seven `cleanup_pending`; six `cleanup_confirmed` with capacity still
held; two `released` after terminal commit. The first fifteen retain one outstanding
unit/active claims; only the last two expose the exact terminal return. Partial/full
native close before a committed cleanup observation never implies a receipt.
Read-only reopen preserves catalog bytes, output/history hashes and committed facts.
No media/control operation is repeated and no recovery/adoption is performed.
The seventeen accepted manifest supervisor-death regressions also remain in the
focused/related/full selections; older results stay historical.

## Remaining limits and exclusions

Generated fixtures establish this new internal path; natural-recording validation,
power-loss behavior, full A1–A20/service acceptance and independent integrated PM
review remain separate gates. Degraded input testing injects a recognized H.264
diagnostic into a real owned encoder tail; clean output does not prove clean source
or resolve #28. Trusted callbacks/native APIs retain their documented bounds.

No service/API/monitor/scheduler wiring, background polling, restart adoption/retry,
production access/change/restart, retention execution, #48 polling, migration/cutover,
dependency/runtime/resource-policy changes, remote worker, merge, release or tag.
Use `Refs #52`, preserve pushed history and stop for PM review after delivery.
