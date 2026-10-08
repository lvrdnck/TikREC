# Issue #52 — explicitly constructed isolated service runtime

## Authority and current boundary

The [PM integration decision](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6030581435)
accepts R12–R13 at `2d542164` and corrected prepared-success recovery. The
[workspace resumption decision](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6030964984)
lifts the temporary audit hold and resumes this same partial task. Accepted
media/control, R1–R13, normal settlement and recovery foundations remain accepted.
[PM decision 6051730786](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6051730786)
accepts focused R14–R15 at `26cc0e7d949a83d85aa15b84acef5eb9a693bec9` and
selects the independent review below.
[PM decision 6056452748](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6056452748)
accepts that bounded implemented-contract **PASS** and selects the single
[isolated HTTP/client successor](ISSUE_52_HTTP_CLIENT.md). The review below remains
historical evidence, not a repeated acceptance task. Default/public activation and
the deferred deployment/release gates remain outstanding.
[PM correction decision 6057613070](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6057613070)
retains that successor's direction but withholds acceptance of `31650357` pending
R16–R17 HTTP request ownership corrections. Accepted runtime R1–R15 and this
bounded review remain accepted and are not repeated. [Correction evidence](ISSUE_52_HTTP_CLIENT.md).
#52 stays OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED; #28 unresolved; owner decisions None.
Review MODEL GATE / PROCEED: Complex; GPT-6.1 Sol — High (2026-10-08).

The following implementation-workspace paragraph is historical; the independent
review below verified the same root/branch/origin/common directory at `26cc0e7d`.
Implementation and every execution use the existing linked Windows worktree
`C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC` on
`codex/capture-journal-handoff`. Its common Git directory is
`C:\Users\Leandro\dev\TikREC\.git`, origin `lvrdnck/TikREC`, accepted HEAD
`2d542164c7c64fbc4a217884bec63c26246fb6fa`. The required pull was conflict-free.
The two modified/fourteen untracked partial files were preserved and continued.
The separate old desktop project and primary/deployed checkout are not editing
targets. Audit observations are not proof of every historical invocation or
the deployed process's in-memory source; prediction-work location remains unknown.

## Independent acceptance review — 2026-10-08

**Implemented contract: PASS within the disposable Windows scope below. No
runtime blocker was reproduced; no runtime source fix or accepted-foundation
redesign was made. PM review only follows this delivery.** This fresh conversation
first inspected the runtime composition and existing coverage, including the
original [integration contract](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6030581435),
H/native ownership, settlement/recovery, automation, status/stop and shutdown.
Preflight verified the exact worktree, branch, origin, common Git directory,
clean baseline `26cc0e7d`, and conflict-free required pull (already current).
The desktop/primary/deployed checkouts were not editing or test-import targets.

### Implemented / PASS / FAIL / deferred evidence

| Implemented boundary | Independent evidence / result |
| --- | --- |
| Two capture writers, one FIFO finalizer, eight units (A1/A2/A3/A10) | **PASS:** new progress cases use whole-tag barriers after real writer callbacks, then prove both byte counts increase while the old finalizer is paused at its media plan. Six tasks plus two writers retain eight units; a distinct ninth admission refuses. Actual copy/libx264 finalization automatically completes the six tasks while both later captures stay active; their subsequent H/terminal results preserve FIFO and return exactly eight units. This proves concurrency/ownership, not simultaneous CPU throughput. |
| Original UUID/room/path/raw and automation acceptance (A4/A8/A14/A15) | **PASS:** new raw-OFF/ON cases lose acknowledgement after a real automatic capture thread starts. The persisted claim survives H and two replacement captures; first-slot generation increases. A fresh coordinator with the opposite raw preference reconciles the original indexed acceptance. Changed creator/room/path/prior UUID keys refuse acceptance; stale callback and old stop cannot alter replacements. Original intent/seal/receipt and terminal history survive explicit runtime restart. |
| H/stop/shutdown and retained owners (A5/A12/A19) | **PASS for covered controls:** independently rerun all existing runtime modules, including lost H hints, oldest exclusive-proof readiness, actual Windows close protection, reused native/CRT identifiers, retained coordinators outside current, original-thread SQLite cleanup, partial thread startup, status read fencing and shutdown without queue draining. Native/input/lease/scratch/control/child, recovery inspection/protection, borrowed SQLite and catalog owners were also inspected in source. Test cleanup of deliberately retained owners is separate from product safe-exit claims. |
| Output/catalog storage readiness (A11) | **PASS for implemented minimum-free/unavailable-storage barriers:** existing admission/launch refusal tests plus new catalog-only prepared-recovery deferral while output storage remains healthy. No task refund or media mutation during deferral. Space reservations/output budgets, watchdogs and retention remain **DEFERRED**, not failures of the implemented contract. |
| Permitted restart and exactly-once accounting (A6/A20) | **PASS for prepared-success/queued/terminal scope:** new runtime recovery admits two progressing real captures while recovery authority is held. A failure after committed recovery terminal reporting preserves completion, original H/cleanup/media and exactly one recovered return. Shutdown retains three queued units; a fresh explicit runtime automatically completes them with three ordinary results, one recovery result and no second recovery generation. Existing supervisor-death, unsupported-pinned, cancellation, acknowledgement and SQLite fault controls are independently rerun. |
| Generated media/control preservation (A7/A8/A16) | **PASS offline:** real generated AVC/AAC captures feed accepted copy and libx264 assembly/validation/publication/manifest/settlement. New tests preserve original source/control/H and predecessor-manifest hashes; progressing raw-ON bytes equal the generated input and raw-OFF creates no raw file. Existing generated/death controls are rerun. No natural recording, deployed service or power-loss acceptance is claimed. |
| Implemented FAIL findings | **None reproduced.** Development fixture failures below are not product defects or passing suites. |
| Remaining public/product/deployment gates (A9/A13/A17/A18 and broader A1–A20) | **DEFERRED:** public HTTP/client rollout, default activation, retention integration/execution, legacy migration/cutover, broader unfinished-phase recovery, reservations/watchdogs/resource/performance policy, natural/deployed/power-loss acceptance and actual non-Windows collection. No automatic successor, merge or release follows a bounded PASS. |

The ownership review follows exact original objects and registries rather than
Python closed flags, slot availability, historical receipts or an empty ExitStack.
Covered faults do not constitute proof of every possible combined failure.
Accepted R1–R15 and the resolved workspace audit remain accepted; no contradictory
foundation evidence was found. The existing A1–A20 table below retains its
partial/offline limits; this review completes the requested independent check
of implemented behavior, not every deferred row of the full design.

### Independently executed verification and provenance

| Frozen selection | Actual pytest summary | Modules | Harness seconds |
| --- | --- | ---: | ---: |
| New connected review cases | 5 passed in 279.80s (0:04:39) | 3 | 280.36 |
| Related runtime/interface regressions | 292 passed in 761.36s (0:12:41) | 28 | 761.94 |

Both selections ran serially against the same **475 raw source/test SHA-256
values**, unchanged before/after. Every one of the **471 existing files** also
matches the accepted R14–R15 verification snapshot; four test/helper files were
added. Runtime source, existing tests, package/schema/defaults/dependencies and
AGENTS are unchanged. The related selection includes all eleven original runtime
test modules, automation/admission/recording/service/storage characterization,
and the three simulated linux/darwin/freebsd import guards. These simulated
guards are not actual non-Windows execution. No skip is relabelled as a pass.

Interpreter: `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`,
Python **3.11.15**, SQLite **3.53.1**; base interpreter
`C:\Users\Leandro\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe`.
Every suite asserts cwd/Git root/HEAD/branch/origin/common directory and actual
`tikrec.__file__` from this exact development worktree. Configuration/temp roots
and generated media are disposable and explicitly isolated; no installation,
external network/LIVE capture, production credentials or production recordings were used.
Frozen source/tests were not edited while either selection ran.

Evidence root: `C:\Users\Leandro\TikREC-tests\issue52-independent-runtime-20261008`.
`focused-final` and `related-final` retain pytest logs, module lists, raw hash
snapshots, process identities, interpreter/import provenance and verification
JSON. `review-baseline-verification.json` checks both snapshots and accepted
bytes; delivery equivalence and task-tagged process retirement are verified
separately. The checked-in tests preserve reproducible scenarios; generated
media, SQLite fixtures and local logs are not tracked.
`process-retirement.json` records zero remaining task-tagged Python/FFmpeg/FFprobe
processes after both selections. Exact native-job/thread cleanup is independently
asserted by the fixtures; deliberately incomplete product shutdown stays recorded
as incomplete, even when independent fixture cleanup subsequently succeeds.

Development evidence is preserved separately: `development-one` **4 failed in
36.26s**, because two simultaneous captures were incorrectly assigned the same
creator page. `development-two` **2 failed, 3 passed in 114.44s**, because the
overflow request still collided with an active page before reaching the backlog
barrier. Both freezes stayed unchanged and both pytest processes exited normally
after independent fixture cleanup. Distinct neutral creator identities correct
the fixtures without relaxing page protection or changing product source.
The final five cases then pass; prior failures are not discarded or relabelled.

Per the authoritative review decision, no redundant focused/related/full
implementation rerun was performed solely for unchanged runtime source. AGENTS'
appropriate broader verification is satisfied by the related selection above.
The earlier **677 focused / 1,440 related / 2,932 full** results and their
skips/subtests/hash provenance below remain historical implementation evidence;
they are not independently rerun results of this review.

## Explicit composition and automatic FIFO

`IsolatedServiceRuntime(journal, root, ffmpeg=..., ffprobe=...)` accepts an existing
identified schema-10 journal and explicit local media root. Fresh initialization
is a separate `SessionJournal.initialize` call. Construction acquires the single
catalog/native authority and remains passive until `start_runtime()`. It does not
construct a legacy RecordingController/StartupReconciler or operate a second
catalog. No CLI, default service factory or configuration activates it. The separate
experimental HTTP composition is documented in [ISSUE_52_HTTP_CLIENT.md](ISSUE_52_HTTP_CLIENT.md).

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

R14 distinguishes committed H/available capture slots from finalizer acquisition
readiness. The oldest queued task waits for its exact local capture thread to
finish and for confirmed exclusive H-proof teardown. It is neither claimed early
nor skipped for a later task. Waiting uses the existing bounded durable poll
outside admission locks; missed hints are harmless. Failed original proof owners
remain explicitly attached to the bridge and visible as
`capture_handoff_inputs_needs_attention`; no H rewrite or finalizer retry occurs.
Compatible root lease cleanup remains separately supervised and does not undo
confirmed exclusive-input readiness. Queued startup without a surviving local
capture owner follows the original authority rules.

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
These internal projections remain separate from the bounded experimental HTTP
projections in [ISSUE_52_HTTP_CLIENT.md](ISSUE_52_HTTP_CLIENT.md); default/deployed rollout remains deferred.

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

R15 wraps the runtime finalizer's newly acquired lifecycle lease with the accepted
exact-open-object close guard before binding inputs. Its duplicate reference
proves native lifetime even when Python marks the original stream closed. Failed
coordinators in the authority registry participate in retirement independently
of `runtime.current`. An explicit shutdown cleans retained readers on the original
worker thread and retires only proved original native references. Reused CRT
descriptors are refused, including fresh opens of the same lock file; an already
closed original can retire its duplicate without touching the reused descriptor.
Unconfirmed Python metadata remains owned too. Known-retired terminal error
history is removed from the active registry; outstanding failed attempts stay
bounded by durable units. Original preparation/cleanup receipts are preserved,
and local cleanup never settles accounting or adopts earlier unfinished work.

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
| A2 | One running/one queued plus two captures, tracked single worker; R14 oldest post-H barrier prevents leapfrogging a ready libx264 task; automatic subsequent FIFO. Offline coverage. |
| A3 | Paused unsupported/faulted work remains counted; disjoint capture safety stays journal-backed. Full watchdog policy deferred. |
| A4 | Same room/unknown same page refuse before source; accepted native path/room regressions retained. Public aliases/deployed tests deferred. |
| A5 | Miss both H hints while actual worker polls a real capture held at confirmed_h; no early claim/reader, two replacement captures admitted, release automatically completes. Actual post-H exclusive marker close fault stays owned/queued. Accepted H-boundary deaths retained. Offline partial. |
| A6 | Actual runtime supervisor death before preparation stays pinned; prepared/already-terminal restart and second recovery death. Earlier adoption/retry excluded. |
| A7 | Accepted immutable-input/drift regressions retained; runtime faults remain paused/pinned. Offline partial. |
| A8 | Copy/libx264 originals/control/H hashes and raw ON/OFF, reused slots and automatic policy. Offline coverage. |
| A9 | Retention integration/execution excluded; existing protection regressions retained. Gate open. |
| A10 | Six tasks plus two captures, reserved H at bound, overflow refusal, exact return; ten lifetime successes and bounded owners/history. Offline coverage. |
| A11 | Output/catalog readiness and minimum-free admission/launch barriers; prepared recovery deferral. Reservation/resource budget excluded; partial. |
| A12 | Two captures/running/queued shutdown, no drain; R14 stop/shutdown during confirmed_h and next explicit queued restart; R15 actual protected finalizer lease, repeated incomplete shutdown, confirmed cleanup, reported-close-after-success, reused descriptors and SQLite cleanup outside current on the original worker. Accepted cancellation/thread-launch controls retained. Offline coverage. |
| A13 | Legacy import/migration/cutover excluded. Schema-10 unchanged; older schema refusal retained. Gate open. |
| A14 | Internal UUID/origin/status/targeted stop/stale callback/ambiguity coverage. HTTP/client/default activation excluded; partial. |
| A15 | Existing automation claim accepted before H/reuse/promotion, indexed restart reconciliation and unchanged raw policy. Offline coverage. |
| A16 | Generated real copy/libx264 through integrated capture/settlement; native process ownership and preserved originals. Natural media gate open. |
| A17 | No unapproved temporary reservation implemented. Resource-policy gate open. |
| A18 | Assembly has no blanket timeout; shutdown grace separate. Full phase watchdog/performance work excluded. Partial. |
| A19 | Actual owned runtime supervisor and recovery deaths plus accepted child-lifetime regressions. Full deployed/power-loss gate open. |
| A20 | Eligible prepared success only, fresh fenced recovery after confirmed finalizer retirement and next automatic FIFO; unchanged media/H/history and original incomplete-cleanup receipt, one recovery result plus one ordinary result. Unsupported work visible/pinned. Broader recovery gate open. |

## Historical 90156913 verification and delivery

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

## Historical R14–R15 correction evidence — 2026-10-07 (accepted by PM 6051730786)

Correction preflight verified Git root/branch/origin/common Git directory in the
exact development worktree above, clean at reviewed `90156913`; the required
`git pull --rebase --autostash` was already current. New MODEL GATE / PROCEED:
Complex / GPT-6.1 Sol — High; owner decisions None. No other checkout was edited,
installed environment changed, or production process accessed/restarted.

Before production edits, two connected regressions ran against unchanged
`90156913` production bytes: **2 failed in 7.54s** (`baseline-one.log`). R14
actually claimed running work while the real capture remained inside confirmed_h
with exclusive proof handles. R15 actually returned complete/released authority
while a PROTECT_FROM_CLOSE finalizer lifecycle handle remained live, despite
Python closed flags. `baseline-production-hashes.json` and `baseline-result.json`
record the unchanged source proof; baseline failures are preserved.

Ten new connected cases cover the exact post-H worker poll with lost hints and
two disjoint captures; true FIFO ahead of a ready libx264 task; targeted-stop and
shutdown/restart; actual exclusive marker teardown failure; protected finalizer
lease both inside/outside current; repeated shutdown, independently confirmed
cleanup, fresh prepared-success recovery and next FIFO; close-after-success;
reused CRT descriptors for different/same files; and an already-terminal SQLite
reader outside current cleaned only by the original worker. Generated media,
original H/capture truth/history and incomplete cleanup receipts are checked.

Development evidence remains separate: `corrected-one` passed 2 (21.10s);
`cleanup-corrected` passed 3 (26.43s). `controls-one` had 21 passes/one teardown
error (223.00s); `controls-two` had 2 passes/one teardown error (23.05s);
`cleanup-diagnostic` had 1 pass/one teardown error (11.52s). Their actual summaries
completed but retained a non-daemon fixture worker. Only each independently
verified task-owned actual pytest child was terminated afterward; exact process
identity evidence is preserved. This was independent test cleanup, never product
shutdown success or a passing suite.

The diagnostic found a confirmed-retired native reference with an open FileIO
metadata owner. Product retirement remains conservative until that Python owner
is also closed. Independent fixture teardown proves the original native reference
gone and its CRT slot unused before disposing metadata on the owning worker;
it refuses a reused slot. It also cleans failed registry coordinators outside
current without settling accounting. `boundaries-one` preserved 5 failures/23
passes (416.19s): two new assertions incorrectly expected recovered results in
the ordinary result table, and three existing controls failed in that development
snapshot. After retirement/fixture corrections, `boundaries-two` had 1 failure/27
passes (297.28s): a new test raced a correctly reaped capture entry. The check now
uses durable queue state. **`boundaries-three`: 33 passed in 369.91s**, including
the unchanged native capture/recovery, cancellation, acknowledgement and SQLite
controls. Earlier results are not relabelled or discarded.

Evidence root:
`C:\Users\Leandro\TikREC-tests\issue52-runtime-r14-r15-20261007`.
The final source/test snapshot is `final-one`, **471 raw SHA-256 files**. Source
and tests remain unchanged during serial portability/focused/related/full runs.
Every suite records/asserts actual interpreter/base interpreter, cwd, Git root,
HEAD, branch, origin/common Git directory and imported TikREC path. The verification
HEAD is reviewed `90156913` plus the recorded task-owned uncommitted bytes; delivery
verifies equivalence to its commit in `delivery-verification.json`. Focused verification passed **677 tests in
2680.11s** (52 module selections; harness 2680.76s), with all 471 hashes unchanged.
Related verification passed **1,440 tests / 2 skips / 17 subtests in 3422.38s**
(131 module selections; harness 3423.14s), again with 471 unchanged hashes.
Full verification passed **2,932 tests / 9 skips / 19 subtests**
(2932 passed, 9 skipped, 19 subtests passed in 3758.56s (1:02:38); harness 3759.25s), with all 471 hashes unchanged.
The ten new connected regressions passed in the focused, related and full suites. The simulated
linux/darwin/freebsd import guard passed 3 (0.08s), preserving Windows assertions;
actual non-Windows collection remains unexecuted. No deployed/natural-recording,
power-loss or complete A1–A20 acceptance is claimed. Schema 10/defaults unchanged;
all original integration exclusions and PM-review-only next action remain.


### Final R14–R15 frozen verification

| Suite | Ordinary passes | Skips | Subtests passed | Module selections | Harness seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| portability | 3 | 0 | 0 | 1 | 0.65 |
| focused | 677 | 0 | 0 | 52 | 2680.76 |
| related | 1440 | 2 | 17 | 131 | 3423.14 |
| full | 2932 | 9 | 19 | 1 | 3759.25 |

All suites exited zero; 471 raw source/test hashes matched before and after
each suite. Full selection is the entire tests directory. Logs, provenance,
module lists, isolated configurations and verification JSON remain in `final-one`.
The actual imported package was the development worktree `tikrec\__init__.py`,
never deployed main or the old desktop project. Commit/push equivalence and
task-owned process retirement are recorded separately at delivery.
