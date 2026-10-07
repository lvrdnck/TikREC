# Issue #52 — isolated capture close and verified durable handoff

## Explicit runtime integration successor — 2026-10-07

The [PM-authorized runtime](ISSUE_52_SERVICE_RUNTIME.md) uses the accepted bridge
through durable H before slot reuse, then one tracked FIFO success worker and
eligible prepared-release recovery. Original UUID/generation/room/path/raw/H
truth remains; late callbacks and capture-only stop cannot affect a replacement
or finalizer. Lost notifications do not lose durable tasks. Unknown post-H native
cleanup retains local authority separately from completed accounting; no bridge
or schema guard is weakened. This successor is complete for PM review;
historical bridge evidence and default synchronous service behavior remain.

## Recovery cleanup and admission correction — 2026-10-06

[PM R12–R13 decision](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6024429330)
retains the prepared-success recovery design pending correction review. Recovery
uses its own execution gate; capture registration/call fencing holds the shared
lock only briefly. File scans, hashing, SQL waits and teardown do not hold capture
admission. Two connected disjoint captures progress during proof and committed
SQLite cleanup. Catalog close refuses active or uncertain recovery owners;
exception-attached leases/descriptors and initial/history readers remain tracked.
Fresh recovery-only native cleanup references distinguish exact open objects from
reused identifiers. Shared-root child creation permits stable directory identity
comparison; attempt inventories and file proofs remain exact. Schema 10 and
accepted capture/media foundations remain unchanged. [Contract and evidence](ISSUE_52_RELEASE_RECOVERY.md).

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

## Authority and historical checkpoint

2026-10-04: [review 5979465363](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5979465363)
**accepted `3d26a7bc` R4–R5**. Those regressions remain unchanged. The next isolated
process-lifetime foundation is implemented for review; [its separate report](ISSUE_52_PROCESS_LIFETIME.md)
records native evidence and remaining A6/A12/A19 gates. It consumes no queued
session and adds no service/publication/cutover claim. Earlier review-pending
wording below describes the historical R4–R5 delivery checkpoint.

2026-10-04: focused R4–R5 corrections are **complete for project-manager review** on
`codex/capture-journal-handoff`. #52 remains **OPEN / SINGLE ACTIVE**, #48
**OPEN / PAUSED**, and #28 unresolved. Production capture availability is not
fixed by this harness. No further owner implementation decision is pending.

[Review 5978780261](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5978780261)
retained the `ea263199` bridge direction and required only post-H cleanup and
exact marker-disposition corrections before another review. This task pulled the
existing isolated branch (already current at `ea263199`), then followed MODEL GATE /
PROCEED with GPT-6.1 Sol — High. It does not start worker or production integration.

[Review 5971119601](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5971119601)
accepted `a96bd6e9` and R1–R3 and selected this slice. That review was not repeated.
The initial bridge task pulled `main` from `a96bd6e9` to `fe28327c` (the intervening change is
ROADMAP maintenance-window planning), then used the normal MODEL GATE / PROCEED
workflow with GPT-6.1 Sol — High. Implementation uses an isolated managed worktree;
the primary editable checkout's source and its 42 unrelated artifacts were preserved.
Historical journal/reproduction/resource results remain in their original reports.

## Focused R4–R5 corrections

**R4:** `CaptureBridge.run()` records the confirmed/reconciled H or empty-settlement
receipt before pending projection, fault hooks or native `ExitStack` teardown.
Only failures before that receipt use `_hold()`. Once confirmed, later errors
return the committed `queued` / `no_assembly` disposition; capture failure remains
unset, the source fence stays closed and no second H or recovery launch is allowed.
The capture lifecycle lease is released independently of native teardown and
notification. `HandoffResult.post_h_errors` retains native, secondary cleanup,
lease and projection exceptions; `notification_error` also retains a projection
failure. These are returned diagnostics, not new journal/control writes or a new
recovery policy. Durable reopen authority remains the original seal/operation/marker.
Unconfirmed H with an unavailable receipt retains the existing pending-admission gate.

**R5:** inspection requires a literal string `assembly` or `empty`, and any stored
closure seal must have that same disposition. Invalid/mismatched values refuse
before operation receipt lookup. Refusal leaves journal state and artifact bytes
unchanged; inspection never grants source resume.

Regression evidence covers assembly and admitted-empty captures; native input and
marker teardown after normally acknowledged and lost-ACK/reconciled H; independent
actual lifecycle release (exclusive lease acquisition only, no retention execution);
slot/generation reuse, exact historical H replay without duplicate task/evidence,
and known-catalog reopen/inspection. Combined confirmed-hook, two native teardown,
lease-after-release and projection failures preserve all five diagnostics. Five
invalid marker values and both assembly/empty mismatch directions reject exactly.

Schema 3, schema-1/2 refusal, H ordering/FIFO, stop/admission guards, eight-unit
accounting, native trust limits, synchronous defaults and the A1–A20 limits below
remain unchanged. No finalizer/media/publication algorithm changed. Real-LIVE and
queued-worker/publication validation remain outstanding; existing synthetic media
checks are included in the correction suites.

### Actual R4–R5 verification

- Regressions first against `ea263199`: **17 failed**, 14.70 s. Ten R4 cases
  reached committed ownership then raised unproved-handoff errors. Five invalid
  empty-marker dispositions were accepted. The two mismatch directions already
  refused at receipt-kind validation; their new regressions require explicit
  seal-disposition refusal before receipt lookup.
- Corrected targeted selection: **20 passed**, 15.67 s. An intermediate probe
  also injected its marker-close fault into later inspection handles (four failures);
  injection now ends after actual capture teardown, keeping the close-boundary
  assertions intact. The initial external log directory was created after a
  runner-copy attempt found it missing; no prior evidence was erased.
- Focused bridge/native/marker/journal selection: **228 passed**, 61.26 s.
- Related capture/LIVE/source/writer/recovery/finalization/journal/automation/raw/
  recording/admission/lifecycle/retention selection: **1,221 passed, six platform
  skips, two subtests passed**, 137.24 s. This selection differs from the initial
  bridge's historical 1,251-test selection below; the full suite includes both scopes.
- Full isolated offline suite: **2,024 passed, seven platform skips, 19 subtests
  passed**, 145.30 s. Includes unchanged synchronous capture-availability
  characterizations, schema-1/2 refusal and synthetic decoder/packet-DTS/deep
  retained-part/output validation; no queued task is finalized.
- All 124 package modules remain below 300 lines; changed public docstrings,
  `compileall` and final diff whitespace checks pass. Only the bridge, marker,
  their regression tests and coordination/design/report documentation changed.

Logs are `baseline-r4-r5.log`, `corrected-targeted.log`, `focused.log`, `related.log`
and `full.log` under `C:\Users\Leandro\TikREC-tests\issue52-r4-r5-20261004`.
The existing runner redirects APPDATA/LOCALAPPDATA/XDG configuration/state and
TMP/TEMP into fresh external per-run roots, with PYTHONPATH at the isolated checkout.
No production configuration/state is used or mutated. No new media/publication
proof or full A1–A20 service case is claimed by R4–R5. The partial matrix below
and every worker/retention/cutover gate remain in force.

## Implemented boundary

- `capture_completion.py` / shared `live.py` and `live_session.py`: an explicit
  internal `CaptureEnded` result, preserving requested output and source closure
  separately from MP4 completion. The original manifest remains schema 1 with its
  capture timeline ended and `finalization.status = pending`. No fake finalizer
  success and no `output_path=None` shortcut. Public CLI/service defaults still
  return their existing synchronous `CaptureResult` and follow the existing lifecycle.
- `capture_fence.py` / shared `live_source.py` and `writer.py`: session/generation
  lifetimes for source iteration, raw/arrival methods and observer/part callbacks.
  A closed fence refuses escaped callbacks. Source/retry generators and the real
  writer/raw code unwind before the bridge can seal. Fresh room admission, stop
  intent and actual raw/FLV writer opening serialize under the authority lock.
  Replayed reserve/admit receipts never authorize a fresh writer after stop/reuse.
- `capture_handoff_authority.py`: one explicitly supplied known journal and local
  media root, OS-backed exclusive state-directory ownership, held catalog identity,
  root writer leases and short journal transactions. No default/discovered catalog,
  alternate empty authority, initialization on reopen or production path is used.
- `capture_handoff_native.py`: fixed local Windows storage, no-follow/reparse and
  multiply-linked refusal; handle-derived volume GUID/canonical path/file ID/size/
  last-write observations. Existing child aliases resolve through native handles;
  absent targets bind a pinned native parent plus basename. Occupied paths refuse
  before acceptance writes. Closed inputs open read/write with **zero sharing**:
  existing readers/writers must unwind and new data/delete access is denied through H.
- `capture_handoff_inventory.py`: mandatory retained-FLV/control flush, bounded
  control hashes and complete actual native inventory. FLV and raw/arrival entries
  retain numeric source order, including numbers beyond four digits. Manifest,
  connection ranges/timings and returned raw/arrival references must agree. Existing
  intentionally coalesced resolver-only attempts are accepted only inside valid,
  closed, UUID-bound recovery summaries; omitted media/raw attempts are refused.
- `capture_handoff_marker.py` / `capture_handoff.py`: immutable, flushed
  `finalization-owner.json` control binds catalog native identity, UUID/generation,
  revision, raw/output intent, seal and durable H operation. Inputs, marker and
  ownership remain held through confirmed commit or receipt reconciliation.
  H uses the marker's exact revision; a stop committed after marker creation
  invalidates that guard and retains responsibility instead of releasing capacity.
  Uncertain receipt lookup blocks new authority admission until explicit inspection.
  Notification/projection loss after H reports its error and leaves the task queued.
  The finalizer worker is unstarted; queue ownership is directly observable.

The bridge does not resume sources on reopen. Inspection reports either retained
capture/closing responsibility or a confirmed queued/evidence owner and explicitly
returns `source_resume_allowed = false`. An uncommitted marker is not queue authority.
It does not retry an unproved H, repair media or invent a clean recovery disposition.

## Empty, failed and optional evidence

Journal schema **3** minimally adds a retained `evidence` unit and typed
`ClosureSeal.disposition = empty`, with atomic `settle_empty_capture`. A proved
admitted zero-media source gets no assembly task and releases its capture binding,
but retains its UUID, seal, room/artifact claims and one of the eight outstanding
units. Explicit retirement/recovery of these units is future policy, not automatic
refund. The audit refuses missing/contradictory empty ownership. Schema 1 and 2
fixtures with retained accepted state are refused byte-for-byte unchanged; no live
migration, recreation or downgrade is implemented. A partial index on sealed
empty sessions keeps this audit bounded independently of terminal history; its
query-plan regression first exposed a full history scan and then passed with the index.

Never-admitted capture uses the separate no-writer reservation disposition only
with held authority/lease, no artifacts and all callbacks unwound. Its original
resolution failure is returned, with fixed durable identity-unavailable intent.
Stop before admission opens no source. A stop racing with a lost admission ACK
can leave an admitted binding without durable capture controls; this remains
visibly held/ambiguous rather than synthesizing an empty seal or launching a writer.

Discarded source tags, nonzero retained raw bytes without completed parts,
unexplained partials, failed/exhausted/open recovery or mandatory closure/control
failure never produce a valid seal or clean `no_assembly`. They retain the capture
unit/binding with `closing / ambiguous_state`; original error and secondary cleanup
evidence are preserved. A source ending is not an MP4 completion claim.

Optional raw write/arrival/close/flush warnings keep their existing media semantics.
The seal preserves actual remnants and fixed warning codes without inventing
successful raw bytes or references. A warning is insufficient if the native raw
handle is still open: that is an unproved mandatory closure and prevents H.
Control/FLV flush is mandatory. Large media is not rehashed or repaired on this path.

## Native trust and proof limits

The isolated adapter is Windows-only, for explicit immediate output/parts pairs
under a local fixed media root. Caller-provided sources/observations and the single
authority are trusted internal code. All participating schedulers/writers must use
that authority, its claims and lifecycle leases. Directory pins deny namespace
replacement but do not claim to prevent arbitrary child creation; a complete
inventory recheck plus closed fences and cooperative ownership exclude late owned
writes. Closed file handles independently deny data/delete access through H.
These guarantees do not certify arbitrary external filesystem writers.

Control reads are bounded to 1 MiB and inventory to 4,096 entries. An unproved or
oversized boundary stays held, not silently released. Native stamps and control
hashes are closure evidence, not decoder/media/publication proof. Queued inputs
must be revalidated by a future finalizer. Process death is not power-loss proof.

The new marker itself makes today's strict retention inventory refuse a session.
Disposable planning proves both actual pending captures and a separately eligible
completed fixture with the new marker cannot become deletion-eligible. Planning
leaves all bytes unchanged. No retention eligibility/executor code changed and no
deletion ran. Journal-aware authority readers and destructive rechecks remain gates.

## Historical initial bridge verification — ea263199

Initial bridge final verification: **211 focused passed**, 43.82 s; **2,007 full isolated passed,
seven platform skips, 19 subtests passed**, 117.70 s. Logs: `focused-final-index.log`
and `full-final-index.log`. All tests use fresh external roots under:
`C:\Users\Leandro\TikREC-tests\issue52-bridge-20261004`.
The subprocess wrapper redirects APPDATA/LOCALAPPDATA/XDG configuration/state,
TMP/TEMP and PYTHONPATH to disposable roots/the isolated checkout; logs and media
are outside Git. It never clears prior evidence or points at production state.

- Initial completion regression: baseline rejects the internal keyword before
  implementation. An initial missing basetemp parent was created, not erased.
- Earlier full checkpoint: 1,999 passed / seven skips / 19 subtests, 115.70 s.
  Final review justified additional alias, recovered-outage, numeric-order,
  marker-revision stop-race and bounded empty-audit query-plan
  regressions; the final full result above supersedes that checkpoint.
- Related capture/raw/recovery/journal/recording/admission/automation/retention
  selection: **1,251 passed, six platform skips, two subtests passed**, 107.73 s.
  Final review then added native occupied-alias, closed coalesced recovery and
  numeric-inventory regressions, then marker-revision and empty-audit regressions;
  the final full suite includes them and this selection.
- Native closure, ownership, same-room/case aliases, held inputs, two simultaneous
  replacement writers, stale callbacks, stop/admit lost ACK, H lost ACK and receipt
  unavailability, optional versus mandatory failures, actual raw/arrival inventory,
  unchanged FIFO/UUID/raw intent, and eight real outstanding captures are exercised.
- Thirteen additional actual capture process-death cases: marker/queue-entry/seal/
  transfer/release/commit boundaries, confirmed H, slot reuse with a real replacement
  writer, and admitted-empty transfer before/after commit. Reopen finds exactly one
  retained old capture/task/evidence owner, no duplicate task or false MP4 completion.
  Existing journal crash/receipt/ownership/FIFO tests remain in the focused/full runs.
- Valid local AVC/AAC FLV passes existing decoder and packet-DTS checks. A separate
  real synchronous capture/finalization passes deep retained-part/output validation;
  queued FLV/raw/control bytes remain unchanged. No queued task was finalized and no
  LIVE was manufactured. Different-AVC queue-worker/publication validation is outstanding.
  The public `tikrec validate PARTS_DIRECTORY --deep --json` CLI entry point also
  returns PASS with no findings for that completed synthetic session; retained media,
  output inspection and output decoding pass. Visual integrity is not checked.
- Existing five synchronous capture-availability characterizations remain unchanged;
  CLI/service/automation/retention regressions run under isolated configuration.
  The final completion-interface selection passed 43 checks after explicit return
  type/docstring updates; the later final full run includes those checks.
- Windows Python **3.12.10**, linked SQLite **3.49.1**, source ID
  `2025-02-18 13:38:58 873d4e274b4988d260ba8354a9718324a1c26187a4ab4c1cc0227c03d0f10e70`.
  A fresh explicit native catalog verifies DELETE / synchronous 3 (EXTRA) / FK 1 /
  busy 1000. No engine/runtime upgrade or production health assertion.
- Final source-size/public-docstring/static diff checks pass; every package module
  remains below 300 lines. No credentials/media or disposable fixture state is in Git.

Test setup corrections were kept separate from product claims: an early CLI subset
inherited the existing output-directory preference and failed two expected-path
assertions; unchanged tests passed with disposable child configuration. The schema
version assertion was updated explicitly from 2 to 3 while older-state refusal
coverage was strengthened. A writer fault first hit a no-op close before media;
the probe now injects at an actual part close. Reconnect fixtures now use the
required `.flv` transport shape, and tamper probes assert the intended boundary ran.

## A1–A20 integration coverage

No complete service acceptance case is passed by this isolated slice.

| Case | Capture-side evidence now covered | Still outstanding |
| --- | --- | --- |
| A1 | Partial: real room A H, then same creator's verified room B; old evidence unchanged. | Service/eligible monitoring cycle and finalizer coexistence. |
| A2 | Partial: two real H sessions, then two simultaneous real replacement writers. | Running tracked finalizer/worker concurrency. |
| A3 | No new finalizer evidence. | Failed/stalled finalizer and storage-aware capture admission. |
| A4 | Partial: same room, native case/occupied aliases, hard links, held writer and stale callbacks refuse. | Full service concurrent alias/unknown-room gate. |
| A5 | Partial: real capture death through H and slot reuse; retained single owner, receipt reconciliation. | Service startup/automation projection recovery. |
| A6 | No child/publication worker implemented. | Owned child lifetime, publication, guarded adoption/retry. |
| A7 | Partial: native inputs held through H; changed controls/partial inventory refuse sealing. | Queued input mutation revalidation by finalizer. |
| A8 | Partial: actual raw/arrival/connection binding, old ON versus replacement OFF, optional warnings/remnants. | Worker assembly/restart invariance. |
| A9 | Partial: actual queue and marker independently refuse disposable retention planning without mutation. | Journal readers and every old/new destructive recheck. |
| A10 | Partial: six real queued + two reserved captures both H at bound eight; ninth refuses, FIFO kept. | Worker completion refund/storage recovery integration. |
| A11 | No new storage/process evidence. | Finalizer disk reservations, output budgets and recovery. |
| A12 | Partial: cooperative source stop and fenced closure; queued ownership survives process death. | Service shutdown and running-child grace/cleanup. |
| A13 | Older journals preserved/refused; no migration evidence. | Legacy import, activation/cutover/downgrade protocol. |
| A14 | Partial: UUID/generation callback refusal and unchanged synchronous compatibility. | Public phase/status/session lookup and old/new active coexistence APIs. |
| A15 | Partial: actual automatic acceptance receipt/intent survives H and slot reuse. | Consumed-state promotion/restart wired to automation. |
| A16 | Partial: real local capture, native locks/death, decoder/DTS and separate synchronous deep validation. | Queue worker/restart and different AVC configurations/publication. |
| A17 | No finalizer reservation implementation. | Yield/reconcile unspent disk budgets. |
| A18 | No phase watchdog implementation. | Legitimate long activity versus stall/deadlines. |
| A19 | No controlled finalizer child spawning. | Job Object/create/assign/resume/exit/PID-reuse guarantees. |
| A20 | Failed/ambiguous capture held; existing journal foundation retained. | Explicit finalizer/backlog recovery with no pin clearing/eviction. |

## Boundaries and safe next action

No production startup/service/API/monitor wiring, database/marker creation,
configured production media/config mutation, installed-service restart/cutover,
finalizer worker/process policy, publication rewrite, dependency/runtime upgrade,
priority benchmark, #48 polling, remote worker, retention execution, release or tag.
Gracie-only raw policy, Ward OFF and monitored order remain untouched; no #28/#48
validation claim or waiver. Source is committed/pushed only on the isolated branch.

Project management should review the actual capture bridge, native trust/lifetime,
R4–R5 confirmed-H/marker corrections, schema-3 empty disposition, tests and remaining
gates before selecting another
bounded implementation slice. Recommended review model: **GPT-6.1 Sol — High**.
Do not auto-start worker or production integration. The issue remains open.
