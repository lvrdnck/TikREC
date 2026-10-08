# Issue #52 — internal one-shot journal-backed MP4 assembly

The [B1/B2 foreground pilot](ISSUE_52_PILOT.md) opts into a 256 MiB writer mux
threshold before durable launch hashing. Near-cap sealed unpublished bytes refuse
before validation/publication; original cleanup may retire while the unfinished
unit stays held. Ordinary defaults/media algorithms remain unchanged; no broader
recovery or terminal release is added.

## Current manifest-completion boundary — 2026-10-06

[PM decision 6012406322](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6012406322) accepts `0ca6144a` publication
and authorizes this single internal slice; earlier accepted foundations remain accepted.
Accepted assembly remains unchanged in scope. The explicit original owner can now
continue through accepted validation/publication to guarded schema-1 manifest
completion, preserving input-decode health and all retained accounting/ownership.
See [same-attempt completion](ISSUE_52_MANIFEST_COMPLETION.md).

## Historical accepted guarded-publication contract — 2026-10-06

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

## Historical accepted candidate-validation contract — 2026-10-05

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

## Historical assembly authority and checkpoint — 2026-10-05

[PM decision 5999162236](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5999162236)
accepts `58e400848658a99f7d5412ad6cac5765e30e224f` and authorizes only this
adapter. It supersedes pending-review/no-successor statements for R8–R10;
accepted R1–R10 foundations remain accepted within their recorded limits.
The existing isolated Windows `codex/capture-journal-handoff` worktree was pulled
before project inspection (already current/clean), then MODEL GATE / PROCEED
selected GPT-6.1 Sol — High. No owner product decision is needed.

#52 remains OPEN / SINGLE ACTIVE; #48 OPEN / PAUSED, with Gracie-only raw/Ward
OFF criteria unchanged; #28 remains unresolved. Delivery requires PM review;
no publication or automatic successor is authorized. Use `Refs #52`. Historical
`6fdacd37` contains `Closes #52`; that remains flagged for eventual separately
reviewed integration and does not authorize closure or history rewriting.

## Connected contract

`JournalAssembly` takes an explicit currently held `CaptureAuthority` and
existing absolute FFmpeg/FFprobe executables. `run()` is single-use and returns
`None` when no eligible FIFO claim exists. Otherwise its own `AttemptCoordinator`
claims at most one session and retains the exact original-H claimed input guard.
There is no catalog/path discovery or polling loop over sessions. Errors retain
the adapter/coordinator and first cause through `AssemblyError`.

Only shared `plan_media`, part ordering, FFprobe frame-rate parsing, FFmpeg command
building, progress and `AssemblyDiagnostics` are reused from the accepted media
implementation. `UnpublishedAssembly._prepare()` and its independent process
owner/directory creation path are never invoked. All planning/input reads run
under held read protection with explicit revalidation around planning/execution.
Matching configuration uses copy; differing configuration uses the accepted
scale/pad/setsar/concat, independent timestamp resets, libx264/AAC, rate/quality
and passthrough frame timing. Public synchronous defaults are unchanged.

### Workspace, helper and single writer

After planning, `reserve_scratch()` persists and exclusively creates the exact
generated sibling directory. The adapter performs no supervisor filesystem
writes there. Copy declares `concat.ffconcat` and `candidate.mp4`; reencode
declares only `candidate.mp4`. Accepted empty-inventory checks at binding,
authorization and resume remain unchanged. Schema 5 permits exactly one writer.

For copy, `assembly_launcher.concat_launch()` binds the complete trusted Python
launcher code, exact concat text and full FFmpeg argv in the durable intent.
The existing base Python executable runs `-I -c <code> <JSON>` inside the same
creation-contained job. The launcher checks empty inventory, creates the named
helper exclusively with `x`, flushes/fsyncs, then invokes FFmpeg without a shell,
breakaway flags or independent owner. FFmpeg inherits the job and native stdout/
stderr pipes. Its return code is propagated; helper exceptions report a semantic
execution failure and exit nonzero. Wrapper exit alone never proves whole-job
exit. Reencode directly launches the exact FFmpeg argv as the one writer.

The payload has no untracked temporary script/specification file, ambient module
lookup or arbitrary existing workspace adoption. Existing Windows command-line
length limits still apply; oversized intents fail and retain ownership, with no
fallback unjournaled path. Trusted commands/hooks remain cooperative code, not a
filesystem sandbox or proof against a privileged adversarial writer.

### Long execution, diagnostics and cleanup

Only declared writers may use `timeout=None`. They poll exact whole-job status
and bounded streamed chunks without an overall assembly deadline, checking local
revocation and waiting briefly on its event outside native/resume/authority/SQLite
locks. Final EOF reconciliation and cancellation/cleanup use separate five-second
bounds. Existing reader/default finite timeout behavior remains intact.

An optional trusted `on_exit` callback interprets final semantic diagnostics
before success, outside authority/SQLite/resume locks. Native confirmed exit,
complete EOF/byte accounting and independent cleanup receipts are still required.
The adapter reuses explicit-error detection, bounded framing/probe documents,
UTF-8 handling, progress and degraded/unknown input classification. The installed
FFmpeg's occupied `-n` output can return zero; this is explicitly rejected.
Nonzero child errors retain the accepted finalization diagnostic semantics.
Semantic failure cannot skip independent exit recording/native cleanup or become
a sealed candidate. Diagnostic prefixes may be bounded while all streamed bytes
remain counted/hashed and interpreted; incomplete interpretation cannot mean clean.

Only after those checks does the same scratch capability bind every observed
artifact, recheck complete inventory/exact native evidence around hooks and hashing,
and seal `candidate.mp4`. Copy decode remains `not_checked` in the result and maps
to the schema's `unknown` input classification. Degraded reencode evidence remains
degraded. Runtime validation is always `not_checked`, publication `unpublished`.

`cancel()`/`close()` revoke local execution. Unknown/unclean native owners and
failed/ambiguous scratch remain reachable. Cleanup success accounts for retained
scratch owners; acknowledgement loss gets one same-operation reconciliation,
never a reissue. Confirmed candidate close releases local protection only; the
task remains unfinished/running and counted with durable raw/room/path/input pins.
No settlement, refund, retry, adoption, publication or deletion is added.

## Disposable Windows verification

Evidence root: `C:\Users\Leandro\TikREC-tests\issue52-connected`.
Interpreter: `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`.
Every test invocation explicitly selects this isolated worktree as cwd and
`PYTHONPATH`; `APPDATA`/`XDG_CONFIG_HOME` select `config-empty` below the evidence
root. Base-interpreter contained helpers/probes do not require extra dependencies.
`verification-environment.json` records the actual interpreter/base executable,
imported worktree package, explicit configuration roots and installed FFmpeg/
FFprobe paths. No production defaults were read to establish this environment.

The first integration test preceded runtime implementation and failed with the
missing `tikrec.journal_assembly` module (`before-adapter.log`). This is new-feature
coverage, not a claim that an accepted foundation was defective. An initial
missing external basetemp parent was a harness setup error. Development also
found/corrected oversized pytest IDs/Windows argv in a diagnostic fixture,
a missing descendant event signal and a death probe importing pytest unavailable
to the base interpreter. These failures are retained in development logs and are
not counted as native product defects. The unchanged legacy pending-manifest
validation mismatch is described below, rather than hidden by changing defaults.

### New-path media evidence

Both connected paths start from actual generated CaptureBridge reconnect sessions,
two sealed FLVs and actual raw/arrival/session/connection/marker evidence. Copy
uses identical configurations; reencode uses 64x64 and 80x64 configurations.
Every planning probe/writer uses the durable coordinator. Complete execution,
same-attempt scratch/candidate receipts, original H fields, source/control/raw/
arrival/marker and unrelated SHA256 values, unit/FIFO/single-finalizer rules,
absent requested final destination and unchanged runtime validation state are
checked. `connected-media-evidence.json` contains commands/native identities,
hashes, candidate receipt and frame evidence for each path.

Both sets of retained parts pass the existing decode/packet-DTS checks. Whole
legacy manifest validation reports precisely `manifest_state_inconsistent` and
`output_missing`: capture completion retains finalization `pending` and no final
output, as required by this internal slice. `retained_media_checks` passes;
no whole-manifest acceptance is claimed. Candidate packet DTS and deep decode
pass. Each candidate has 12 video frames matching the accepted synchronous
comparison's PTS/duration/dimensions and media facts. These external disposable
checks do not mutate candidate validation/publication. Separate accepted assembly
tests remain regressions, not substitutes for the connected evidence.

Final-focused concrete media receipts (both also record every original control/
raw/arrival/marker hash in the external JSON):

| Path | Candidate bytes | Candidate SHA256 | Frames |
| --- | ---: | --- | ---: |
| Copy | 17,883 | `564dc75486b06c55dfe12ab6acaeccd3eeaaba46f1d53374943323a8f9ee24af` | 12 |
| libx264 | 16,855 | `675817cf334dbce51ee8efd41559f3ec1ead86ca9deb9648caa7363734326d6c` | 12 |

Original generated 64x64 source SHA256:
`880bf089561569627028361e96a834c4e083bcea6e8952043c1d8127214cce97`;
80x64 source: `49a199fcef6abaad2e75d555329a41b384843dc94c2adc17c81d6bf23321671b`.
Held 64x64 part: `ba3bd1029bbfdb81065eadd09902b0c54a32dd11abb184a9f31b630fff61f51a`;
80x64 part: `4bae5f76efb6d7768bc2a1e953f5a6600b08b96fad827f6d351fd6d4374d58a0`.
Unrelated sentinel: `033d65782b8f33c467d269583f413ba3c6ecda08ac605c9527794ddcf4bcd675`.
All remain unchanged through assembly and assertions.

### Connected ownership and failure checks

- Empty queue/single-use, one FIFO claim, competing finalizer refusal and unchanged
  running task/count/pins. A real 31.1-second contained writer exceeds the reader
  wait bound while two disjoint captures reserve, run and hand off independently.
- Helper/output collisions before launch, identity/resume and exclusive helper
  production; inventory additions after artifact binding and final sealing hook.
- Cancellation/concurrent close at intent/create/identity/resume and after semantic
  diagnostics; no late seal. Descendant survival after wrapper exit gates whole-job
  completion; cancellation leaves an unrelated exact job alive.
- Actual exact writer/descendant termination; unknown whole-job status/termination
  retains inputs and scratch. Incomplete observer/final EOF, native process cleanup
  and artifact close faults remain distinct from exit evidence.
- Zero-exit explicit/occupied-output errors (including actual installed FFmpeg),
  oversized/UTF-8 final tails, nonzero descendant failure and missing candidate.
  A final degraded tail beyond the native prefix remains degraded, not repaired.
  First execution failures survive secondary scratch bookkeeping faults.
- Candidate acknowledgement loss reconciles once or retains exact owners when
  unavailable; no adoption/refund/retry. Failed durable probes never reach scratch
  reservation or writer authorization.
- Twelve actual connected supervisor-death boundaries: post-plan, reservation
  commit/create, intent/native create/resume, semantic execution completion,
  artifact commit and candidate before/after commit/local-ready. These use a real
  one-part generated sealed capture and actual helper/FFmpeg, not a mocked runner.
  Reopen inspects only committed facts and leaves DB bytes unchanged, task/unit/pins
  retained, hashes unchanged and final output absent. `connected-death-evidence.json`
  records each case. Independent exact-job guards bound fixture cleanup.

R4–R10, schemas 1–4 refusal/schema-5 semantics and accepted synchronous CLI/service
coverage are included in the final isolated selections. Source/test files stay
frozen during the final focused/related/full runs; later checkpoint edits are
documentation only. Exact selections are saved in `focused-files.txt` and
`related-files.txt`; pytest logs and disposable fixtures remain external.

Actual final delivered-source/test suite results, with no failures:

| Selection | Result | Seconds | Log |
| --- | --- | ---: | --- |
| Focused | 129 passed | 145.95 | `final-focused.log` |
| Related, 69 modules | 651 passed, 2 skipped | 257.04 | `final-related.log` |
| Full | 2,389 passed, 9 skipped, 19 subtests passed | 328.64 | `final-full.log` |

Final verification confirms zero changes to the 361 recorded runtime/test Python
files across these runs. Skips retain existing platform/native privilege/optional
fixture limitations; none substitutes for the new Windows media/death checks.
Delivery is complete for PM review, not issue/service/release acceptance.

Actual final invocation environment and selections (PowerShell):

```powershell
Set-Location 'C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC'
$env:PYTHONPATH = (Get-Location).Path
$env:APPDATA = 'C:\Users\Leandro\TikREC-tests\issue52-connected\config-empty'
$env:XDG_CONFIG_HOME = $env:APPDATA
$env:PYTHONUNBUFFERED = '1'
$taskTests = rg --files tests | Where-Object { $_ -match 'test_journal_assembly|test_attempt_scratch|test_session_journal_scratch|test_session_journal_version|test_assembly_diagnostics' }
python -m pytest $taskTests -q --basetemp='C:\Users\Leandro\TikREC-tests\issue52-connected\final-focused'
$taskTests = rg --files tests | Where-Object { $_ -match '^tests[\\/]+test_(session_journal|capture_handoff|sealed_inputs|attempt_coordinator|attempt_scratch|owned_process|unpublished_assembly|journal_assembly|assembly_diagnostics).*\.py$|^tests[\\/]+test_(finalize|finalization_recovery|recovery_finalization|finalizing_capture_availability|live)\.py$' }
python -m pytest $taskTests -q --basetemp='C:\Users\Leandro\TikREC-tests\issue52-connected\final-related'
python -m pytest tests -q --basetemp='C:\Users\Leandro\TikREC-tests\issue52-connected\final-full'
```

Each invocation redirected all output to its matching `final-*.log` and captured
the real pytest exit code; those log/fixture names identify completed runs, not
instructions to reuse an existing basetemp. The related selection has 69 modules.
`final-source-test-sha256.json` records all 361 runtime/test Python file hashes
for the frozen tree and is compared again after verification. All changed source/
test modules remain below 300 lines (largest coordinator: 235; new adapter: 138).

## Remaining limits and next action

Directory protection does not prevent every child addition; scans/hashes and
SQLite mutation are separate cooperative boundaries, not an atomic filesystem/
SQLite snapshot. Process-death tests are not power-loss proof. Some fault fixtures
substitute trusted disposable writer work to isolate native/diagnostic behavior;
both media paths and supervisor-death fixtures use actual FFmpeg. No natural
recording or production authority/configuration/service was accessed.

No full A1–A20, Scheduled Task/service, natural-recording, publication/validation,
settlement/refund, retry/adoption, scheduler/service/API/monitor/storage/retention,
migration/cutover or #28 repair gate is passed. Schema 5 and existing accounting/
ownership/input-preservation rules remain unchanged. No dependencies/upgrades,
resource policy, production access/change/restart, #48 polling, merge/release/tag
or history rewrite occurred. Next action is PM review of the delivered commit;
stop before publication or any further successor.
