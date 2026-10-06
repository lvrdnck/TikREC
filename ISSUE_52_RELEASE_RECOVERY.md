# Issue #52 — explicitly recover prepared successful releases

## Authority and accepted foundation

[PM decision 6017389662](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6017389662)
accepts `0665b5e8fe6021fa088d0bab82a3470aece72617` as the successful owned
settlement foundation and authorizes only this bounded successor. R1–R11,
assembly, validation, publication, and corrected manifest completion remain
accepted without another review cycle. #52 stays OPEN / SINGLE ACTIVE; #48 stays
OPEN / PAUSED; #28 remains unresolved. This is not service, deployment, merge,
or release approval.

This task recovers one explicitly addressed attempt only after durable successful
release preparation exists. A completed MP4 and installed/flushed manifest are
already present. Earlier unfinished capture, assembly, validation, publication,
manifest, or no-preparation states remain unsupported and pinned. Recovery never
reopens the old success capability, changes media/control files, invokes FFmpeg,
replays publication, installs a manifest, or adopts arbitrary paths.

## Explicit entry and idempotency

`CaptureAuthority.recover_prepared_release(session_id, token)` requires the
caller to supply the known existing journal, media root, session, and attempt.
The ordinary journal open/read APIs remain observational. `CaptureAuthority`
holds its existing exclusive local catalog owner and native catalog/root pins
before recovery can add journal facts. No default catalog, media-directory scan,
catalog recreation, or service startup is involved.

An already-terminal addressed result is fully audited and returned without a new
recovery generation, task mutation, claim change, or attempt-file open. A prepared
but unsettled task must still own its exact task unit, task revision, room and
artifact claims. A missing or conflicting preparation, output, manifest, H/seal,
control chain, or catalog proof remains outstanding.

## New authority, fencing, and proof

Each attempt acquires a fresh compatible existing-only writer lease, then commits
an append-only recovery generation before opening attempt files. The lease refuses
to create or extend a missing/truncated lifecycle lock during recovery. A live
old `CaptureAuthority` prevents a new catalog authority from opening; a local
original attempt must also have confirmed closed native owners and SQLite readers.
Unknown ownership is a refusal. Recovery cannot impersonate the original Python
capability.

The durable recovery head fences original cleanup/settlement callbacks and all
older recovery generations. Each invocation has a new authority ID, operation
receipt and generation. Fresh no-follow handles cover only the immutable
successful-release resource list; ordinary claimed-input and native acquisition
defaults are unchanged. Recovery reads the published output and controls, checks
exact original resource identity/size/stamp, hashes output bytes, validates the
original manifest predecessor and installed successor, validates original H and
marker evidence, checks sealed control hashes, and compares complete applicable
parts/scratch inventories. The proof is rechecked under retained handles before
cleanup. It binds to the accepted validation/publication chain and preserves the
recorded interrupted or degraded-input classification.

Filesystem observations and SQLite transactions are cooperative boundaries, not
an atomic snapshot. Native metadata and directory pins retain the limits recorded
by the accepted capture-handoff contracts; no hostile-writer or power-loss
guarantee is added.

## Cleanup, restart, and terminal accounting

Original release preparation, cleanup, and settlement receipts remain immutable,
including absent or incomplete original cleanup. New proof and new recovery-owned
handle cleanup are stored separately. Every exact acquired handle and writer
lease has an explicit close result. First and bounded secondary errors remain
visible; an uncertain native or SQLite owner stays reachable and blocks another
generation on that authority. Closing a new handle never claims the old cleanup
receipt became complete.

After one generation has a complete fresh proof and confirmed cleanup, one SQLite
transaction appends the recovery terminal receipt, completes the exact task,
attempt, and session, and removes exactly its existing task unit and active
task-lifetime claims. Unknown proof, cleanup, or acknowledgement leaves capacity
outstanding. The generic `settle_task` prohibition and normal live
`JournalSettlement` path are unchanged. A confirmed terminal result cannot be
reversed or returned twice.

A second process death leaves the committed generation phase inspectable. A new
explicit invocation obtains fresh authority and starts a new generation unless
the addressed terminal result already committed. Historical receipts are never
live permission. This includes process death after authorization, proof, native
cleanup, cleanup receipt, immediately before terminal settlement, and after the
terminal commit.

Schema **10** appends recovery generation, authority, proof, cleanup, and terminal
records with immutable receipts and a 32-generation per-attempt ceiling. The
accepted schema-9 layout is frozen for refusal tests. Schemas **1–9 are
refused/preserved unchanged**; there is no migration or cutover.

## Verification and evidence

Generated Windows catalogs use actual `JournalSettlement` executions and fresh
`CaptureAuthority` recovery calls. Coverage includes two-part stream-copy,
differing-config libx264, interrupted capture and injected degraded-input truth;
the next explicit FIFO task finishes after successful recovery. Source FLVs,
raw/arrival/connection controls, both manifest versions/history, output, marker,
H and unrelated files remain byte-identical. The drift cases alter output/control
bytes while restoring the original timestamp, add an unexpected parts artifact,
and introduce a hard-link alias; all stay outstanding with no repair. Tests also
cover already-terminal idempotency, concurrent recovery calls, a competing
catalog owner, live original ownership, unsupported unprepared work, cancellation, retained native-close
failure, lost close/proof/terminal acknowledgements, and stale original callbacks.

Actual Windows `TerminateProcess` barriers cover original `cleanup_pending`,
`cleanup_incomplete`, and `cleanup_confirmed` states. A second sequence kills six
successive recovery supervisors after authority, proof, native cleanup, cleanup
receipt, before terminal settlement, and after terminal settlement; each fresh
generation or already-released result remains exact-once. Native close uncertainty
remains retained until exact cleanup is confirmed. Ordinary reopen tests continue
to require no recovery mutation.

The first child-supervisor probe could not import the repository test package
because it ran from a disposable working directory; the test now passes the
isolated worktree in `PYTHONPATH`. An initial incomplete-cleanup probe patched
`NativeHandle.close`, but the candidate is a `ScratchHandle` subclass with its
own close method, so it reached `cleanup_confirmed`; the corrected fixture injects
the fault into the exact prepared candidate owner and verifies
`cleanup_incomplete` before restart. These harness corrections did not relax
product assertions. Two attempted frozen focused runs were interrupted after
test-only changes landed during execution. Their logs and basetemps are preserved
but excluded from final counts; the final suites use one corrected frozen tree.

The first recovery-path test also exposed three implementation integration bugs:
recovery's existing-only lifecycle-lock open path was wrong, typed resource
identities needed JSON normalization before receipt comparison, and the fresh
input-1 lock handle conflicted with the newly held recovery writer lease. Each
was fixed in the implementation and the generated copy recovery passed before
the broader suites. The default pytest temp parent was ACL-denied, so all final
runs use isolated basetemps/configuration under the external evidence root.

Final frozen verification ran serially on the corrected tree and used an
independent configuration/basetemp for each suite:

- **Focused:** 18 modules; 302 passed in 1,360.88 seconds.
- **Related:** 97 modules; 1,065 passed, 2 skipped, 17 subtests passed in
  1,811.64 seconds.
- **Full:** all tests; 2,826 passed, 9 skipped, 19 subtests passed in
  2,061.33 seconds.

Every run covered the same **439 Python source/test files** and verified their
SHA-256 manifest unchanged before and after. These final runs followed restoration
of the accepted settlement test's original EOF whitespace. The direct
lease-compatibility and recovery/FIFO regression check also passed (2 passed).
The first related run on
this task exposed one compatibility failure: the new existing-only lease option
was passed to a legacy monkeypatched two-argument `_open_lock` on the normal
acquisition path. The fix preserves that established call signature and passes
the keyword only for recovery's existing-only path. The failed run and its log
remain preserved; all three final suites were rerun on the corrected frozen tree.

Logs, suite metadata, the hash manifest, disposable catalogs and outputs are
outside Git at
`C:\Users\Leandro\TikREC-tests\issue52-recovery-20261006\final-reviewed-base`.
Earlier interrupted focused attempts and initial related failures are preserved
in the parent evidence directory and excluded from final counts.

No service/API/monitor/scheduler wiring, production access/change/restart,
unfinished-phase adoption, automatic re-encoding retry, retention, #48 polling,
migration/cutover, dependency/runtime/resource-policy change, remote worker,
merge, release, or tag is included. Delivery uses `Refs #52`; historical pushed
history and accepted reports are preserved. Stop after handoff for PM review.
