# Issue #52 — explicitly constructed isolated service runtime

## Authority and current boundary

The [PM integration decision](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6030581435)
accepts R12–R13 at `2d542164` and corrected prepared-success recovery. The
[workspace resumption decision](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6030964984)
lifts the temporary audit hold and resumes this same partial task. Accepted
media/control, R1–R13, normal settlement and recovery foundations remain accepted.
Current implementation is complete for PM review after final frozen verification.
#52 stays OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED; #28 unresolved; owner decisions None.
Recorded MODEL GATE / PROCEED: Complex; GPT-6.1 Sol — High.

Implementation and every execution use the existing linked Windows worktree
`C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC` on
`codex/capture-journal-handoff`. Its common Git directory is
`C:\Users\Leandro\dev\TikREC\.git`, origin `lvrdnck/TikREC`, accepted HEAD
`2d542164c7c64fbc4a217884bec63c26246fb6fa`. The required pull was conflict-free.
The two modified/fourteen untracked partial files were preserved and continued.
The separate old desktop project and primary/deployed checkout are not editing
targets. Audit observations are not proof of every historical invocation or
the deployed process's in-memory source; prediction-work location remains unknown.

## Explicit composition and automatic FIFO

`IsolatedServiceRuntime(journal, root, ffmpeg=..., ffprobe=...)` accepts an existing
identified schema-10 journal and explicit local media root. Fresh initialization
is a separate `SessionJournal.initialize` call. Construction acquires the single
catalog/native authority and remains passive until `start_runtime()`. It does not
construct a legacy RecordingController/StartupReconciler or operate a second
catalog. No CLI, default service factory, HTTP route or configuration activates it.

Admission uses the existing CaptureAuthority/CaptureBridge and real LIVE, FLV,
raw, connection and manifest code. UUID/generation, creator, proven room, paths
and raw policy remain original. H commits or reconciles before the journal
releases its capture binding. Two captures share one bounded catalog; accepted
captures already reserve their future H unit. At eight outstanding units a new
start refuses `finalization_backlog_full`; H transfers without another unit.

One tracked non-daemon processing worker automatically selects FIFO queued work
through JournalSettlement: assembly, validation, guarded publication, manifest,
exact cleanup and terminal accounting. It periodically reads bounded durable
work, so notifications and thread-exit hints can both be lost. No caller invokes
each settlement manually. Media work, hashing and teardown execute outside the
runtime admission lock. Accepted algorithms, tools and resource policies stay.
Local active maps are retired after exact cleanup, latest slot identities number
at most two, diagnostics retain at most 32 actual exceptions plus dropped count,
and journal history is accessed by bounded pagination/indexed UUID lookup.
Rejected admissions discard only known-closed leases without a surviving bridge.
Failed original capabilities remain in the retirement registry, so cache cleanup
cannot bypass the accepted original-owner checks.

## Status, automation and stop

Internal `health()` separates two capture slots from finalization/task counts,
storage refusal, backlog and paused reasons. `session_status(UUID)` preserves
original slot/generation/room/path/raw identity after reuse; capture availability
never implies MP4 completion. Only durable completed phase exposes a completed
output. Singular status/stop refuses multiple outstanding owners.

Targeted stop affects the addressed live capture only. Finalization-only returns
`capture_already_closed`; a concurrent H is reconciled under the same capture
authority fence. Completed capture is not found as an active stop target. Late
callbacks require the exact current binding/generation and an accepting runtime.

Existing RecordingAdmission and AutomationCoordinator accept this backend through
optional methods; legacy controllers use their original calls. A deterministic
UUID binds all fields of the already-persisted schema-1 automatic claim, including
the prior session identity, into schema-10's indexed acceptance receipt. Reconcile
that receipt after H/reuse/completion, rather than inferring acceptance from an
idle/replacement slot. Unknown acceptance keeps the pending claim and disables
automation. Raw opt-in and creator policy use existing coordinator rules; no
creator-list or configuration writes occur. The caller explicitly composes the
isolated coordinator/store and assigns `runtime.automation` for owned shutdown.
These internal projections do not declare public HTTP/client compatibility.

## Startup, storage and shutdown

Explicit startup consumes queued work and invokes only accepted prepared-success
release recovery for an addressed running attempt with durable preparation.
Fresh recovery authority/generation/native protection and immutable evidence
checks remain mandatory. Already-terminal history needs no file reopen or new
accounting. Unknown or earlier unfinished states remain outstanding/pinned with
`unsupported_unfinished_phase` or `finalizer_needs_attention`; no automatic retry,
refund, discard, LIVE resume, publication replay or manifest installation.
Disjoint proved captures remain available subject to actual catalog/storage/bound
ownership. Schema 10 is unchanged; schemas 1–9 are preserved/refused, no migration.

Both explicit output and catalog StorageStatus scopes are checked before new
admission and finalizer/recovery launch. Existing minimum-free/unavailable-storage
barriers defer work without returning capacity. Storage recovery rechecks eligible
startup work. No guessed output budget, deletion or retention eligibility is added.

Shutdown fences starts and late callbacks, stops the composed automation and
cooperatively closes captures using reserved units. It does not drain queued work.
The injectable grace defaults to 30 seconds and cannot exceed it; grace is a
shutdown wait, not an assembly deadline. Expiry requests accepted addressed
recovery cancellation or exact attempt/job cancellation. Cleanup runs on the
owning worker's SQLite thread. Catalog ownership is released only after tracked
threads/native/SQLite owners are confirmed retired.

A constructed thread is retained if startup reporting fails after native start,
or interruption leaves startup unconfirmed. Worker failure fences processing and
new starts. Capture startup acknowledgement loss preserves the writer's original
UUID/thread and allows targeted stop/H. Join errors stay actual diagnostics;
only a confirmed join permits catalog release, even when is_alive is false for
an unconfirmed, not-yet-started object. Known ordinary pre-start failures remain
separate and never silently refund accepted recording units.

Unknown cleanup returns incomplete shutdown with retained non-daemon ownership;
it is not safe exit. A later explicit shutdown can finish confirmed local cleanup
without retrying terminal accounting. Unsupported protected scratch/unfinished
work remains pinned. Terminal accounting remains final despite acknowledgement,
reporting or later SQLite close errors. Capture post-H teardown uncertainty is
separate from a harmless lost notification: it retains its owners/diagnostics,
blocks further acceptance to bound local ownership, and refuses authority release.
Independent fixture cleanup is explicitly separate from product cleanup claims.

The explicitly supplied journal instance additionally observes borrowed SQLite
connection lifetime during runtime use. The original connector, same catalog,
transaction code and durable capability guards remain; no schema or second
authority is introduced. At most 32 opening/live/partial connections are tracked.
Setup errors retain their accepted partial reader owner; close errors retain the
exact connection and creator thread. Accepted settlement/recovery readers keep
their existing cleanup owners. Generic control readers are cleaned only on their
original thread, and unresolved control ownership blocks new admission and safe
exit. Unknown health counts are null, never invented zeroes. A generic unresolved
control close also refuses successful release preparation/accounting. Explicit
cleanup requests are consumed once, rather than repeatedly retrying uncertain
closes on every poll. The connector is restored only after borrowers and native
catalog owners retire; an emptied ExitStack alone cannot prove failed native closes.
Before final native catalog closure, an atomic read fence prevents a concurrent
status call from opening another borrower between the ownership check and close.
Historical UUID observation remains available after confirmed shutdown.

## Development failures and portability

External evidence is retained under
`C:\Users\Leandro\TikREC-tests\issue52-runtime-20261007`.
The initial fixture-availability error and native manifest-reopen PermissionError
were corrected using the existing managed-process fixture and exact held control
handles. Three guard passes and five connected passes before the audit are only
development evidence. The resumed first run records 13 passes/one failure: the
stop fixture blocked before any media tag reached the writer, leaving raw media
and legitimately pinned closing evidence. Its corrected scenario stops after
actual writes; the unsupported earlier boundary is not relaxed or refunded.
The second resumed run recorded 17 passes, two failures and one teardown error:
an assembly fixture used the wrong child field, and an injected SQLite close fault
remained installed for the fresh-runtime control. Its retained non-daemon test
worker correctly refused retirement; only the verified disposable pytest process
was terminated after pytest completed, with native test jobs independently closed.
The corrections select the actual child intent, retire failed fixture readers on
their original thread, snapshot mutable owner registries and remove the injected
fault before the fresh control. A selected rerun passed 14; the combined runtime
development run passed 39. Additional reader/recovery/shutdown checks passed 22;
the final read-fence/automation/capacity/restart selection also passed 22. Those
selections overlap and must not be added into a unique-test count. All these are
development evidence, not final suites.

The Windows close test now skips at module level before `msvcrt` and native
fixtures on non-Windows platforms, preserving all original Windows assertions.
Focused regressions execute that real module with linux/darwin/freebsd platform
values and forbidden native imports. No available non-Windows runtime was used;
this simulated import check is not a native cross-platform suite claim. No runtime
or dependency was installed, upgraded or redirected in the deployed environment.

The first frozen attempt (`final-one`) completed 661 focused passes with two
failures in accepted supervisor-death coverage, at the 10-second setup event
wait. Both supervisors were still running without stdout/stderr at that deadline;
no source/test bytes changed during the run. Related/full were not started after
that failed focused result. Diagnostic reruns of those exact cases passed (actual
initial native event waits 7.531 and 7.547 seconds); this does not prove the cause
or eventual progress of the independently cleaned failed supervisors.

The test-only correction permits 30 seconds for the full generated-success
supervisor setup to signal its exact owned native event. The general event helper
still defaults to 10 seconds, refuses invalid/unbounded waits, and still fails
without the actual event. A connected Windows regression verifies both timeout
refusal and the exact signaled event. Existing Windows close assertions and
product phase/cancellation/ownership/accounting guards are unchanged. This is
fixture setup headroom, not a product assembly timeout or a performance policy.
The failed snapshot, diagnostic log and corrected development rerun are preserved.

A further actual native-thread probe reproduced lost startup ownership: after a
real finalizer thread started and its launch acknowledgement raised, the backend
lost its reference and reported joined/complete while the blocked thread lived.
The probe independently released/joined that exact disposable thread. The second
frozen attempt (`final-two`) was therefore stopped before further source/test
edits: its recorded 467-file snapshot stayed unchanged, exit 4294967295, no final
pass claim. The exact actual pytest child below its Windows launcher was verified
before termination; its owned native test jobs were retired and no tagged suite
or supervisor processes remained. This is independent test cleanup, not product
shutdown evidence. The initial ambiguity from two Windows launcher/process
matches was refused before selecting the verified actual child.

The runtime correction retains started/unconfirmed worker and capture threads,
fences processing on worker launch failure and bases safe exit on actual joins.
Three regressions cover a real blocked worker after startup acknowledgement loss,
a real writer still addressable through stop/H/automatic completion, and an
interrupted startup without a confirmed join. The combined corrected development
selection passed 33; the earlier event-setup/Windows/restart selection passed 15.
The actual probe, aborted snapshot, corrections and development logs remain.

## A1–A20 evidence map

All current runtime evidence is disposable offline Windows coverage, not full
deployed acceptance. Accepted lower-layer regressions are preserved separately.

| Requirement | Runtime evidence / remaining gate |
| --- | --- |
| A1 | Same creator/new known room while old finalizer paused; next automation cycle, immutable old intent. Offline coverage. |
| A2 | One running/one queued plus two captures, tracked single worker; automatic subsequent FIFO. Offline coverage. |
| A3 | Paused unsupported/faulted work remains counted; disjoint capture safety stays journal-backed. Full watchdog policy deferred. |
| A4 | Same room/unknown same page refuse before source; accepted native path/room regressions retained. Public aliases/deployed tests deferred. |
| A5 | Miss both H hints; runtime supervisor deaths preserve H and replacement. Accepted complete H-boundary deaths retained. Offline partial. |
| A6 | Actual runtime supervisor death before preparation stays pinned; prepared/already-terminal restart and second recovery death. Earlier adoption/retry excluded. |
| A7 | Accepted immutable-input/drift regressions retained; runtime faults remain paused/pinned. Offline partial. |
| A8 | Copy/libx264 originals/control/H hashes and raw ON/OFF, reused slots and automatic policy. Offline coverage. |
| A9 | Retention integration/execution excluded; existing protection regressions retained. Gate open. |
| A10 | Six tasks plus two captures, reserved H at bound, overflow refusal, exact return; ten lifetime successes and bounded owners/history. Offline coverage. |
| A11 | Output/catalog readiness and minimum-free admission/launch barriers; prepared recovery deferral. Reservation/resource budget excluded; partial. |
| A12 | Two captures/running/queued shutdown, no drain; actual child cancellation, retained native/SQLite cleanup, partial/unknown real thread startup and launch failure. Offline coverage. |
| A13 | Legacy import/migration/cutover excluded. Schema-10 unchanged; older schema refusal retained. Gate open. |
| A14 | Internal UUID/origin/status/targeted stop/stale callback/ambiguity coverage. HTTP/client/default activation excluded; partial. |
| A15 | Existing automation claim accepted before H/reuse/promotion, indexed restart reconciliation and unchanged raw policy. Offline coverage. |
| A16 | Generated real copy/libx264 through integrated capture/settlement; native process ownership and preserved originals. Natural media gate open. |
| A17 | No unapproved temporary reservation implemented. Resource-policy gate open. |
| A18 | Assembly has no blanket timeout; shutdown grace separate. Full phase watchdog/performance work excluded. Partial. |
| A19 | Actual owned runtime supervisor and recovery deaths plus accepted child-lifetime regressions. Full deployed/power-loss gate open. |
| A20 | Eligible prepared success only, fresh fenced recovery and next automatic FIFO; unsupported work visible/pinned. Broader recovery gate open. |

## Final verification and delivery

Final serial suites used the existing interpreter
`C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`
(Python 3.11.15 / SQLite 3.53.1), isolated configuration and temporary directories.
Every suite recorded cwd, Git root, HEAD, branch/origin/common Git directory and
actual imported `tikrec.__file__`, asserting the identified development worktree.
Verification HEAD was the accepted parent `2d542164` plus these uncommitted
source/test bytes; the delivery commit records that exact verified snapshot.
No installed/deployed editable environment was changed.

| Final suite | Actual pytest result | Harness seconds | Test selections |
| --- | --- | --- | --- |
| portability | 3 passed in 0.08s | 0.68 | 1 |
| focused | 667 passed in 3084.51s (0:51:24) | 3085.19 | 50 |
| related | 1430 passed, 2 skipped, 17 subtests passed in 3696.68s (1:01:36) | 3697.55 | 129 |
| full | 2922 passed, 9 skipped, 19 subtests passed in 3629.50s (1:00:29) | 3634.15 | 1 |

All 468 raw source/test SHA256 values matched before and after every suite;
source/tests were not edited during any frozen run. The full suite includes
47 new runtime/import-guard regressions. Accepted regressions and existing
synchronous characterization test bytes remain. The required Windows module guard
preserves its assertions, and the supervisor setup helper now allows a bounded 30 seconds for the exact native
event. Its default wait remains 10 seconds; ownership/accounting assertions stay.
Skips/subtests above are distinct from ordinary test passes. Simulated linux/darwin/freebsd import guarding is checked;
actual non-Windows collection remains unexecuted, with no cross-platform claim.

Evidence directory:
`C:\Users\Leandro\TikREC-tests\issue52-runtime-20261007\final-three`.
`frozen-source-test-hashes.json`, focused/related module lists, four pytest logs,
and per-suite provenance/verification JSON preserve exact bytes, environments,
timings, source assertions and results. Earlier development logs remain separate.
The first full run in this snapshot ended at 77% without a completion result;
its process was no longer present when the session resumed. It is incomplete
verification, not a passing suite or a diagnosed test failure. Its log, provenance,
configuration and temporary test root remain under `full*.interrupted`. The full
suite was rerun separately against the same unchanged frozen source/test bytes.
Locating the vanished harness used a read-only Windows Python process
inventory, which also displayed unrelated process command lines. No unrelated
process was signalled or changed; remaining retirement checks match only this
task's evidence and probe paths.
The full selection is the entire `tests` directory; other counts list modules.
The selected venv interpreter launches the existing base interpreter at
`C:\Users\Leandro\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe`;
both actual paths are recorded before every suite.
Git content/working-tree equivalence is checked again after commit/push.

Excluded: production access/change/restart, default activation, HTTP rollout, legacy
import/migration, broader unfinished-phase recovery, retention, #48 polling,
upgrade, performance experiment, remote worker, merge, version bump, release or
tag. Public compatibility, broader recovery/storage/retention integration,
independent integrated review and authorized natural-service validation remain
release gates. Delivery uses Refs #52, preserves pushed history including the
flagged historical `6fdacd37` Closes #52, and stops for PM review.
