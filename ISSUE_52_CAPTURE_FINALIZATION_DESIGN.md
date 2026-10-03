# Issue #52 — capture availability and durable local finalization

## Review status and authority

2026-10-03: **isolated journal slice IMPLEMENTED for review; service integration NOT implemented.**
[Review 5970143137](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5970143137)
approves internal journal operations only, not service integration or cutover.
#52 remains OPEN / SINGLE ACTIVE; production behavior remains synchronous.
Implementation, exact internal operations, tests and proof limits are in
[ISSUE_52_SESSION_JOURNAL.md](ISSUE_52_SESSION_JOURNAL.md).
#48 remains OPEN / PAUSED, with all criteria and Gracie-only raw policy preserved;
monitored production order is `wardsimons`, `gracie.kf`, Ward raw OFF. #28 remains
unresolved. This task did not access the service, configuration or recording root.

The [priority correction, comment 5969640467](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5969640467)
supersedes the Below Normal-only next-slice recommendation in `978cce93`.
That resource investigation remains valid within its scope, including the old
TikREC NVENC attribution. Slowing the current synchronous finalizer can lengthen
the capture-availability exposure. Capture ownership separation comes first.

## Deterministic reproduction of CURRENT behavior

Source baseline: `978cce93779ad151c3906924bd6cfccc36b1f54d`.
`tests/test_finalizing_capture_availability.py` uses real `RecordingController`,
`RecordingManager`, `JobStateStore`, `RecordingAdmission`, `AutomationCoordinator`
and `AutomationStateStore`. Injected source/finalizer callbacks enter the actual
`finalize_capture_result` wait. Events establish phase boundaries, not sleeps.
Named parts/output are fake paths only; no FFmpeg, network or media is involved.
All state/lock files live under pytest's disposable external root.

| Reproduction | Assertions supported by the running test |
| --- | --- |
| Old creator room 123 finalizing, slot 2 free | Slot 1 remains active/unavailable, durable UUID/raw flag/stop intent intact. Same page / expected room 456 is rejected as `public LIVE page already owned`. An unrelated creator can use slot 2. Old output path remains protected; retention lease acquisition fails. |
| Two closed sources finalizing | Both durable jobs remain `finalizing`; available slots = 0. An unrelated third creator is capacity-rejected. |
| Return room 456 across cycles 1 and 2 | Real admission reports ready; manager rejects the page. Automation reports `suppressed / duplicate_live_owned`, clears pending intent and leaves consumed room 123 unchanged. No new capture begins. |
| Old finalizer completes OR fails | Ordinary non-recovery worker settles and releases ownership. Settlement does not invoke monitoring. Replaying cycle 2 does nothing; new complete cycle 3 starts room 456, preserves its selected raw flag and consumes 456. Cycle 4 suppresses the same room. |
| Return room ends before release | Cycle 1 rejection followed by trustworthy offline cycles starts no returning session, even after the old finalizer settles. |

Focused result: **5 passed in 0.44 s**, repeated **5 passed in 0.42 s**;
related manager/ownership/worker/job/automation regression checks: **181 passed
in 3.05 s**, final rerun **181 passed in 2.93 s**, Windows Python 3.12.10.
At the historical `9d6299d9` reproduction checkpoint, no full offline suite or
real-media check was run: that task changed tests/design, not assembly code.
The later isolated journal slice runs a full suite, reported separately above. The first command
failed at pytest setup because the new external basetemp parent did not exist;
creating that test directory resolved setup, without changing product code.
The five tests characterize the limitation and must be replaced/adapted when
the queue is implemented; they are not acceptance of the limitation as policy.

Mechanism: `RecordingController.health()` checks `_active`; `_run()` holds a
root writer lease around `run_recording_worker`; that worker persists its result
before clearing `_active`. `RecordingManager.start()` checks `same_page` before
selecting a slot, including finalizing owners. Automation matches creator AND
room, not page alone, and duplicate rejection does not consume a new room.
A later eligible cycle may catch a still-live return, but cannot recover its
missed interval. This does not show that every overlap misses a whole LIVE, nor
explain missing post-activation Gracie evidence or #28 corruption.

## Recommended minimum architecture (PROPOSED)

Keep **two capture slots** and add **one tracked Windows-local finalization
worker**. The manager controls admission and durable transitions; workers never
decide ownership by clearing busy flags. No remote host, transfer, ASR, encoder
change, priority policy or new third-party dependency is part of this slice.
Direct one-shot local recording remains synchronous; the service uses a split
capture-only result / queued-finalization path. Shared assembly/media rules remain.

Use Python's standard-library `sqlite3` for one per-user local durable session
journal, beside the existing service state, proposed `sessions.sqlite3`.
Each UUID has a permanent independent session record and at most one finalization
task; it survives slot reuse. Transactions combine queue handoff and slot release.
An authoritative JSON queue plus separately authoritative slot files would need
a cross-file recovery protocol; this design avoids that dual authority.
Use the Task account's verified native local state location/file identity, not a
redirected desktop APPDATA view or a UNC path for journal storage. Configuration's
separately proven service-visible UNC path is unchanged. Catalog identity/location must be
bound at cutover and in session markers; tools that cannot prove the same view
fail closed rather than invent an empty alternate journal.

Approved persistence for this slice: standard-library SQLite on local storage,
`journal_mode=DELETE`, `synchronous=EXTRA`, foreign keys ON, verified settings,
explicit short transactions and a **1-second** busy timeout. No transaction spans
network/media I/O or FFmpeg execution. Reopen known state without creating a
replacement; reject unexpected catalog identity/schema/mode. Never discard a
potentially hot rollback journal or copy a live database alone. Reconcile a lost
commit acknowledgement by durable operation identity before retry/refund.
EXTRA with DELETE adds directory synchronization after journal unlink, subject to
OS/storage guarantees. Record the linked SQLite version/source identity; do not
infer it from Python. This supersedes proposed WAL/FULL; a future WAL change
requires explicit review and a verified engine with applicable WAL-reset fixes.
[SQLite synchronization](https://www.sqlite.org/pragma.html#pragma_synchronous),
[atomic commits](https://www.sqlite.org/atomiccommit.html),
[WAL-reset notice](https://www.sqlite.org/wal.html#walreset).

| Durable component | Required contents / constraints |
| --- | --- |
| Session | UUID PK, canonical creator/page, expected room separately from proven room, original requested output/parts/root identities, origin slot, accepted raw flag, start/close timestamps, stop/recovery intent, phase, revision. Identity and raw policy cannot drift. No token, transport URL or command supplied by a client. |
| Capture bindings | Exactly slot-1/slot-2; each has at most one UUID, generation counter. Only capture/resolving/recovery/closing work binds slots. Unique current page and verified/expected room claims. |
| Finalization task | UUID UNIQUE/FK, sealed generation, ordered closed parts and control evidence, enqueue time, phase, attempt number/token, owned child PID+creation time, heartbeat/progress, error code and publication receipt. One `running` task globally. |
| Artifact claims | Session-bound output, parts, attempt partials and evidence paths. Uniqueness uses native canonical parent/volume/file identity plus basename, including case/UNC aliases and path overlaps. Unknown identity cannot prove disjointness. |
| Automation acceptance | Existing consumed-room semantics plus durable accepted automatic-start receipts bound to a persisted claim UUID and intended creator/room/paths. Expected room is a reservation, never misrepresented as source proof. Pending automatic claim reconciliation can search every accepted session, including one already handed off. |

Catalog queries/status are bounded; completed history is not returned wholesale.
Do not delete historical session rows to recycle a slot. The DB is orchestration
intent; `session.json`, parts, connection/raw evidence and final output remain
authoritative media facts. Neither store alone proves valid publication.

### Ownership rules

1. LIVE ownership covers resolving, recording, reconnect/network recovery and
   capture closing. One current creator page remains exclusive; known room IDs
   also guard aliases across pages. Existing ambiguous-current-owner refusal stays.
2. Artifact ownership begins at acceptance, before files exist, and persists
   independently through queued/running/failed/blocked finalization. It never
   reserves a capture slot after a proven durable handoff.
3. Handoff releases the old LIVE/page claim, not its artifact/room protection.
   A proven different room for that creator may capture into entirely different
   paths. The same old room still owned by an outstanding finalization is refused.
   Unknown old room or conflicting creator proof cannot establish a same-page
   new-room exception. Other pages remain eligible when their disjoint ownership
   is proven; catalog/path ambiguity is a genuine admission failure.
4. Automatic expected room comes from observation, is reserved atomically at
   acceptance and must still be verified by the existing bound resolver before
   media writing. A manual request retains the existing HTTP fields: it may be
   asynchronously `resolving` with a provisional LIVE/page reservation, but may
   not open a writer until room comparison under the manager proves safe. Missing
   or conflicting room proof fails that candidate without altering prior evidence.
5. Same-room suppression uses capture owners AND outstanding finalization records,
   not only the latest two slot files. Existing trusted-offline re-arm semantics
   remain; an old outstanding task still protects its own room after a newer room
   becomes the creator's latest consumed room. Terminal history alone is not a
   new perpetual LIVE-page lock.
6. Slot reuse changes only its binding/generation. No old task, source identity,
   selected raw flag or completion is inferred from the replacement slot snapshot.
   All progress/state callbacks carry accepted UUID + slot generation; late
   callbacks cannot mutate a replacement session. Finalizer callbacks target only
   their journal session/manifest, never the current controller's mutable `_job`.

Automation acceptance must commit the claim UUID receipt in the same acceptance
transaction as its session/binding. On restart use that receipt to resolve the
cross-store consumed-state promotion window; an idle/reused slot is no longer
negative proof of no accepted start. A valid catalog and absent claim receipt,
with no conflicting legacy intent, are required to clear an unaccepted claim.
Import schema-1 pending claims conservatively using existing creator/room/path
proof; ambiguous import stays blocked, not assigned a guessed receipt.

### States and handoff ordering

```mermaid
stateDiagram-v2
    [*] --> capturing: accepted durable intent / slot binding
    capturing --> closing: source ends or cooperative stop
    closing --> queued: sealed certificate + atomic handoff H
    queued --> running: durable attempt claim
    running --> completed: proven output + manifest + receipt
    running --> failed: owned child exited / evidence retained
    running --> queued: verified crash reconciliation
    queued --> blocked: low disk or unusable evidence
    closing --> needs_attention: handoff cannot be proven
```

`capturing` here also covers resolver and same-room recovery phases. Empty or
failed capture follows existing semantics: no manufactured assembly if no valid
parts; retained partials/error evidence stay protected. Recovery intent is not
converted to a closed source merely because a thread stopped.

**Before acceptance:** acquire the root writer lease, then manager ownership
lock, then short DB transaction; atomically reserve a capture slot, output/parts
claims and one eventual queue capacity unit, and commit intent before starting
the capture worker. A single OS-backed service-state owner lock excludes a
second scheduler using that journal even on another HTTP port. Root acquisition
is nonblocking, as today. All mutation uses this lock order; retention takes its
exclusive root lease then reads the journal, never waits for the manager lock.

**At capture close:**

1. Persist closing intent. Unwind source/retry generators, close capture and raw
   writers, promote/flush completed parts and persist the last connection record
   and manifest counters. No code may still append after closure is certified.
2. Build a sealed generation: UUID/page/proven room/raw flag/root and paths,
   ordered parts with native identities/sizes/stamps, stop/recovery outcome,
   original start and capture-end time, closed connection count, control byte
   hashes and raw/arrival inventory including existing warnings. Require no
   unexplained writer partial; genuine partial recovery remains existing guarded
   recovery, not an opportunistic queue repair.
3. Write/flush a proposed immutable `finalization-owner.json` in that session's
   `.parts`, identifying catalog UUID, session UUID and seal digest. Persist
   nonterminal manifest finalization intent (`pending`); never mark MP4 success
   just to release a slot. Queue does not add fictitious raw evidence.
4. **Transaction H:** verify current binding/session revision; commit the seal,
   task `queued`, artifact claims and release of the slot/LIVE-page binding in
   one transaction. Its reserved backlog unit becomes the task's existing unit.
   Preserve old-room protection. H commit is the sole slot-reuse authority.
5. Publish in-memory availability after H; notify the one finalizer. Root writer
   lease can then release. A slot JSON projection may be refreshed/overwritten
   only because the older UUID remains authoritative in the journal. Notification
   is a hint: startup/worker scanning finds committed tasks without it.

Do not synchronously reread/hash every old FLV/raw byte at handoff; closure
inventory/control binding is collected as writers close. Expensive per-part
proof and existing media inspection run in the finalizer. It opens old inputs
with stable read handles/Windows sharing that excludes write/delete, verifies
the seal before and after use, and holds its own root writer lease. Control/raw
changes invalidate proof; no source bytes are repaired or silently accepted.
Mandatory media/control flush failure prevents a claimed handoff; optional raw
I/O failures retain their existing warning semantics. Raw ON is intent, not proof
that all requested raw files were successfully captured.
The seal binds immutable capture fields and a specific initial control revision.
Finalization/recovery control updates must have journaled predecessor/successor
byte hashes and phase intent before writing; reconcile only those exact declared
successors after a crash. Do not ignore a manifest/log change just because a
worker might have written it. The marker binds the seal digest without hashing
itself recursively; its own immutable byte hash is stored with the task.

### Finalizer and publication

One non-daemon tracked worker chooses oldest eligible queued task, commits its
attempt token before launch, and owns only that UUID's immutable inputs/paths.
Use existing stream-copy versus libx264 decision, filters, quality, frame timing,
diagnostics and validation semantics. Capture jobs never wait on its join.
The service assembly adapter must separate unpublished assembly from publication
and preserve queue-owned failed partials; today's opaque `finalize_parts` publishes
internally and cleans up its failed temporary output, so simply calling it on a
detached thread cannot implement the receipt ordering below. Keep direct CLI
behavior compatible while exposing the required internal phase boundary.

Each attempt's FFmpeg must belong to a Windows Job Object with kill-on-close;
start suspended, assign before resume, and retain the job/process handles.
Persist PID AND creation time / attempt token. Failure to establish child control
fails the attempt before execution. Process death must not leave a writing child
which a replacement finalizer can race. Job Objects support grouped child
lifetime control; nested-job/Task Scheduler behavior needs native acceptance,
not assumption. [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

Record progress heartbeat independently of capture heartbeat. Proposed review
ideas (NOT approved): a five-minute media-progress-only kill rule is unsafe.
Integration must use phase-aware activity/deadlines for assembly, mux/publication,
hashing and validation, distinguishing long-progressing work from a true stall.
Only proven stalled owned work may be terminated, with bounded
5-second cleanup then owned Job Object termination. A stopped/stalled attempt
retains its partial and becomes failed/needs_attention; no automatic endless
retry loop. Unknown child liveness keeps the sole worker unavailable and its
paths pinned, while disjoint safe capture can continue. No general PID killing.

Publication remains absent-destination and session-bound. An attempt partial may
be published only with a recorded token/input seal and successful assembly plus
the applicable existing output checks. Write a durable publication receipt
(attempt/input seal, output native identity/size/hash, checks) before final
promotion; guard final path against replacement. Then flush completion manifest
and commit task/session completed. Preserve current success/diagnostic semantics:
if assembly succeeds despite degraded input, retain that input-decode classification
and distinguish output assembly success from clean full-session validation.
Do not conceal or "resolve" #28's source errors. No source/raw evidence deletion.
Capture-end time is separate in the journal/status; existing manifest lifecycle
`ended_at`/elapsed interpretation is not retroactively rewritten.

## Crash / restart / migration contract

Startup acquires listener/state ownership before scheduling any work, opens the
known catalog without silently creating an empty replacement, validates schema,
integrity and all live/nonterminal claims, then reconciles slots/tasks/automation.
The database and any potentially hot rollback journal are one recovery
state set. A missing/corrupt catalog after an activation marker
is an ownership failure, not an idle system. Cross-record UUID/path/slot collisions
fail closed. No finalization record may cause a source resolver/new LIVE start.

| Crash point | Required restart result |
| --- | --- |
| Accepted row committed, worker never started | Preserve accepted UUID/intent and existing no-start/recovery rules; no second acceptance for its paths/room. |
| Source closed but seal/H not committed | Old binding still occupied. Inspect existing media/intent; complete a proved close or report needs_attention. Never infer release from `_active=false`, thread absence or file names. |
| Marker/manifest written, H rolled back | Same as above; a marker is not independently authoritative. No detached task can run before H. |
| H committed, notification/projection not written | Task exists and slot is free. Rebuild view; old slot JSON cannot resume the closed source or remove the queue item. |
| H committed, slot reused, process dies | Old task and new capture have separate UUID records. Reconcile new capture under its own intent; recover old assembly only. |
| Running committed, child not launched / PID not saved | Job Object control prevents an orphan; prove absence before retrying assembly. Never rely on a reused PID alone. |
| Child died or service crashed during assembly | Verify owned process exit and sealed artifacts; preserve exact partial under guarded attempt identity. Requeue one bounded automatic crash retry (initial proposal: at most two total attempts); otherwise failed/needs_attention. |
| Output promoted, manifest/DB not terminal | Adopt only matching durable publication receipt and unchanged validated output/control proof. Missing/conflicting receipt is ambiguity: retain all artifacts, no overwrite/re-encode over an existing output. |
| Manifest complete, DB terminal commit lost | Reconcile matching receipt, manifest and task; commit completion idempotently. No second FFmpeg or source capture. |

Initial cutover is a separate authorized deployment task, never part of this
design pass. Back up/hash legacy `job.json`, `job-2.json`, automation and relevant
controls locally; import strict schema-1 intent/stop/raw flags idempotently by UUID
and transactionally mark catalog activation. Keep originals. Completed legacy
jobs remain settled; interrupted capture keeps existing identity/writer recovery;
legacy `finalizing` becomes an artifact task after evidence proof, never resumes
the LIVE. Conflicting import blocks admission. No migration by scanning arbitrary
media directories or treating historical artifacts as new work.
Today's `RecordingController` constructor can start reconciliation immediately;
the new bootstrap must gate that behavior until import/catalog reconciliation
has decided ownership. Never start legacy slot recovery in parallel with catalog
task recovery or feed a stale finalizing projection back into a LIVE controller.

After activation, slot JSON is a compatibility projection only; a mismatched
same UUID is a conflict, while a known older generation is a stale projection.
Unknown/newer projection is not silently discarded. Downgrade to an old scheduler
while catalog work exists is unsupported; add explicit cutover/rollback procedure
before deployment. Never let two implementations act as authorities together.

## Retention and raw-copy protection

The finalizer uses the existing root writer lease, compatible with two captures.
Pending, failed, blocked and unknown tasks also have durable retention pins while
no worker runs or the service is stopped. Extend read-only planning/authorization
and every destructive recheck to read the catalog/marker and bind their revision,
not merely the latest two slot job files. Unreadable/unknown queue authority
cannot authorize deletion. No new deletion, eligibility relaxation or retry
authority is granted by this design.

The proposed per-session marker also makes today's retention refuse the session
as unrecognized evidence (`retention_plan._unrecognized_evidence`); verify that
fail-closed behavior against supported older executors in acceptance. A new
executor must explicitly recognize/validate the marker AND journal. Never remove
it automatically just to make retention pass. Preserve current barriers for raw
or other unrecognized evidence; this task does not expand raw-session deletion.
Terminal journal history alone is not a perpetual deletion pin: only after
proven completion, no current slot reference, no outstanding task/uncertainty,
and ordinary fresh retention authorization can any target become eligible.
Any future authorized retirement must bind the terminal revision and retain a
non-media tombstone; it cannot run concurrently with a new queue mutation.

Keep raw flag accepted at start, connection numbering, filenames, `.arrivals.jsonl`,
`connections.jsonl` references and retained FLVs under the original UUID/parts.
No worker renames/moves/deletes them, toggles preferences, creates replacement
raw streams or confuses a reused slot's policy with the old session's policy.

## Bounds, storage, failure and shutdown

Proposed initial outstanding-work bound **8**, including queued/running/failed/
blocked tasks AND one reserved future unit per accepted capture. Count/reserve
atomically at acceptance, including manual starts. H requires no extra unit,
so two already accepted captures can always enqueue without evicting another
task. Proven completed assembly or capture needing no assembly releases a unit;
failed assembly and evidence uncertainty retain their unit until guarded retry
or separately authorized retirement resolves them. Failed work is not dropped
to make capacity appear free.
At the bound refuse new acceptance as `finalization_backlog_full`; an isolated
failed/stalled task below the bound does not consume capture slots or stop new
safe captures. Completed metadata remains queryable through bounded pagination.

Check each output volume and catalog volume, not only the configured automatic
root. Preserve the configured minimum-free threshold. Defer finalization at low
disk; it is not a capture-slot failure. Propose a per-attempt temporary-output
budget `4 * retained_FLV_bytes + 64 MiB` is an UNAPPROVED heuristic,
not an encoded-size bound or production admission default. Before integration,
specify yielding/reconciliation of unspent reservations, accounting for preserved
partial bytes, so a reservation alone does not unnecessarily block safe capture. Existing captures take priority: monitor free space/progress
at least
each second; stop only owned assembly if it reaches that output budget or the
free-space floor, preserving partial/evidence. Base low disk, unavailable storage,
catalog write failure or unprovable ownership still refuse unsafe new capture.
No threshold/byte-rate model guarantees an indefinitely growing LIVE fits disk;
these are explicit review defaults needing controlled boundary tests. No retention
or automatic deletion is a backlog/low-disk remedy.

Graceful shutdown disables starts/monitor callbacks, cooperatively stops captures
through their existing source unwind and seals them using already reserved units.
Do not drain the whole queue. Allow the one running assembly up to a proposed
30-second shutdown grace; then terminate its owned child, preserve the attempt
and leave a durable queued/failed result after confirmed exit. Join that tracked
worker; release state ownership last. If a capture cannot safely close, remain
visibly shutting_down / blocked rather than claim safe handoff or abandon a daemon
writer. An externally forced process exit is handled by restart reconciliation.

## Status and compatibility proposal (review required)

Preserve existing routes, start fields/202 acceptance, fixed error/status codes,
UUID identity, two slot IDs, auth/bind policy and safe redaction. Do not expose
signed URLs, raw stderr, DB internals or arbitrary control commands.

| Interface | Proposed meaning / compatibility guard |
| --- | --- |
| `/health`, `/recordings` existing capacity/active/available/slots | Capacity stays 2; active/available now describe capture ownership, including unresolved capture recovery, not MP4 assembly. This intentional semantic clarification must be documented and client-tested; do not claim transparent behavioral compatibility. |
| Additive `capture` / `finalization` summaries | Separate counts, worker availability, backlog limit/reservations, fixed blocked reasons. Finalization-only never sets a capture busy flag. Announce capability `durable_finalization_v1`; a slot may be reused before its old MP4 is complete. |
| `/recordings` additive finalization list | All outstanding tasks (bounded by 8) have UUID, creator/room, artifact paths, state/progress/error and immutable `origin_slot_id`, not a claim on today's slot. Existing `slots` shape stays exactly two current/latest capture snapshots. |
| Proposed authenticated `GET /sessions/UUID` | Stable whole-session capture/finalization status survives slot reuse and reports terminal completion only after output is proved. Add bounded finalization-history lookup; no media serving or mutation API. |
| Legacy `/recording` singular | Include current capture and outstanding artifact sessions when choosing a sole owner. More than one is 409; do not silently select the new UUID for a client waiting for the old one. One finalization-only result stays `state=finalizing`, `active=false`, with explicit phase fields. |
| Targeted stop | Active capture UUID signals only its capture. An outstanding finalization-only UUID (including failed/blocked) returns 202 capture-already-closed no-op; never stops assembly or a replacement slot's capture. Unknown/completed UUID retains 404. Empty-body stop remains 409 for multiple current capture/artifact owners. |
| `/monitoring` | Admission distinguishes backlog/storage/catalog failures from capture capacity. Duplicate clears pending claim without consuming the candidate room; existing cycle cadence remains. Ownership scans accepted-session receipts plus capture/queue records so a fast handoff cannot erase start provenance. |

Old clients must not equate slot reuse or `active=false` with successful MP4
completion. Test current `remote.py` / CLI and document capability fallback before
rollout. No endpoint/schema/default change is made in this task.

## Acceptance matrix for implementation (NOT yet executed)

Use Events/barriers, fake clock/disk/child handles, injectable commit failures
and a reopened real disposable journal; no sleeps/network/LIVE required. Each
case checks UUID/revision/path/raw flags, queue counts, durable bindings and
side effects, not only the health response.

| ID | Arrange / action | Required assertions |
| --- | --- | --- |
| A1 | Room A closes; pause its finalizer; observe same creator room B | H committed before reuse; B starts next eligible cycle in either free capture slot. A artifact task/paths/raw flag unchanged; no second A capture; no page bypass before B identity proof. |
| A2 | Two sessions handed off with scheduler paused, then permit one finalizer | First two queued, then one running + one queued; zero capture bindings throughout. Both capture slots available. Accept two independent new captures; no third capture and no second finalizer. |
| A3 | Old finalizer fails or watchdog stalls it below backlog/disk bounds | Known disjoint new room/path captures normally. Old failed/partial/diagnostics stay pinned. Unknown child exit blocks another finalizer, not by itself capture. Genuine storage/catalog/ownership failures still refuse. |
| A4 | Same room / different page alias, same output/parts native alias, or ancestor overlap | Reject before new writer/job side effects. Same-page unknown/conflicting room cannot bypass guard. Simultaneous admissions yield one accepted room/path claim. |
| A5 | Inject death at every H boundary, including after slot reuse | Reopen journal: exactly one old task and the correct new capture UUID, or old closing binding retained if H absent. No lost responsibility, duplicate task or closed-source resume; notification/projection loss is harmless. |
| A6 | Kill finalizer owner before/after child spawn, during FFmpeg, publication receipt/promotion/manifest/DB completion | Native Job Object prevents orphan writer; PID reuse rejected. Exactly one guarded retry/adoption, immutable inputs, no overwrite of conflicting output and no published completion without matching proof. |
| A7 | Change old part/control/raw metadata or replace paths while queued | Do not repair/consume changed evidence; preserve error and pin. Unrelated safe capture remains possible only if its ownership is proved disjoint. |
| A8 | Raw ON session queued; reuse slot with raw OFF session | No flag crossover; original raw/arrival/connection files byte-identical before/after assembly. Existing optional diagnostic warnings retained, no invented raw evidence. |
| A9 | Service absent, queue pending/running/failed/blocked; ask retention plan/authorization using both new and supported old executor | Queue/marker protection refuses target; corrupt/missing catalog fails closed. Bind revision at every destructive recheck. No deletion executed in this design task. |
| A10 | Six outstanding tasks + two accepted captures (bound 8) | Third acceptance refuses; both reserved captures can still H-enqueue. One completion frees one unit; no queued/failed item evicted. Concurrent admissions cannot exceed bound. |
| A11 | Base free space below threshold, finalizer reservation insufficient, output budget crossed; recovery of free space | Fixed distinct reasons; defer/stop only assembly as specified, retain evidence. No duplicate starts or automatic deletion; eligible queue task resumes only after proved storage and ownership. |
| A12 | Shutdown with two captures + one running + one queued task | Stop capture cooperatively, commit seals before release; bounded finalizer grace/owned cleanup, queued task retained, no late callback start, no daemon escape or premature safe-exit claim. |
| A13 | Legacy imports: completed/finalizing/capturing/stopped/missing raw field; repeated migration, corrupt/duplicate identities | Idempotent import; flags/UUID/timing/parts preserved; finalizing cannot resume LIVE. Activation/cutover and downgrade refusal work; no second authority or automatic empty catalog. |
| A14 | Legacy/current API consumers; old target finalizes while replacement records; delayed old progress callback | Existing shapes/request fields/codes retained; advertised phase/count change and stable session lookup tested. Stop old UUID and stale callback cannot alter replacement. Singular ambiguity stays explicit; slot status cannot prove old completion. |
| A15 | Automation claim accepted, H/reuse occurs before consumed-state promotion; restart | Accepted durable session receipt proves original creator/room/path acceptance even after slot reuse; promote once. A genuine duplicate clears without consuming new room, then retries on a later cycle. |
| A16 | Actual short disposable media, same/different AVC configs, queue/restart boundaries | Existing deep/packet-DTS checks and timing/diagnostic expectations pass with identical assembly options. Retained FLV/raw/evidence hashes unchanged; include native process/locking tests, never a forced production LIVE. |

### Additional integration cases from review 5970143137 (NOT executed)

| ID | Case | Required result |
| --- | --- | --- |
| A17 | Unspent finalizer reservation alone would block capture | Yield/reconcile unspent budget safely; preserve partial bytes; real low disk fails closed. |
| A18 | Long assembly/mux/hash/validation activity versus true stall | Phase-aware deadlines permit legitimate activity, isolate genuinely stalled work. |
| A19 | Parent death during child create/assign/resume/last-handle close | Native child control/exit proven; PID/heartbeat alone is insufficient. |
| A20 | Failed/backlog-blocked work recovery | Explicit guarded recovery, no infinite retry, false completion, eviction or pin clearing. |

## Review boundary and safe next action

The historical reproduction/design commit contained tests/contracts only. The
current slice implements an isolated internal journal with disposable file-backed
tests. No production catalog, worker, migration, runtime/config change, restart,
LIVE, media mutation, production retention operation, priority benchmark, #48
search, dependency, remote setup or release occurred. Production stays synchronous.

Project management approved the bounded internal journal slice in review
5970143137. Schema/transactions and disposable acceptance/crash tests are now
implemented with **no service wiring or cutover**. The next review examines the actual journal
and selects a bounded integration slice. Stored typed seals are caller-supplied
ownership evidence, not proof that a writer closed or media is valid.
Subsequent tracked worker/ownership/API/retention integration requires the full
matrix before a separately authorized safe Windows deployment. Process-priority
tuning is later work, not the capture-availability remedy. Keep #52 OPEN.

Reproduction command (fresh basetemp parent required):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_finalizing_capture_availability.py --basetemp C:\Users\Leandro\TikREC-tests\issue52-capture-design-20261003\FRESH -q
```

Related regression selection: `test_recording_manager`, `test_recording_ownership`,
`test_recording_worker`, `test_service_job`, `test_job_state`, `test_automation`,
`test_automation_state`, `test_automation_capacity`, `test_automation_recovery`,
plus the new characterization module. Logs remain in that external test workspace.
