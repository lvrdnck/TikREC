# Issue #52 — durable attempt and child-launch authority

## Authority and scope — 2026-10-04

[PM review 5982869804](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5982869804)
accepts `44711e65` sealed-input protection and approves this isolated slice.
The existing branch was pulled/reconciled before inspection; MODEL GATE /
PROCEED selected GPT-6.1 Sol — High. Accepted R4–R7/assembly/guard reviews were
not repeated. #52 remains OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED with Gracie-only
raw/Ward-OFF criteria intact; #28 unresolved. Owner decisions: None.

`AttemptCoordinator` is an internal one-shot owner over an explicit existing
`CaptureAuthority`. It claims FIFO once, protects actual committed H inputs,
and executes sequential explicitly authorized contained readers. It neither
polls nor connects the queue to MP4 assembly. Successful readers leave the task
running/unfinished, with its counted unit and every artifact/raw/room/path pin.
There is no publication, success settlement, automatic retry or adoption.

## Durable contract

The approved minimal journal revision is **4**. `attempt_owners` adds permanent
local-owner UUID, independent revision, held/revoked state, claim operation,
original H operation/revision/seal, attempt-time marker observation and sequence.
`child_launches` stores permanent launch UUID/sequence, phase/executable/argv/cwd,
input bindings and predecessor, then independent native identity, whole-job exit,
diagnostic and cleanup records. Each phase has its own immutable operation receipt.
Launch intent and identity/exit/diagnostic/cleanup history cannot be rewritten or
deleted; marker binding cannot be rebound and revocation cannot be reversed.

Schemas 1, 2 and 3 are retained/refused unchanged, with no migration, empty
recreation, alternate authority or engine upgrade. A frozen schema-3 fixture
contains retained state and proves byte-identical refusal. Existing schema-1/2
fixtures remain. DELETE/EXTRA, foreign keys, 1000-ms busy timeout, operation
receipts and the existing eight-unit/two-capture/single-finalizer rules remain.

| Boundary | Required proof / effect |
| --- | --- |
| Claim | Existing FIFO/single-running rule; fresh local owner UUID; exact claim receipt confirmed/reconciled before native creation |
| Inputs | Actual current task/attempt ownership plus original H seal/receipt/marker independently validated; held read protection |
| Intent | Unique launch UUID and next sequence; explicit executable/argv/input seal/marker/predecessor durably committed before creation |
| Suspended authorization | Current local owner/revision, final input checks and exact native PID/creation FILETIME/image durably bound before resume |
| Resume | Short local gate plus DELETE-mode read transaction serialize immediate exact native verification/ResumeThread against revocation commit |
| Exit | Native-confirmed whole-job zero membership and exact retained creation identity, separately from EOF/diagnostics |
| Successor | Prior whole-job exit, local control release and confirmed/reconciled durable exit/diagnostic/cleanup receipts; complete diagnostics |
| Close | Irreversible local cancellation and durable revocation; retain input protection while any possible reader/unclean native owner remains |

Lost acknowledgements receive one bounded lookup of the **same** permanent
operation, with kind/argument digest checks. The mutation is not reissued. Missing
or unavailable reconciliation blocks execution/successors. Operation replay is
historical evidence, never permission for another creation or resume. Every
child uses a fresh single-use `OwnedProcess`; repeated authorization refuses.

Legacy `hold_attempt`/failure/retry/settlement callbacks are fenced for owned
attempts. Caller-supplied exit/publication assertions cannot release their unit
or pins around unresolved children. Existing legacy journal operations continue
for attempts without this owner protocol; no automatic retry policy is added.

Current audits inspect at most eight unfinished owner records and the latest
child/immediate predecessor, with indexed receipt bindings. Child history is
explicitly paged (maximum 100). Inspection/reopen exposes held/revoked facts;
it cannot reconstruct local launch capability, adopt a process, infer absence
from a PID or restart source capture. Unrecorded exit remains unrecorded even
when independent test handles prove that owner death killed disposable readers.

## Claimed-input and process lifetime

`acquire_sealed_inputs` remains original-queued-only. `ClaimedInputs` is a
distinct protocol using the accepted native protection mechanics. It validates
the current running task/attempt/token/local owner, independently validating
original H and marker revision. A claim/task revision is never substituted for
the stored H revision. Explicit receipt-scoped `advance` accepts only the next
expected owner revision; unexplained current state changes fail closed.

Complete FLV/raw/arrival/control/marker inventory remains held with read-compatible,
noninheritable native controls denying conflicting data-write/delete sharing.
Controls compare stored hashes; media compares native identity/size/write stamps.
The durable marker hash is an **attempt-time observation**, not a retroactive H
byte hash. No capture control or original seal is rewritten. Compatible existing
root lifecycle protection permits disjoint capture and takes no capture unit.

Scanning, file reads, process creation, authorization hooks, streaming, waiting
and cleanup run outside authority/SQLite locks. The final resume transaction
contains only current-row checks and immediate exact native verification/resume.
Local cancel intent takes the gate before acquiring process locks, avoiding the
inverse-order deadlock. Cancel winning the gate prevents execution; resume
winning leaves the child in its existing contained exact-job owner for cancellation.
External revocation linearizes at commit. No polling, native waits or caller
barriers belong inside the resume transaction.

Creation-time JOB_LIST containment, restricted inherited handles, exact handles,
kill-on-last-job-handle-close and R6–R7 remain. The recording service is never
put in a per-attempt job. Whole-job exit, stream EOF, diagnostic completeness,
local cleanup and media outcome remain separate facts. Streaming accounts/hashes
all observed chunks with bounded prefixes/drop counts; observer/read/EOF/cleanup
failures prevent complete diagnostics and preserve already-proved exit.

`AttemptError` retains first failure, secondary diagnostics, coordinator, child
owners and guard. Secondary diagnostics are capped at 32 with an explicit drop
count. Only the latest sequential child can retain live controls; cancellation
and native cleanup do not revisit every historical child's wait bound. Unknown
lifetime or cleanup failure retains the protected guard alongside exact owners.
Local proven exit/cleanup can permit guard release despite unavailable durable
bookkeeping; that uncertainty still holds the task and forbids any successor.

## Actual verification

Initial regressions before implementation: **three failed** (missing coordinator),
0.83 s. An added real cancellation ordering subsequently reproduced a revision/
guard-advance race: **one failed / seven passed**, 3.87 s. Serialized receipt
advances and independent native cleanup corrected it; subsequent selections pass.

| Selection | Actual result | Duration |
| --- | --- | --- |
| Focused complete | 484 passed, two skips | 106.33 s |
| Related | 1,281 passed, six skips, two subtests passed | 168.04 s |
| Full isolated offline | 2,270 passed, nine skips, 19 subtests passed | 184.20 s |

Windows build 26200 x64, Python 3.12.10, SQLite 3.49.1 and installed FFmpeg/
FFprobe N-124716-g054dffd133-20260531, unchanged. An earlier narrower focused
selection passed 424/two skips in 102.15 s. Skips are existing POSIX/native-
platform cases and two direct-symlink privilege fixtures; no privilege/config
changes. The related selection here differs from the prior guard slice; the
full selection remains all tests.

All runs use fresh external roots, redirected APPDATA/LOCALAPPDATA/XDG/TMP/TEMP,
isolated-source PYTHONPATH and disabled pytest cache. Logs and disposable evidence
are retained under `C:\Users\Leandro\TikREC-tests\issue52-durable-launch-20261004`.
Full invocation: `python -m pytest tests --basetemp <fresh-directory> -q
-p no:cacheprovider` through the retained `run.py` environment wrapper.
Focused includes attempt/claimed input, capture handoff/fence, journal, sealed
input, process, unpublished assembly/diagnostics and lifecycle tests. Related
adds capture/session/finalization/recovery/retention/live/raw/source/part/FLV.
Changed package/test modules remain below 300 lines; whitespace checks pass.

Coverage uses actual disposable CaptureBridge H/raw/journal/guard fixtures.
It covers FIFO/competing claims, two disjoint replacement captures, sequential
readers, lost claim/input/intent/identity/exit/diagnostic/cleanup acknowledgements,
unavailable reconciliation, historical/stale callbacks, legacy transition fences,
revocation and namespace tampering after identity, final tails beyond one drain
batch, EOF/observer/cleanup faults, retained handles and repeated cleanup.
Native barriers cover both sides of authorization; cancel-winning payloads do
not execute. Root exit with a live descendant refuses durable exit/successor;
exact-job cancellation proves whole-job exit while an unrelated process survives.

**Ten real supervisor-death orderings** cover uncommitted claim, committed claim,
uncommitted/committed launch intent, contained suspended creation, uncommitted/
committed identity persistence, resume, uncommitted exit and committed exit.
Tests duplicate only exact child process handles, not private jobs; an independent
ancestor-job guard guarantees cleanup if assertions fail. Reopened real journals
retain exactly the committed records/ownership, no duplicate launches, refunds
or fabricated cleanup. Process-death/rollback evidence is not power-loss proof.

### Generated read-only FFprobe evidence

The focused fixture session is `e277b3cf-6c76-4001-99c2-ef83402f492e`, original H
revision **4**, attempt `ccf896cc-7bb2-4b89-afa5-6585da768438`, owner revision
**12** after two readers. These are historical fixture identities, not launch
or termination permission. Existing part decoding and packet-DTS validators pass.

| Sequence / launch | Native PID / creation FILETIME | Exit / active / EOF / stdout bytes |
| --- | --- | --- |
| 1 / `7b3f11ed-1c27-4878-a612-3e44bfdbe9c6` | 17704 / 134356129826657116 | 0 / 0 / both complete / 275 |
| 2 / `f0bc93a1-f8a2-4975-8380-3ed9c2547950` | 59596 / 134356129828794450 | 0 / 0 / both complete / 2635 |

Both children use the installed absolute FFprobe executable, mandatory suspended
authorization, complete diagnostics, no truncation/errors and confirmed local
cleanup while input protection remains held. Source/raw SHA-256 is
`880bf089561569627028361e96a834c4e083bcea6e8952043c1d8127214cce97`; retained FLV
is `ba3bd1029bbfdb81065eadd09902b0c54a32dd11abb184a9f31b630fff61f51a`.
Marker is `9190cb3c884a5b771821af9c80c0199ec15b9f555fa21a03ddb6708066dfa23c`.
Actual raw/arrival/manifest/connections/marker hashes and source bytes are unchanged.
Complete hashes, receipts and child evidence are in `durable-reader-evidence.json`.
Lifecycle byte-lock files are excluded from byte hashing and checked natively.

Journal bytes intentionally change. Table snapshots prove only the declared
claim session/task/attempt fields, owner/child records and new operation receipts
change; bindings/units/artifact/room/queue/automatic receipts and original H/seal
remain identical. Final destination is absent; unfinished task/unit/pins remain.
Separate matching-copy/differing-libx264 generated assembly regressions rerun
existing part, packet-DTS and deep output validation with unchanged inputs and
absent requested destinations. No sealed queued fixture is assembled.

## Limits and remaining integration gates

This is partial internal launch/input/process evidence, not full A1–A20 service
acceptance, Scheduled Task acceptance, media completion, real-LIVE performance
or power-loss certification. No production or pre-existing recording is read.
Generated media exercises validators; a natural-recording check is outstanding.
Trusted hooks must return promptly and native APIs must obey their contracts.

Accepted guard limits remain: native media metadata is not whole-media hashing
or raw semantic provenance; sufficiently capable writers can reproduce metadata
before acquisition. Directory pins permit child creation; repeated inventory
checks require cooperative namespace ownership and are not an atomic namespace
snapshot. Privileged interference/compromised callers are outside this proof.
The inherited direct-symlink privilege skips remain explicit; junction refusal
is exercised without privilege changes. Test hash equality is not a new seal
guarantee or proof that Windows excludes every attribute operation.

Remaining reviewed gates: durable scratch/candidate protocol, queued assembly,
validation/publication receipts and promotion, success/failure settlement and
retry policy, scheduler/service/API/monitor/bootstrap integration, storage/
watchdog/resource/priority policy, retention integration/destructive rechecks,
migration/cutover and deployment acceptance. No such path is implemented here.
No production change/restart, retention execution, #48 polling, dependency/runtime
upgrade, release/tag/remote worker or merge/cutover. Next action: PM review of
this pushed slice; pull/reconcile its decision before any successor work.
