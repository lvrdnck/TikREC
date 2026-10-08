# TikREC current state

Last reviewed: 2026-10-08. This is a short handoff record, not a replacement
for [ROADMAP.md](ROADMAP.md), [SPEC.md](SPEC.md), [SERVICE.md](SERVICE.md),
[SESSION_MANIFEST.md](SESSION_MANIFEST.md), or
[CONNECTION_LOG.md](CONNECTION_LOG.md).

## Coordination

**v0.11.0 storage-focused publication COMPLETE / VERIFIED (2026-10-08).** [Owner authorization](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6059131758) was executed after PM acceptance 6059047079; no repeat permission/review cycle. Current released version is **v0.11.0**, published at **2026-10-08T11:50:27Z**. [TikREC v0.11.0](https://github.com/lvrdnck/TikREC/releases/tag/v0.11.0) is non-draft/non-prerelease, Release ID `406770680` / node `RE_kwDOUTgsvs4YPtP4`.

Immutable annotated tag object **`ef8c5215712d454855a033700116bdc8fc0906a3`** peels to the exact approved **`2fe6354aa508d53ce3a3452ce08743d97400fe73`**, not a bookkeeping commit or main/development tip. [Wheel](https://github.com/lvrdnck/TikREC/releases/download/v0.11.0/tikrec-0.11.0-py3-none-any.whl), asset ID `621682513`, is **207,542 bytes**, SHA-256 **`7cf87363cde6ce9817b79c4c7eb86fe37a3e77bcf564cde91019aadec7e902ca`**. Existing wheel checked before writes against 105 module bytes, metadata/entrypoint/RECORD and 223 frozen files. Draft and published downloads match the approved bytes. No rebuild/substitution or conflicting object overwrite occurred. [Publication execution/evidence](V0_11_RELEASE_PUBLICATION.md).

Accepted evidence reused, not rerun: 1,731 Windows passes / 7 skips / 19 subtests, two focused version checks, compile/diff/30 help paths and installed-wheel smoke; unchanged #51 independent/public and native real-media PASS. #51 stays CLOSED/PASSED; its deletion authorization remains consumed. #52/#48 stay OPEN/explicitly PAUSED, #28 unresolved; B1/B2/B3 neither implemented, repeated nor waived. **No implementation task is active and no automatic successor is selected.** PM decides any future resume separately.

The released package is the historical storage scope from `ebf501c4`, excluding later #30/#48/#52 source; automatic admission-only space checks and exact-confirmation Windows retention with disabled-unset age remain. The newer development installation/configuration/state/services/media and Gracie-only policy were not accessed or changed. This #52 branch still advertises package 0.10.0; published 0.11.0 is the separate historical storage release. The running installation was not inspected or changed. No main merge, executable-source change, package install, service/recorder restart, LIVE, user-media deletion, migration, upgrade, PyPI upload or #52 activation occurred. Both branch bookkeeping commits are documentation-only and recorded in #52; tag stays fixed. Refs #52. **Next: stop; no automatic successor.**

- **Historical R12–R13 delivery (accepted by PM decision 6030581435) — issue #52 OPEN / SINGLE ACTIVE — R12–R13 recovery corrections complete for PM review (2026-10-07):** [PM decision 6024429330](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6024429330) retains the bounded prepared-success recovery design but withholds acceptance of `45243f6c` pending correction review. R1–R11 and the accepted normal settlement at `0665b5e8` remain accepted. The correction preserves exact earliest exceptions and bounded actual secondary errors; tracks partial lifecycle/native and every SQLite reader owner; refuses unsafe close/new recovery; preserves committed terminal facts. Separate recovery execution fencing keeps scans, hashes, SQL waits and teardown outside capture admission, retaining catalog/thread/call/generation/cancel fences. Shared-root child creation compares stable directory identity while attempt inventories/file proofs stay exact. Actual Windows close-protection tests retain native handles even when Python marks a stream closed; cleanup refuses reused descriptors, including a fresh open of the same lock file. Schema 10 unchanged; schemas 1–9 preserved/refused; no migration. [Recovery contract, actual failures and evidence](ISSUE_52_RELEASE_RECOVERY.md). Final frozen isolated Windows suites: **351 focused passed; 1,114 related passed / 2 skipped / 17 subtests passed; 2,875 full passed / 9 skipped / 19 subtests passed**; no failures; **448 source/test hashes unchanged** before/after every serial run. Prior reviewed suites remain historical: **302 focused; 1,065 related/2 skips/17 subtests; 2,826 full/9 skips/19 subtests**. #48 OPEN/PAUSED; #28 unresolved; owner decisions None. Service/API/monitor/scheduler wiring, production access/change/restart, broader unfinished-phase recovery, retention, runtime/resource-policy changes, merge/release/tag remain outside scope. Natural-recording, power-loss, service/A1–A20 and integrated review remain separate gates. **PM review only after delivery; no automatic successor or deployment-readiness claim.**

- **Historical accepted owned success settlement — accepted by PM decision 6017389662
  (2026-10-06):** [Original settlement review decision 6014913888](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6014913888)
  accepts `df954dd2` R11/corrected manifest completion; prior foundations remain
  accepted. Explicit `JournalSettlement` completes assembly through manifest,
  immutable release preparation/revocation, confirmed exact native/SQLite cleanup
  and atomic terminal settlement/exact-one unit and active task-claim return.
  Original live owners authorize release; unknown cleanup remains outstanding.
  Schema 9 only, schemas 1–8 preserved/refused, no migration. Immutable completed
  history stays valid after claim release; active audits/admission remain bounded.
  [Contract, actual failures/results/limits](ISSUE_52_OWNED_SETTLEMENT.md). Final
  frozen isolated suites: **282 focused; 1,045 related/2 skips/17 subtests; 2,806
  full/9 skips/19 subtests passed**, no final failures, 427 unchanged hashes.
  110 new regressions plus schema-8 refusal; seventeen new actual supervisor-death
  boundaries and accepted regressions, ten sequential successes, reused claims,
  disjoint captures and unchanged media/H/manifest history. First-snapshot fixture
  failures and their strengthened corrections remain recorded, not relabelled.
  #48 OPEN/PAUSED; #28 unresolved; owner decisions None. No production/service
  wiring, restart adoption/retry, retention, migration, upgrade/resource-policy,
  merge/release/tag. v0.10.0 remains released; natural-recording, power-loss,
  service/A1–A20 and independent integrated review remain separate gates.
  Safe resume: pull/reconcile this isolated branch, #52 and the focused report.
  **PM review only next; no automatic successor.**

- **Historical accepted R11 correction:** `df954dd2`; 171 focused, 934 related/
  2 skips/17 subtests and 2,695 full/9 skips/19 subtests passed, 408 unchanged hashes.
  [R11/manifest evidence](ISSUE_52_MANIFEST_COMPLETION.md) preserves baseline failures,
  competing-writer and wrong-thread proof, and seventeen supervisor-death cases.

- **Historical accepted manifest-completion delivery — corrected by R11:**
  `580104fc` records 128 focused, 891 related/2 skips/17 subtests and 2,652 full/
  9 skips/19 subtests passed, seventeen supervisor deaths and 404 unchanged hashes.
  Those results remain valid historical suites, not acceptance of the R11 gap.

- **Historical guarded publication — accepted by 6012406322; delivered for PM review
  (2026-10-06):** [PM decision 6010639470](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6010639470)
  accepts `1e1e1cae` validation and supersedes its pending-review checkpoint for
  this single slice. Original coordinator/candidate ownership now connects to a
  root-relative native no-replace transition, preceded by exact preparation and
  followed by separate observed proof. Schema 7 appends publication records;
  schemas 1–6 remain refused/preserved without migration/cutover. The original
  candidate/assembly/validation evidence, source/raw/arrival/control/H, pending
  manifests and task/unit/room/path/durable/local pins remain retained.
  Publication-capable acquisition alone adds DELETE rights; its three owned
  validators use read-only inherited seekable stdin. Existing assembly-only,
  validation-only and synchronous CLI/service defaults remain.
  [Publication evidence and limits](ISSUE_52_GUARDED_PUBLICATION.md).
  Final frozen suites: **72 focused passed; 755 related passed / 2 skips /
  17 subtests; 2529 full passed / 9 skips / 19 subtests**. No failures;
  all 388 source/test hashes unchanged. Eleven actual supervisor-death boundaries,
  generated copy/libx264, mutation/collision/ack-loss/cancellation/unknown/cleanup
  and two disjoint capture bindings are verified. No atomic filesystem/SQLite,
  power-loss or natural-recording/service/A1–A20 guarantee. Owner decisions None;
  #48 OPEN/PAUSED, #28 unresolved.
  No production access/change/restart, service/API/monitor/scheduler integration,
  manifest completion, settlement/refund, retry/adoption, retention, #48 polling,
  migration/cutover, dependency/runtime/resource-policy changes, merge/release/tag.
  Use `Refs #52` and preserve pushed history. Commit is recorded in #52's current
  checkpoint and delivery comment. Next: PM review only; no automatic successor. Safe resume: pull the existing isolated
  branch and reconcile current issue/report; historical receipts grant no replay.

- **Historical candidate validation — accepted by 6010639470; delivery COMPLETE FOR
  PM REVIEW (2026-10-05):** [PM decision 6000035417](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6000035417)
  accepts `ee884bdc` and supersedes the prior pending assembly checkpoint.
  `JournalValidation` validates the exact same-attempt unpublished candidate while
  its original scratch/native/input protection remains held. Three fixed owned
  validators inspect output, fully decode and stream packet DTS checks; a narrow
  append-only authority preserves the arbitrary post-candidate launch prohibition.
  Minimal schema 6 adds validation authority/receipts; schemas 1–5 are refused and
  preserved unchanged, without migration/cutover. Assembly/candidate evidence stays
  immutable `not_checked / unpublished`; separate success grants no promotion,
  settlement/refund, retry/adoption or unit/raw/room/path/pin release. Cancellation,
  complete streamed diagnostics/EOF, first failures, exact native cleanup and
  one-operation acknowledgement reconciliation remain explicit. Unknown lifetime
  and failed/ambiguous validation retain protection. See [validation contract/evidence](ISSUE_52_CANDIDATE_VALIDATION.md).
  Final frozen tree: **75 passed; 687 passed, 2 skipped, 17 subtests passed; 2461 passed, 9 skipped, 19 subtests passed**. No failures;
  all 376 source/test hashes unchanged. Full details are in that report/current #52 checkpoint.
  Generated copy/libx264 media, corruption/identity/hash changes, native lifetimes,
  capture availability and twelve real validation supervisor-death boundaries are
  exercised. No atomic filesystem/SQLite snapshot, power-loss or natural-recording
  validation is claimed. #48 OPEN/PAUSED; #28 unresolved. Owner decisions: None.
  Next action: PM review only. No service/API/monitor/scheduler wiring, production
  access/change/restart, #48 polling, retention, dependency/runtime/resource-policy
  change, merge/release/tag. Use `Refs #52`; preserve pushed history. Safe resume:
  pull the existing isolated `codex/capture-journal-handoff` worktree and reconcile
  the current issue decision/report. Delivery commit is recorded in the issue top
  checkpoint; task-owned source/tests/docs are committed and pushed normally.

- **Historical connected assembly — accepted by 6000035417; prior delivery
  COMPLETE FOR PM REVIEW (2026-10-05):** [PM decision 5999162236](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5999162236)
  accepts `58e40084` and supersedes the previous pending-review/no-successor
  checkpoint. The isolated one-shot adapter claims at most one FIFO sealed
  session through `AttemptCoordinator`, retains its exact original-H inputs,
  shares accepted copy/libx264 planning and uses one durable contained scratch
  writer. Copy helper code/text/FFmpeg argv are bound in the same launch intent;
  only the contained writer creates the helper. Long assembly has no overall
  timeout, with bounded final drain/cancel/cleanup and complete semantic diagnostics
  before sealing an unpublished/not_checked candidate. Schema 5 and R4–R10 remain.
  The unfinished running task/unit/raw/room/path pins remain counted and retained.
  Both new connected generated media paths pass part/DTS/deep output checks and
  synchronous frame timing; legacy pending-manifest findings remain explicit.
  Twelve real connected supervisor-death boundaries and integrated native failure/
  cancellation/diagnostic/acknowledgement checks pass. Final source/test tree:
  **129 focused passed; 651 related passed / 2 skips; 2,389 full passed / 9 skips /
  19 subtests passed**, no failures. Source/test hashes remain unchanged across runs.
  See [connected evidence](ISSUE_52_JOURNAL_ASSEMBLY.md).
  #48 remains OPEN/PAUSED with Gracie-only raw/Ward OFF; #28 unresolved. Owner
  decisions: None. Next action after delivery: PM review only, no automatic successor.
  No publication, settlement/refund, retry/adoption, scheduler/service integration,
  production access/change/restart, #48 polling, retention, migration, dependencies/
  upgrades, merge/release/tag. Safe resume: pull the isolated branch and reconcile
  this report/current #52 decision. Use `Refs #52`; historical `6fdacd37` contains
  `Closes #52`, flagged for eventual separately reviewed integration. Preserve history.
  Branch: `codex/capture-journal-handoff`; task-owned source/tests/documentation
  committed and pushed normally. Actual delivery commit is in the current #52
  top checkpoint; no merge/cutover occurred.

- **Historical R8–R10 delivery — accepted by 5999162236; prior checkpoint follows
  (2026-10-05):** [PM review 5993102551](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5993102551)
  retains the scratch direction but does not accept `d35f946f` for successor
  integration. After required pull and MODEL GATE / PROCEED, this task corrects
  first-failure/partial-native-owner retention, truthful cleanup completion, and
  complete scratch inventory/artifact revalidation. Schema 5 and all accepted
  foundations remain intact. Real Windows regressions against unchanged reviewed
  code reproduce five defects. An isolated comparison against `3d4e15ce` confirms
  the two CLI failures depend on configured output-directory leakage; the CLI
  fixture now isolates unset defaults. Final tree: **71 focused passed; 593
  related passed / 2 skips; 2,339 full passed / 9 skips / 19 subtests passed**,
  no failures. Thirteen real supervisor-death boundaries plus scratch writer
  cancellation/descendant/status/diagnostic/native cleanup checks pass. Original
  H/input/unrelated hashes and both separate generated media paths are preserved.
  This is process-death evidence, not power-loss or atomic namespace proof.
  Owner decisions: None. #48 OPEN/PAUSED and #28 unresolved. Next action: PM review
  of only these corrections; no successor integration is authorized. Safe resume: pull
  `codex/capture-journal-handoff`, read the linked review and
  [scratch evidence](ISSUE_52_DURABLE_SCRATCH.md). Use `Refs #52`; historical
  `6fdacd37` contains `Closes #52`, which must be addressed at a separately
  reviewed integration and does not authorize closure. Do not rewrite history.
  Branch: `codex/capture-journal-handoff`; final source/test files are committed
  and pushed normally. No production access/change/restart or merge/release/tag.

- **Historical first scratch delivery — corrections required by 5993102551:
  durable scratch/candidate ownership COMPLETE
  FOR PM REVIEW (2026-10-05):** The 2026-10-05 PM decision accepts `3d4e15ce`
  as the internal
  durable-attempt/child-launch foundation and narrows the next slice to durable
  scratch and unpublished-candidate ownership bound to `AttemptCoordinator`.
  This supersedes the earlier GitHub comment selecting queue-connected assembly:
  do not connect the queue to MP4 assembly here. Persist reservation before
  filesystem creation; keep exact attempt/session/H-seal/operation bindings and
  native scope protection; preserve ambiguous artifacts; seal only unpublished,
  unvalidated candidate evidence after complete writer execution proof. No queue
  assembly, validation, publication, settlement, retry, scheduler or service work.
  Schema 5 adds the durable scratch/candidate ledger; schemas 1-4 remain unchanged
  and are refused without migration. **Historical delivery status: implementation complete,
  awaiting PM review; review subsequently required R8–R10.** Focused ownership/
  journal/coordinator suite: **33 passed** after the final
  test-file split. Full offline suite: **2,289 passed, 9 skipped, 19 subtests
  passed; 2 failed**. Both `test_live.py`
  assertions failed because the host's default Videos path is absolute while the
  assertions expect a relative path (unrelated to scratch ownership). Evidence:
  [ISSUE_52_DURABLE_SCRATCH.md](ISSUE_52_DURABLE_SCRATCH.md).
  #48 remains OPEN/PAUSED and #28 unresolved. Preserve all existing capture,
  accounting, raw, room, path and original H evidence. Safe resume: pull this
  branch `codex/capture-journal-handoff`, inspect commit `6fdacd37`, and read the
  current #52 checkpoint/evidence report before continuing. The implementation
  commit is pushed; the branch remains isolated pending PM review.

- **Historical checkpoint — Issue #52 durable attempt/child authority COMPLETE FOR REVIEW
  (2026-10-04):** [PM review 5982869804](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5982869804)
  **accepted `44711e65`** and selected durable attempt/child launch with claimed
  input protection. The isolated one-shot `AttemptCoordinator` now combines existing
  FIFO/single-finalizer claiming, distinct claimed protection and sequential
  creation-contained readers. Original H/marker evidence is separate from current
  task/owner revisions. Approved schema **4** adds permanent intent/native identity/
  whole-job exit/diagnostic/cleanup records; schemas 1/2/3 are retained/refused
  unchanged, without migration. Final resume fencing serializes cancellation/
  revocation with exact native resume. Unknown/unclean owners retain reachable input
  guards; historical receipts do not authorize creation, resume or adoption.
  Successful readers leave unfinished tasks held with counted units/raw/room/path
  pins while disjoint capture retains both slots. No scratch protocol, queued MP4
  assembly, publication/settlement/retry or service integration.
  Final **484 focused / two skips; 1,281 related / six skips / two subtests;
  2,270 full / nine skips / 19 subtests passed**. Ten native owner-death boundaries,
  final diagnostic tails, claimed teardown faults and bounded sequential FFprobe
  on actual sealed H inputs pass; evidence hashes stay unchanged. Both separate
  generated assembly paths retain part/packet-DTS/deep validation and absent final
  destinations. [Complete evidence and limits](ISSUE_52_DURABLE_LAUNCH.md).
  **Historical next action (2026-10-04): PM review of that slice; superseded by
  the 2026-10-05 decision above.**
  #52 OPEN/SINGLE ACTIVE, #48 OPEN/PAUSED (Gracie-only raw/Ward OFF), #28 unresolved;
  owner decisions: None. Scratch/publication/settlement/retry, scheduling/service/
  retention/migration/cutover and full A1-A20/Scheduled Task acceptance remain gates.
  No production access/change/restart, retention execution, #48 polling, resource
  policy/upgrade/release/tag/remote worker/merge.
  Safe resume: pull/reconcile the isolated branch and latest #52 PM decision.
  Pending owner action: None. Branch `codex/capture-journal-handoff`; primary
  `main` remains `fe28327c`, with its 42 unrelated artifacts preserved.

- **Issue #52 historical native sealed-input guard — accepted by 5982869804
  (2026-10-04):** [review 5981877279](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5981877279)
  **accepted `2d6896ce` including `c22c482f`** and selected only the read guard.
  Explicit known authority/session/revision/seal binds original queued H task,
  immutable claims, catalog, marker and receipt. Distinct noninheritable native
  read protection holds the complete FLV/raw/arrival/control inventory, permits
  readers and denies conflicting data-write/delete access. Controls use stored
  hashes; media uses native identity/size/write stamps. Marker byte hash is only
  lease-local; schema 3 is unchanged. Compatible existing root writer protection
  takes no capture slot/unit and allows disjoint capture. Explicit revalidation
  brackets native work outside authority/SQLite locks; cleanup retains possible
  live owners and first/secondary failures. No claim, durable launch, queued
  assembly, scratch/publication/settlement/retry or service integration.
  Final **434 focused / two skips; 1,365 related / eight skips; 2,220 full /
  nine skips / 19 subtests passed**. An introduced R5 lookup-order regression
  was fixed and all selections rerun; R4–R7 are preserved. Real H fixtures with
  actual raw/arrival/controls, bounded owned FFprobe, exit/EOF/protection lifetime,
  unchanged hashes and both generated assembly/deep-validation paths pass.
  [Sealed-input evidence and limits](ISSUE_52_SEALED_INPUTS.md).
  Partial A7/A8 only; media hashes/decoder validation are not guard guarantees;
  native metadata/cooperative namespace limits and two symlink-privilege skips
  are recorded. No full A1–A20 or Scheduled Task gate passed. Durable attempt/
  launch/claimed-phase input/scratch protocols and publication/service/retention/
  migration/cutover remain later reviewed gates. **Historical next: guard review, completed by 5982869804. Safe resume: pull this isolated branch, reconcile this checkpoint and
  #52's latest PM decision; do not connect a worker or use production inputs.
  Pending owner action: None.** #48 OPEN/PAUSED with all Gracie-only raw/Ward-OFF
  criteria intact; #28 unresolved; #13/#8 unstarted. No production access/change,
  restart/polling/retention execution/resource policy/upgrade/release/tag/merge.
  Branch: `codex/capture-journal-handoff`; deployed editable `main` remains
  `fe28327c`, its 42 unrelated artifacts preserved.

- **Issue #52 historical unpublished assembly — accepted by review 5981877279
  (2026-10-04):** [review 5980268720](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5980268720)
  **accepted `b2bff05f` R6–R7**, selecting only the internal closed-input ->
  attempt-owned MP4 primitive. Shared copy/libx264 planning preserves ordering,
  timing, filters, quality and decoder diagnostics; synchronous CLI/service and
  `finalize_parts` defaults/publication/cleanup remain unchanged. All new-path
  probes/FFmpeg use sequential `OwnedProcess` with fresh suspended authorization.
  Complete streamed diagnostics/EOF and native exit/cleanup are required for
  execution readiness; validation/publication stay explicitly unperformed.
  Failed/cancelled candidates and scratch are preserved; unknown lifetime retains
  exact owners and forbids successor launch. No blanket assembly deadline.
  Actual occupied-output exit-0 behavior is fenced before resume and through
  explicit error diagnostics. Structure extraction: `c22c482f`, separate commit.
  Final focused **198 passed / 17 subtests**; related **1,222 / six skips /
  17 subtests**; full isolated **2,162 / seven skips / 19 subtests**. Matching and
  differing generated AVC fixtures pass part/packet-DTS/deep validation with
  unchanged source/raw/arrival/control hashes, matching synchronous frame timing
  and absent final destinations. [Assembly evidence](ISSUE_52_UNPUBLISHED_ASSEMBLY.md).
  R4–R7 and schema 3/history/refusal/FIFO/stop/admission/eight-unit accounting
  remain intact; no full A1–A20 or Scheduled Task gate passed. Durable attempt/
  launch/input-seal adapters, validation/publication/settlement/retry, scheduler/
  service/API/monitor/storage/retention/migration/cutover remain later reviewed
  work. **Historical next: primitive review, now completed; pending owner
  action: None.** #48 OPEN/PAUSED, #28 unresolved, #13/#8 unstarted. No real queued
  session/production access/change/restart/polling/retention/resource policy/
  upgrade/release/tag/merge. Branch: `codex/capture-journal-handoff`; deployed
  editable `main` stays `fe28327c`, with 42 unrelated artifacts preserved.

- **Issue #52 historical R6–R7 delivery — accepted by review 5980268720
  (2026-10-04):** [review 5979948212](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5979948212)
  retained `86b9d4d4` containment and selected only startup/close fencing and final
  stream corrections. Close/cancel intent now linearizes with allocation/resume
  and never resets; confirmed exit and per-stream pending/complete/incomplete
  EOF evidence are separate. Tail delivery/prefix/drop accounting survives exit,
  and final stream faults/timeouts retain proved process exit. Baseline **14 failed /
  three controls passed**, corrected focused **91 passed**; related **675 passed /
  two skips**; full isolated **2,115 passed / seven skips / 19 subtests passed**.
  Generated FFmpeg fixture hashes and existing deep validation pass.
  [Process evidence and remaining limits](ISSUE_52_PROCESS_LIFETIME.md).
  R4–R5 accepted and preserved; schema 3/history/refusal/FIFO/eight-unit accounting,
  creation-time containment and synchronous defaults unchanged. No full A1–A20
  or Scheduled Task gate passed. **Historical next action was correction review,
  now completed by 5980268720; current next action is above.** No worker,
  queued assembly/publication, retry, production access/change, restart, retention,
  polling, resource policy, upgrade, release/tag or merge/cutover. #48 OPEN/PAUSED,
  #28 unresolved, #13/#8 unstarted. Branch: `codex/capture-journal-handoff`.

- **Issue #52 historical subprocess-foundation delivery — review required R6–R7
  (2026-10-04):** [review 5979465363](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5979465363)
  **accepted `3d26a7bc` R4–R5** and selected only the Windows process-lifetime slice.
  `OwnedProcess` binds session/attempt UUIDs, associates a private kill-on-close job
  during suspended creation, requires fresh caller authorization before resume,
  retains exact native handles/creation identity, and bounds wait/cancel/streams/
  cleanup. Native-confirmed whole-job exit is distinct from unknown lifetime;
  uncertainty retains control and grants no retry, task or media completion.
  Actual disposable owner-death/descendant/last-handle/nesting/fault evidence and
  separate FFmpeg candidate/input hashes/deep validation are in
  [the process report](ISSUE_52_PROCESS_LIFETIME.md). Final focused **71 passed**;
  related **655 passed / two skips**; full isolated **2,095 passed / seven skips /
  19 subtests passed**. Generated scratch media deep validation passed. R4–R5 regressions are
  preserved; their historical 228/1,221/2,024 results remain in
  [the bridge report](ISSUE_52_CAPTURE_HANDOFF.md). Schema **3**, old-schema refusal,
  H ordering/FIFO/stop/admission/eight-unit accounting and synchronous defaults
  remain unchanged. No queued session is consumed. No full A1–A20 case is passed;
  only partial A6/A12/A19 process evidence is added.
  Branch: `codex/capture-journal-handoff`, isolated from the deployed editable checkout.
  **Review outcome: foundation retained; R6–R7 required. Current next action is
  recorded above. Pending owner action: None.**
  Scheduler/durable launch/input reopening/assembly/publication/settlement/service/
  API/monitor/storage-recovery/retention-reader/migration/cutover gates remain.
  No production mutation/restart, #48 polling, release/tag or merge. #48 OPEN/PAUSED,
  #28 unresolved, #13/#8 unstarted. Historical journal results remain in their report.

- **Issue #48 OPEN / explicitly PAUSED (owner decision, 2026-10-03):**
  Implementation/deployment passed; natural-recording validation did not.
  Preserve all acceptance criteria and approved Gracie-only raw policy, Ward
  OFF, monitored order `wardsimons`, `gracie.kf`. Resume when qualifying natural
  evidence is available, or credible missed-LIVE evidence warrants source-access
  investigation. Unknown/unverifiable does not prove offline. Do not repeat
  polling/searches as part of #52. This sequencing decision supersedes the older
  active/next-action statements below; it does not close #48, resolve #28 or
  authorize release. Historical evidence remains intact.

- **Issue #48 ACTIVE / OPEN — bounded natural gate PARTIAL (2026-10-03):**
  Deployment and approved Gracie-only policy remain intact. Current PID **16480**,
  creation **2026-10-02T12:32:54.1650210Z**, matches the task's later launch time;
  intervening launch reason is unproven because its Operational log is disabled.
  Task/config hashes match deployment; no rollback or restart was performed.
  All 54 immediate output-root `.parts` manifests are readable; no Gracie start
  after policy activation exists there or in current jobs. Latest Gracie began
  2026-10-02 03:44:57 UTC, before activation. Post-activation Ward job is raw OFF,
  failed/inactive on anonymous stream unavailability (4003110), with coherent
  UUID/room/paths and no stop/resume/recovery; no repair was attempted.
  Read-only 12:30:09–12:31:35 UTC / cycles 2663–2666 found healthy storage/config,
  two available slots, stable current jobs/automation, creators unknown/unverifiable
  and no selected automatic start. Current raw list remains **`gracie.kf` only**;
  monitored tuple **`wardsimons`, `gracie.kf`**, never Eliss.
  **Pending owner action: None.** Gracie automatic provenance, accepted true flag,
  raw/arrival/references/ranges/progress and suitable validation/finalization
  evidence remain unavailable. Next is another bounded read-only existing/natural
  Gracie evidence check, without restart/config change/manufactured LIVE.
  [ISSUE_48_DEPLOYED_VALIDATION.md](ISSUE_48_DEPLOYED_VALIDATION.md) records scope,
  hashes and limitations. #52 stays queued; #13/#28/#8 not started/resolved.
  v0.10.0 remains released/package version; v0.11.0 remains unreleased.

- **Issue #48 ACTIVE / OPEN — deployed opt-in PASSED, natural gate outstanding
  (2026-10-02):** The owner authorized Gracie-only automatic raw capture.
  Both slots were naturally completed/stable before the two required idle
  restarts: supporting code first, then saved startup-policy activation.
  Active PID **63796**, creation **2026-10-02T11:11:44.4280260Z**, runs #48 with
  **`automatic_raw_copy_creators = ["gracie.kf"]`**. Ward stays OFF; monitored
  order remains **`wardsimons`, `gracie.kf`**, never Eliss. Only the normal CLI
  against the proven UNC config saved the preference after supporting code loaded.
  Unrelated config bytes/settings, task definition, both completed job hashes
  and automation were unchanged. Health/storage/configuration are good.
  Both creators remained offline through normal monitoring cycles; no natural
  Gracie automatic capture/raw evidence was available during this gate.
  **Pending owner action: None.** Approved policy remains enabled. Safe next step
  is read-only validation of one natural automatic Gracie recording, preserving
  media/evidence. No further restart, config change or repeated authorization is
  needed. Close #48 only when raw/arrival/connection evidence and normal recording
  ownership/progress pass. Evidence and deployment details:
  [ISSUE_48_DEPLOYED_VALIDATION.md](ISSUE_48_DEPLOYED_VALIDATION.md).
  #48 is the single active task; #52 stays queued, #13/#28/#8 separate.
  v0.10.0 remains released/package version; v0.11.0 remains unreleased.

- **Issue #48 implementation checkpoint (superseded deployment status):** Implementation and isolated Windows
  offline verification are complete. Independent schema-1
  `automatic_raw_copy_creators` preferences default OFF, survive monitor removal,
  and use normal `monitor raw-copy enable/disable/list` locked atomic CLI updates.
  Service startup selects the policy; each accepted automatic start persists its
  boolean in the existing durable job, which governs recovery. #30 still reloads
  only monitored creators. Existing capture/evidence, capacity and admission
  paths are reused. Focused: 166 passed; broader: 634 passed / 2 subtests;
  full: **1,783 passed, 7 platform skips, 19 subtests**, Python 3.12.10 Windows,
  with fresh external config/test roots and no production token.
  **Then pending owner action (now granted/executed above):** authorize safe deployment and opt-in for one intended
  creator, followed by one natural automatic recording proving co-located raw /
  arrivals / connection references. Do not restart an active recording; do not
  manually start a LIVE to manufacture the gate. Deploy supporting code before
  saving a nonempty new field, which older strict readers reject. No deployment,
  production opt-in, restart, retention or release action occurred. PID 18660
  and creation time and exact host-visible config bytes remain unchanged;
  production monitoring stays **`wardsimons`, `gracie.kf`**, never Eliss.
  Final read-only check: Ward remains the original slot-1 UUID
  `9d3720f4-0123-4fcf-917d-4546d754be9d`, recording at 367,802,920 bytes,
  raw-copy OFF, no stop request or recovery state. Configuration health is `ok`;
  SHA256 stays `8f35fd61beb58fc35ae4d824598454dc3623cd9315464085ee195764c6303d10`.
  Local isolated results and before/after metadata:
  `C:\Users\Leandro\TikREC-tests\issue48-20261002-implementation`.
  #48 remains the single active task. #52 is queued afterward; #13/#28/#8 remain
  separate. v0.10.0 remains released/package version; v0.11.0 is unreleased.

- **Issue #51 COMPLETED / PASSED (project-manager decision, 2026-10-01):**
  #51 is closed as completed. The public retention CLI independent review gate
  and native Windows real-media retention validation are both **PASSED**.
  Exactly one authorized ordinary
  Eliss session returned COMPLETE/0; its 12-event durable audit records retained/
  control artifacts first, final MP4 last, and durable completion. Immediate
  verification proved exactly five intended paths removed, all 753 unrelated
  observed entries unchanged, and unaffected service/slot/job ownership. The
  deleted UUID was absent from subsequent planning. Age was safely restored to
  its original unset state. The later Gracie move was a separate owner-initiated,
  hash-checked Drive workflow after retention completion and immediate scope
  verification; the audit contains no Gracie target. `Unsorted`'s size-only API
  discrepancy establishes no content mutation or retention involvement.
  No production retention defect is demonstrated. **The one-deletion
  authorization is consumed; #51 authorizes no further destructive validation,
  retry, repair or second deletion.** Evidence and final decision:
  [ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).
  v0.10.0 remains the current released/package version; v0.11.0 remains
  unreleased pending normal release readiness/bookkeeping. This closure task
  changes documentation/issues only, without touching media, evidence, policy,
  service or production code. No feature implementation or release action starts.

- **Issue #30 COMPLETED / PASSED (2026-10-02, 11:53–11:56 CEST):**
  The deployed creator-only cycle-boundary hot reload passed real active-session
  removal/adoption/continuity/restoration. Ward's natural automatic session
  `9d3720f4-0123-4fcf-917d-4546d754be9d`, slot-1, room
  `7692001759392418593`, retained its output/parts paths and authoritative
  576-byte job unchanged through removal and restoration. Bytes advanced
  102,697,695 → 106,788,455 → 113,661,646 → 118,873,560 at cycles
  120/122/125/126. PID **18660**, creation **10:48:25.158312 CEST**,
  slot/session ownership, both durable jobs and automation bytes were unchanged;
  no stop, recovery, replacement or duplicate occurred. Configuration stayed
  healthy; Ward's restored room was suppressed as already consumed.
  The full original config bytes and intended ordered tuple
  **`wardsimons`, `gracie.kf`** are restored. Do not restore Eliss.
  Only normal CLI commands used the proven host-visible UNC config:
  `\\localhost\C$\Users\Leandro\AppData\Roaming\TikREC\config.json`.
  No restart, manual LIVE start/stop, retention, code, other issue implementation
  or release/tag action. Ward remained active at the final check; service
  operation continues normally. Implementation `e3864589` already passed
  120 focused / 422 broader / 1,754 full offline tests (7 skips, 19 subtests);
  no suite rerun was needed for this configuration/documentation-only gate.
  Evidence, hashes and earlier checkpoints:
  [ISSUE_30_DEPLOYED_VALIDATION.md](ISSUE_30_DEPLOYED_VALIDATION.md).
  **#48 is now the single active task**, with implementation/offline tests complete
  and its authorized deployed validation pending as recorded above.
  No owner action is pending for #30.
  #52 remains queued; #8/#28 remain opportunistic non-blocking evidence work,
  and #13 is separate queued rendition-policy work. None was started.
  v0.10.0 remains current released/package version; v0.11.0 remains unreleased.
  #30 completion does not perform or authorize release/tag work.

### Historical coordination checkpoints (superseded)

The entries below preserve what was known then. Their pending-review, active-task
and unused-authorization statements do not override the final decision above.

- **Issue #51 read-only reconciliation COMPLETE — A, explained unrelated
  change (2026-10-01):** The separate owner chat “Restore latest TikREC
  recording” executed a hash-checked `Move-Item` of the exact Gracie MP4 to the
  mounted Drive archive at 21:22:09.857–21:22:23.268 CEST, after Eliss retention
  completed and immediate scope verification passed. That chat subsequently
  restored the standard Videos path. Current local/Drive copies match its
  recorded SHA256; the restored local file has a new identity. The unchanged
  12-event audit contains only the Eliss operation and no Gracie target.
  `Unsorted`'s historical discrepancy is directory size only (4096 versus 0),
  with identity/timestamps unchanged; both values are reproduced by different
  read-only Windows APIs. The historical query cause remains unproven, and no
  content mutation there is established. No retention involvement or production
  defect is demonstrated. All 29 prior evidence checksums still match.
  **State:** #51 remains OPEN/single active, awaiting ChatGPT/project-manager
  review of the reconciled validation evidence; no unconditional full PASS or
  issue closure is claimed here. Age remains unset, its one deletion attempt
  remains consumed, and no retry/repair/second deletion is authorized.
  Investigation changed no media, sync settings, policy, service or audit.
  Detailed timeline, checksums and limitations are in
  [ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).
  **Next:** project-manager review of #51, without further destructive testing
  or starting another roadmap issue. Historical checkpoints follow.

- **Issue #51 deletion COMPLETE; full validation NOT PASSED (2026-10-01,
  21:05–21:24 CEST):** Fresh native Windows checks found both slots naturally
  idle, completed durable jobs and matching five-second root snapshots. The
  public age-unset plan cleared the root-wide conflict (19 retained, 27
  ineligible, three excluded raw diagnostics). The approved public temporary
  age-1 update and fresh plan allowed one ordinary Eliss candidate,
  `044cc8c0-9be6-4da6-8d0d-fef8e85dbf79`, the smallest safe non-Gracie session
  (four files / 196,673,543 bytes). One exact-confirmation public delete returned
  **COMPLETE/0**, operation `29d6d5a2-34cc-4420-91cf-324b29ba8cec`.
  Its 12-event durable audit proves retained FLV, connection log, manifest,
  empty parts directory, then final MP4 removal, ending `completed`.
  Immediate verification found exactly those five paths removed and all 753
  other observed entries unchanged, with both jobs/service ownership unaffected.
  During the subsequent public plan, however, unrelated
  `gracie.kf-20261001-201956.mp4` disappeared from the root. That plan exits 0
  with 48 root-wide conflicts and no deleted target. Final preservation also
  observes changed `Unsorted` directory metadata. No attribution, move or
  destruction of that Gracie media is inferred; its path was present at the
  immediate post-delete verification and is outside the retention operation.
  **State:** #51 remains open, single active, waiting for separate read-only
  reconciliation of the later root change; the complete validation is NOT PASSED.
  No defect is proven, no retry/repair/second deletion is authorized, and the
  **single-attempt allowance is consumed**. Age was safely restored through the
  public config path after proven completion, byte-for-byte to this resume's
  original SHA256 `2ac169bd603d6675b87ac9b9f875699d6f1872536354f393cc12d3bf6081dfa1`.
  Service PID 37772/creation time and both completed jobs remain unchanged;
  no stop/restart, production-code change, archive segregation or release work.
  Evidence, exact limitations and safe resume are in
  [ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).
  No owner action is needed for the read-only reconciliation; any further
  destructive validation would require new explicit owner authorization.
  Older checkpoints below retain their historical unused-allowance status.

- **Issue #51 Windows resume NOT PASSED (2026-10-01, 20:22–20:23 CEST):**
  The public configuration confirms `C:\Users\Leandro\Videos` and age unset;
  configuration SHA256 remains `02e4b5fe9fcb106d3c6b593ec7c596fc5e7eaa09976bbed33d0befc721ece507`.
  Slot 1 is recording Gracie session `ffcc2566-2085-4faa-940e-2bc177b5288c`;
  slot 2 holds completed Gracie `05f3e981-b713-403c-9bef-198282ec5766`.
  Both durable jobs match; slot 1 retains non-terminal recording intent.
  Five-second read-only root observations have 49 claims and zero uncertain
  claims, but differ as the active Gracie writer partial grows. One normal
  age-unset public plan exits 0 with all 49 sessions
  `needs_attention / evidence_conflict`. Stop boundary honored: no policy
  change, candidate selection, deletion attempt, retry, repair or service
  interruption. Age restoration is unnecessary because age was never changed;
  the one-deletion allowance remains unused. Service PID 37772 / creation
  2026-10-01 11:35:56 CEST and both slot UUIDs persist; health/storage remain OK.
  The lifecycle file is unchanged and the root-bound audit remains absent.
  Original archive untouched; new read-only evidence and checksums are recorded
  in [ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).
  **State:** #51 is the single active task, waiting for natural root
  inactivity/stability; no owner action is pending. Resume with fresh service,
  job, root and age-unset public-plan checks; retain all original exclusions
  and the one-attempt/restoration boundaries. No defect was demonstrated,
  production code/tests are unchanged and no other task or release was started.

- **Windows platform restored by owner decision (2026-10-01):** Windows
  `main-pc` is the sole active and planned recording/service runtime. The four
  unreleased Fedora commits after `0cc59bac` were reversed through an ordinary
  history-preserving cleanup; production code, tests and packaging match that
  pre-Fedora baseline. Managed Linux storage, backend, service integrations,
  deployment templates, tests and active Fedora reports are removed. #53/#54
  are superseded and closed as not planned; no Fedora validation gate remains.
  The interrupted backend review did not approve `12052e5` or validate Fedora.
  Its disposable WSL installation, identity and temporary unit were removed.
  **Single active/next task: #51**, Windows real-media retention validation,
  awaiting natural root inactivity/stability. No owner action is pending.
  First recheck the intended Windows root through the public age-unset plan;
  only after conflict clearance reconsider the existing temporary age-1 approval
  and at most one ordinary eligible non-Gracie session. All Gracie, forensic,
  diagnostic, raw-copy, protected, active/recoverable, ambiguous and job-linked
  exclusions remain. Real-media validation is NOT PASSED, age remains unset
  and the one-deletion allowance is unused. This rollback accessed no real
  media, evidence archive, owner configuration or service state and performed
  no deployment, service interruption or release. v0.10.0 remains released;
  v0.11.0 remains unreleased. Verification on Windows Python 3.12.10 / pytest
  9.1.1: focused retention/lifecycle/policy/service/recording/automation tests
  **674 passed / 5 skipped**; full isolated offline suite **1,731 passed /
  7 skipped / 19 subtests**, 67.62 s. APPDATA and LOCALAPPDATA were isolated
  under a fresh external temporary root; pytest used separate basetemps with
  `-p no:cacheprovider`. Removed-module import checks, CLI help checks and
  `git diff --check` passed. Unrelated untracked test artifacts are preserved.
  Earlier dated entries are historical checkpoints.

- **Issue #49 comparison complete; #51 still paused (2026-09-30):** The exact
  issue-#28 Gracie room was captured by both recorders, but with different video
  renditions. Shared AAC hashes place current MP4 10:15 inside an old capture
  gap of 16.43 seconds, after the old recorder rejected an IDR's push-dimensions
  announcement without a new AVC header. Old-style NVENC normalization preserves
  the current damaged excerpt's 1,124 frames and visible columns; `discardcorrupt`
  changes neither examined packets nor decoded output pixels. Re-encoding produces
  decoder-clean files containing damaged imagery. The old raw FLVs for this LIVE
  are absent; surviving remuxed inputs are clean around the gap, and source-versus-
  writer attribution remains open/non-blocking #28. See
  [ISSUE_49_GRACIE_COMPARISON.md](ISSUE_49_GRACIE_COMPARISON.md).
  No current defect was proven or fix implemented; 42 original files passed
  repeated hashes/metadata checks. No implementation task is active. #51 remains
  authorized but paused awaiting a naturally idle/stable root; no owner action
  is pending, its one-deletion allowance is unused, the age rule is unset, and
  its evidence archive stays in place. Safe next action: resume only #51's public
  age-unset plan after natural inactivity; preserve its existing stop boundaries.
  #48 remains queued for opt-in watcher raw evidence, with #13 separate rendition
  policy work. v0.10.0 remains released; v0.11.0 is unreleased and its real-media
  retention gate remains unpassed.

- **Issue #51 segregation complete; validation awaiting a stable idle root
  (2026-09-30):** Only the six approved manifestless `test*.parts` directories
  and existing `test3.mp4`/`test5.mp4`/`test6.mp4` siblings were moved to
  `C:\Users\Leandro\TikREC-evidence\issue-51-manifestless`. All 19 files
  (806,859,876 bytes) passed before/after SHA256, size, identity, and timestamp
  checks; the nine original paths are absent. No Gracie path was moved.
  The public age-unset plan exited 0 but still marked all 47 remaining sessions
  `evidence_conflict`, triggering the approved stop boundary. Later read-only
  snapshots had 48 claims and zero uncertain claims, but differed as the active
  Eliss and naturally started Gracie writer partials grew. This is expected
  whole-root stability refusal; active writers also conflict with the exclusive
  retention lifecycle lease. No age rule was set and no deletion command was
  issued; configuration bytes are unchanged and the one-deletion authorization
  remains unused. See [ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).
  **Safe resume:** #51 remains the single active task, awaiting natural root
  inactivity/stability; no owner action is pending. Leave the archive in place
  and do not repeat segregation. First rerun the public plan with age unset;
  only if the root-wide conflict clears may the approved temporary one-day rule
  and one safe ordinary non-Gracie candidate be reconsidered. Preserve all
  diagnostic/forensic/job-linked/active media. #30/#48/#49/#28/#13/#8 remain
  outside this task; v0.11.0 remains unreleased.

- **Issue #51 owner unblock approved (2026-09-30):** The owner approved
  preserving/segregating only the six manifestless `test*.parts` evidence sets
  (including any same-stem sibling MP4s) to a dedicated archive outside
  `C:\Users\Leandro\Videos`, with before/after metadata and hashes, and approved a
  temporary `retention_max_age_days=1` solely for this validation. All Gracie
  recordings are categorically excluded, along with active/job-linked,
  raw-copy/forensic/diagnostic, ambiguous, or protected sessions. After a fresh
  public plan, at most one clearly safe non-Gracie ordinary session may be
  deleted under the existing #51 authorization. No second deletion is authorized.
  Restore the age rule to its prior unset state after the validation attempt unless
  an incomplete/uncertain result makes any further mutation unsafe, in which case
  stop and preserve evidence. #51 is the single active task; v0.11.0 remains
  unreleased.

- **Issue #51 read-only root-conflict investigation complete (2026-09-30):**
  A stable snapshot now contains 53 immediate `.parts` directories. Six
  `test.parts`/`test2.parts`–`test6.parts` lack `session.json`; their claims are
  uncertain, and `retention_plan.py` deliberately promotes any uncertain
  claimant to root-wide `evidence_conflict`. No duplicate known UUID, lexical
  output, or physical output was observed; no claimant directory or known output
  was a reparse point. Before that override, 16 current completed sessions
  classify `retained` (age rule disabled), 27
  older/legacy sessions classify `ineligible` (creator absent; 18 completed,
  six interrupted, three failed), and 10 classify individually
  `needs_attention`: the six manifestless directories, three raw-copy
  diagnostic sessions with extra evidence, and one active Eliss writer partial.
  The public plan confirms all 53 display `evidence_conflict`.
  This is intended fail-closed behavior, not a demonstrated planner defect.
  No media, configuration, policy, service, or production code changed.
  **State:** investigation complete; #51 real-media validation remains blocked
  and its CLI review gate remains PASSED. The owner must choose how to preserve
  and segregate the six manifestless directories (or identify an existing clean
  recording root) and separately choose an age rule. No in-place subset filter
  exists; no clean direct-child root was found under `Videos`. Then rerun the
  public plan, exclude the active/job-linked/diagnostic/forensic sessions, and
  consider one already-eligible ordinary session. #30, #48, #49, #28, #13, and
  #8 remain outside #51; v0.10.0 is released and v0.11.0 unreleased.

- **Prior #51 validation checkpoint — BLOCKED without deletion
  (2026-09-30; superseded by the investigation above):** The public
  `retention plan --json` completed twice against the configured
  `C:\Users\Leandro\Videos` root. `retention_max_age_days` was unset, and all
  52 immediate sessions were `needs_attention` / `evidence_conflict`;
  there is no already-`eligible` candidate. The service was reachable with
  `active_count=0` and two available slots; both durable jobs reference completed
  Gracie sessions. No delete command, audit operation, policy change, service
  restart, or media mutation was attempted. The public CLI gate remains PASSED,
  but real-media validation is NOT PASSED. #51 remains the single blocked task.
  **Safe resume:** first investigate the root-wide planner conflict read-only;
  owner direction is needed before enabling an age rule. Rerun the public plan
  and reconsider one ordinary candidate only after it is already `eligible`
  under configured policy. #30, #48, #49, #28, #13, and #8 remain outside this
  task; v0.10.0 is released and v0.11.0 unreleased.

- **Owner authorization recorded (2026-09-30; issue #51; superseded by the
  blocked checkpoint above):**
  The public retention CLI gate passed at `7724e21`. The owner has now explicitly
  authorized deletion of exactly one real Windows recording for validation.
  #51 became the single active task. Candidate selection must exclude active,
  protected, ambiguous, raw-copy, forensic, and issue-linked evidence; do not
  stop/restart the service to force eligibility. Use only the public CLI with
  exact confirmation, never the private executor. On refusal/incomplete/uncertain
  result, stop with no retry, repair, manual cleanup, or second deletion. On
  proven COMPLETE/0, verify audit order, exact filesystem scope, fresh plan, and
  unaffected service ownership. #30, #48, #49, #28, #13, and #8 remain queued or
  non-blocking outside this task. v0.11.0 remains unreleased.

- **Fresh independent public retention CLI gate PASSED (2026-09-29;
  reviewed `f3dd917`):** Rechecked the full preview, consent, authorization,
  audit, lifecycle, policy, held-artifact, and result paths against corrections
  #39–#50. Six new disposable Windows probes covered confirmation read failure,
  parser diagnostics, lifecycle and policy acquisition, post-quarantine failure,
  and combined post-intent `BaseException`/failed-event/outer cleanup faults;
  all passed. Native Windows retention/lifecycle/policy/audit: 477 passed,
  five skipped; isolated full offline: 1,731 passed, seven skipped,
  19 subtests; applicable WSL/POSIX: 117 passed, 60 skipped, plus 15 direct
  audit/history passes. No review blocker was found. **State:** public CLI gate
  PASSED; the next retention step is separately authorized real-media retention
  validation. No owner decision was required for this review. #30, #48, #49,
  #28, #13, and #8 remain outside this task. v0.10.0 is released and v0.11.0
  unreleased. No production code or real media changed.

- **Issue #50 pre-intent `SystemExit` correction complete (2026-09-29):**
  The public retention delete CLI now returns `REFUSED`/1 with the first
  `SystemExit` reason, selected UUID, absolute root, and no-operation notice
  when intent sync has not begun. Later audit/lifecycle cleanup faults remain
  secondary; broken stderr cannot alter exit 1. Pre-intent Ctrl-C remains 130,
  after-intent uncertainty remains 3, and durable completion remains 0.
  Native Windows retention/lifecycle/policy: 477 passed, five skipped;
  isolated full offline: 1,731 passed, seven skipped, 19 subtests;
  applicable WSL/POSIX: 117 passed, 60 skipped, plus 15 direct audit/history
  passes. **State:** #50 correction complete; the single next v0.11 task is
  a NEW fresh-context independent public retention CLI review. The gate
  remains NOT READY before separately authorized real-media validation.
  No owner decision is pending. #30, #48, #49, #28, #13, and #8 remain outside
  this task. v0.10.0 is released and v0.11.0 unreleased. No real media was
  deleted.

- **Fresh independent public retention CLI gate NOT READY (2026-09-29;
  reviewed `72996a7`; issue #50):** Disposable Windows probes found that a
  first pre-intent `SystemExit` from preview stdout or audit-entry validation
  escapes the public delete command instead of returning `REFUSED`/1. In the
  audit case, later handle-close and lifecycle-unlock faults did not replace
  the first cause, but no refusal diagnostic was attempted. No intent or
  removal occurred. New combined fault probes: 14 passed. Native Windows
  retention/lifecycle/policy: 467 passed, five skipped; isolated full offline:
  1,721 passed, seven skipped, 19 subtests; applicable WSL/POSIX:
  117 passed, 40 skipped, plus 15 direct audit/history passes. **State:**
  #50 is the single next bounded v0.11 correction; repeat a NEW independent
  public CLI review afterward. The gate remains NOT READY before separately
  authorized real-media validation. No owner decision is pending. #30, #48,
  #49, #28, #13, and #8 remain outside this task. v0.10.0 is released and
  v0.11.0 unreleased. No production code or real media changed.

- **Issue #47 audit/lifecycle teardown correction complete (2026-09-29):**
  Audit-entry validation and acquisition faults now survive later handle-close
  faults, preserving genuine pre-intent `REFUSED`/1 and interruption/130.
  Lifecycle unlock, handle close, registry decrement, and writer-slot release
  are attempted once; the first fault stays authoritative and later faults
  remain secondary. Acquisition rollback also releases a partly registered
  writer slot before closing its handle. Disposable combined-fault tests
  preserve incomplete/3, persisted `failed.error_type`, and proven
  `COMPLETE`/0. Native Windows retention/lifecycle/policy/audit: 466 passed,
  five skipped; isolated full offline: 1,721 passed, seven skipped, 19
  subtests; applicable WSL/POSIX: 185 passed, 15 skipped. **State:** #47
  correction complete; the single next v0.11 task is a NEW fresh-context
  independent public retention CLI review. The
  gate remains NOT READY until that review passes, before separately
  authorized real-media validation. No owner decision is pending; #30 stays
  queued and #8/#13/#28 remain non-blocking evidence work. v0.10.0 remains
  released and v0.11.0 unreleased. No real media was deleted.

- **Fresh independent public retention CLI gate NOT READY (2026-09-29;
  reviewed `75ffb1d`; issue #47):** Disposable native Windows probes found
  that audit-entry cleanup can replace a first pre-intent validation fault,
  letting a later `SystemExit` escape without `REFUSED`/1. Lifecycle unlock
  can likewise be replaced by later handle-close failure; after proven
  completion the result stays `COMPLETE`/0 but names the wrong first fault,
  and the in-process lifecycle registry remains occupied after the OS handle
  closes. A combined artifact/policy/held/failed-event/audit/lifecycle probe
  retained the first mutation fault and its `failed.error_type`, but lost the
  first lifecycle cleanup fault. Native Windows retention/lifecycle/policy:
  446 passed, five skipped; isolated full offline: 1,701 passed, seven
  skipped, 19 subtests; applicable WSL/POSIX: 169 passed, four skipped.
  **State:** #47 is the single next bounded v0.11 correction. Repeat a NEW
  fresh-context independent public CLI review afterward; the gate remains
  NOT READY before separately authorized real-media validation. No owner
  decision is pending; #30 stays queued and #8/#13/#28 remain non-blocking
  evidence work. v0.10.0 remains released and v0.11.0 unreleased. No
  production code or real media was changed in this review.

- **Issue #46 cleanup fault correction complete (2026-09-29):** Policy-lock
  teardown now preserves a body fault or its own first close/release fault
  before later cleanup faults, exposing the latter in order as secondary
  diagnostics. Before completion, audit cleanup is retained separately from
  later lifecycle cleanup. The public incomplete result and persisted failed
  event keep the first known cause; proven completion remains COMPLETE/0.
  Native Windows retention/lifecycle/policy: 446 passed, five skipped;
  isolated full offline suite: 1,701 passed, seven skipped, 19 subtests;
  applicable WSL planning/refusal/direct audit/policy: 186 passed, 38 skipped.
  **State:** #46 correction complete; the single next v0.11 task is a NEW
  fresh-context independent public retention CLI review. The gate remains
  NOT READY until that review passes, before separately authorized real-media
  validation. No owner decision is pending; #30 stays queued and #8/#13/#28
  remain non-blocking evidence work. v0.10.0 remains released and v0.11.0
  unreleased. No real media was deleted.

- **Fresh independent public retention CLI gate NOT READY (2026-09-29;
  reviewed 2ccf464; issue #46):** Disposable native Windows probes found that
  a first policy-lock descriptor-close fault can be replaced by a later
  condition-notification fault inside the same cleanup block. The public
  PARTIAL/3 reason and persisted failed.error_type then name the later fault.
  Audit cleanup can also disappear from secondary diagnostics when lifecycle
  cleanup fails afterward. Native retention/lifecycle/policy: 435 passed, five
  skipped; isolated full offline suite: 1,690 passed, seven skipped, 19
  subtests; applicable WSL planning/refusal/direct audit checks: 176 passed,
  37 skipped. **State:** #46 is the single next bounded v0.11 correction;
  repeat a NEW fresh-context public CLI review afterward. The gate remains
  NOT READY before separately authorized real-media validation. No owner
  decision is pending; #30 stays queued and #8/#13/#28 remain non-blocking
  evidence work. v0.10.0 remains released and v0.11.0 unreleased. No
  production code or real media was changed in this review.

- **Issue #45 inner artifact fault correction complete (2026-09-29):**
  The mutation boundary now captures the first proof/removal or handle-entry
  fault before policy or held-handle cleanup can replace it. The original
  exception type reaches the `failed` audit event; its message reaches the
  public `FAILED`/`PARTIAL` reason. Later inner cleanup faults remain secondary
  diagnostics. Native Windows retention/lifecycle tests: 435 passed, five
  skipped; isolated full offline suite: 1,690 passed, seven skipped, 19
  subtests; applicable WSL planning/refusal/read-only audit: 143 passed,
  five skipped. **State:** #45 correction complete; the single next v0.11
  task is a NEW fresh-context independent public retention CLI review. The
  gate remains NOT READY until that review passes. No owner decision is
  pending; separately authorized real-media validation follows a passing
  review. #30 stays queued and #8/#13/#28 remain non-blocking evidence work.
  v0.10.0 remains released and v0.11.0 unreleased. No real media was deleted.

- **Fresh independent public retention CLI gate NOT READY (2026-09-28;
  reviewed `1b38b65`; issue #45):** Disposable native Windows proof and
  held-handle cleanup faults showed that inner mutation cleanup can replace
  the first post-intent operation cause before executor progress captures it.
  The CLI keeps `PARTIAL`/3 and operation/audit context but reports only the
  later close fault; a primary `SystemExit` can be misrecorded as `OSError`
  in the `failed` event. Focused retention/lifecycle: 424 passed, five
  skipped; isolated full offline suite: 1,679 passed, seven skipped, 19
  subtests; applicable WSL planning/refusal/read-only audit: 143 passed, five
  skipped. **State:** #45 is the single next bounded v0.11 correction; repeat
  a NEW fresh-context public CLI review afterward. No owner decision is
  pending. Separately authorized real-media validation remains later; #30
  stays queued and #8/#13/#28 remain non-blocking evidence work. v0.10.0
  remains released and v0.11.0 unreleased. No production code or real media
  was changed in this review.

- **Issue #44 post-completion fault correction complete (2026-09-28):** After
  proven `completed` sync, caller-owned progress now retains the first operation
  or audit cleanup fault before lifecycle cleanup can mask it. The public CLI
  keeps `COMPLETE`/0 and operation/audit context, reports later cleanup faults
  separately when stderr works, and survives broken diagnostics. Native Windows
  focused tests: 120 passed, one skipped; isolated full offline suite: 1,679
  passed, seven skipped, 19 subtests; applicable WSL planning/refusal and
  read-only audit checks: 100 passed, two skipped. **State:** #44 correction
  complete; the single next v0.11 task is a NEW fresh-context independent public
  retention CLI review. The gate remains NOT READY until that review passes;
  separately authorized real-media validation follows a passing review. No
  owner decision is pending. #30 stays queued; #8/#13/#28 are non-blocking
  evidence work. v0.10.0 remains released and v0.11.0 unreleased. No real media
  was deleted.

- **Fresh independent public retention CLI gate NOT READY (2026-09-28;
  HEAD `3850d8c`; issue #44):** Disposable native Windows probes found that
  after a synced `completed` event, a later audit/lifecycle cleanup fault can
  hide the first post-completion interruption or cleanup error from `COMPLETE`/0
  diagnostics. The result code and operation/audit context remain correct, but
  fault precedence is not. Focused retention/lifecycle tests: 403 passed, four
  skipped; isolated full suite: 1,663 passed, seven skipped, 19 subtests;
  applicable WSL planning/refusal and read-only audit checks: 177 passed, five
  skipped. Combined pre-completion fault and post-preview claimant probes held
  their expected boundaries. **State:** #44 is the single next bounded v0.11
  correction; repeat a NEW fresh-context public CLI review afterward. No owner
  decision is pending. Separately authorized real-media validation remains
  later; #30 stays queued, and #8/#13/#28 remain non-blocking evidence work.
  v0.10.0 remains released and v0.11.0 unreleased. No production code or real
  media was changed in this review.

- **Issue #43 after-intent result correction complete (2026-09-28):** The
  executor now publishes the first operation fault before audit or lifecycle
  cleanup can mask it. The public CLI retains that cause in `FAILED`/`PARTIAL`
  exit 3, reports a secondary cleanup fault when stderr works, and converts
  post-intent `SystemExit` to an incomplete result with operation/audit context.
  Pre-intent 1/130, uncertain intent/completion sync, and proven `COMPLETE`/0
  remain intact. Native Windows retention/lifecycle tests: 402 passed, four
  skipped; isolated full suite: 1,663 passed, seven skipped, 19 subtests;
  applicable WSL planning/refusal and read-only audit history: 116 passed,
  five skipped. **State:** #43 correction complete; the single next v0.11 task
  is a NEW fresh-context independent public CLI review. The public CLI gate
  remains NOT READY until that review passes. No owner decision is pending;
  separately authorized real-media validation follows a passing review.
  #30 stays queued; #8/#13/#28 remain non-blocking evidence work. v0.10.0
  remains released and v0.11.0 unreleased. No real media was deleted.

- **Issue #28 intermittent Gracie recurrence investigated (2026-09-28):**
  Owner-reported battle-linked columns around MP4 10:11 are visible in both the
  retained FLV and final MP4 at 10:15. Both retained parts use one identical
  640x1280 AVC configuration; no retained 640/720 switch or timestamp replay was
  found. This session has no raw/arrival copy, so source-versus-writer origin is
  unresolved. The next useful evidence is an owner-authorized normal `--raw-copy`
  occurrence with battle times and all raw/retained/final artifacts preserved.
  #28 stays non-blocking; #43 is corrected and the single next v0.11 task is a
  NEW independent public retention CLI review before separately authorized
  real-media validation.
  #30 stays queued; v0.10.0 remains released and v0.11.0 unreleased.

- **Fresh independent public retention CLI gate NOT READY (2026-09-28;
  HEAD `b8ad110`; issue #43):** Disposable native Windows probes showed that
  an audit or lifecycle cleanup `OSError` after an execution failure replaces
  the original cause in the public `FAILED`/`PARTIAL` result. A `SystemExit`
  during an audit attempt after durable intent escapes without exit 3 or
  operation/audit context, despite a journaled `failed` event. Focused
  retention/lifecycle tests: 388 passed, four skipped; isolated full suite:
  1,649 passed, seven skipped, 19 subtests; applicable WSL planning/refusal
  and read-only audit history: 116 passed, five skipped. **State:** #43 is the
  single next bounded v0.11 correction; repeat a NEW fresh-context public
  CLI review afterward. No owner decision is pending. Separately authorized
  real-media validation remains later; #30 stays queued and #8/#13/#28 remain
  non-blocking evidence work. v0.10.0 remains released and v0.11.0 unreleased.
  No real media was deleted or production code changed in this review.

- **Issue #42 completion-result correction complete (2026-09-28):** The
  caller-owned retention progress now records a proven `completed` audit sync
  before audit-handle or lifecycle cleanup. Later cleanup faults report
  `COMPLETE`/0 with the original cause and operation context through one
  best-effort diagnostic; an interrupted or failed `completed` sync remains
  non-complete/3. Native Windows retention/lifecycle tests: 388 passed, four
  skipped; isolated full suite: 1,649 passed, seven skipped, 19 subtests;
  applicable WSL planning/refusal and read-only audit history: 116 passed,
  five skipped. **State:** #42 correction complete; the single next v0.11
  task is a NEW fresh-context independent public CLI review before separately
  authorized real-media validation. No owner decision is pending. #30 stays
  queued; #8/#13/#28 remain non-blocking evidence work. v0.10.0 remains
  released and v0.11.0 unreleased. No real media was deleted.

- **Fresh independent public retention CLI gate NOT READY (2026-09-28;
  HEAD `cc0824d`; issue #42):** Native Windows disposable `OSError` and
  `KeyboardInterrupt` probes after the synced `completed` audit event, during
  audit-handle cleanup, returned `PARTIAL`/3 although the journal ended in
  `completed` and all synthetic artifacts were removed. The CLI has no
  caller-owned proof of completion until the executor returns, leaving a
  completion-to-return gap after #40. Focused retention/lifecycle tests:
  376 passed, four skipped; isolated full suite: 1,637 passed, seven skipped,
  19 subtests; applicable WSL planning/refusal and read-only audit history:
  116 passed, five skipped. **State:** #42 is the single next bounded v0.11
  correction; repeat a NEW fresh-context public CLI review afterward. No
  owner decision is pending. Separately authorized real-media validation is
  later; #30 stays queued, #8/#13/#28 remain non-blocking evidence work.
  v0.10.0 remains released and v0.11.0 unreleased. No real media was deleted.

- **Issue #41 intent-sync and diagnostic result correction complete
  (2026-09-28):** The audit marks sync started after writing intent and before
  `fsync`; faults inside that boundary report uncertain `FAILED`/3 with the
  original cause, operation ID, and audit path instead of a definitive
  pre-intent result. Proven pre-sync faults retain `REFUSED`/1 or interruption
  130. Failure diagnostics are best-effort, so broken stderr writes/flushes
  preserve exit 3; #40 completed-output exit 0 remains intact. Native Windows
  Python 3.11 retention tests: 369 passed, four skipped; isolated full suite:
  1,637 passed, seven skipped, 19 subtests; applicable WSL planning/refusal:
  107 passed, 39 skipped, plus ten read-only audit-history checks passed.
  **State:** #41 correction complete; the single next v0.11 task is a NEW
  fresh-context independent public CLI review. No owner decision is pending;
  separately authorized real-media validation remains later. #30 stays queued;
  #8/#13/#28 remain non-blocking evidence work. v0.10.0 remains released and
  v0.11.0 unreleased. Only disposable synthetic fixtures were deleted.

- **Fresh independent public retention CLI gate NOT READY (2026-09-28;
  HEAD `653f5fe`; issue #41):** Native Windows disposable probes found two
  result-reporting gaps. An interrupt after the OS successfully syncs `intent`
  but before the durability callback runs reports pre-intent `130` (or
  `REFUSED`/1 for an exception) despite a complete intent record. A broken
  stderr write during an after-intent failure escapes instead of returning
  `FAILED`/3. No artifact was removed in either probe. Native Python 3.11
  retention tests: 360 passed, four skipped; isolated full suite: 1,628
  passed, seven skipped, 19 subtests; applicable WSL planning/refusal: 107
  passed, 39 skipped, plus ten read-only audit-history checks passed.
  **State:** #41 is the single next bounded correction; repeat a NEW
  fresh-context public CLI review afterward. No owner decision is pending;
  separately authorized real-media validation remains later. #30 stays queued;
  #8/#13/#28 remain non-blocking evidence work. v0.10.0 remains released and
  v0.11.0 unreleased. No real media was deleted.

- **Issue #40 completed-output reporting correction complete (2026-09-28):**
  After the executor returns with synced `completed`, success-output failures
  now keep `COMPLETE`/exit 0. The CLI makes one bounded stderr report with the
  original output cause, operation UUID, and audit path; a failed diagnostic
  channel does not change the completed result. Native Windows Python 3.11
  focused retention tests: 364 passed, four skipped; isolated full suite:
  1,628 passed, seven skipped, 19 subtests; selected WSL planning/refusal:
  107 passed, 44 Windows-only skipped. **State:** #40 correction complete;
  the single next v0.11 task is a NEW fresh-context independent public CLI
  review before separately authorized real-media validation. No owner decision
  is pending. #30 stays queued; #8/#13/#28 remain non-blocking evidence work.
  v0.10.0 remains released and v0.11.0 unreleased. Only disposable synthetic
  fixtures were deleted.

- **Fresh independent public retention CLI gate NOT READY (2026-09-28;
  HEAD `f99528f`; issue #40):** A disposable native Windows Python 3.11
  probe raised `OSError` or `KeyboardInterrupt` while the CLI printed
  `COMPLETE`, after the executor returned. Both paths reported `PARTIAL`/exit 3,
  although the audit ended with synced `completed` and all authorized synthetic
  artifacts were gone. The #39 post-intent correction held; this is a distinct
  terminal-output classification gap. Focused retention suite: 355 passed,
  four skipped; isolated full suite: 1,619 passed, seven skipped, 19 subtests;
  selected WSL planning/refusal: 107 passed, 35 Windows-only skipped.
  **State:** #40 is the single active bounded correction; no owner decision is
  pending. After it, repeat a NEW fresh-context public CLI review before
  separately authorized real-media validation. #30 stays queued; #8/#13/#28
  remain non-blocking evidence work. v0.10.0 remains released and v0.11.0
  unreleased. Only disposable synthetic fixtures were deleted.

- **Issue #39 post-sync intent reporting correction complete (2026-09-28):**
  Audit append now marks caller progress immediately after a successful intent
  `fsync`, before control can return to a faulting caller. A later exception or
  `KeyboardInterrupt` reports `FAILED`/exit 3 with the original cause, operation
  UUID, and audit path; pre-sync failures still report refusal/exit 1 or
  pre-intent interruption/exit 130. Synthetic Windows regressions cover both
  sides of the boundary. Python 3.11 focused suite: 414 passed, four skipped;
  isolated full suite: 1,619 passed, seven skipped, 19 subtests. Selected WSL
  read-only planning/refusal suite: 109 passed, 33 Windows-only skipped.
  **State:** correction complete; the single next v0.11 task is a NEW
  fresh-context independent public CLI review before separately authorized
  real-media validation. No owner decision is pending. #30 stays queued;
  #8/#13/#28 remain non-blocking evidence work. v0.10.0 remains released and
  v0.11.0 unreleased. Only disposable synthetic fixtures were deleted.

- **Fresh independent public retention CLI review NOT READY (2026-09-28;
  HEAD `bddcedd`; issue #39):** A disposable native Windows fault injected
  immediately after a synced audit `intent` but before executor progress was
  marked durable. The public CLI reported `REFUSED`/exit 1 or pre-intent
  interruption/exit 130, although the journal contained a durable intent and
  operation UUID. No artifact was removed. **State:** #39 is the single active
  bounded correction for truthful post-intent reporting; no owner action is
  pending. After it, repeat a NEW
  fresh-context public CLI review before separately authorized real-media
  validation. Python 3.11 focused Windows suite: 409 passed, four skipped;
  isolated full suite: 1,614 passed, seven skipped, 19 subtests. Native WSL
  selected planning/refusal suite: 109 passed, 28 Windows-only skipped.
  v0.10.0 remains released, v0.11.0 unreleased; #30 stays queued and
  #8/#13/#28 remain non-blocking evidence work. No real media was deleted.

- **Issue #38 owner-facing retention CLI implementation complete (2026-09-28):**
  The unreleased local CLI now extends read-only planning with safe nullable
  file counts/bytes and offers explicit one-UUID Windows deletion with exact
  confirmation, a display-evidence veto, fresh executor authorization, and
  truthful audit-backed COMPLETE/FAILED/PARTIAL outcomes. Python 3.11 focused
  Windows suite: 442 passed, three skipped; isolated full suite: 1,609 passed,
  six skipped, 19 subtests. Native WSL POSIX refusal/planning tests passed.
  Only disposable synthetic media was deleted; no real recording or power-loss
  validation was performed. **State:** implementation complete; the single next
  v0.11 step is a NEW fresh-context independent review of the public CLI,
  preview/authorization boundary, and result/audit reporting before real-media
  validation or release readiness. No owner action is pending. #30 stays
  queued; #8/#13/#28 remain non-blocking evidence work. v0.10.0 remains
  released and v0.11.0 unreleased.

- **Owner-facing retention CLI design complete (2026-09-28):**
  [RETENTION_CLI.md](RETENTION_CLI.md) is the approved design-only contract for
  an expanded read-only plan and explicit, one-UUID local Windows deletion
  command. It specifies exact-UUID confirmation, a preview-evidence veto plus
  fresh executor authorization, truthful refusal/partial reporting, audit
  visibility, and exit codes. **No public deletion command was implemented.**
  **State at that checkpoint:** design complete; issue #38 became the bounded
  implementation slice for this local CLI workflow and offline tests. No
  owner action is pending. #30 remains queued; #8/#13/#28 remain non-blocking
  evidence work. v0.10.0 remains released and v0.11.0 unreleased.

- **Fresh independent retention gate passed (2026-09-28; HEAD `ef8d01b`):**
  Windows-only private deletion is READY FOR OWNER-FACING RETENTION DESIGN under
  the documented cooperative-filesystem boundary. Native NTFS handle,
  collision, byte-proof, final-MP4 order, policy-race, two-slot, and audit/crash
  checks found no in-scope blocker. Focused Windows suite: 403 passed, one
  skipped; isolated full suite: 1,581 passed, five skipped, 19 subtests. WSL
  POSIX refusal and historical journal reopening passed. A cross-process
  protection change before disposition refused removal and recorded `failed`;
  preexisting hard links refused before audit intent. A deliberately added
  hard link after final identity proof is outside the cooperative boundary.
  No real recording was deleted or power-loss validation performed.
  **State:** gate complete; the single next v0.11 slice is owner-facing explicit
  retention execution design, not yet implementation. #30 stays queued;
  #8/#13/#28 remain non-blocking evidence work. v0.10.0 remains released and
  v0.11.0 unreleased. No owner action is pending for this review.

- **Issue #37 corrective implementation complete (2026-09-28):** Windows
  retention holds one exclusive object handle through non-overwriting quarantine,
  byte proof, and handle-based file/directory deletion. Configuration promotion
  and the final policy/job recheck plus removal share a short cross-process lock;
  CLI read-modify-write transactions preserve concurrent protection changes.
  The owner explicitly approved Windows deletion with POSIX refusal before any
  retention mutation, replacing the earlier POSIX normal-deletion criterion.
  Read-only POSIX planning and valid schema-1 history remain supported.
  Native Windows/Python 3.11 full offline suite: 1,581 passed, five skipped,
  19 subtests passed. Native WSL/POSIX refusal, collision preservation, and
  historical unusual-name journal reopen passed. Deterministic collision,
  substitution, policy-race, alias, and process-crash regressions passed.
  No real recording was deleted or power-loss test performed.
  **State:** implementation complete; the single next task is a NEW fresh-context
  independent executor/lifecycle/authorization/mutation/audit safety review before
  owner-facing retention design. No owner action is pending. #30 stays queued;
  #8/#13/#28 remain non-blocking evidence work. v0.10.0 remains released and
  v0.11.0 unreleased.
- **NEW fresh independent retention gate NOT READY (2026-09-28; issue #37):**
  Review of current HEAD `5d27dc8` reproduced a post-quarantine proof-to-unlink
  race on native Windows: an FLV, final MP4, or empty parts directory can be
  replaced at its private name, the replacement removed, and the audit marked
  `completed` while the authorized object survives. Native WSL/POSIX `rename`
  overwrote an unexpected private-name occupant inserted after the occupancy
  check. A public creator-protection update after the last policy check but
  before unlink allowed one newly protected part to be removed before the next
  check stopped the operation. #37 records reproductions and narrow corrective
  scope. Focused Windows suites passed 312 (four skips); the isolated full
  offline suite passed 1,535 plus 19 subtests (four skips); native WSL/POSIX
  journal reopen passed. No real media was deleted or power-loss behavior tested.
  **State:** v0.11 owner-facing retention design is blocked on #37. Correct #37,
  then run another NEW fresh-context independent gate. #30 stays queued;
  #8/#13/#28 remain separate non-blocking evidence work. No owner action is
  pending. v0.10.0 remains released and v0.11.0 unreleased.
- **Issue #36 corrective implementation complete (2026-09-28):** The private
  executor now byte-binds every authorized file across the first plan,
  authorization, closing plan, and each surviving deletion position. It moves
  each artifact to an audited same-directory quarantine name and verifies the
  moved identity and bytes before removal; a failed move/proof leaves evidence
  and stops. Schema-1 history accepts legal POSIX literal backslashes and
  rejects unpaired writer-recovery evidence/part paths while reading old valid
  journals. Native Windows and Python 3.11 focused suites passed, native
  WSL/POSIX unusual-name reopen passed, and the isolated full offline suite
  passed 1,535 plus 19 subtests (four skips). No real media was deleted and no
  power-loss test was performed.
  **State:** #36 implementation complete; a NEW fresh-context independent
  retention executor/lifecycle/authorization/audit safety review is the single
  next gate. No owner action is pending. #30 stays queued; #8/#13/#28 remain
  separate non-blocking evidence work. v0.10.0 remains released and v0.11.0
  unreleased.
- **Fresh independent retention gate NOT READY (2026-09-28; issue #36
  opened):** Reviewed HEAD `d20ed7a` could delete ordinary FLV and final MP4
  media after a same-size/restored-metadata Windows byte change makes fresh
  planning `needs_attention`; a final check-to-unlink replacement can delete
  the wrong file and still record `completed`. On native POSIX, an eligible
  legal literal-backslash name was deleted and journaled, but the journal
  cannot reopen; audit history also accepts an unpaired writer-recovery
  evidence artifact. #36 records disposable reproductions and narrow fix
  scope. Focused tests passed 333 (three skips); the isolated full suite
  passed 1,510 plus 19 subtests (three skips). WSL audit fsync failure blocked
  use and retry succeeded; no power-loss test was performed. No real media or
  production code changed. **State:** v0.11 retention design blocked on open
  #36; no implementation task was active and no owner action was pending.
  **Next task at that review:** fix #36, then repeat a new
  independent retention gate. #30 stays queued; #8/#13/#28 remain non-blocking
  evidence work. v0.10.0 remains released and v0.11.0 unreleased.
- **Issue #35 corrective implementation complete (2026-09-28):** The private
  executor now carries the planner's coherent whole-root claim snapshot into
  authorization and repeats the same planner after artifact binding; changed
  lifecycle, finalization, controls, recovery, media eligibility, or ownership
  must fail before audit intent. Schema-1 audit history is bound to its canonical
  recording root, freezes older incomplete operations after a new intent, and
  requires the executor's child/control/directory/final-MP4 order and artifact
  shape. Native Windows restored-metadata and synthetic journal regressions pass.
  Focused retention/lifecycle/recovery suites passed 370 (three skips); the final
  isolated full offline suite passed 1,510 plus 19 subtests (three skips). WSL
  `/var/tmp` accepted a valid reopened journal and rejected a foreign-root
  intent; no power-loss validation was performed. No real media was deleted.
  **Next gate:** a NEW fresh-context independent retention executor, lifecycle,
  authorization, and audit safety review. #30 remains queued; #8/#13/#28 remain
  separate non-blocking evidence work. No owner action is pending. v0.10.0
  remains released and v0.11.0 unreleased.
- **Fresh independent retention gate NOT READY (2026-09-28; issue #35 opened):**
  Review of current HEAD `3ff83bc` found that eligibility can change after the
  fresh plan but before authorization: a native Windows synthetic manifest status
  edit with restored size/mtime/ctime/inode made a new plan `needs_attention`, yet
  the private executor deleted the session and recorded `completed`. Existing
  audit history also accepts an earlier operation resuming after a later intent,
  a foreign-root intent, and a falsified final-MP4-first order. #35 contains
  reproductions and the bounded corrective scope. Focused suites passed 253
  (three skips) apart from one transient Windows `os.replace` fixture failure
  that passed on exact rerun; the isolated full suite passed 1,491 plus 19
  subtests (three skips). Native WSL first-use audit reopen and failed-sync
  retry passed; power-loss validation was not performed. No real media was
  deleted or production code changed. **Single next task:** fix #35, then run
  another fresh independent retention gate. #30 stays queued; #8/#13/#28 remain
  separate non-blocking evidence work. No owner action is pending. v0.10.0
  remains released and v0.11.0 unreleased.
- **Issue #34 corrective implementation complete (2026-09-28):** The private
  executor now captures stable byte hashes of each writer-recovery evidence file
  and its referenced retained part under the exclusive lease, validates the
  manifest's recovery proof, and rechecks every surviving proof artifact before
  each unlink. The durable intent records those hashes. Existing audit JSONL
  must now represent coherent schema-1 operations with unique IDs, exact
  artifact order, valid event transitions, and valid completed counts; legitimate
  incomplete crash histories remain readable without repair or resume. Native
  Windows restored-metadata regressions pass before evidence deletion, after
  evidence deletion while its part survives, and after an audit attempt.
  Python 3.11 focused suites passed 211 (one skip); the isolated full offline
  suite passed 1,491 plus 19 subtests (three skips). A native WSL `/var/tmp`
  audit reopen and orphan rejection check passed; power-loss validation was not
  performed. No real media was deleted. **Next gate:** a NEW fresh independent
  review of the corrected executor, lifecycle locking, authorization, and audit
  protocol. #30 remains queued after that gate; #8/#13/#28 remain separate
  non-blocking evidence work. No owner action is pending. v0.10.0 remains
  released and v0.11.0 unreleased.
- **Fresh independent retention gate NOT READY (2026-09-28; issue #34 opened):**
  Review of current HEAD `bcfe38b` found two blockers. On native Windows, a
  same-size writer-recovery evidence byte change with restored timestamps leaves
  artifact metadata unchanged; a fresh plan becomes `needs_attention`, yet the
  executor deletes the final MP4 and records `completed`. Existing audit JSONL
  with an orphan `completed` event or duplicate `intent` operation ID is also
  accepted before a new deletion, so prior history is not reliably
  reconstructable. Issue #34 has the synthetic reproductions and narrow fix
  scope. Focused Windows tests passed 176 (one skip); the isolated full offline
  suite passed 1,456 plus 19 subtests (three skips). Native WSL POSIX first-use
  directory fsync ordering and failed-sync retry passed; power-loss testing was
  not performed. No real media was deleted or production behavior changed.
  At that checkpoint the next task was to fix #34 and repeat the independent
  gate. #30 remained queued; v0.10.0 was released and v0.11.0 unreleased.
- **Issue #33 corrective implementation complete (2026-09-28):** The private
  executor now binds the target claim and control hashes, rechecks surviving
  controls before every unlink, and records their hashes in the intent. Existing
  audit JSONL must be complete and readable before another intent; malformed or
  torn history fails closed without repair. POSIX audit ancestors are synced
  root-to-leaf on every attempt, creating and syncing each new entry before its
  child; the journal entry is synced before use.
  Native Windows restored-metadata regressions and audit fault/retry tests pass.
  Focused retention/planner tests passed 191 (one skip); Python 3.11 focused
  tests passed 54; the isolated full offline suite passed 1,456 plus 19 subtests
  (three skips). A WSL Ubuntu test exercised real POSIX directory fsync order on
  its `/var/tmp` filesystem; power-loss crash validation was not performed. No
  real media was deleted. v0.10.0 remains released and v0.11.0 unreleased.
  At that checkpoint the next gate was a separate fresh independent review of
  the corrected executor, lifecycle lock, and audit protocol.
- **Retention executor gate NOT READY (2026-09-28; issue #33 opened):** Fresh
  independent review of current HEAD `ef4ef30` found three blockers before any
  owner-facing deletion design. On Windows, a same-size target manifest edit
  with restored mtime can change an eligible creator to a protected one after
  authorization; target metadata still matches, so the executor deletes it and
  audits the old creator. A torn existing audit line is accepted for append, so
  the next completed deletion can have an unreadable intent. On first POSIX use,
  the new audit directory's parent entry is not synced, risking loss of the
  journal after durable removals. Two synthetic reproductions passed on native
  Windows; the POSIX finding follows from the current sync order and awaits
  native validation. Focused executor/authorization/audit/lock tests passed 34;
  the isolated full run had 1,436 passing tests plus 19 subtests, three skips,
  and one intermittent unrelated Windows `os.replace` denial that passed on
  targeted rerun. No real media was deleted, and production code was not changed.
  At this checkpoint #33 was the next fix; #30 remained queued. v0.10.0 was
  released and v0.11.0 unreleased.
- **Issue #32 recovery and readiness complete (2026-09-27):** The owner approved
  guarded real recovery/finalization to make both watched accounts ready. The
  service loads fixed code `0d44c5f`; monitoring exactly `eliss4r.n` and `gracie.kf`
  is running with an operational coordinator, both accounts offline, empty
  durable consumed-room/pending-start state, two available slots, no active
  recordings, and storage OK (about 65 GiB free versus the 10 GiB reserve).
  Offline creators report `armed=false/not_applicable` by design; they become
  eligible when a fresh LIVE is observed. The unchanged task-definition SHA-256
  is `CF57505AA9BB57CFEB089D476098F8ECB31C5950EBCC2F4069A92B49F3E8A40C`;
  unauthenticated health remains 401. Two idle/offline restarts and the normal
  targeted stop settled Eliss `f5a33415-d19e-4fbd-91dd-d71724b61cb2`: the first
  restart committed part 50 and its exact writer record; bound lookup could not
  establish the old room, so explicit `user_stop` finalization followed the
  second restart. The job completed at 20:25:18 UTC with resume count zero and
  original room `7689313707369335565`; the manifest truthfully says interrupted,
  50 parts, one writer recovery, and zero discarded source bytes. All 57 immutable
  baseline files, including every Eliss part/crash artifact and Gracie's latest
  completed job/session/output, retained their hashes. The MP4 is 3,290,677,180
  bytes, 720x1280, and 22,018.720 seconds; inspection and full output decode pass.
  **Historical media limitation:** full 50-part `validate --deep` exits 1 for
  unchanged input decode errors in parts 7, 12, 14, 25, 26, 29, and 44; it also
  reports 26 backward-DTS warnings. Input decode health is truthfully degraded
  (103 finalizer H.264 diagnostics); a clean output decode does not prove visual
  repair or identify the original error source. #32 journals the full result.
  At this checkpoint no implementation task or owner action was pending; the
  then-next gate was fresh review of the v0.11 retention executor. #30 remained
  queued after that gate. v0.10.0 was released and v0.11.0 unreleased.
- **Issue #31 production fix complete (2026-09-27):** Windows path/open-handle
  identity comparison now excludes only the incomparable `st_ctime_ns` field.
  Each path and handle still retains its complete pre/post metadata stamp,
  including ctime; regular/reparse protection, other identity fields, exact
  reads, coherent source SHA-256/prefix proof, durable ownership, and conditional
  manifest promotion remain enforced. Both aged native Windows regressions
  reproduced `failed/ambiguous_state` on the previous code under project Python
  3.12.10, then passed for fresh recovery and already-published retry, including
  later persisted-evidence validation. Focused tests passed 192 (two POSIX skips);
  the isolated full offline suite passed 1,436 plus 19 subtests (three platform
  skips). Python 3.11 compatibility passed 38 focused tests (two skips).
  At the production-fix handoff, no real Eliss artifact, durable state, or service
  process had changed. The separately authorized real procedure is tracked above
  and in issue #32. Issue #31 retains the diagnosis and fix evidence. At that
  checkpoint, issue #30 and the v0.11 retention review remained queued/paused;
  v0.10.0 remains released and v0.11.0 unreleased.
- **Gracie monitoring activated; Eliss recovery failed closed (2026-09-25):**
  The owner authorized one restart of the unchanged `TikREC Service` task while
  Eliss was recording. Before restart, slot 1 held session
  `f5a33415-d19e-4fbd-91dd-d71724b61cb2` in room `7689313707369335565`
  with 49 completed parts and 2,687,344,663 reported bytes; slot 2 held an
  older completed Eliss job. The task definition SHA-256 stayed
  `CF57505AA9BB57CFEB089D476098F8ECB31C5950EBCC2F4069A92B49F3E8A40C`.
  The restarted v0.10.0 service reports monitoring `running=true` for exactly
  `eliss4r.n` (live) and `gracie.kf` (offline), with its coordinator operational.
  Startup recovery preserved a 462,154,077-byte part-50 crash evidence file
  and published `part-0050.flv` of identical length and SHA-256. It then failed
  closed: slot 1 reports `recovering/failed/ambiguous_state`, error "invalid or
  conflicting session storage; preserve artifacts", and is unavailable. The
  session manifest still records 49 parts; no resume or final MP4 occurred.
  Slot 2 remains independently completed and available; health reports capacity
  2, available slots 1, active recordings 0, and storage `ok`. No manual media
  repair or second restart was attempted. The earlier idle-only heartbeat is
  paused. **Issue #31 is now the active task:** perform a read-only investigation
  of the preserved startup-recovery evidence, identify the exact ambiguity and
  whether recovery created it, and reproduce any suspected defect offline before
  any repair. Do not describe the Eliss capture as uninterrupted. Issue #30
  remains the queued hot-reload design, and the v0.11 retention review remains
  paused until #31 is triaged.
- **First internal bounded retention executor complete (2026-09-24):** The
  independent foundation review concluded READY TO DESIGN BOUNDED RETENTION
  EXECUTION. An internal one-session executor now takes an exclusive root lease,
  reloads current configuration, replans the whole root, checks both durable
  service slots, binds an exact local artifact allowlist, and revalidates before
  each deletion. A synced schema-1 JSONL intent and per-artifact results live
  outside the recording root. Current completed service-job references block
  deletion. Service and local CLI mutators take compatible writer leases; two
  service slots may share a root. The executor has no CLI/API/automatic cleanup
  caller, does not resume partial operations, and has been exercised only on
  synthetic fixtures. v0.10.0 remains released/package version, v0.11.0 is
  unreleased, and #8/#13/#28 are separate non-blocking evidence work. Next gate:
  fresh independent review of the executor, lifecycle lock, and audit protocol
  before any owner-facing deletion surface. Windows cross-process lease, crash,
  two-slot, audit, and exact-deletion tests passed; the isolated full suite
  passed 1,414 plus 19 subtests (three platform skips). Native POSIX locking
  and real-recording validation were not run on this Windows development pass.
- **Sixth v0.11.0 retention-safety correction complete (2026-09-24):** Fresh
  independent review of `9feafa1` passed the targeted planner/root checks but
  remained NOT READY on one writer-recovery byte-proof coherence blocker.
  Separate source hashing and recovered-prefix comparison could accept a
  same-length mutation between observations and publish a stale source hash.
  Final conditional manifest authorization and persisted-evidence validation
  now share one bounded proof: opened regular artifacts retain their identity
  and metadata while the exact compared source prefix and full source SHA-256
  come from the same source read. Same-length prefix/tail mutations fail before
  manifest publication; the previous manifest remains intact. The planner is
  read-only and advisory; deletion remains unimplemented. v0.10.0 remains the
  released/package version, v0.11.0 unreleased, and #8/#13/#28 remain separate
  non-blocking evidence work. Next gate: another fresh independent safety
  review of the retention foundation and recovery byte proof before any
  destructive retention design. Focused recovery/manifest/retention tests passed
  359 (three skips); the isolated full suite passed 1,378 plus 19 subtests
  (three skips). Unittest discovery passed 228; compilation, 29 CLI help
  paths/version, all 91 package sources under 300 lines, and diff checks passed.
  Native Windows junctions and injected identity/reparse/locality checks passed.
  Native file symlink creation and two POSIX open-file replacement tests skipped
  on this Windows host; native POSIX mounts and a real mapped drive were not run.
- **Fifth v0.11.0 retention-safety correction complete (2026-09-24):** The latest
  fresh independent review of `32de6ed` remained NOT READY on exactly two
  observation-completeness blockers. R1: a claimant created inside a closing
  root enumeration could evade that snapshot; root and child identities now
  bracket the entire closing inventory, with the final root stamp taken only
  after its enumeration and child stamps finish. R2: equal short reads could
  falsely prove a writer-recovery prefix; one shared helper now requires every
  requested byte for both persisted evidence and the final conditional manifest
  guard. Regressions reproduced both failures on `32de6ed`. The planner stays
  advisory and read-only; deletion remains unimplemented. v0.10.0 is the
  released/package version, v0.11.0 is unreleased, and #8/#13/#28 remain
  separate non-blocking evidence work. Next gate: another fresh independent
  safety review before any destructive retention design. Focused retention,
  recovery, and manifest tests passed 353 (one skip); the isolated full suite
  passed 1,372 plus 19 subtests (one skip). Unittest discovery passed 228;
  compilation, 29 CLI help paths/version, all 91 package sources under 300
  lines, and diff checks passed. Native Windows junctions passed; native file
  symlink creation skipped because unavailable. POSIX mount and Windows drive
  classifications passed injected offline tests; native POSIX mounts and a real
  mapped drive were not run on this Windows host.
- **Fourth v0.11.0 retention-safety correction complete (2026-09-24):** Independent
  review of `0089a6d` remained NOT READY on five reproduced gaps. Root claims
  now require an internally bracketed stable inventory; observed control or
  evidence divergence poisons the entire planning call, including after a
  later byte restoration. Every `resolver_error` connection must be
  resolver-only. Linux locality now verifies covering mount ancestry and
  device identity where available. Writer-partial recovery rechecks current
  job, manifest, and source at preservation/publication boundaries, after
  slow media proof, and at a conditional manifest commit. The planner is
  read-only and saved plans never authorize deletion; no deletion executor
  exists. v0.10.0 remains released, v0.11.0 unreleased, and #8/#13/#28 remain
  separate non-blocking evidence work. Next gate: fresh independent safety
  review of this correction before any destructive retention design. Focused
  tests passed 242 (one skip); the isolated full suite passed 1,355 plus 19
  subtests (one skip). Unittest discovery passed 228; compilation, 29 CLI help
  paths/version, all 91 package sources under 300 lines, and diff checks pass.
  Native Windows junctions pass; one native
  file-symlink test skips for unavailable privilege. Linux/macOS mounts and
  Windows drive types are exercised with injected offline evidence; native
  POSIX mounts and a real mapped drive were not tested on this Windows host.
- **Third v0.11.0 retention-safety correction complete (2026-09-24):** Fresh
  independent review of `ccdf9d3` remained NOT READY. Five reproduced blockers
  were unbound control reads after an immutable claim snapshot, impossible
  pre-manifest HTTP/media chronology, incomplete or stacked mount proof and
  nested remote artifacts, retained FLV/writer-evidence reparse acceptance, and
  stale ownership before writer-partial mutation. Inspection now verifies each
  parsed manifest/log read against its exact captured content fingerprint;
  any observed mismatch stays non-eligible even if restored. Retention chronology
  permits only resolver-only failures or a proven first successful resolution
  before manifest start; HTTP/media must follow session initialization. Every
  candidate/output/control/retained artifact needs no-follow and same proven
  local-volume evidence. Writer recovery performs a fresh read-only ownership
  and partial preflight before job or media mutation, then rechecks the manifest
  and recovered source before committing recovery evidence. Generic recovery
  compatibility remains separate. No deletion executor exists, and stale plans
  authorize nothing. v0.10.0 remains released; v0.11.0 is unreleased;
  #8/#13/#28 remain separate and non-blocking. Next: fresh independent safety
  review of this corrected foundation before destructive retention design.
  Verification: 1,323 isolated pytest tests and 19 subtests passed, with one
  native Windows file-symlink test skipped for missing privilege; 228 unittest
  tests, compilation, 29 CLI help paths/version, all 90 package files under
  300 lines, and diff checks passed. Native Windows junction tests passed.
  Linux/macOS mount and Windows mapped-drive classifications passed injected
  offline tests; native POSIX mounts and a real mapped drive were not run.
- **Second v0.11.0 retention-safety correction complete (2026-09-24):** Fresh
  independent review of `99495eb` remained NOT READY. It found changed or
  incomplete claims, whole-root planning races, under-constrained event time,
  a fresh startup-reconciliation creator gap, and output alias/locality gaps.
  The read-only planner now captures immutable bounded claims and a whole-root
  evidence snapshot before inspection, then compares a fresh snapshot before
  publishing eligibility. Missing claims, instability, aliases, ambiguous
  physical identity, and unproven local storage fail closed. Retention-only
  connection/event/outage chronology is stricter; startup reconciliation
  rechecks creator before evidence or job writes. No deletion executor exists;
  stale plans authorize nothing. v0.10.0 remains released, v0.11.0 unreleased,
  and #8/#13/#28 separate/non-blocking. Verification: 1,291 isolated pytest
  tests plus 19 subtests, 228 unittest tests, compilation, 29 CLI help paths
  and version, 89 package sources under 300 lines, and diff checks passed.
  Both native Windows junction tests passed; native file symlink creation
  skipped for unavailable privilege. Mapped-drive and POSIX mount classifications
  passed injected offline tests; no genuine mapped drive was available.
  Next gate: fresh independent review
  of this correction before any destructive retention design.
- **Active v0.11.0 retention safety correction complete (2026-09-23):** Fresh
  independent review of `82f3363` found five blockers: rejected competing
  UUID/output claims could disappear; terminal time could predate durable
  activity; contradictory completed fields could pass; fresh LIVE resume did
  not recheck creator; and Windows junctions could redirect `.parts` outside
  the selected root. The read-only planner now discovers bounded claims before
  eligibility, requires coherent terminal chronology/lifecycle, and rejects
  reparse/symlink redirects. Fresh resume rechecks optional creator before
  writing. Native Windows junction tests ran. No deletion executor or artifact
  mutation was added. Focused tests pass 195 and the final isolated suite passes
  1,238 plus 19 subtests; unittest discovery passes 228, with compilation, 29
  CLI help paths/version, source-size, and diff checks passing. A stale plan is
  never deletion authorization; any future
  executor needs immediate revalidation and separate approval. v0.10.0 remains
  released; v0.11.0 is unreleased. Next: fresh independent review of the
  corrected retention foundation before any destructive design is authorized.
- **Active v0.11.0 retention foundation complete (2026-09-23):** New LIVE
  manifests persist canonical page-derived creator identity; recovery checks it
  against current durable job intent without filling legacy manifests. Strict
  optional protected-creator and age-rule configuration feeds a read-only plan
  over immediate session children. Only proven completed, unprotected sessions
  at or beyond their durable `ended_at` threshold can be marked eligible;
  unknown/conflicting evidence is retained. No artifact cleanup exists, and
  v0.10.0 remains released. Next gate: fresh independent review of this
  eligibility foundation before any deletion executor is authorized.
- **Active v0.11.0 development (2026-09-23):** The first smart-storage slice
  adds a strict configurable automatic reserve (default 10 GiB), a shared
  read-only storage policy, and a sanitized authenticated `/health` summary.
  Warning starts below `max(20 GiB, 2 × minimum)`; blocked starts below the
  minimum. Manual capture, media, and retention remain unchanged. This is
  untagged development on `main`; v0.10.0 remains the current release. Next
  v0.11 work is safe retention policy design and implementation, with any
  destructive action requiring its own bounded safeguards and review.
- **v0.10.0 publication completed (2026-09-23).** The immutable annotated
  `v0.10.0` tag object is `014fa0b785f77c6b42ffe73a86ba28b00126a4ff`
  and peels to the exact independently reviewed candidate
  `dfb81b683a89d01f55d70291fb5cdcfead654976`. The published, non-draft,
  non-prerelease [GitHub Release](https://github.com/lvrdnck/TikREC/releases/tag/v0.10.0)
  is `TikREC v0.10.0` (ID `RE_kwDOUTgsvs4XiIOd`). Its historically scoped
  notes cover two-slot ownership, #27/#29 reliability, the manual Eliss/Sinaloan
  deployed gate, and the offline automatic-selection limit. The tag was not
  moved to this later documentation commit. Package, tag, and Release now make
  v0.10.0 the current released version. #8, #13, and #28 remain open,
  separate, and non-blocking. No LIVE, deployment, or v0.11 work occurred.
- **Previous v0.10 task: untagged release candidate prepared (2026-09-23).** The
  owner-provided final fresh-context review of `a9c172f` concluded READY for
  v0.10 release preparation. The candidate package and checkout now report
  0.10.0; its immutable tag and GitHub Release do not yet exist. The v0.9.0 to
  v0.10.0 delta adds two independent durable recording slots, aggregate status,
  targeted stop, capacity-aware automation, case-equivalent page/room arbitration,
  restored and later-proven owner fallback, and fail-closed ownership of pending
  output/parts paths. #29 adds bounded crash-part recovery and #27 preserves
  truthful retained-input decode health. The deployed Eliss/Sinaloan manual
  second start proved real distinct-LIVE isolation; automatic second-slot
  selection has deterministic offline coverage. Verification passes 280 focused
  and 1,164 isolated pytest tests plus 19 subtests, 223 unittest tests,
  compilation, 24 local CLI
  help paths plus version, and all 78 package sources under 300 lines. An
  isolated build/install smoke passed for `tikrec-0.10.0-py3-none-any.whl`
  (SHA-256 `C5C1E3706381B3CD4A67806B9417FF0A0BD5918FE806AD9D91172000D54898E9`),
  with no dependencies. v0.9.0 remains the current released/tagged/published
  version. Next: independent review of the exact candidate commit before any
  separate tag or GitHub Release authorization; #8, #13, and #28 remain open,
  separate, and non-blocking. No LIVE, deployment, tag, or publication occurred.
- **Previous v0.10 task: pending output/parts ownership corrected; independent
  review subsequently passed (2026-09-23).** Independent review of `0759e6f`
  found that a current pending or restored session could lose its output/parts
  collision guard when rich status failed, while narrow LIVE ownership still
  allowed slot 2 allocation. Five offline manager/API regressions failed on that
  baseline, including real controllers, durable slots, first-read restored
  ownership, and HTTP. Current controller ownership and the manager's
  session-bound cache now include accepted absolute output and parts paths.
  Known paths survive weaker reads, missing current path facts fail allocation
  closed, and settlement/session replacement release old facts. A proven-empty
  corrupt slot remains isolated. The earlier deployed Eliss/Sinaloan
  distinct-LIVE gate remains valid; v0.9.0 is the current release and v0.10.0
  remains unreleased. Release preparation is blocked pending fresh independent
  review of this correction and final readiness. #8, #13, and #28 remain
  separate non-blocking evidence work. Focused tests pass 242; isolated pytest
  passes 1,164 plus 19 subtests; unittest discovery passes 223. Compilation,
  24 CLI help paths plus version, and all 78 package sources under 300 lines pass.
- **Previous v0.10 task: first-read unknown ownership corrected; independent
  review found a pending-path gap (2026-09-23).** Fresh independent review of
  `4dbcf45` found that an unreadable rich status and narrow ownership snapshot,
  with no cached
  owner, could leave slot 2 available when health reported `ambiguous_state` or
  health itself failed. Offline real-controller active and blocked-recovery
  regressions failed on `4dbcf45`. The manager now treats this state as unknown
  and suppresses all new allocation until a healthy read proves availability or
  identifies the owner. A reliable narrow `current=false` still lets a truly
  empty corrupt slot remain isolated, and capacity recovers after transient
  reads heal or the owner settles. Three new manager tests and four cache tests
  cover the boundary, including invalid current snapshots after an earlier
  available-health or settled-status read; 166 focused tests and 1,151 isolated
  pytest tests plus 19 subtests pass. Unittest discovery passes 223; compilation,
  24 CLI help/version paths, and all 78 package sources under 300 lines pass.
  No LIVE, media, schema,
  expected-room persistence, or #29 recovery behavior changed. The deployed
  Eliss/Sinaloan distinct-LIVE gate remains valid. v0.9.0 is the current release;
  v0.10.0 preparation remains blocked pending fresh independent review of this
  correction and final readiness. #8, #13, and #28 remain separate non-blocking
  evidence work.
- **Previous restored/learned ownership correction: independent review found a
  first-read unknown-owner gap (2026-09-23).** Independent review of `2e1002c`
  found that a restored current controller was absent from the new manager's
  `_owners` cache, and a manual job's later proven room was not added to its
  fallback. If rich status became unreadable at allocation, either case could
  accept a duplicate in slot 2. Five manager regressions and one end-to-end
  automation regression failed on `2e1002c`. Each controller now exposes only
  current session/page/proven room under its lock; the manager refreshes a
  session-bound in-memory cache under its allocation lock. Partial reads retain
  known facts, and settlement and session replacement release old claims. Its
  intended bounded `RecordingBusy` fallback missed the first-read condition
  corrected above. The automatic expected-room reservation stays
  memory-only; no unproven room or cache is persisted. Focused tests pass 133;
  the isolated full suite passes 1,144 plus 19 subtests. Unittest discovery
  passes 223; compilation, 24 CLI help/version paths, all 78 package sources
  under 300 lines, and diff checks pass. No LIVE or media was touched. The deployed
  Eliss/Sinaloan isolation gate remains valid for distinct LIVEs. Release
  preparation remains blocked until fresh independent review of this correction
  and final v0.10 readiness. #8, #13, and #28 remain separate non-blocking
  evidence work.
- **Previous mixed-case page ownership correction: independent review found a
  restored/learned fallback gap (2026-09-23).** Fresh review of `b309135` found
  that a resolving manual `@Alpha/live` job could coexist with an automatic
  `@alpha/live` job because both readable status and the manager's in-memory
  owner fallback compared page spelling case-sensitively. Seven focused offline
  regressions failed on `b309135`, including real-controller automation,
  direct/API starts, unreadable status, and a loaded mixed-case durable job.
  The manager now compares a lowercase identity derived only from an already
  accepted normalized public page; controller and durable source URLs retain
  their original spelling. The previous atomic expected-room reservation and
  duplicate-claim cleanup remain unchanged. An unproven expected room need not
  be persisted and is not a release blocker. All 120 focused tests and the
  isolated full suite (1,131 tests plus 19 subtests) pass; unittest discovery
  passes 223, compilation and 24 CLI help/version paths pass, all 77 package
  sources remain under 300 lines, and diff checks pass. No LIVE or media changed.
  The deployed two-slot isolation gate passed for distinct LIVEs. v0.10 release
  preparation remains blocked until fresh independent review of this correction
  and final refreshed readiness on current `main`. #8, #13, and #28 remain
  separate, non-blocking evidence work.
- **Previous duplicate-start correction: independent review found a further
  case-equivalent bypass (2026-09-23).** An independent fresh-context review of
  `94f3191`
  found that capacity 2 could start a monitored LIVE in slot 2 while a manual
  same-page job in slot 1 was still resolving with `room_id=null`; two monitored
  handles observed in one canonical room could likewise fill both slots before
  either worker published identity. Offline real-controller regressions reproduced
  the manual race before correction. The manager now rejects duplicate current
  normalized pages and atomically reserves an automatic expected room for its
  current session. Automation clears a duplicate candidate's pending claim,
  reports fixed suppression, and continues to another eligible creator. The
  three new real-controller race regressions failed on the old code and passed
  after correction. The isolated full suite passes 1,124 tests plus 19 subtests;
  unittest discovery passes 223, compilation and 24 CLI help/version paths pass,
  and all 77 package sources remain under 300 lines. No new LIVE or media change
  was needed for this allocation/automation correction. The
  deployed two-slot isolation gate below passed and remains valid; it did not
  exercise this automatic-selection race. v0.10.0 release preparation remains
  blocked until a fresh independent review of the corrected `main` and regression
  impact. #8, #13, and #28 remain separate, non-blocking evidence work.
- **v0.10 deployed two-slot isolation gate completed on 2026-09-23; independent
  fresh-context review found the separate duplicate-start blocker.** The owner manually started authorized
  `sinaloanprincess` through the normal authenticated remote CLI, while the
  original automatically started and #29-recovered Eliss session kept recording.
  At 09:07:09--09:07:27 UTC the service reported capacity 2, `active_count=2`,
  `available_slots=0`, and stable distinct identities/paths: Eliss session
  `349adec0-b203-499b-bb05-444e3a99240d`, room `7688598578159274765`,
  slot 1, grew from 454,379,854 to 456,704,297 bytes; Sinaloan session
  `a8738177-43cc-41d3-8986-aff79296d14d`, room `7688642728217479950`,
  slot 2, grew from 27,309,223 to 29,775,146 bytes. Aggregate status exposed
  both; singular `remote status` and empty `remote stop` each returned expected
  HTTP 409 without stopping either. Sinaloan's explicit UUID stop alone set
  her `stop_requested=true`. At 09:08:06 slot 2 was `finalizing` while Eliss
  remained `recording`, `stop_requested=false`, with the same room/session/paths.
  Eliss grew from 459,921,415 bytes before the targeted stop to 461,786,659
  during Sinaloan finalization, 463,152,924 as Sinaloan completed, and
  470,514,781 after that completion. No cross-slot state/path/progress leak was
  observed. Sinaloan's completed job and intentionally interrupted-by-stop
  manifest retained two parts (33,840,512 bytes), a 41,323,977-byte H.264/AAC
  720x1280 MP4 (262.900 seconds), and `clean` input-decode health in manifest
  and service. Retained-session, standard MP4, and deep MP4 checks all pass.
  Eliss was then stopped by her explicit UUID; her job completed, with nine
  retained parts (471,842,611 bytes), a 516,885,748-byte H.264/AAC 720x1280
  MP4 (3,735.707 seconds), and `degraded` input-decode health (29 bounded H.264
  diagnostics). Her retained-session check fails on H.264 errors in parts 3/5
  and reports DTS warnings in part 8; these parts all predate Sinaloan's start.
  Part 8's connection log records the timestamp replay before 08:52:58 UTC;
  Sinaloan started at 09:03:35 UTC. No finding names overlap-era Eliss part 9.
  Eliss standard and deep MP4 validation pass. These pre-overlap retained-media
  findings remain honestly reported and are not evidence of a two-slot defect;
  their exact source attribution is not established by this non-raw capture.
  The #29 crash evidence remains 31,380,072 bytes with SHA-256
  `976633B298C1527301A4846B9BA5A337D70CE331BBFE4544C738C4CAAA11391E`;
  recovered part 7 remains 31,247,682 bytes with SHA-256
  `D964C5BFA28F4AB53168AAF65C59C7BC80D2EADDD0CF94C2E55A72DFB551C77C`.
  The manifest still records 132,390 discarded bytes, same session/room,
  `resume_count=1`, and now three connections after finalization. Both durable
  jobs remained completed in their own slots with distinct outputs/parts;
  automation retained Eliss's consumed room and no pending claim from the
  manual Sinaloan start. One authorized restart of the unchanged idle Scheduled
  Task reloaded capacity 2, both completed jobs, and the exact Phoebe/Eliss
  monitoring pair without relaunching either. The task-definition SHA-256
  remained `CF57505AA9BB57CFEB089D476098F8ECB31C5950EBCC2F4069A92B49F3E8A40C`;
  all 18 settled output/parts/evidence files matched pre-restart hashes;
  unauthenticated health/recordings each returned 401, and authenticated
  aggregate status exposed no bearer, cookie, or signed transport. Focused
  tests pass 238,
  isolated pytest passes 1,114 plus 19 subtests, unittest discovery passes 223;
  compilation, 24 CLI help paths/version, under-300-line package sources,
  and diff checks pass. The implementation team's earlier review found no
  demonstrated isolation, media-health, security, or scope blocker; the
  independent ownership finding above supersedes its readiness conclusion. The owner-manual
  second start proves real concurrency/isolation, not automatic second-slot
  selection; deterministic offline capacity tests and earlier deployed
  automatic-start evidence cover that separately. No version bump, tag,
  publication, or v0.11 work occurred. A separate independent fresh-context
  review of the full v0.10 and #29 delta is required before release preparation.
- **Active v0.10 two-slot gate: PARTIAL checkpoint on 2026-09-23.** From
  current `main` at `93c53e6`, authenticated health showed capacity 2,
  `active_count=1`, `available_slots=1`. Eliss's original recovered session
  `349adec0-b203-499b-bb05-444e3a99240d`, room `7688598578159274765`,
  remained in slot 1 with `resume_count=1`, no error or stop request; progress
  grew from 386,389,480 to 397,170,827 bytes. Slot 2 held only the historical
  completed Phoebe job. Monitoring still listed exactly Phoebe (offline) and
  Eliss (LIVE/same-room suppressed). Fresh public resolution at 08:59:19 UTC
  found newly owner-authorized `sinaloanprincess` trustworthy LIVE in room
  `7688642728217479950`, status 2, `hd1`/`flv_pull_url`. The selected unused
  output was
  `C:\Users\Leandro\Videos\sinaloanprincess-v010-overlap-20260923-085920Z.mp4`.
  The single normal authenticated `remote start` attempt was rejected by
  automatic command review before execution with only `blocked by policy`.
  Read-only follow-up at 08:59:46 UTC still showed only Eliss active, slot 2
  free, and both proposed output/parts paths absent. No TikREC start failure,
  second session, media, claim, stop, restart, or configuration change occurred.
  The exact normal PowerShell command was supplied to the owner for manual
  execution only while Eliss remains active, slot 2 remains free, and Sinaloan
  remains trustworthy LIVE. If the owner starts her, first inspect aggregate
  recordings and use the real sessions; never issue a duplicate start. The
  two-active, ambiguity, targeted-isolation, dual-media, idle-restart, and
  final readiness gates remain outstanding. No tests were rerun in this
  no-code checkpoint; the preceding `93c53e6` checkpoint records 1,114
  isolated pytest passes plus 19 subtests and 223 unittest passes. The
  independent fresh-context review remains after the deployed gate and before
  any v0.10 release preparation. #29 is closed; #8/#13/#28 stay separate and
  non-blocking.
- **Active v0.10 deployed two-slot gate: PARTIAL checkpoint on 2026-09-23.**
  GitHub `main` was current at `3960007`; #29 was closed, and #8/#13/#28
  remained separate non-blocking issues. Authenticated health reported capacity
  2 with Eliss session `349adec0-b203-499b-bb05-444e3a99240d` in slot 1,
  same room `7688598578159274765`, `resume_count=1`, recording without error,
  and slot 2 available with the historical completed Phoebe job. Eliss service
  progress grew from 286,220,513 to 327,732,701 bytes; its active part 8 grew
  from 38,871,761 to 93,948,583 bytes. Monitoring continued to list exactly
  Phoebe (offline) and Eliss (LIVE/same-room suppressed). Public resolution
  found owner-authorized `tomwhoasmr` trustworthy LIVE at 08:46:44 UTC in room
  `7688596234675800849`, status 2, `hd1`/`flv_pull_url`. Two attempts to invoke
  the normal authenticated `remote start` CLI, first with precondition checks
  and then as a single command, were rejected before process execution by
  automatic command review with only `blocked by policy` stated. No Tom session,
  output, parts directory, or automation claim was created; the service was not
  restarted, reconfigured, or stopped. A fresh public check at 08:51:59 UTC
  returned explicit status 4/offline for Tom's same room, so the overlap window
  ended without a legitimate second recording. No two-active, ambiguity,
  targeted-stop, dual-media, or idle-restart acceptance was possible. Focused
  offline tests passed 160/160; isolated pytest passed 1,114 plus 19 subtests;
  unittest discovery passed 223; compilation, CLI help/version, source-size,
  and diff checks passed. The v0.10 delta was surveyed from tagged v0.9.0,
  but deployed readiness and the independent fresh-context review remain
  outstanding. **Safe resume:** while Eliss remains active, recheck both slots
  and a newly trustworthy LIVE owner-authorized second creator. Use a permitted
  normal authenticated CLI path for real overlap; do not manufacture a LIVE,
  stop Eliss alone, or restart the active service. If command review still
  blocks the start, obtain an operator-executed normal CLI action or wait for a
  configured creator's natural automatic start. Do not proceed to release
  preparation.
- **Issue #29 deployed acceptance completed on 2026-09-23; v0.10 two-slot
  gate is next.** Immediately before the one authorized restart, public
  resolution found `eliss4r.n` trustworthy LIVE in the original room
  `7688598578159274765` (status 2, `hd1`/`flv_pull_url` at 08:37:04 UTC).
  All 11 fingerprinted originals matched their earlier SHA-256 values,
  including the 31,380,072-byte seventh writer partial
  (`976633b298c1527301a4846b9ba5a337d70ce331bbfe4544c738c4caaa11391e`).
  The unchanged `TikREC Service` task was restarted once; its definition hash
  remained `CF57505AA9BB57CFEB089D476098F8ECB31C5950EBCC2F4069A92B49F3E8A40C`.
  Running code came from editable `main` at `d6cf214` (package version 0.9.0).
  Startup preserved the exact original partial as
  `.tikrec-writer-crash-349adec0-b203-499b-bb05-444e3a99240d-part-0007.evidence`
  with the same size/hash, and published only the parser-proven 31,247,682-byte
  `part-0007.flv` (SHA-256 `D964C5BFA28F4AB53168AAF65C59C7BC80D2EADDD0CF94C2E55A72DFB551C77C`).
  Its bytes match exactly the evidence prefix; the excluded 132,390 bytes are
  all zero. The manifest records source hash/bytes, recovered bytes, and
  discarded bytes; prior parts 1--6 retained their hashes. Part 7 passes
  TikREC structure, full decoder/DTS validation without findings, and H.264/AAC
  media inspection (640x1280, 230.567 seconds). Durable `job.json` and manifest
  still bind session `349adec0-b203-499b-bb05-444e3a99240d` to the same room
  and output, with `resume_count=1`, `connection_count=2`, and the next fresh
  `.part-0008.flv.partial`. Its observed size grew from 7,060,143 to
  20,413,648 bytes; service progress grew from 229,700,846 to 240,051,227
  bytes. `connections.jsonl` has two service-recovery boundaries and one
  `capture_resume` for connection 2/part 8, without a synthetic downtime
  connection. Health is capacity 2, active 1, available 1; slot 2's completed
  Phoebe job and hash remain unchanged. Monitoring lists exactly Phoebe and
  Eliss; the consumed same-room automation state suppresses duplicates.
  Eliss remains actively recording, so terminal finalization and final MP4
  validation were not part of this bounded recovery acceptance. No second
  restart or stop was performed. The all-zero tail after the unexpected reboot
  most strongly fits interrupted buffered/filesystem writing; a normal writer
  defect is unproven.
- **Historical #29 pre-deployment checkpoint:** Two independent public checks at 08:17:53 and
  08:18:12 UTC on 2026-09-23 resolved `eliss4r.n` as LIVE, status 2, room
  `7688598578159274765`, `hd1` via `flv_pull_url`. This is the exact interrupted
  session's room: the same LIVE survived the unexpected reboot while TikREC
  failed to resume it. On a disposable copy, all 11,164 FLV tags through byte
  31,247,682 parse correctly; the remaining 132,390 bytes are entirely zero,
  so the next zero header/trailer is implausible and no later tag can be proven.
  The prefix starts with its own AVC configuration and rebased video keyframe,
  passes TikREC structure plus FFprobe full decode/DTS with no findings, and
  probes as H.264/AAC, 640x1280, 230.567 seconds. The all-zero tail following
  an unexpected reboot most strongly supports an interrupted buffered/filesystem
  write, but raw source and low-level storage evidence are absent; a writer defect
  is not proven. Issue #14's proven-prefix principle now also stops at the first
  malformed tag, never scans forward, preserves the original, and still requires
  existing ownership, structure, decoder, and DTS gates. A controlled copied
  session with a fake same-room resolver preserved the original
  31,380,072-byte SHA-256, published exactly 31,247,682 validated bytes,
  recorded 132,390 discarded bytes, and reached `resuming` with the original
  session/room; it opened no media. Focused recovery tests pass (83), isolated
  pytest passes 1,114 plus 19 subtests, unittest discovery passes 223, and
  compilation/changed-source-size checks pass. The live service was not
  restarted or changed: slot 1 remains failed closed, all 11 existing original
  job/automation/manifest/media files rehashed unchanged (the connection log
  was absent before and after), and same-session deployed recovery is **not yet
  proven**. Do not
  resume the v0.10 two-slot gate inside issue #29.
- **Previous #29 discovery checkpoint:** On 2026-09-23, Eliss was no longer
  active. Windows booted at 09:49:45 local after an unexpected shutdown
  (System event 6008); the unchanged `TikREC Service` task ran at 09:51:02.
  Authenticated health showed capacity 2, `active_count=0`, `available_slots=1`:
  `slot-1` was unavailable with `recovering/failed/ambiguous_state`; `slot-2`
  retained its historical completed Phoebe job. Durable `job.json` and the Eliss
  manifest still identify session `349adec0-b203-499b-bb05-444e3a99240d`, room
  `7688598578159274765`, as recording/pending finalization; `job-2.json` and
  automation's consumed Eliss room/no pending claim remain coherent. Six
  completed Eliss FLV parts and a 31,380,072-byte `.part-0007.flv.partial` are
  retained; no final MP4 exists. Read-only startup inspection rejected the
  partial's FLV framing: 11,164 valid tags end at byte 31,247,682, where
  `PreviousTagSize` mismatches, with 132,390 bytes remaining. Its SHA-256 is
  `976633b298c1527301a4846b9ba5a337d70ce331bbfe4544c738c4caaa11391e`.
  The cause of the malformed bytes is unproven; the fail-closed recovery policy
  preserved all artifacts. The task definition hash stayed
  `CF57505AA9BB57CFEB089D476098F8ECB31C5950EBCC2F4069A92B49F3E8A40C`;
  the task-visible configuration still monitors exactly Eliss/Phoebe with
  `C:\Users\Leandro\Videos` as output. A fresh public resolver found newly
  owner-authorized `tomwhoasmr` LIVE in room `7688596234675800849`, status 2,
  `hd1` FLV, but Tom was **not** started because Eliss was not active and no
  second live recording existed. No targeted stop, dual validation, or idle
  persistence test was possible. Issue #29 records the recovery investigation;
  preserve all original media/job evidence and do not restart or reconfigure the
  service to force this session to resume. The owner now permits an explicit
  manual Tom start as real two-slot isolation evidence only when Eliss is active
  and slot 2 is free; do not claim this proves automatic second-slot selection.
- **Previous v0.10 natural-overlap checkpoint:** On 2026-09-23,
  two public resolver checks found `eliss4r.n` LIVE in room
  `7688598578159274765`, while `phoebelightt` and `moealkaf` were explicitly
  offline. Eliss and Phoebe were selected: Phoebe had two recent natural
  automatic sessions and a fresh trustworthy offline monitor baseline. The
  task-visible configuration now contains exactly those two creators and keeps
  `C:\Users\Leandro\Videos` as output storage. Desktop `%APPDATA%` writes were
  redirected: two safe idle restarts initially loaded only Phoebe despite the
  interactive CLI listing both. The documented normal CLI `--config` path
  `\\127.0.0.1\C$\Users\Leandro\AppData\Roaming\TikREC\config.json`
  exposed the task-visible Phoebe-only file; adding Eliss there and restarting
  the unchanged task while both slots were idle loaded the exact pair. The task
  definition SHA-256 stayed
  `CF57505AA9BB57CFEB089D476098F8ECB31C5950EBCC2F4069A92B49F3E8A40C`.
  The first ordinary cycle automatically started Eliss session
  `349adec0-b203-499b-bb05-444e3a99240d` in `slot-1` without manual start.
  Through completed cycle 11, Phoebe remained offline, Eliss remained LIVE,
  and its retained-byte progress grew from 936,181 to 46,843,763. Capacity is
  2 with `active_count=1` and `available_slots=1`; `slot-2` still holds its
  historical completed Phoebe job. Durable `job.json` binds the Eliss room,
  session, and unique output/parts paths; `job-2.json` remains unchanged;
  `automation.json` has the consumed Eliss room and no pending claim. Missing
  bearer authentication returns 401, status exposes no unsafe marker, and the
  task definition is unchanged. No genuine overlap occurred, so targeted stop,
  dual-media validation, and final idle-restart readiness remain untested.
  **Do not restart or stop the active Eliss recording.** Issue #27 is closed;
  #28, #8, and #13 remain non-blocking. No v0.9.1 or v0.10 release action is
  warranted by this partial gate.
- **Historical v0.10 gate (superseded by #27):** The first bounded v0.10.0
  multiple-recording slice is
  implemented and deployed from `dd00400`; its natural simultaneous-LIVE gate
  remains outstanding but is now paused. v0.9.0 remains
  published and synchronized across package metadata, its immutable annotated
  tag, and its GitHub Release. The v0.9 primary deployed-service gate passed on
  2026-09-22 with
  owner-authorized `westvlammer`:
  monitoring found one canonical room, automatic recording started without a
  manual start, retained/final media validated, the same room was suppressed,
  durable state survived an idle task restart, and a natural explicit-offline
  cycle then re-armed the creator without a duplicate session or output. The
  v0.9 deployed configuration contained only `westvlammer` and
  `C:\Users\Leandro\Videos`. The current unchanged Scheduled Task now runs the
  editable v0.10 development checkout at `dd00400` while package version remains
  0.9.0. The first deployed attempt configured `westvlammer` and `lilymaye207`;
  five bounded complete-cycle checkpoints found both naturally offline, so no
  automatic session or media was created. The second deployed attempt configured
  exactly owner-authorized `ranaerose7` and `moealkaf`, with the same output
  directory. `moealkaf` was naturally LIVE in room
  `7688395628493949717` and automatically started session
  `c7927922-0381-410d-8020-0272aa96f265` in `slot-1`; `ranaerose7` remained
  unverifiable through the bounded overlap window, so `slot-2` stayed available
  and the simultaneous gate did not begin. While that legitimate recording
  remained active, the host-visible persisted configuration was safely staged to
  exactly `moealkaf` and newly authorized `phoebelightt`. The running service was
  initially left on its old in-memory `ranaerose7`/`moealkaf` snapshot while the
  recording remained active. That session later ended naturally and finalized:
  788,464,216 retained bytes in one FLV over 5,886.833 seconds, two connections,
  one reconnect, `room_ended`, and no interruption, startup recovery, job/finalization
  error, or stop request. A 16.109-second transient network-recovery episode
  confirmed offline at the end; the earlier "no recovery" wording was incorrect.
  Its 787,935,979-byte, 6,250.443-second H.264/AAC MP4
  passes standard validation, but retained-session and deep MP4 validation both
  fail on extensive matching H.264 decoder errors. The connection evidence has
  zero timestamp replays and raw copy was disabled, so this does not resolve or
  reclassify opportunistic issue #8; all evidence remains preserved. Once both
  slots were idle, the unchanged task restarted once with its definition hash
  preserved and loaded exactly `moealkaf`/`phoebelightt`. Authentication,
  sanitization, capacity 2, durable completed slot 1, absent/idle slot 2, and
  empty pending/consumed automation state all remained coherent. Six completed
  cycles through cycle 7 found both creators explicitly offline, so no overlap,
  new session, relaunch, or output occurred. Historical v0.9 release checks
  passed; #27 now requires investigation of possible shared-path exposure.
  v0.9.0 remains the synchronized current release. v0.10.0 is a paused
  development target;
  its two-slot architecture, deployed idle/status path, one-slot natural
  completion, and idle restart are proven, but valid simultaneous recording,
  targeted isolation, dual-output validation, and completion/readiness work
  remain. Issues #8 and #13
  remain open, paused/non-blocking, and opportunistic.
- **Completed first v0.8 configuration slice:** Strict schema-1 JSON configuration
  now lives at `%APPDATA%\TikREC\config.json` on Windows or the POSIX XDG config
  location, with an explicit global `--config FILE` override and atomic writes.
  `config show/path/set/unset` manages the first setting, `output_directory`.
  Relative local `live`/`record` outputs use it; absolute outputs bypass config,
  missing config keeps CWD-relative behavior, and traversal outside the configured
  base fails closed. Remote, finalize, recover, service state, and retained-session
  paths are unchanged. Automatic naming plus retry, validation, and logging
  defaults remain queued v0.8 work; v0.7.0 remains the current released version.
- **Completed second v0.8 automatic-naming slice:** Local manually started `live`
  now permits omitted output only when `output_directory` is configured. It uses
  a locally parsed/sanitized public creator handle plus an injectable one-second
  local timestamp and bounded deterministic collision suffix, keeping output and
  `.parts` direct children of configured storage. Explicit outputs retain first-
  slice precedence and are never renamed; `record`, remote, finalize, recover,
  service, and retained sessions are unchanged. Filename templates and retry,
  validation, and logging defaults remain queued; v0.7.0 remains released.
- **Completed third v0.8 recovery-default slice:** Strict schema-1 configuration
  optionally persists an integer `recovery_window_seconds` from 60 through 3600.
  Local `live` and `serve` use CLI override, configuration, then the unchanged
  900-second built-in default. The service snapshots the selected policy at
  startup and applies it to both active and startup recovery; outage status
  reports the selected window. Retry delays/cap, retry classification, room-end
  confirmation, output handling, direct `record`, remote/API behavior, and prior
  configuration compatibility remain unchanged. Restart is required after a
  service configuration change. Validation and logging defaults remain queued;
  v0.7.0 remains released.
- **Completed fourth v0.8 validation-default slice:** Strict schema-1
  configuration optionally persists `validation_mode` as `standard` or `deep`
  for the explicit `tikrec validate` command. Mutually exclusive `--deep` and
  `--standard` overrides take precedence without reading configuration;
  otherwise configuration precedes the built-in standard default. Validation
  semantics and reports are unchanged, retained FLVs still receive their full
  decoder/DTS checks in either mode, and deep completed-output validation still
  decodes the full artifact. Guided recovery validation and both finalization
  safety checks remain explicitly standard and do not inherit the preference.
  Focused coverage passes 93 tests, the full offline suite passes 908 tests plus
  19 subtests, and unittest discovery passes 210 tests. Logging defaults remain
  queued; v0.7.0 remains released.
- **Completed fifth v0.8 logging-default slice:** Strict schema-1 configuration
  optionally persists boolean `debug_tracebacks`, which controls only whether an
  unexpected CLI exception includes its Python traceback. Explicit mutually
  exclusive `--debug`/`--no-debug` overrides win without configuration I/O;
  otherwise configuration is read lazily only after an unexpected exception,
  with built-in false preserving prior behavior. Known errors, successful
  commands, progress/warnings, service request-log suppression, remote/API and
  media behavior, and sensitive-data boundaries are unchanged. Focused coverage
  passes 98 tests, the full offline suite passes 921 tests plus 19 subtests, and
  unittest discovery passes 215 tests. This completes the intended v0.8
  configuration/default scope. At slice completion, v0.7.0 remained released
  and v0.8.0 had not yet been prepared, tagged, or published.
- **Released v0.8 configuration/defaults:** Package metadata reports v0.8.0. A
  combined review found the five configuration/default slices coherent: strict
  schema-1 validation is preserved; explicit CLI choices retain precedence;
  unrelated commands avoid configuration I/O where designed; absent settings
  retain prior behavior; and remote/API, media, codec, part-boundary, and
  finalization behavior remain unchanged. Verification passes 182 focused tests,
  all 921 offline tests, and 215 unittest-discovery tests. Compilation, 14 CLI
  help paths, CLI version output, and an isolated built-wheel/install smoke test
  pass. The wheel metadata and `tikrec` entry point are correct for
  `tikrec-0.8.0-py3-none-any.whl` (SHA-256
  `E87C6283CB43744D279332798E63B5D9532C36F17F7EE387B36B64C0742DFE4C`).
  One initial focused run encountered `WinError 5` while pytest scanned its
  shared temp root, before affected tests ran; fresh isolated temp roots passed
  focused and full runs, and no TikREC `os.replace` failure reproduced. No new
  real-media run is required because v0.8 changes configuration/default
  selection only, not media handling; existing capture, recovery, finalization,
  and validation evidence remains applicable. Final publication verification
  repeated all 921 offline tests, 215 unittest-discovery tests, compilation, 14
  CLI help paths, CLI version output, and the isolated built-wheel/install smoke
  test. The immutable annotated tag and GitHub Release are now synchronized.
- **Completed first v0.9 creator-monitoring slice:** Strict schema-1
  configuration optionally persists an ordered, unique tuple of canonical
  lowercase public TikTok handles. `monitor add/remove/list` accepts a bare
  handle, `@handle`, or standard public LIVE URL and normalizes it entirely
  offline. Duplicate additions and absent removals fail clearly; an absent
  configuration lists no creators; existing v0.8 settings and atomic writes are
  preserved; and `output_directory` is not required. List order is deterministic
  but is not scheduling priority. No polling, detection loop, recording,
  disk-space check, notification, or concurrency behavior exists yet.
  Verification passes 139 focused tests, all 960 offline tests, and 215
  unittest-discovery tests, plus compilation, CLI/help parsing, source-size
  checks, and an add/list/remove smoke using an isolated configuration file.
- **Completed second v0.9 creator-monitoring slice:** The persistent service now
  snapshots configured creators at startup and observes them with one independent
  read-only worker. It polls promptly, sequentially in configured order, and 30
  seconds after each completed non-overlapping cycle. Thread-safe memory-only
  observations remain conservative: only structured LIVE identity becomes
  `live`, only `TikTokOfflineError` becomes `offline`, and every network,
  access, malformed, missing-identity, or unexpected outcome remains `unknown`
  with a fixed safe category. LIVE status retains canonical room ID but never
  signed transport. Authenticated `GET /monitoring` and `remote monitor-status`
  expose sanitized status/cycle timing. Monitoring remains independent of manual
  recording and is cooperatively stopped on service shutdown. No automatic
  recording, output creation, disk policy, notification, schema persistence, or
  multi-recording behavior exists yet. Verification passes 179 focused tests,
  all 974 offline tests plus 19 subtests, 215 unittest-discovery tests,
  compilation, CLI/help checks, and source-size checks. No real-LIVE recording
  applies because the slice records no media; resolver outcomes and timing were
  exercised with deterministic injected offline tests.
- **Completed third v0.9 admission/storage slice:** A separate service-owned
  admission component now enriches each monitoring-status snapshot from current
  controller and storage state without selecting or starting a recording.
  Non-LIVE observations are not applicable; every unavailable controller state
  safely skips a LIVE; missing/unavailable storage, less than the built-in
  10 GiB floor, and bounded naming exhaustion use fixed blocked reasons. Ready
  status reuses creator/timestamp naming and exposes collision-safe candidate
  output/parts paths plus safe byte facts. A not-yet-created output directory is
  assessed at its nearest existing parent, and admission creates/reserves
  nothing, persists nothing, and does not affect manual recording or recovery.
  The service snapshots `output_directory` with creators; under an explicit
  recovery override, unrelated known validation/debug preferences remain lazy
  while strict JSON/schema/unknown-field and service-needed settings validation
  remains intact. Verification passes 136 focused tests, all 1,015 offline tests
  plus 19 subtests, 215 unittest-discovery tests, compilation, CLI/help, and
  source-size checks. No real-LIVE/media check applies because no recording or
  media behavior changed. Automatic recording still does not start.
- **Completed fourth v0.9 automatic-start/re-arm slice:** A separate service-
  owned coordinator consumes only complete monitoring cycles and makes at most
  one automatic attempt. It refreshes admission/candidate naming immediately
  before start, applies a canonical-handle lexical tie-break to simultaneous
  ready LIVEs, and preserves controller authority for the single slot and path
  collisions. Automatic capture freshly proves the monitor's canonical room ID
  before session/media creation; manual/API starts remain unbound and compatible.
  Accepted creator/room pairs are durably suppressed across completion, failure,
  manual stop, and restart until explicit offline or a different room re-arms
  them. Strict atomic `automation.json` state and a pending claim reconcile the
  controller-start crash window; corrupt, unwritable, or ambiguous state disables
  only automatic starts and preserves manual/read-only service operation.
  Monitoring status exposes only fixed safe operational, selection, armed,
  suppression, failure, output, and session facts. Notifications, concurrent
  recordings, retention, configurable storage thresholds, authenticated TikTok,
  and v0.10 behavior remain out of scope. No suitable owner-authorized public
  LIVE was identified during implementation, so deployed natural automatic-
  start/re-arm validation remains outstanding rather than being manufactured.
  Focused verification passes 99 tests; a clean full run in an explicit fresh
  non-checkout temp root passes all 1,069 offline tests plus 19 subtests;
  unittest discovery passes 215 tests; and
  compilation, 14 CLI help paths, version output, diff, and source-size checks
  pass. Checkout-local isolated roots intermittently hit the known Windows
  `os.replace` `WinError 5` in varying unrelated manifest tests after 1,065+
  passes; the non-checkout full run and focused automation-state persistence
  tests did not reproduce it.
- **Bounded v0.9 deployed-service readiness pass:** Before deployment, the
  existing service reported a completed, error-free prior job and no unresolved
  recovery/finalization; `automation.json` did not yet exist. The idle Scheduled
  Task alone was stopped, current `main` was installed into its existing `.venv`,
  and the same task was restarted without changing its action, token, bind,
  firewall, recovery, or storage architecture. Deployed health now reports
  version 0.8.0, `available=true`, `active=false`; authenticated monitoring is
  operational and safely reports zero configured creators and no selected or
  started automatic job. Because `%APPDATA%\TikREC\config.json` is absent, this
  pass could not observe automatic start, room binding, output/finalization,
  durable same-room suppression, restart persistence, or natural re-arm. That is
  an evidence limitation rather than a demonstrated correctness defect, but the
  required automatic-start/output/suppression gate remains unmet, so v0.9.0 is
  not yet a release-preparation candidate. A unique non-checkout temp root passes
  all 1,069 offline tests plus 19 subtests; unittest discovery passes 215 tests;
  compilation, CLI/help/version, diff, and strict under-300-line source checks
  pass. An initial shared-temp full run was interrupted after widespread Windows
  temp setup errors; the clean isolated run did not reproduce a TikREC failure.
- **Configured v0.9 deployed-validation continuation:** The originally supplied
  `lilsmaye207` handle was a typo. Its five `unknown/unverifiable` cycles are not
  evidence about the intended creator. Normal `tikrec monitor remove` and
  `monitor add` commands against the host-visible configuration replaced it with
  owner-authorized `lilymaye207` while preserving
  `C:\Users\Leandro\Videos`; no JSON or Scheduled Task definition was edited.
  After the idle task restarted, health remained good and three complete cycles
  reported trustworthy `offline` for the corrected creator. Monitoring stayed
  sanitized and no room, admission candidate, automatic job, output, or
  `automation.json` appeared. With no consumed room, this is an offline baseline
  rather than evidence of a post-consumption re-arm transition. The service
  remains healthy, idle, and normally monitoring. The primary automatic-start/
  output/suppression gate remains outstanding; v0.9.0 is still not a release-
  preparation candidate.
- **Completed v0.9 deployed automatic-start/readiness gate:** With
  `westvlammer` as the sole monitored creator, the first service cycle observed
  canonical room `7688299000113400608` and automatically started session
  `a6b73227-d637-48d5-8ea5-90cd8ea1c806` at
  `C:\Users\Leandro\Videos\westvlammer-20260922-152933.mp4` with matching
  `.parts`; no manual start occurred. The job and monitor room IDs matched, the
  10 GiB floor was enforced, and a later idle admission snapshot was explicitly
  `ready` with 52,455,370,752 free bytes. Capture retained 30,723,109 bytes over
  129.406 seconds with no error or reconnect before a normal authenticated stop.
  Finalization produced a 30,750,722-byte MP4 and one retained FLV; retained-
  session, standard output, and deep output validation all pass. Durable
  `automation.json` consumed the room, a later same-room LIVE cycle reported
  `suppressed/same_room_consumed`, and no second artifact or session appeared.
  After the idle Scheduled Task restarted, its first trustworthy observation was
  naturally `offline` and reported `rearmed/offline_observed`; that result is
  emitted only when the consumed room was restored and then removed, proving
  durable restart loading plus natural re-arm. No duplicate was created and the
  service remains healthy, idle, and monitoring. A clean run with isolated
  `APPDATA` passes all 1,069 offline tests plus 19 subtests and all 215 unittest-
  discovery tests; compilation, 15 CLI/help paths, version, diff, and strict
  source-size checks pass. An initial unisolated run failed only two CLI text
  assertions because the real configured output directory correctly made their
  relative test paths absolute; isolation removed that environmental influence.
  No correctness blocker remains, so v0.9.0 release preparation is next.
- **Released v0.9 creator automation:** Package metadata, CLI version output,
  service version source, and new session manifests now report 0.9.0. Combined
  review found the four implementation slices coherent with the completed
  `westvlammer` deployed gate and preserved the public-only, single-slot,
  authenticated-status, no-auth-bypass, no-notification, no-retention, and
  no-concurrent-recording boundaries. Verification passes 207 focused tests,
  all 1,069 offline pytest tests under isolated configuration and temp roots,
  all 215 unittest-discovery tests, compilation, 24 CLI help/
  version paths, strict package source-size and diff checks, and an isolated
  wheel build/install smoke. Wheel metadata and the `tikrec` console entry point
  are correct for `tikrec-0.9.0-py3-none-any.whl` (SHA-256
  `7CDFACD9887B2D3D3ADA599F3724202846326EDB5C171849962B875919E450CC`). The
  immutable annotated `v0.9.0` tag (tag object
  `3e26f06903aad9fffa4f1be2e560d5fba30139fa`, peeled release commit
  `9786961d1ecaaed8fddc4c7d10eda85a27b5c968`) and published non-draft,
  non-prerelease GitHub Release are synchronized. Final publication verification
  repeated all 1,069 isolated pytest tests, 215 unittest-discovery tests,
  compilation, 24 CLI help/version paths, strict source-size and diff checks,
  and the recorded wheel metadata/install smoke.
- **Completed first v0.10 multiple-recording slice:** The persistent service now
  owns a built-in fixed capacity of two independent `RecordingController`
  instances behind `RecordingManager`. Each slot retains its own worker/Event,
  session identity, capture/reconnect progress, recovery, result, finalization,
  output/parts, and durable store. Slot 1 preserves legacy `job.json`; slot 2
  uses sibling `job-2.json`, so old installs need no migration. Corrupt state
  blocks only its slot, and two interrupted jobs claiming one path fail the
  second closed without rewriting either record. Atomic allocation and path
  checks prevent a third start or cross-slot collision; global shutdown closes
  and joins both independently.
  Authenticated `/recordings` and extended health expose safe capacity and stable
  slot/session facts. Singular status/empty stop remain compatible only when
  unambiguous; validated session-targeted stop and the new `remote recordings`
  / `remote stop --session-id` controls never signal another slot. Automation
  now inspects all jobs, sequentially fills freshly admitted capacity in lexical
  order, preserves the single crash-safe pending claim invariant, represents
  simultaneous starts honestly, and reconsiders capacity-skipped creators.
  One synchronous start failure conservatively ends remaining attempts for that
  cycle. The 10 GiB per-start floor, room binding, same-room suppression/re-arm,
  public-only security boundary, and local standalone commands remain unchanged.
  Verification passes 134 focused service/manager/automation/admission/remote/
  CLI tests, all 1,091 offline pytest tests plus 19 subtests in a fresh isolated
  non-checkout root, all 215 unittest-discovery tests, compilation, 25 CLI help/
  version paths, strict under-300-line package source and diff checks. One prior
  checkout-local full run hit the known intermittent Windows `os.replace`
  `WinError 5` in an unrelated manifest test; that exact test and the complete
  non-checkout rerun passed without a product change.
  A separately authorized bounded deployment then installed `dd00400` into the
  existing editable environment only while idle. The unchanged Scheduled Task
  now reports capacity 2, two stable available slots, useful legacy singular
  status, authenticated/sanitized monitoring, and package version 0.9.0 while
  the checkout separately verifies the development commit. Host-visible
  configuration contains exactly `westvlammer` and `lilymaye207`, with automatic
  output under `C:\Users\Leandro\Videos`. Legacy `job.json` remained completed
  and finalized, missing `job-2.json` remained a clean idle second slot without
  migration, and `automation.json` retained no pending claim or consumed room.
  Five bounded complete-cycle checkpoints found both creators naturally offline;
  no start, new session, output, or media was manufactured. The service remains
  healthy and monitoring on current `main`, while the simultaneous-LIVE,
  targeted isolation, dual-media validation, and idle-restart gate remains
  outstanding. Issues #8 and #13 produced no new evidence and remain
  non-blocking/opportunistic.
  A later authorized validation pair replaced only the monitored list through
  the proven host-visible CLI path: `ranaerose7` then `moealkaf`, with
  `C:\Users\Leandro\Videos` preserved. After the unchanged task restarted,
  `moealkaf` was trustworthy LIVE in canonical room `7688395628493949717` and
  automatic recording started without a manual request as session
  `c7927922-0381-410d-8020-0272aa96f265`, output
  `moealkaf-20260922-182902.mp4`, in `slot-1`. Its retained-byte status grew from
  1,274,670 to 26,839,748 bytes over about 194 seconds with no reconnect,
  recovery, stop, or error. `ranaerose7` remained `unknown/unverifiable` through
  seven completed cycles, so no genuine overlap or second session occurred and
  `slot-2` remained idle/available. Authentication still rejects missing tokens;
  status exposed no bearer token, signed transport marker, traceback, or unsafe
  exception text. Durable `job.json` matches the active room/session/output,
  `job-2.json` remains absent/idle, and `automation.json` contains only the
  consumed `moealkaf` room with no pending claim. The recording was deliberately
  left running; no restart, manual start, or stop was used to manufacture the
  missing overlap. This is useful one-slot deployed evidence, not the v0.10
  simultaneous gate.
  The owner then replaced only the non-useful validation creator with
  `phoebelightt`. While the same `moealkaf` session remained active, normal
  TikREC CLI commands against the proven host-visible path removed `ranaerose7`
  and added `phoebelightt`, leaving persisted order exactly `moealkaf`,
  `phoebelightt` and preserving `C:\Users\Leandro\Videos`. The service was not
  restarted, so live monitoring correctly continued to show its startup snapshot
  `ranaerose7`/`moealkaf`. Three bounded post-change checkpoints left session
  `c7927922-0381-410d-8020-0272aa96f265` healthy in `slot-1`; status grew from
  126,257,571 to 137,712,136 bytes with zero reconnects, no recovery, stop,
  finalization, or error, while `slot-2` remained available. Applying the staged
  pair and observing `phoebelightt` are explicitly deferred until the recording
  safely completes; the historical `ranaerose7` evidence remains unchanged.
- **Completed v0.7 guided recovery implementation:** `recover --finalize`
  implies standard validation and accepts only one explicitly named, consistently
  `recoverable` session with a safe stored output. It snapshots and rediscovers
  evidence before mutation, then reuses `finalize_parts`, overwrite protections,
  standard validation, and schema-1 recovery fields. Parent-root batch attempts,
  active/ambiguous/changed/symlinked evidence, output/partial conflicts, and
  undeclared outputs fail closed. Completed, failed, and interrupted attempts
  preserve retained FLVs and return plain or JSON outcomes; discovery and
  `--validate` remain read-only, and manual `tikrec finalize` is unchanged.
  Release verification passes 181 focused tests, 832 full-suite tests
  plus 19 subtests, and 204 unittest-discovery tests. Compilation, all CLI help
  paths, the installed CLI version, and an isolated wheel smoke test pass. The
  built `tikrec-0.7.0-py3-none-any.whl` reports the expected package metadata and
  entry point (SHA-256
  `D39D345C81EE5F71BBF5E155C30D82BD094C5A30680358ACD6069C32D811DDD7`).
  An isolated copy of the retained v0.4 service session exercised
  the real command: its 30,370,944-byte FLV passed pre-validation, stream-copy
  recovery, post-session validation, and deep output validation while the
  manifest retained its historical interrupted lifecycle and recorded completed
  recovery. Original evidence was untouched and temporary copies were removed.
- **Completed blocker fix:** Established capture and startup recovery now retain
  the canonical room ID as an independent resolution anchor. A username
  LIVE-page 404 can use direct public status for that room and the public account
  lookup: the same live room reconnects, trustworthy offline status retains the
  three-observation end policy, a different live room uses existing live-changed
  semantics, and unverifiable state fails closed. Initial page 404 remains a
  permanent safe failure. An established media-URL 404 requests fresh identity
  resolution after the existing failure backoff; the 404 itself is never an
  offline claim.
  Focused resolver/LIVE/service/recovery coverage passes 308 tests and the full
  offline suite passes 748 tests plus 19 subtests.
- **Post-#17 release validation:** Sessions
  `ba3f26eb-c90b-4559-a60f-7c4cdf48c979` (`aishaaa.ts`, room
  `7687819052166040350`) and `ed63dc43-eae5-4b46-a779-97c12d36dade`
  (`gracie.kf`, room `7687851874133003038`) both ran through the normal remote
  service path and ended through three trustworthy offline observations. Both
  manifests are completed, uninterrupted, error-free, and finalized; the
  current Gracie job additionally records `stop_requested=false` and
  `recovery_reason=room_ended`. Aishaaa had two ordinary media reconnects at
  1.526 and 1.531 seconds, with only 0.008 and 0.024 seconds of local/backoff;
  Gracie had no media reconnect. Terminal offline attempts retained no media
  and are not counted as successful reconnects. Both MP4s pass normal and deep
  validation, and all 19 FLVs decode successfully.
- **Issue #18 result:** The read-only benchmark separates username
  LIVE-page, optional public-account lookup, room/info, and total timings while
  comparing room/rendition/source/transport only through safe facts. It cannot
  open media or mutate capture/session state. A diagnostic predicate bug found
  during the live run was fixed so strict comparison now requires equal room,
  label, source, and exact transport; production code was never affected.
  Zoraida supplied 22 corrected alternating live pairs and ten strict matches.
  The primary six-pair batch measured bound/direct medians of 0.942/0.351
  seconds and 0.587 seconds saved (0.458--1.085 range). All bound paths invoked
  page + account lookup + room/info. Slayyyboo22 ended before paired sampling.
  The result is material and supports issue #19, not release publication.
- **Completed issue #19 implementation and validation:** Established bound resolution now overlaps a
  saved-room room/info refresh with the public account lookup. It accepts the
  fresh transport only when both independently identify the saved live room;
  every offline, malformed, conflicting, failed, or otherwise insufficient
  fast result falls back to the prior full bound path. Different live rooms
  retain `live_changed`, and only numeric non-live status for the saved room can
  enter three-observation end confirmation. Initial resolution, retries,
  backoff, media open, writer, finalization, and ranking are unchanged. A
  12-pair Zoraida recheck supplied nine strict pairs: safe bound/direct medians
  were 0.366/0.324 seconds, with only 0.044 seconds median identity-check
  overhead. The previous bound median was 0.942 seconds. Full offline coverage
  passes 774 tests plus 19 subtests. The completed Zoraida deployment run
  retained 288,436,284 bytes in one FLV and produced a 288,187,757-byte,
  2,191.564-second H.264/AAC 432x864 MP4; session, standard output, and deep
  output validation pass. Its only reconnect allocation was the media-free
  terminal room-end check. The later `luhpollisecret` media-bearing connection
  1-to-2 recovery is not an `ordinary` sample: the analyzer classifies
  it as `network_recovery` after `IncompleteRead(0 bytes read)` and an explicit
  recovery boundary, not an ordinary healthy-close reconnect. It retained media
  on both sides with the same room, `hd1`/`flv_pull_url`, codec configuration,
  and clean decoder/DTS checks. Its 7.758-second gap comprised 5.988 seconds of
  dying-connection tail, 1.024 local/failure backoff, 0.419 resolution, 0.175
  HTTP setup, 0.151 initial media, and zero keyframe gate. Established resolution
  necessarily attempted the identity-safe known-room path, but persisted evidence
  does not record whether the fast result was accepted or the full fallback ran.
  Connection 2-to-3 was a second `network_recovery`, not an ordinary reconnect;
  its 7.522-second gap included 5.992 tail, 1.034 failure backoff, 0.397 resolution,
  0.070 HTTP setup, 0.030 initial media, and zero keyframe gate. The completed
  analyzer therefore reports two recovery reconnects and zero ordinary reconnects.
  Both nevertheless ran the deployed established resolver, retained same-room
  media successfully, and measured 0.419/0.397-second resolution, consistent
  with the optimized 0.366-second benchmark. Persisted connection evidence does
  not prove fast-result acceptance versus fallback, and no qualifying ordinary
  reconnect was captured. Under the rare-evidence rule this missing branch marker
  and exact healthy-close timing sample do not represent a meaningful remaining
  safety risk: the production resolver benchmark directly proves fast-path
  acceptance, comprehensive offline tests prove fallback and identity semantics,
  Zoraida proves deployed natural-end behavior, and Luhpol proves two deployed
  media-bearing reconnects. No regression is evident. Issue #19 is closed; a
  future identity, fallback, room-end, media-open, or reconnect regression should
  be filed as a new correctness issue.
- **Preserved soak recovery:** Session `43248309-a69f-45cf-a4e2-f4fc35a82a40`,
  room `7687483539771624223`, retained 1,300,258,942 bytes in six unchanged FLVs
  across 10,031.395 wall seconds. Four allocated attempts produced three reported
  reconnects, but only two were successful media reconnects: 1.121 and 2.987
  seconds. Attempt 4 resolved a transport, then received HTTP 404 while opening
  the signed media URL and retained nothing. Supported manual finalization produced a
  1,560,230,782-byte, 10,008.064-second H.264/AAC 720x1280 MP4 with SHA-256
  `066BC0AF501F4055901AB56A2FEDC4FF5D16A2B2B31722F90E192F30EA8944B5`;
  deep output validation passes without findings. Retained validation remains
  honestly failed: part 2 has H.264 decoder errors and parts 2/4/5/6 contain
  stored-DTS reversals already represented by 16 replay records. This is
  additional issue #8 evidence without a matching raw copy, not caused by #17.
- **Completed release task:** Issue #15 is closed. The annotated v0.5.0 tag and
  published non-draft GitHub Release remain synchronized and unchanged.
- **Paused, non-blocking issue:** Issue #13 remains open, but active random-LIVE
  screening has stopped. Resume it opportunistically only when normal use
  exposes genuinely distinct simultaneous public source media.
- **Issue #8 evidence and reassessment:** The historical pre-#17 Gracie run still
  contributes its decoder/replay evidence without raw bytes. The new Aishaaa
  session separately recorded two recovered replays in part 16 and two
  unrecovered tail replays in part 17; their four packet-DTS warnings exactly
  match the recorded magnitudes, all parts decode, and the finalized MP4 deep-
  validates. With no raw copy, this is additional issue #8 evidence and is not
  attributed to #17. The Zoraida #19 session adds two recovered in-connection
  replays (video 1,480 and audio 1,399 timestamp units) whose two packet-DTS
  warnings match the connection evidence; its FLV decodes and finalized MP4
  deep-validates. No raw copy exists, so origin remains unproven and this is not
  attributed to #19. The completed Promi raw-copy session recorded zero timestamp
  replays, so it does not answer the replay-specific attribution question. It did
  expose four H.264 decoder failures already present at matching timestamps and
  payload hashes in the raw source; all 158,062 retained media-and-later tags match
  raw payload/type/order exactly after one timestamp rebase. This establishes
  upstream provenance for separate non-replay malformed media, not a TikREC
  writer divergence. The completed Luhpol session adds 303,564 complete raw tags
  across three media connections, two natural network recoveries, 22 retained
  parts, and zero raw or retained timestamp replays. Full session validation
  found one H.264 decoder error in part 22; the untouched connection-3 raw copy
  produces the same error, and all 924 retained tags from that part's first
  keyframe match raw payload/type/order exactly with only the expected timestamp
  rebase. The final MP4 deep-validates. Together Promi and Luhpol cover 461,629
  complete raw tags without a replay and twice establish source-origin malformed
  H.264 without a TikREC divergence. They cannot prove where the older replay-
  associated damage originated, but the remaining ideal sample is too rare to
  block releases absent a current retained-only divergence or reproducible
  parser/writer defect. Issue #8 therefore stays open, non-blocking, and
  opportunistic. Issue #9's incremental raw/arrival implementation is now real-
  validated and closed. Issue #13 remains paused/non-blocking.
- **Issue #8 diagnostic readiness:** Normal remote capture now has an explicit
  `remote start --raw-copy` opt-in. The service co-locates raw connections and
  arrival sidecars in the matching `.parts` directory, persists the opt-in for
  safe service recovery, and leaves ordinary starts unchanged. Current `main`
  (`0dcdbce`) was installed into the existing environment on 2026-09-21 and the
  existing `TikREC Service` Scheduled Task alone was restarted. The service is
  healthy, loads the current checkout, and exposes `remote start --raw-copy`.
  Replay-specific source comparison remains available opportunistically.
  Focused coverage passes 197 tests plus 2 subtests; the full offline suite
  passes 785 tests plus 19 subtests, and unittest discovery passes 204 tests.
- **Completed issue #8 validation opportunity:** Owner-authorized `promi.streams` session
  `e4aa8dc4-532c-42ce-96fa-76596df0a2a9`, canonical room
  `7687931142670682901`, ran through the deployed normal service at
  `C:\Users\Leandro\Videos\promi-streams-v060-issue8-raw-replay-validation-20260921.mp4`
  with `raw_copy_enabled=true` and ended naturally. Connection 1 retained one
  435,598,545-byte FLV after source EOF left an 861-byte incomplete raw-tag tail;
  three status-4 observations then confirmed room end and connection 2 retained
  no media. Session/finalization state is completed, uninterrupted, error-free,
  and `recovery_reason=room_ended`. The 435,356,044-byte, 3,283.875-second
  H.264/AAC 720x1280 MP4 passes normal validation but, like the retained FLV and
  untouched raw source, fails deep H.264 decoding at four source-identical frames.
  Stored FLV and MP4 DTS are strictly increasing. Arrival evidence contains
  79,810 contiguous byte records covering all 435,600,600 raw bytes, including a
  3,799-byte final read followed seven seconds later by `read_end=eof`; this
  completes issue #9's real boundary requirement. No fault was manufactured.
- **Completed issue #8 validation opportunity:** Owner-authorized `luhpollisecret`
  session `c5c070f3-93a3-4c13-be63-f7109fc6e974`, canonical room
  `7687950152400816913`, recorded through the normal deployed service at
  `C:\Users\Leandro\Videos\luhpollisecret-v060-issue8-raw-replay-validation-20260921.mp4`
  with `raw_copy_enabled=true`. Connection 1 ended naturally after an
  `IncompleteRead(0 bytes read)` and retained ten parts plus 161,769,336 raw
  bytes; all ten part records report zero timestamp replays. The service recovered
  normally into connection 2 without operator action. At the latest read-only
  checkpoint it remains active and error-free with one reconnect, 15 completed
  parts, 382,779,526 retained bytes, and growing connection-2 raw/arrival evidence
  (about 221 MB and 33,287 records). An independent read-only timestamp scan of
  completed parts 1--15 found no replay. The session was left running normally;
  no fault, replay, stop, or restart was manufactured, so issue #8's replay-specific
  raw-versus-retained acceptance criterion remains outstanding. A later read-only
  checkpoint found the recovery sustained for more than 4,100 seconds on connection
  2, with 19 completed parts and 724,162,228 bytes of total retained progress. A
  source-aware scan found no replay in connection 1's 56,187 complete raw tags or
  connection 2's first 192,506 complete raw tags; an active-tail truncation was
  expected while connection 2 continued growing. All 164,759 tags in completed
  parts 1--19 are replay-free, and connection-2 parts 11--19 pass decoder and
  packet-DTS validation without findings. This strengthens the no-divergence
  evidence but still does not supply the rare replay required for attribution.
  Connection 2 later ended with another natural `IncompleteRead(0 bytes read)`
  after retaining parts 11--20. Its complete 666,852,312-byte raw copy contains
  235,300 complete tags and zero source-aware timestamp replays across ten codec
  configuration epochs; its durable part timings also report zero replays.
  Connection 3 retained parts 21--22; its 35,539,119-byte raw copy contains 12,077
  complete tags and zero replay across two codec epochs. Three numeric status-4
  observations then confirmed room end and connection 4 ended offline without
  media. The session completed naturally with 22 parts, `interrupted=false`,
  `error=null`, and completed finalization. Its 1,781,146,349-byte, 6,326.199-
  second H.264/AAC MP4 passes standard and deep validation. Full retained-session
  validation found one H.264 decoder error in part 22. The untouched connection-3
  raw copy emits the identical decoder messages, while all 924 retained tags from
  part 22's first keyframe match the raw payloads, types, and order exactly and
  differ in timestamp only by the expected 9,364,937-unit rebase. This is another
  source-origin non-replay defect, not TikREC-generated corruption. Across all
  three connections, 303,564 complete raw tags and all durable part timings
  contain zero timestamp replays. No fault was manufactured.
- **Pending owner action:** None. Publication and synchronization are complete.
- **Next queued task at that release checkpoint:** ChatGPT/project management
  selects the next bounded roadmap task. The next planned version is v0.11.0 smart storage, retention,
  and disk protection, but it has not started. #8, #13, and #28 remain separate
  non-blocking evidence work.

GitHub issues and this file are authoritative for active/pending work. Reconcile
this file, ROADMAP.md, relevant open issues, and repository state before choosing
new work; calendar entries are reminders only.

## Released version and development target

- **Package version:** v0.10.0 on this untouched experimental development branch; newer installed environments were not modified/inspected.
- **Tagged version:** immutable annotated `v0.11.0`, object `ef8c5215712d454855a033700116bdc8fc0906a3`, peeled commit `2fe6354aa508d53ce3a3452ce08743d97400fe73`.
- **GitHub Release:** [TikREC v0.11.0](https://github.com/lvrdnck/TikREC/releases/tag/v0.11.0), ID `406770680` / node `RE_kwDOUTgsvs4YPtP4`, published 2026-10-08T11:50:27Z, non-draft/non-prerelease.
- **Verified wheel:** [download](https://github.com/lvrdnck/TikREC/releases/download/v0.11.0/tikrec-0.11.0-py3-none-any.whl), asset `621682513`, 207,542 bytes, SHA-256 `7cf87363cde6ce9817b79c4c7eb86fe37a3e77bcf564cde91019aadec7e902ca`; original/draft/published downloads match.
- **Current released version:** v0.11.0; published package/tag/Release are synchronized at the approved historical storage commit. v0.10.0 remains an unchanged historical release: tag object `014fa0b785f77c6b42ffe73a86ba28b00126a4ff`, peeled `dfb81b683a89d01f55d70291fb5cdcfead654976`.
- **Development:** later #30/#48/#52 behavior is outside v0.11.0. #52/#48 paused; B1/B2/B3 not waived; no successor selected. #51 closed/passed with consumed deletion authorization. Bookkeeping changes documentation only, never the tag target.

## Issue #13 rendition investigation

- Owner sequencing decision on 2026-09-15: issue #13 is intentionally paused
  and non-blocking. Do not actively hunt random public LIVEs; resume only when
  normal use reveals potentially distinct simultaneous sources. TikREC still
  aims for the highest genuine public source quality and native FPS, without
  upscaling or synthesized frames. Escalate a measured quality/FPS conflict.
- Current production selection remains unchanged: known rendition labels form
  heuristic tiers, with deterministic source/label/URL tie-breaks. The public
  response evidence audited so far does not validate per-candidate resolution,
  native FPS, bitrate, codec, or reliability metadata.
- Current logs already retain selected label/source, per-part SPS dimensions and
  optional nominal cadence, plus completed-output codec/dimensions. Explaining a
  future stronger choice additionally needs a safe candidate inventory,
  selection-policy identifier, and verified metadata provenance without URLs.
- A prior real `hd1` service recording passes TikREC validation and measures
  640x1280 H.264 at 25 fps and about 1.07 Mbit/s overall. It proves delivered
  facts can be compared with a label, but it contains no alternative candidates.
- On 2026-09-15, `ninika_live` anonymously resolved through TikREC's existing
  public path. The room exposed `hd1` through `flv_pull_url` and `default`
  through `rtmp_pull_url`, both as HTTPS FLV, with no public HLS candidate.
  Aligned 30-second and three-minute samples showed that the two labels carried
  identical H.264/AAC media payloads. The longer samples delivered 720x1280
  H.264 High video at a measured 29.983 fps and about 1.999 Mbit/s average;
  startup was 0.406 seconds, the longest observed output-growth pause was 1.407
  seconds, and neither candidate disconnected, changed configuration, replayed
  timestamps, or failed decoder/DTS checks. Both stream-copy finalizations also
  passed deep output validation.
- A second anonymous comparison on `noahdksl` exposed the same two source/label
  candidates and no public HLS. The aligned 30-second files were byte-identical,
  including all 740 video and 704 audio payloads. Both delivered 640x1280 H.264
  High/AAC at a 40 ms median packet interval (nominal 25 fps), measured 24.631
  packets/s across the sample, and about 0.626 Mbit/s average. Both started in
  about 1.4 seconds and passed FLV structure, decoder, and DTS checks with one
  unchanged audio/video configuration and no timestamp replay. Representative
  stream-copy finalization produced a 30.037-second MP4 that passed deep output
  validation.
- A third anonymous comparison on `theo_fitness1` exposed the same alias FLVs
  plus the first public HLS choice. FLV and HLS carried matching H.264/AAC source
  content at 720x1280 and 15 fps in the short sample. Over the longer matched
  window, 3,894 video frames and 3,775 normalized AAC payloads agreed; both
  transports had the same cadence gaps and passed decoding/timestamp checks.
  HLS started in 2.813 seconds versus FLV's 0.610 seconds and was 18.964 seconds
  farther from the live edge. Neither disconnected, while maximum observed
  output-growth pauses were 10.828 seconds for HLS and 6.422 for FLV.
- The source changed configurations repeatedly within the selected `hd1` FLV:
  640x1280, 320x640, 432x864, and 720x1280 all appeared. TikREC stream-copy
  finalization preserved every configuration and passed deep output validation;
  a diagnostic HLS stream copy also passed.
- A fourth anonymous comparison on `sbomberbomp1` again exposed only alias
  `hd1`/`default` FLVs and no public HLS. The aligned 30-second files were
  byte-identical, including all 451 video and 703 audio payloads. Both delivered
  stable 720x1280 H.264 High/AAC at measured 15 fps and about 0.992 Mbit/s,
  started in 1.266 seconds, and passed structure, decoder, DTS, configuration,
  and timestamp checks. Representative stream-copy finalization produced a
  30.061-second MP4 that passed deep validation. Room metadata advertised
  `HD1` as 720p but supplied zero dimensions; earlier `hd1` media was 640 pixels
  wide, so the label claim remains unsuitable as verified quality evidence.
- A later attempt on `vandaelesir` found that the supplied LIVE had ended before
  comparison. The normal anonymous resolver and two short rechecks returned the
  same room with status 3; no candidates, transport URLs, media, or dataset from
  that attempt were collected.
- A fifth anonymous comparison on `brycebennet1` exposed only `hd1` through
  `flv_pull_url` and `default` through `rtmp_pull_url`, both as HTTPS FLV, with
  no public HLS. The aligned 30-second files were byte-identical, including all
  451 video and 704 audio payloads. Both delivered stable 720x1280 H.264
  High/AAC at measured 15 fps and about 0.922 Mbit/s, started delivering output
  in 2.984 seconds, and passed structure, decoder, DTS, configuration, and
  timestamp checks. Representative stream-copy finalization produced a
  30.059-second MP4 that passed deep validation. The conclusive alias result did
  not justify a longer duplicate-media comparison.
- A subsequent ordered screening pass checked six owner-supplied public LIVE
  pages without capturing routine inventories. `lxkt16`, `thorben1891`, and
  `thethomb` were live but each exposed only the familiar HTTPS FLV
  `hd1`/`default` pair, no HLS, and no additional quality tier. `wukiyampi`,
  `tim_tokii`, and `imullaa` did not yield a current room ID through TikREC's
  anonymous public path. No promising room, media capture, signed-URL artifact,
  or sixth dataset resulted from this screening.
- All five datasets show alias labels, and the same labels carry materially
  different dimensions, cadence, and bitrate across rooms. Dataset three
  supports the existing FLV choice for equal fidelity with lower latency, but
  one FLV/HLS run cannot establish global transport reliability. Production
  selection remains unchanged. Resume #13 opportunistically when normal use
  exposes genuinely distinct simultaneous source media; escalate if resolution,
  cadence, bitrate, codec, or reliability goals conflict.

## v0.5 and diagnostic handoff

- Durable service job intent, canonical public room identity, retained-session
  continuation, startup reconciliation, bounded network recovery, and safe
  interrupted-FFmpeg finalization reconciliation are committed in `b6f190b`
  through `a384dd3`.
- The opt-in raw-arrival diagnostic slice is separately complete: raw copies can
  record HTTP-read byte ranges/timing in `connection-NNNN.arrivals.jsonl` without
  interrupting capture. It supports issue #8 investigation but does not reduce
  reconnect gaps or alter resume/finalization policy.
- The 2026-09-15 offline audit found no missing slice and the full suite passed
  707 tests plus 19 subtests, but the 2026-09-16 real deployment run exposed
  issue #14 at the first abrupt-process-death boundary.
- **Failed phase-B evidence:** Task Scheduler stopped the actively recording
  deployed service without graceful cleanup. Restart kept session
  `41dd234c-3d8c-42c3-ba36-742de92367d7`, room `7685987454411344653`, durable
  `recording` intent, and the original 11,789,861-byte writer partial, but health
  reported `failed`/`ambiguous_state` and no new part or connection opened while
  the same room remained live. The partial ends at a clean FLV tag boundary,
  contains 3,765 media tags through 86.653 seconds, and passes decoder/DTS checks.
  It remains ignored/local under `runs/v05-deployment-allynwd04-20260916.parts/`.
- **Implemented #14 policy:** generic `discover_parts()` remains strict. Startup
  alone may recover the canonical next writer partial when durable recording job,
  manifest identity/lifecycle/paths/counts, connection evidence, output absence,
  artifact inventory, FLV structure, and FFprobe decoder/DTS checks all agree.
  It durably marks recovery first, atomically preserves the exact original under
  a session/index evidence name, admits only a separately copied complete prefix,
  and records its SHA-256 plus byte counts/discarded tail in manifest evidence.
  Clean and torn-tail cases resume at a fresh connection/next part; arbitrary,
  empty, malformed, unowned, conflicting, colliding, or nonregular artifacts block.
- **Offline verification:** 728 tests plus 19 subtests pass, including byte-exact
  preservation, truncated-tail salvage, recovery-restart idempotence, count/timing
  honesty, correct next part/connection allocation, and the fail-closed matrix.
- **Repeat abrupt-restart validation passed:** On 2026-09-19 the deployed service
  recorded `lilymaye207` as session `c3d05742-242e-4093-b8cb-69297f967e39`, room
  `7687184860712225537`. `Stop-ScheduledTask` left a 7,874,881-byte writer partial
  with SHA-256 `AC27A60670479A99A179AA53CEC838361A2EF85734752FF69EDF480FD0D44CB1`.
  Restart exposed `recovering/writer_partial_recovery`, preserved the exact bytes
  under the deterministic evidence name, published an equal 7,874,881-byte clean
  prefix with zero discarded bytes, and resumed the same session/room with
  `resume_count=1`, connection 3, and fresh `part-0002.flv`. The recovered part and
  resumed part both passed FFprobe decoder/DTS checks and began near timestamp zero,
  while status/media continued growing without ambiguous or failed recovery.
- **Preserved validation anomaly:** The resumed source later changed 720x1280 to
  640x1280 and back within connection 3. The short middle `part-0003.flv` has valid
  FLV framing, a source-marked keyframe start, and clean DTS but FFprobe reports H.264
  decoder errors; surrounding `part-0002.flv` and `part-0004.flv` decode cleanly.
  TikREC copies source payloads unchanged, so this run does not justify a recovery
  code change. A normal remote stop was used only to freeze evidence after the
  finding; its completed output was not deep-validated or claimed as the deferred
  graceful-finalization phase.
- **Temporary-network-outage validation passed:** On 2026-09-19 a new deployed
  `lilymaye207` session `73675685-5c7c-4310-b94f-dd749e2bc5b8`, canonical room
  `7687184860712225537`, was routed through a loopback HTTPS CONNECT proxy that
  covered both TikTok resolution and the selected media CDN while remote control
  stayed direct over Tailscale. Killing only that proxy closed a 6,293,414-byte
  `part-0001.flv`, entered durable `recovering_network/network_outage`, and held
  retained bytes and identity fixed through staged retries. Restoring the proxy
  produced an automatic same-room reconnect without a new start; connection
  allocation advanced to 8 (`reconnect_count=7`) and fresh `part-0002` grew from
  650,080 to more than 43 MB. Part 1 and a read-only probe of the actively
  growing part 2 both passed FFprobe decoder/DTS checks with near-zero rebased
  starts. The proxy was unavailable for about 93 seconds; the next CDN tunnel
  opened about 102.6 seconds after part 1's last retained-media observation, so
  that interval is an observed capture gap, not recorded media.
- **Final deployment validation passed:** The same session was remotely stopped
  through TikREC after more than 1,150 seconds of useful post-outage capture.
  Connection 8 closed as interrupted with completed `part-0002.flv` through
  `part-0004.flv`; the coalesced recovery boundary closed honestly as `user_stop`
  with retry attempt 7 rather than inventing source EOF. Its connection record
  proves successful same-room media from `1789820978.7953813` through
  `1789822129.9061882`. Manifest/job state retained the original session and room,
  4 parts, 8 allocated connections, 7 reconnects, completed finalization, and
  intentional interruption. All four FLVs passed decoder/DTS validation without
  warnings. The 159,231,842-byte H.264/AAC MP4 (720x1280, 1,200.636 seconds,
  SHA-256 `9B6C75049EFE5E7708938345B2642D0B1DDED8216D93EEFD8B4CF9204B701B3E`)
  passed deep validation without findings. The 103.366-second interval between
  pre- and post-outage retained media remains absent from the output timeline.
- **Validation-discovered fix:** Restarting the idle service initially exposed
  `reconnect_count=0` even though the completed manifest retained 7. Inactive
  status now restores that durable count without reading the manifest while active
  capture may atomically replace it on Windows. Focused tests and the full 729-test
  suite pass. The validation proxy was retired, user-level `HTTPS_PROXY` remains
  absent, and the Scheduled Task was restarted healthy/available in its normal
  environment.
- **Release finalization:** v0.5.0 tag `173d25f4736a2b900ffb381d98e218aaae31770c`
  was pushed and peels to `7e65248bb4061cf74e84986314db0b6b16d5fc02`; the verified
  non-draft GitHub Release is published. Issue #15 is ready to close.
- **Optional non-blocking evidence:** issue #9's real raw-copy stall-boundary
  check, issue #8's replay with matching raw bytes, and issue #13's distinct
  rendition comparison remain open for opportunistic collection.

## Durable decisions and risks

- TikREC supports one manually supplied public LIVE plus configured creator
  monitoring, admission, and durable one-slot automatic recording. Deployed
  automatic-start/output/suppression validation and v0.9 release completion
  remain outstanding; TikTok authentication remains deferred.
- Automatic resume requires the same canonical room ID and valid retained
  evidence. Only the exact proven active writer partial is recoverable; all
  unowned or conflicting partials remain preserved and blocked.
- Raw-copy diagnostics are best-effort and record local processing boundaries,
  not provable source-byte arrival.
