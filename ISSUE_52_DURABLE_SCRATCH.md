# Issue #52 — durable scratch and unpublished-candidate ownership

## Current candidate-validation contract — 2026-10-05

[PM decision 6000035417](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6000035417) accepts `ee884bdc` connected assembly and supersedes its pending-review
checkpoint. The new [validation contract/evidence](ISSUE_52_CANDIDATE_VALIDATION.md) describes `JournalValidation`: exact same-attempt
validation with original native/input ownership retained, three fixed durable
contained FFprobe phases, append-only evidence and no arbitrary post-candidate
launches. Schema 6 adds validation authority/receipts; schemas 1–5 are refused and
preserved without migration. Assembly/candidate evidence remains immutable
`not_checked / unpublished`; separate validation success does not publish, settle,
release units/claims/pins or permit retry/adoption. Pending manifests are unchanged.
Only explicit candidate validation joins the writer's cancellation-aware long
execution allowance; generic readers remain finite, with bounded final drain/
cancel/cleanup. Failure/ambiguity and unknown lifetime retain native protection.
#52 OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED; #28 unresolved. Delivery stops for PM
review; no service/production/cutover/release action. The checkpoints below are
historical accepted evidence within their recorded limits.

## Historical acceptance and adapter contract — 2026-10-05

[PM decision 5999162236](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5999162236)
accepts `58e40084` R8–R10 within their recorded limits. The new internal
[journal-backed assembly](ISSUE_52_JOURNAL_ASSEMBLY.md) uses this exact scratch
capability, preserving schema 5, empty authorization inventory, one writer and
R8–R10. Copy's declared concat helper is produced only inside the contained
writer whose code/text/FFmpeg argv are durable intent bytes. Writer `timeout=None`
permits cancellation-aware long execution with bounded final drain/cleanup;
readers/default waits remain finite. Trusted semantic diagnostics finish before
same-attempt unpublished/not_checked sealing. Current delivery/evidence is in
the linked adapter report; the correction checkpoint below is historical.

## Historical correction checkpoint — R8–R10, 2026-10-05

[PM review 5993102551](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5993102551)
retains the direction and requires focused corrections before successor
integration. This task started from clean reviewed `d35f946f`, pulled the isolated
branch before inspection, and passed MODEL GATE / PROCEED for GPT-6.1 Sol — High.
Accepted R1–R7/`3d4e15ce` foundations were preserved, without restarting reviews.
Schema 5 is unchanged. #52 stays OPEN/SINGLE ACTIVE; #48 stays OPEN/PAUSED with
Gracie-only raw/Ward OFF; owner decisions: None.

### Corrected contract

- **R8:** The entire secondary hold path catches lookup/audit/persistence/advance
  faults. First failures remain reachable through the original accepted process
  wrapper, `AttemptError`, and scratch owner; bounded secondary diagnostics remain
  separate. Hold revokes local execution even when bookkeeping is unavailable.
  The scratch handle constructor explicitly attaches a possibly-open owner after
  proof and cleanup fail, and artifact acquisition registers it before propagating
  the first failure. The accepted general native foundation was not rewritten.
- **R9:** `close()` reports incomplete cleanup whenever workspace/artifact native
  protection is retained. `cleanup_evidence()` separately reports execution
  revocation, complete local cleanup, and retained scratch owners. Failed or
  unacknowledged ownership is preserved; repeated/concurrent close/cancel does not
  authorize retry, release durable pins, or delete partials. A committed candidate
  with missing local acknowledgement remains protected. Guard release still
  requires the existing exact child-exit/local cleanup proof.
- **R10:** The empty workspace is checked around binding hooks and before writer
  authorization. After observation, every binding/sealing check compares the full
  inventory and every held artifact's exact native identity/size/stamp. Checks
  bracket hashing and unlocked hooks, including a final scan after
  `before_candidate_ready`. Multiple helpers and reversed output declarations are
  canonicalized correctly. Native scans/hashing precede the short resume fence and
  occur outside authority/SQLite locks.

### Reproduced review regressions versus new coverage

Five regressions fail against unchanged reviewed code using actual disposable
Windows H/workspace/process fixtures: writer failure masked by unavailable hold
lookup; hash failure masked by the same lookup; successful native artifact open
followed by proof plus close failure without an explicit retained registry owner;
bound scratch reported as successful cleanup; and an unexpected file introduced
at `after_artifact_bind` accepted as candidate-ready. The definitive reviewed-code
run is **5 failed**, recorded in `review-baseline-corrected-probe-real.log`.
It used detached `baseline-d35f946f` with only the added regression test/helper
fixtures copied in, clean tracked runtime source, baseline cwd/`PYTHONPATH`, and
isolated `config-empty`. Command: `python -m pytest
tests/test_attempt_scratch_review.py -q
--basetemp=<evidence root>\review-baseline-corrected-probe-real`.
The pinned baseline helper predates the additional cleanup/hash report fields;
the baseline copies and logs remain at the evidence root.
The initial fixture-registration error was a harness error and is not defect
evidence. Native writer failures use the already accepted `ProcessOwnerError`
wrapper; its original cause remains preserved rather than being replaced by a
secondary journal failure.

Additional coverage exercises secondary hold persistence/advance failure and
bounded diagnostics, unbound created owners, durable-commit/local-ack divergence,
native descriptor/directory close faults, repeat/concurrent close/cancel, empty
workspace binding hooks, missing/replaced/changed helpers, hashing orderings,
and valid multiple-helper/output ordering. These are new checks, not claims that
every such ordering was independently demonstrated broken in the reviewed code.

Thirteen actual supervisor-death cases cover reservation writes/commit,
intent/create, native bind before/after commit, artifact bind before/after commit,
and candidate seal before/after commit plus local-ready acknowledgement. Exact
supervisor termination and independent job cleanup guards establish process-death
evidence. Reopen shows only committed facts, unchanged H/input hashes, one counted
running task, no publication, and no adoption/retry/refund. This is not power-loss
proof. Existing exception-interruption tests remain present.

Actual scratch-owning writer checks cover cancellation before/after resume,
root exit with a living descendant, an unaffected separate job, unavailable
whole-job status, incomplete observer/final-EOF diagnostics, and native cleanup
failure. All use disposable local objects and independent exact-job cleanup.

### Same-environment CLI failure comparison

Both exact nodes were run against accepted `3d4e15ce` and reviewed `d35f946f`:

```text
tests/test_live.py::LiveCliTests::test_interrupted_live_clears_a_visible_heartbeat_before_stderr
tests/test_live.py::LiveCliTests::test_interrupted_live_with_output_still_exits_130
```

Interpreter: `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`.
Imported packages were respectively the `tikrec/__init__.py` inside disposable
`baseline-3d4e15ce` and the isolated implementation worktree, as recorded in the
comparison JSON files. `APPDATA`/`XDG_CONFIG_HOME` explicitly selected disposable
configuration roots; `PYTHONPATH` and cwd selected each exact repository. No
production configuration was read or changed. Effective defaults: schema 1,
validation/recovery unset, either no output directory or synthetic absolute
`C:\Users\Leandro\TikREC-tests\issue52-r8-r10\synthetic-output`.

| Revision/settings | Exact nodes |
| --- | --- |
| Accepted `3d4e15ce`, synthetic configured output | 2 failed |
| Reviewed `d35f946f`, identical configured output | 2 failed |
| Accepted `3d4e15ce`, unset defaults | 2 passed |
| Reviewed `d35f946f`, identical unset defaults | 2 passed |
| Corrected CLI fixture, surrounding configured output | 2 passed |

Commands and import/default metadata are in `accepted-configured.json`,
`current-configured.json`, `accepted-empty.json`, `current-empty.json`, and
`corrected-configured.json`. Each invokes the same interpreter with
`-m pytest <both exact nodes> -q --basetemp=<disposable directory>`.
`compare_live.py` is the saved executable harness. The fixture now supplies an
isolated unset default-config directory for injected `LiveCliTests`, preserving
the assertions and all product defaults. This establishes the earlier failures
as configuration leakage; the earlier unsupported attribution is historical.

### Final delivered-tree verification and evidence

- Focused scratch/journal/version selection: **71 passed**, 49.18 seconds.
- Related selection: **593 passed, 2 skipped**, 151.85 seconds (62 modules).
- Full isolated suite: **2,339 passed, 9 skipped, 19 subtests passed**, 229.01
  seconds. No failures. All three final runs followed the final source/test
  organization; subsequent edits are documentation/checkpoint recording only.

Evidence root: `C:\Users\Leandro\TikREC-tests\issue52-r8-r10`.
All suites explicitly use the current worktree in `PYTHONPATH`, disposable
`config-empty` in `APPDATA`/`XDG_CONFIG_HOME`, and a unique `--basetemp`:

```powershell
$tests = rg --files tests | Where-Object { $_ -match 'test_attempt_scratch|test_session_journal_scratch|test_session_journal_version' }
python -m pytest $tests -q --basetemp='<evidence root>\final-focused'
# The exact output is saved in related-files.txt; regenerate on another device:
$related = rg --files tests | Where-Object { $_ -match '^tests[\\/]+test_(session_journal|capture_handoff|sealed_inputs|attempt_coordinator|attempt_scratch|owned_process|unpublished_assembly).*\.py$|^tests[\\/]+test_(finalize|finalization_recovery|recovery_finalization|finalizing_capture_availability|live)\.py$' }
python -m pytest $related -q --basetemp='<evidence root>\final-related'
python -m pytest tests -q --basetemp='<evidence root>\final-full'
```

Per-fixture `scratch-integration-evidence.json` and `death-inspection.json`
record committed outcomes, original H/input hashes, unchanged unrelated sentinel
hashes and explicit cleanup evidence before the independent disposable cleanup.
Keep the distinction between native process proof, unvalidated synthetic scratch
candidates, and the separately accepted generated-media assembly checks.

Both separate generated copy/libx264 paths pass part validation, packet DTS and
deep validation, keep the requested final destination absent, and preserve all
source/raw/arrival/control hashes. Related-run `assembly-evidence.json` records:

| Fixture | Recorded SHA-256 |
| --- | --- |
| Matching/copy source FLVs | `880bf089561569627028361e96a834c4e083bcea6e8952043c1d8127214cce97` |
| Differing/reencode second FLV | `49a199fcef6abaad2e75d555329a41b384843dc94c2adc17c81d6bf23321671b` |
| Unrelated scratch fixture sentinel | `492b53968c1e26ec5ba483e54a47e9eb694f0682b6a4393f119ab19e64159cdd` |

Each assembly path has 12 frames and matches synchronous frame timing. Generated
scratch candidates remain unvalidated; no natural recording was accessed.

Historical `6fdacd37` contains `Closes #52`; this is flagged for the eventual
separately reviewed integration and does not authorize closure. Correction
commits use `Refs #52`; no history is rewritten.
Current outcome: corrections and required verification delivered for PM review.
No successor scope is authorized until PM review of this correction.

## Scope

The 2026-10-05 PM decision accepts `3d4e15ce` as the attempt/child-launch
foundation and limits this slice to durable scratch and unpublished-candidate
ownership. It supersedes the earlier queue-connected assembly selection. The
queue remains disconnected from MP4 assembly. No validation, publication,
settlement, retry, scheduler, service integration, or full A1–A20 acceptance is
included. Issue #52 remains OPEN/SINGLE ACTIVE for PM review.

## Durable ownership contract

- Schema 5 records a scratch reservation before filesystem creation. The
  reservation binds catalog and session identity, exact original H operation,
  revision, seal and marker evidence, owner attempt, generated workspace path,
  and the declared candidate/helper outputs. Schemas 1–4 remain unchanged and
  are refused without migration.
- The workspace is a generated sibling under the held media-root directory.
  Windows `NtCreateFile` uses `FILE_CREATE` relative to the already-held root
  handle and returns the exact newly created directory handle; sharing is denied
  while owned. The recorded native identity and final path are checked against
  the expected directory scope.
- Writer execution has a distinct authority from `run_child`, which remains
  read-only. One writer launch is allowed per attempt scratch. Only predeclared
  outputs are accepted, and pre-existing collisions are refused without opening
  or adopting them. Child completion, diagnostics and cleanup proof precede
  candidate sealing and hashing.
- A sealed candidate is explicitly `publication=unpublished` and
  `validation=not_checked`. Failures preserve ambiguous files and handles as
  held. Reopening the journal permits inspection only; it does not adopt a
  process, workspace, or candidate.

## Limits

Native directory handles establish identity and constrain the owned workspace
creation. They are not a filesystem sandbox: an authorized writer is trusted
internal code and can still make other filesystem changes if defective. A held
directory handle does not prevent another actor from adding entries. Process
containment remains the existing Windows job/lifecycle mechanism; it is not a
filesystem security boundary. No real recording or production runtime was used,
and candidate validation/publication are deliberately unattempted.
Inventory/hash checks and SQLite receipts are separate operations under
cooperative ownership, not an atomic filesystem/SQLite namespace snapshot. A
foreign mutation after the final unlocked scan or during the commit is outside
this proof; directory protection does not exclude all entry creation.

## Historical first-delivery verification — not final acceptance

- Focused ownership/journal/coordinator run: **33 passed**.
- Related suite: **2,289 passed, 9 skipped, 19 subtests passed; 2 failed**.
  The original report attributed these to existing `test_live.py` expectations for relative
  `final.parts`; on this host the configured default Videos directory resolves
  that path to `C:\Users\Leandro\Videos\final.parts`. They do not exercise the
  scratch changes without a same-environment baseline. The comparison above now
  supplies that missing evidence.
- Full offline suite: **2,289 passed, 9 skipped, 19 subtests passed; 2 failed**
  in 195.19 seconds. Both failures are the same `test_live.py` relative-versus-
  absolute `final.parts` path expectation described above. The full run included
  the scratch tests before their final test-file split; the focused post-split
  run is recorded below.

The 300-line source-file limit is satisfied; the native Windows scratch suite is
split between `test_attempt_scratch_windows.py` and
`test_attempt_scratch_cleanup.py`.

## Durable references

- Historical implementation commit: `6fdacd37` on `codex/capture-journal-handoff`.
- [PM scope decision](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5991952747)
- [Current issue #52 design checkpoint](ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md)
- [Prior attempt/launch evidence](ISSUE_52_DURABLE_LAUNCH.md)
