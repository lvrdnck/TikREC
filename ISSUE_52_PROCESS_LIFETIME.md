# Issue #52 — isolated Windows subprocess lifetime evidence

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

- Final focused runner selection: **71 passed, 3.90 seconds** (`focused-final-identity.log`).
- Final related process/finalization/capture/journal/lifecycle/live/writer/recovery
  selection: **655 passed / two skips, 75.34 seconds** (`related-final.log`).
- Final full isolated suite: **2,095 passed / seven skips / 19 subtests passed,
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

These references explain the mechanism. The tests supply only the empirical
native evidence and limits described above.
