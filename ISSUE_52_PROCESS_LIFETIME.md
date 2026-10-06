# Issue #52 — isolated Windows subprocess lifetime evidence

## Current guarded-publication contract — 2026-10-06

[PM decision 6010639470](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6010639470)
accepts `1e1e1cae` candidate validation, preserving accepted R1–R10/assembly.
The [publication contract/evidence](ISSUE_52_GUARDED_PUBLICATION.md) connects the
original one-shot coordinator and continuously protected candidate to its exact
claimed MP4 destination. Original acquisition narrowly adds candidate DELETE
rights; only publication-capable validation uses read-only inherited seekable
stdin. Assembly-only/validation-only defaults and arbitrary-launch refusal remain.
Schema **7** appends immutable preparation and separate observed-result evidence;
schemas **1–6 are refused/preserved unchanged**, no migration/cutover. Preparation
is not completion; native root-relative no-replace rename has no reopen/replay.
The exact local scratch-to-output successor retains all ownership. Original
assembly/candidate/validation evidence, pending manifests, accounting/claims/pins
and synchronous CLI/service defaults remain. No settlement/refund, retry/adoption,
service/production integration or release. #52 OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED;
#28 unresolved. Earlier checkpoints below are historical within their limits.

## Historical accepted validation extension — 2026-10-05

[PM decision 6000035417](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6000035417)
accepts `ee884bdc` assembly. The [same-candidate validation contract](ISSUE_52_CANDIDATE_VALIDATION.md)
adds only explicit retained-native validation authority and append-only schema-6
evidence; schemas 1–5 remain refused/preserved without migration. Original H,
accounting/input preservation, exact job ownership and R1–R10 remain accepted.
Candidate validation is the only additional cancellation-aware long reader phase;
generic readers stay finite and arbitrary post-candidate launches stay refused.
No publication, settlement, retry/adoption, service wiring or production change.
Earlier checkpoint/schema statements below are historical evidence within their
recorded limits. #52 OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED; next action: PM review.

## Durable caller fence checkpoint - 2026-10-04

The accepted R6-R7 containment/lifetime contract remains. `OwnedProcess.start`
adds an optional trusted `resume_guard` context for immediate exact verification
and resume, defaulting to existing behavior. The new internal
[durable coordinator](ISSUE_52_DURABLE_LAUNCH.md) uses this short fence to serialize
revocation commit with resume; scanning, authorization hooks, waits and streams
remain outside it. Exact process/job ownership and final-tail/EOF proof remain.
No scheduler, assembly, process adoption or service wiring. Earlier schema-3
references describe historical slices; current isolated journal schema 4 is
explicitly approved by 5982869804.

## Accepted process checkpoint and unpublished assembly use

2026-10-04: [review 5980268720](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5980268720)
**accepted `b2bff05f` R6–R7** and selected the internal unpublished-assembly
boundary. Accepted corrections were preserved without another review-only task.
The primitive now runs every required probe and FFmpeg sequentially through
`OwnedProcess`, with fresh per-child before-resume authorization, reachable exact
owners on uncertainty and no successor before exit/control release. Optional
observers on `cancel/close` preserve streaming diagnostic tails through cleanup;
existing defaults, containment, identity, irreversible cancellation and independent
whole-job/EOF evidence remain unchanged. There is no overall assembly deadline.

[Assembly contract, actual native/media evidence and limits](ISSUE_52_UNPUBLISHED_ASSEMBLY.md):
**198 focused / 1,222 related / 2,162 full passes**; related six skips / 17 subtests,
full seven skips / 19 subtests. Two generated AVC paths pass existing part,
packet-DTS and deep-output validation with unchanged source/control hashes,
unchanged synchronous frame timing and absent requested final paths. No queued
session, durable launch record, sealed-input adapter, publication or settlement.
No full A1–A20 or deployed Scheduled Task gate is inferred. #52 stays OPEN/SINGLE
ACTIVE; #48 OPEN/PAUSED; #28 unresolved. Next is project-manager review of the
pushed assembly primitive, not automatic worker integration or cutover.

## Historical focused R6–R7 correction checkpoint — now accepted

2026-10-04: [review 5979948212](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5979948212)
retained `86b9d4d4` creation-time containment but required startup/close fencing
and final-stream reconciliation before integration. R4–R5 remain accepted.
The existing isolated branch was pulled (already current/clean), repository and
open issues reconciled, then MODEL GATE / PROCEED used GPT-6.1 Sol — High.
#52 stays OPEN / SINGLE ACTIVE; #48 OPEN / PAUSED; #28 unresolved.

**R6:** close now commits irreversible cancellation intent under the same lock
that guards native allocation and resume. Startup checks that intent both before
allocation (after unlocked validation) and before resume. Close computes whether
termination is required only after obtaining that lock; a prior read of an empty
native process cannot skip required cleanup after creation wins. Intent is never
cleared and `closed=True` only describes completed resource cleanup. The hook
still runs outside the lock, permitting cancellation while authorization is
blocked. Already-confirmed exit survives a stale-hook failure during cleanup.

**R7:** `ProcessEvidence.stream_status` is an internal `(stdout, stderr)` tuple:
`not_open`, `pending`, `complete` (native EOF observed), or `incomplete` (drain
fault/bound reached without EOF). It is independent of process lifetime. Native
zero-member/root-handle exit proof stays `confirmed_exited` during final stream
faults or timeouts. A collection pass before status is not final-stream proof.
After exit confirmation, polling uses bounded final batches, and wait repeats
them until both EOFs, a stream fault or the supplied deadline. An empty available
read without EOF remains pending; there is no single extra-read assumption.

Each collection batch retains the existing eight × 8-KiB per-stream limit; a
poll that first proves exit can perform an initial and a final batch. Subsequent
confirmed-exit polls perform only the necessary final batch. Prefix capacities
are unchanged. Observers are supplied per poll/wait call, not registered across
calls; collected bytes update prefixes and dropped-byte counts once before an
observer is invoked. A failing observer's chunk is not replayed; the original
error remains even if later pipe EOF is reconciled. Counts describe bytes actually
collected, and incomplete status explicitly leaves the unread remainder unknown.

Wait leaves pending readers available for reconciliation; a fault/deadline makes
incompleteness explicit. Close spends its remaining shared cancellation/drain
budget before reader release. A normal close drains both EOFs. If a stream still
fails or exceeds the bound, close can release it only with the retained incomplete
status/error, while preserving native-confirmed exit and already collected bytes.
Unknown **process** lifetime still retains all native controls. Creation faults
can leave parent write copies open; after proved exit these are released before
EOF draining, without replacing the original creation failure.

### Reproduction and corrected evidence

Regressions were added before implementation. Against unchanged `86b9d4d4`, the
expanded baseline was **14 failed / three passing controls, 0.75 seconds**
(`baseline-orderings.log`): five startup/cleanup expectations and nine tail/drain
expectations failed. The real validation-gap close returned first, then the child
actually wrote `forbidden.txt`. All three native tail fixtures returned confirmed
exit with final stdout/stderr missing. Some state tests also expose absent stream
completion metadata; those are contract gaps, not separate Windows failures.
The earlier smaller baseline was 13 failed / one passed, labelled separately.

Independent exact-job guard cleanup was strengthened for the baseline's hidden
controls: after the guard proves zero members, it verifies the exact root object
and releases handles directly without trusting the broken owner's `closed` flag.
No baseline failure can strand that disposable job. No PID/name termination.

Twenty new regression cases now distinguish portable native-double state evidence
from real Windows evidence. Native barriers cover close winning validation,
creation winning before three concurrent close/cancel callers, cleanup during
blocked authorization, and resume winning before exact-job cleanup. Native tails
are published only after initial collection, then actual root signaling and zero
job membership are observed before the final collection. Tests cover stdout,
stderr and both streams, prefix/drop accounting and no duplicate observation.

Additional state cases require multiple bounded batches and delayed bytes after
an empty final read. Native final ReadFile failure retains exit proof and permits
tail reconciliation; a duplicated test-only parent writer deliberately withholds
stdout EOF after zero job members, proving a bounded incomplete result and later
EOF reconciliation after that writer closes. All extra handles and test threads
have bounded independent cleanup. No reader thread was introduced.

- Final focused runner selection: **91 passed, 4.49 seconds** (`focused-final.log`).
- Final related process/finalization/capture/journal/lifecycle/live/writer/recovery
  selection: **675 passed / two skips, 76.15 seconds** (`related.log`).
- Final full isolated suite: **2,115 passed / seven skips / 19 subtests passed,
  230.21 seconds** (`full.log`).
- The generated FFmpeg fixture reran with unchanged command/media settings and
  input hash; existing part and deep output validation passed. The retained
  focused input/candidate hashes equal the historical values below byte-for-byte.
- Existing containment, owner-death, descendants, nesting, identity, streams,
  cancellation, native cleanup and R4–R5 coverage are preserved.

New logs/config/state/media are external and disposable under
`C:\Users\Leandro\TikREC-tests\issue52-r6-r7-20261004`, using the same isolated
configuration/temp/import harness and selection patterns recorded below.
The first corrected run passed 88 cases; expanded coverage passed 91. Duration
inspection exposed parent-owned write endpoints postponing EOF after creation
faults; releasing them before final drain removed those artificial timeouts.
Only the final run above describes the current correction code.

No containment, journal schema/public interface or synchronous launch default is
changed. No queued session is consumed. No production access/mutation, worker,
assembly/publication, settlement/retry, migration/cutover, restart, retention
execution against user data, #48 polling, resource policy/benchmark, upgrade,
release/tag or merge occurred. The stuck-native-API/uncooperative-callback limits,
deployed Scheduled Task gate and all full A1–A20/integration gates remain. Next
is project-manager review of the pushed R6–R7 correction; no owner decision pending.

## Historical `86b9d4d4` process-foundation checkpoint

## Authority and scope

2026-10-04: the process owner is implemented on `codex/capture-journal-handoff`,
based on `3d26a7bc`, for project-manager review. [Review 5979465363](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5979465363)
accepted R4–R5 and selected this process-only slice. Normal pull, reconciliation,
MODEL GATE / PROCEED used GPT-6.1 Sol — High. #52 remains OPEN / SINGLE ACTIVE;
#48 OPEN / PAUSED, #28 unresolved. No owner product decision is pending.

This completes an isolated internal process boundary. No synchronous caller is
switched to it. There is no scheduler, queue consumption, sealed-input adapter,
publication, success settlement, recovery adoption or automatic retry. No full
A1–A20 service acceptance follows from these fixtures. Production state, markers,
configuration, media and service were not accessed or changed by this slice.
No migration, retention execution against user data, polling, resource policy,
benchmark, dependencies/runtime upgrades, remote worker, release/tag or merge.

## Implemented contract

`OwnedProcess` is single-use, bound to explicit canonical session and attempt
UUIDs. `start()` requires an absolute existing `.exe`, an explicit argument vector,
an absolute existing working/output scope and a mandatory before-resume hook.
The caller must supply a disposable scope; the runner does not discover paths.
Native command-line quoting uses `subprocess.list2cmdline`; no shell is started.
The argv tests include spaces, quotes, trailing backslashes, empty and Unicode
arguments, and shell metacharacters.

An unnamed, noninheritable private Job Object is configured and queried for
kill-on-close with no breakaway. `STARTUPINFOEXW` includes `JOB_LIST` and an exact
three-handle `HANDLE_LIST` (NUL stdin, stdout/stderr write endpoints). Association
is part of `CreateProcessW`, which requests suspension and no visible window.
There is no create-then-assign interval or uncontrolled fallback. The owner/service
never joins the attempt job. Process/thread/job handles and parent pipe readers
are noninheritable. Parent copies of child stream endpoints close before the hook.

PID, native creation FILETIME and actual executable are derived from the exact
held process object. The caller's hook receives this immutable attempt-bound
identity and must return that exact identity after fresh authorization. A token
or historical receipt alone grants nothing. The future scheduler must validate
its current durable claim and persist/bind this launch identity before returning.
This implementation does not perform those journal operations. Hook failure,
mismatch or cancellation leaves the child unresumed and triggers bounded owned
cleanup. A post-create fault retains obtainable identity before releasing handles.

The hook runs outside the owner lock so another thread can cancel a suspended
launch while authorization is blocked. All native operations serialize on the
owner lock. Hooks/stream observers are trusted synchronous caller code and must
return promptly; arbitrary blocked Python callbacks cannot be forcibly preempted.
Timeout bounds apply to native polling/cleanup loops, not to caller callback
execution or a stalled operating-system API. No reader threads exist.

`poll`, `wait`, `cancel` and `close` expose `not_created`, `suspended`, `running`,
`confirmed_exited` and `exit_unknown`. Wait/cleanup bounds are explicit finite
0–30 seconds; cleanup defaults to five. Native pipe availability is polled;
each poll reads at most eight 8-KiB chunks per stream without waiting for lines.
Retained stdout/stderr prefixes default to 16 KiB each (configurable 0–64 KiB),
with dropped-byte counts. The first error and at most 31 secondary errors are
retained, with an overflow count. Context exit preserves a body error and attaches
cleanup diagnostics; otherwise accumulated failure evidence raises an owner error.

Cancellation targets only the exact owned job. Repeated cancellation/close never
launches another child. Exit proof requires the exact root process handle to be
signaled, its held creation identity to remain consistent, and native whole-job
active membership to be zero. Exit code 259 is valid when the handle is signaled.
Root exit, EOF, PID absence, a termination request or elapsed timeout alone cannot
confirm whole-job exit. Windows can include private console-host members, so
tests do not infer lifetime from an assumed one-process count. Native image
queries are used while suspended; they can fail after exit (observed WinError 31).
Stable PID/creation FILETIME checks use the retained object after exit instead.

Unknown lifetime retains exact handles and evidence. The caller must retain this
owner and reconcile/close it; it must not interpret uncertainty as permission for
a replacement. Failed native handle closes remain tracked for another bounded
close. Confirmed exit is not downgraded by a later resource-release failure.
There is deliberately no conversion to `AttemptExitProof`, media completion,
durable task settlement or launch/retry authorization.

## Native fixtures and independent cleanup

Every ordinary test launch obtains a second, noninheritable handle to its exact
private job through an independent kernel API instance. Fixture teardown restores
injected APIs, terminates that exact guard job, proves native zero membership,
then closes runner resources. Assertions and simulated runner cleanup failures
cannot strand test children. No executable-name or PID-based killing is used.

Owner-death probes run inside an outer disposable guarded job. Their inner
runner's kill-on-close job is never duplicated by the supervising test. Only
exact child process handles are duplicated from the held outer owner process.
Named native events establish phase boundaries with independent bounded waits.
The test terminates the exact disposable owner process, then waits on held inner
child/descendant objects and checks outer whole-job exit. This proves inner job
last-handle owner-death behavior while retaining independent emergency cleanup.

| Case | Actual bounded evidence |
| --- | --- |
| Creation/containment faults | Nine phase faults plus partial pipe/attribute setup and unavailable limits/JOB_LIST/CreateProcess refusal; no fallback; original error retained and resources released. |
| Owner death | Before CreateProcess, after contained suspended creation, blocked before-resume authorization, running child and running child with descendant. Held child objects signal; native outer job reaches zero. |
| Last handle / nesting | Compatible outer/inner jobs execute; closing one of two inner job handles leaves the child live, closing the last kills it. Exhausted one-process parent limit refuses nested child creation before execution. |
| Descendants | Root exits while native members remain; no whole-job confirmation until exact-job cancellation reaches zero. A separate live job and its held root remain untouched and later exit normally. |
| Authorization / identity | Session, attempt, PID, FILETIME and image mismatches; token-only response; hook error; cancellation while hook is blocked; corrupted retained creation identity never grants exit proof. |
| Native observation failures | Job query, root wait, creation-time read, pipe peek/read, exit-code query and termination faults retain unknown lifetime and exact control, then reconcile after restoration. |
| Streams / cleanup | Silent child, 1 MiB on each stream without newlines, bounded prefixes/drop counts, observer error, primary plus secondary close errors, attribute-list cleanup error and repeated query errors. No abandoned reader threads. |

A parent UI-handle restriction did **not** refuse nesting on this host; no such
support claim is made. The enforced parent active-process limit supplies the
actual incompatible-containment fixture: native WinError 1816, `not_created`.
Observed private job members included
`conhost.exe`; zero-member exit checks cover that member too. These results do
not establish compatibility with the deployed Scheduled Task or every parent
job/Windows policy. Unsupported APIs and incompatible creation fail closed.
Native lifetime containment is not a filesystem/network security sandbox or
power-loss certification. Caller code and its chosen executable remain trusted;
native permission/handle operations must succeed to obtain the stated evidence.

## Real bounded FFmpeg fixture

The test generates 0.6 seconds of 64×64 AVC/AAC FLV using the existing local
fixture helper (30-second bound). The runner executes the existing concat
stream-copy command builder into a separate scratch `candidate.mp4`, with the
current `-nostdin -n`, `-map 0 -c copy -movflags +faststart` settings unchanged.
It proves native root exit 0 and zero job members within 30 seconds. The input
SHA-256 is identical before/after. Existing `validate_part` returns no problems
or warnings; `validate_target(..., deep=True)` passes including output decode.
No queued session, publication promotion or completion receipt is involved.

One retained focused run (`focused-native-passed`) produced:

- Input `part-0001.flv`: 8,823 bytes, SHA-256
  `880bf089561569627028361e96a834c4e083bcea6e8952043c1d8127214cce97`.
- Scratch candidate: 9,635 bytes, SHA-256
  `3e58d102d463d6fdaf6dfd498b937144a7fc6b2f9eb61bfad6703bf387d1838c`.

This is suitable generated-media process evidence, not a natural recording,
codec-change proof, queued publication or service acceptance. #28 remains unresolved.

## Verification and retained evidence

Environment: Windows native build 26200, x64 pointer ABI; existing Python 3.12.10,
SQLite 3.49.1; existing FFmpeg/FFprobe `N-124716-g054dffd133-20260531`.
All logs, child barriers and media live outside Git and production roots under
`C:\Users\Leandro\TikREC-tests\issue52-process-owner-20261004`.
The harness redirects APPDATA, LOCALAPPDATA, XDG configuration/state, TEMP/TMP
and pytest basetemp; it imports the isolated worktree and disables pytest cache.

- Historical focused runner selection: **71 passed, 3.90 seconds** (`focused-final-identity.log`).
- Historical related process/finalization/capture/journal/lifecycle/live/writer/recovery
  selection: **655 passed / two skips, 75.34 seconds** (`related-final.log`).
- Historical full isolated suite: **2,095 passed / seven skips / 19 subtests passed,
  141.55 seconds** (`full-final.log`).
- R4–R5 tests are preserved in the related/full selections; schema 3 and existing
  refusal/history/FIFO/stop/admission/eight-unit accounting are unchanged.

Reproduce with the retained `run.py` harness: focused `tests/test_owned_process*.py`;
related adds `tests/test_finaliz*.py`, `test_ffmpeg_progress.py`, `test_capture*.py`,
`test_session_journal*.py`, `test_lifecycle_lock.py`, `test_live*.py`, `test_writer*.py`,
`test_recovery*.py`, `test_automatic_raw_copy_recovery.py`, and
`test_automation_recovery.py`; full uses `tests`. All patterns are under `tests/`.
Earlier related/full runs passed 654 / 2,094 before the final bounded-error test
and final identity-retention refinement; the final runs above cover the delivered code.

The first regression collection failed because the new module did not yet exist.
Early native iterations exposed the post-exit image-query failure, probe module
invocation mistakes, console-host count assumptions, a missing command-builder
keyword and misplaced test assertions. Independent exact-job guards cleaned
failed fixtures. These intermediate runs are retained; they are not passing
acceptance evidence. Final result counts above supersede intermediate runs.

## Partial service evidence and remaining gates

| Design case | Added evidence; full gate still outstanding |
| --- | --- |
| A6 | Contained creation/owner-death/identity/descendant control only. Durable launch records, crash retry/adoption, immutable input reopening and publication/manifest/database crash ordering remain. |
| A12 | Bounded isolated cancellation/wait/stream/cleanup, no reader-thread escape, unknown-exit retention. Two captures plus running/queued task, coordinated service shutdown and task retention remain. |
| A19 | Actual owner death at creation/resume/execution boundaries, last-job-handle behavior and nesting fixtures. Deployed Scheduled Task acceptance and integration with durable attempt ownership remain. |

No full A1–A20 row is marked passed. Other bridge/journal proof limits remain
exactly as recorded in their reports. Next safe action is project-manager review
of this pushed process slice, then selection of one bounded integration slice
under a new MODEL GATE. No automatic worker implementation or production cutover.

## Primary native references

- [UpdateProcThreadAttribute: JOB_LIST and HANDLE_LIST](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
  documents creation-time association and handle-list requirements; JOB_LIST
  requires Windows 10 / Server 2016 or later. This states the API support floor,
  not tested coverage of every supported OS.
- [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
  documents child containment, nesting and last-handle kill semantics.
- [Job basic limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information)
  documents kill-on-close; this runner sets no resource/priority/breakaway policy.
- [Job accounting information](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information)
  supplies whole-job membership evidence; a job handle signal alone is not used
  as a general proof that every member exited.
- [PeekNamedPipe](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-peeknamedpipe)
  reports currently available bytes; availability is not proof of final stream
  completion. Its synchronous-handle API-stall caveat remains a native trust limit.
- [Redirected child output example](https://learn.microsoft.com/en-us/windows/win32/procthread/creating-a-child-process-with-redirected-input-and-output)
  distinguishes output draining from process creation and requires parent write
  copies to close for EOF. This runner uses bounded availability polling/EOF
  reconciliation instead of copying the example's blocking read loop.

These references explain the mechanism. The tests supply only the empirical
native evidence and limits described above.
