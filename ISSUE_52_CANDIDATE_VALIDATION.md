# Issue #52 — durable same-attempt candidate validation

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

## Historical accepted authority and checkpoint — 2026-10-05

[PM decision 6000035417](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6000035417)
accepts `ee884bdc80f5def801b4e49c16f59d842f17a30d` as the connected assembly
foundation and authorizes this single internal validation slice. R1–R10 and the
accepted assembly remain accepted; their reviews were not restarted. The existing
isolated Windows worktree was pulled before inspection, already current/clean.
MODEL GATE / PROCEED selected GPT-6.1 Sol — High. Owner decisions: None.

#52 remains OPEN / SINGLE ACTIVE. #48 remains OPEN / PAUSED with Gracie-only
raw/Ward OFF; #28 remains unresolved. Delivery stops for PM review. Use `Refs #52`;
preserve pushed history, including the previously flagged historical `Closes #52`.

## Connected live capability

`JournalValidation` owns a single `JournalAssembly` and its original
`AttemptCoordinator`. `run()` claims at most one sealed FIFO session, assembles
through the accepted writer path, then validates that same protected candidate.
An empty queue returns `None`. Repeated invocation is refused. There is no CLI,
service, API, scheduler, discovery, polling, retry, adoption or promotion path.

The assembly adapter opts into validation read sharing at **original artifact
acquisition**. The same `ScratchHandle` keeps its read/write native handle and
descriptor through artifact flush, binding, hashing, sealing and validation.
`FILE_SHARE_READ` permits FFprobe readers, denies new writers and deletion, and
does not permit a close/reopen gap. Standalone `JournalAssembly` keeps its default
zero sharing. Validation never closes protection to reopen an arbitrary path.
Workspace creation, concat production, one writer and assembly receipts stay
unchanged. No standalone independent finalizer or validator owner is invoked.

`CandidateValidationExecution` is a live capability over this exact runner,
scratch and candidate snapshot. Native scans/hashes run outside SQLite/resume
locks. Hashing reads the original descriptor in bounded chunks and checks
cancellation between reads. Complete inventory, native identity, size, stamp and
SHA-256 are revalidated at authority binding, before launch, native authorization,
resume, after work/cleanup, semantic result and before/after receipt commit.
Inputs and original H are revalidated throughout through the accepted guard.

## Minimal schema 6, no migration

Schema 5 cannot append validation state to its immutable `scratch_candidates`
without contradicting accepted `validation='not_checked'` evidence. Schema 6
therefore adds only `candidate_validations` and `validation_receipts`, with
immutable/keep triggers, plus the catalog/version fingerprint change.
Schemas 1–5 are refused and preserved without migration. Schema 5's frozen
fixture is copied from accepted `ee884bdc`; refusal leaves its bytes unchanged.
No production catalog, schema migration or cutover is involved.

`begin_validation` appends one authority containing exact session/attempt,
candidate snapshot, workspace and three fixed FFprobe argv vectors. The candidate
snapshot includes native identity/size/stamp/hash, original seal/marker hashes,
writer launch/sequence/execution diagnostics and candidate-seal operation. Its
existing receipt chain binds original H, owner and assembly evidence. A separate
append-only `finish_validation` receipt binds the authority hash, semantic report
and all three exact child identities/intents/exit/EOF/diagnostic/cleanup receipts.
Audit checks the entire bounded validation chain independently of assembly.

The existing prohibition on arbitrary post-candidate launches remains. Only the
next fixed validator can launch with `access='candidate_validation'`, matching
the unique open validation operation, exact executable/argv/cwd, phase and index.
At most three validators are permitted; a receipt permanently closes that
authority. Ordinary readers and writers cannot bypass the candidate-ready fence
by changing their phase name. Journal inspection reconstructs facts only, never
the retained local native capability.

Assembly/candidate rows remain immutable, including `not_checked / unpublished`.
Successful validation is a **separate** receipt, not a candidate-state rewrite,
publication permission, task completion, accounting release, retry or adoption.
The running task/unit, raw/room/output/parts claims, original H and durable pins
remain retained. This phase also retains local candidate/workspace/input pins
after success, failure or ambiguity; `close()` revokes execution and closes
provably finished child controls, but reports incomplete resource cleanup while
these pins remain. Disposable fixture teardown releases them independently.

## Applicable media semantics and complete execution

The first two fixed commands reuse output inspection and actual full frame decode
through `_validate_output` / `validate_decoding`, with an injected owned runner.
The target is the candidate file itself; the intentionally pending whole session
manifest is neither changed nor used to reject valid pre-publication media.
Container/video/duration checks and the existing missing-audio warning semantics
are preserved. Failed inspection still consumes the explicit decode check.

The third command streams packet stream-index/DTS records. Each stream's previous
packet is checked through existing `verify_packet_dts`: duplicate DTS is an error,
backward DTS remains a warning, and malformed/missing DTS fails. No valid packets
fails. Streaming keeps at most 64 stream predecessors and 32 packet findings;
overflow or malformed framing produces explicit ambiguity rather than success.
Inspection documents/lines retain the existing bounded 64 KiB parser contract.

All three processes use durable launch-before-create, suspended native job
containment, exact authorization/resume and independent exit/diagnostic/cleanup
receipts. Only this explicit phase may have no overall deadline; cancellation
wakes the polling loop, and final drain/cancel/cleanup retain separate bounded
five-second operations. Generic readers remain finite. A root exit does not
establish whole-job exit when a descendant remains.

Every stdout/stderr byte is streamed, counted and hashed; native prefixes and
drop counts remain explicit. UTF-8, observer/framing errors or incomplete EOF
cannot produce a success receipt. Any FFprobe stderr or nonzero exit fails media
validation, including a zero-exit diagnostic beyond the native prefix. A bounded
stderr tail preserves the final unterminated failure text. Findings retain bounded
excerpts with full diagnostic counts/hashes/EOF in the child receipt chain.
First execution failures are preserved even when the best-effort legacy inspector
catches `OSError`; secondary cleanup/journal faults remain separate.

Semantic failures can append an honest failed report after all three checks and
confirmed native/diagnostic cleanup. Execution/ownership/diagnostic ambiguity
retains authority, children and candidate without a final receipt. Unknown whole-
job lifetime stays pinned. Acknowledgement loss reconciles the exact operation
once without reissuing it; unavailable reconciliation returns failure even if a
historical receipt was committed.

## Verification and evidence

Final delivered source/test tree: no failures.

| Suite / selection | Actual result | Seconds | External log |
| --- | --- | ---: | --- |
| Focused — 6 modules: new connected path/schema | 75 passed | 203.01 | `focused-delivery.log` |
| Related — 73 modules: accepted regressions/media semantics | 687 passed, 2 skipped, 17 subtests passed | 278.01 | `related-delivery.log` |
| Full — all tests | 2461 passed, 9 skipped, 19 subtests passed | 509.16 | `full-delivery.log` |

All 376 working source/test SHA-256 hashes remain unchanged across these final
runs; `source-test-hashes-delivery.json` and `final-tree-verification.json` retain
the inventory/results. Source/test files owned by this task are under 300 lines.
Whitespace review passes. The full suite includes the original `test_live.py`
assertions under explicit disposable configuration; no assertion or product
default is weakened. Accepted R1–R10 and connected assembly regressions pass
in the final related/full tree. Skips remain platform/environment limits;
all 75 focused new-path/schema checks execute on Windows.

Commands use the exact module lists recorded in `focused-delivery-files.txt`
and `related-delivered-files.txt`: `python -m pytest <selected modules> -q
--basetemp=<suite>-delivery`; full uses `python -m pytest tests -q` with its
own `full-delivery` basetemp. Each suite has its own empty APPDATA/XDG root.
The final focused/related/full runs overlap only through the read-only source
tree; fixture catalogs/media/native jobs/events/configuration are separate.
These basetemps identify completed evidence and must not be reused. Each shell
captures the actual pytest exit code before displaying its log.


Environment: Windows, explicit isolated worktree
`C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC`;
Python `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`.
Disposable configuration and basetemps are under
`C:\Users\Leandro\TikREC-tests\issue52-validation`, outside the repository.
Every test run sets `PYTHONPATH` to this worktree, `APPDATA` and `XDG_CONFIG_HOME`
to the same explicit empty fixture configuration, and `PYTHONUNBUFFERED=1`.
Installed FFmpeg/FFprobe executables are explicit absolute paths; no dependencies
or runtimes are installed/upgraded. Disposable validator executables use the
already installed Windows .NET Framework compiler; they delegate to actual
FFprobe except for explicitly documented fault/lifetime behavior.

Coverage directly exercises **the new connected path**, with actual queued/sealed
generated copy and differing-configuration libx264 sessions. Tests preserve source,
raw, arrivals, controls, original H receipts, input seals and unrelated hashes;
requested final output remains absent, candidate unpublished and unit/pins held.
They cover container/mdat corruption, candidate writes/rename refused by native
protection, owner-descriptor byte changes even with restored last-write timestamp,
complete-inventory changes before/after native resume/result/receipt, failed
decode, nonzero/zero-exit diagnostics, final EOF tail, invalid UTF-8, observer/EOF/
native cleanup faults, first-plus-secondary failures, cancellation around nine
boundaries, descendants, unknown status/termination, and authority/receipt ack loss.
Long validation runs beyond 31 seconds without changing reader behavior. A
blocked validator leaves two independent capture bindings available, retains
queued work and cancels only its exact job while an unrelated job survives.

Twelve actual supervisor deaths cover pre-authority, authority transaction before/
after commit, post-authority, launch intent, native create, pre-resume, post-resume,
semantic result, receipt transaction before/after commit, and post-receipt.
Reopen inspects committed facts only, preserves database bytes/input hashes and
does not infer lifetime or reconstruct adoption/execution authority. Actual native
process handles are independently duplicated/waited; fixture cleanup owns exact jobs.

External evidence includes `validation-media-evidence.json`, twelve
`validation-death-evidence.json` files, suite logs, exact selected module lists
and source/test hash inventory. Generated artifacts are disposable evidence;
none are committed as production media or authority.

Final connected media receipts bind copy's 17,883 bytes / 66 packets to
`564dc75486b06c55dfe12ab6acaeccd3eeaaba46f1d53374943323a8f9ee24af`, and
libx264's 16,855 bytes / 67 packets to
`675817cf334dbce51ee8efd41559f3ec1ead86ca9deb9648caa7363734326d6c`.
Both output inspection and full frame decode pass while protection remains held.

### Development failures, reported honestly

- Initial unchanged-code regression collection fails because the new validation
  module does not exist. No accepted foundation review was restarted.
- Initial fixture runs exposed a missing external basetemp parent and an assertion
  looking for the inner journal error on the outer `AttemptError`; both corrected
  without weakening the candidate-ready prohibition assertion.
- Schema-refusal test insertion briefly attached version-1 assertions to the new
  version-5 case; the assertions were restored to their respective fixtures.
- The first death run had twelve barrier failures because its trusted fixture hook
  indexed the child list before the first child existed. Guarding the fixture
  hook corrected it; all twelve actual death checks subsequently passed.
- A first focused command named a nonexistent old test file and collected no tests;
  the final selection uses the actual module inventory recorded externally.
- Source review then found that a diagnostic framing failure raised a generic
  incomplete-diagnostics error. A regression reproduced this before correction;
  the first specific parser failure is now preserved.
- Exact-warning parity added a later backward DTS jump and reproduced incorrect
  pair-local packet numbering. The bounded parser now retains per-stream positions
  and matches the existing validator's warning exactly. Earlier 191/192-pass focused,
  791/687-pass related and prior full runs are development evidence. Final focused
  coverage selects the new path/schema cases; final related coverage includes all
  accepted ownership/scratch/assembly regressions plus existing media semantics.
  All final suites are rerun on the corrected frozen source/test tree.

## Remaining limits and next action

This is cooperative namespace/process-death evidence, **not** an atomic filesystem/
SQLite snapshot or power-loss guarantee. Directory pins deny deletion/rename but
do not prevent new children. A namespace mutation inside the receipt commit window
can leave an immutable historical passed receipt for the original exact binding;
post-commit revalidation rejects the live result, retains pins and grants no new
authority. That receipt never validates a changed candidate or inventory and is
never a standalone permission to publish, reopen, adopt or retry. Future promotion
would require its own separately authorized live boundary and revalidation.

Only generated disposable recordings are used. Natural-recording validation,
power loss, production/service integration and the full A1–A20 gate remain
outstanding; this slice claims none of those gates. No `ffmpeg -f null -` corruption
check is used. #28 remains unresolved.

No publication/promotion, completion-manifest mutation, settlement/refund, retry/
adoption, scheduler/service/API/monitor, retention, production access/change/
restart, #48 polling, migration/cutover, dependency/runtime upgrade, resource-
policy work, merge, release or tag occurred. Next action: PM review of this
partial slice; no automatic successor. Safe resume: pull the isolated branch,
read this report/current #52 checkpoint and reconcile the latest PM decision.
