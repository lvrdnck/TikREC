# Issue #52 — isolated unpublished assembly evidence

## Authority and scope

2026-10-04: [project-manager review 5980268720](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5980268720)
accepted `b2bff05f` R6–R7 and selected only closed FLVs -> an attempt-owned,
unpublished MP4 candidate. Accepted R4–R7 reviews were not repeated. The existing
isolated `codex/capture-journal-handoff` was pulled (already current), repository/
open issues reconciled, and MODEL GATE / PROCEED used GPT-6.1 Sol — High.
#52 remains OPEN / SINGLE ACTIVE; #48 OPEN / PAUSED; #28 unresolved.

The structure-only extraction is `c22c482f`; behavior and this report follow in
a separate task commit. Nothing merges into the deployed editable checkout.

## Internal contract

`UnpublishedAssembly` takes canonical session/attempt UUIDs, explicit absolute
closed input paths, absolute FFmpeg/FFprobe executables, a fresh nonexistent
attempt directory, a direct-child `.mp4` candidate and mandatory before-resume
authorization. The parent directory must exist. Scratch must be separate from
source evidence; duplicate inputs, relative paths, occupied scopes/candidates and
out-of-scope candidates refuse. Exclusive directory creation never adopts an old
attempt. Candidate absence is checked again after authorization, before resume;
FFmpeg retains `-n`. No final destination is accepted by this API.

**Trusted preconditions:** the caller owns the scratch namespace and supplies
immutable, closed FLVs. Hooks, progress observers and any injected process factory
are trusted caller code; the factory must return a fresh attempt-bound
`OwnedProcess`. This is not native sealed-input reopening, durable launch/claim
authorization, protection against an adversarial scratch writer, or permission
to consume real queued media. A token alone never authorizes any child.

Shared `finalize_media` / `finalize_plan` logic owns numeric part ordering, AVC
selection, copy concat manifests, maximum dimensions, per-part rate probes,
scale/pad/setsar/concat, independent video/audio timestamp resets, libx264/AAC,
nominal encoder rate, passthrough frame timing, filter time base and progress
command flags. Encoder quality defaults are unchanged. Existing decode/progress
classifiers are reused. The public `finalize_parts` signature, injected runner/
frame-rate contracts, synchronous CLI/service defaults, atomic promotion and
failed-temporary/manifest deletion remain unchanged. Internal helper exports and
the legacy nominal-rate injection point are preserved.

Every new-path child, including each required FFprobe, uses `OwnedProcess`.
Phases run sequentially; prior exit and control release are required before a
successor. Owners enter the attempt's reachable child inventory before creation.
Whole-job zero-member/root-handle exit proof and both native pipe EOFs are required.
Unknown lifetime retains native controls and fails with an `AssemblyError` holding
the attempt, child owners, original error, evidence and secondary diagnostics.
Reconcile the retained exact owner; do not retry the single-use invocation.

Cancellation is irreversible through preparation, probes, suspended authorization,
execution and final draining. Running children are polled without an overall time
limit. Each final EOF reconciliation and exact-owner cancellation/cleanup call
has a five-second bound; the existing runner's per-call wait ceiling is never
used as a thirty-second assembly deadline. No stall watchdog/resource policy is
introduced. Trusted callbacks and stalled synchronous native APIs retain the
process report's limits.

`OwnedProcess.cancel/close` add optional streaming observers so cleanup/cancellation
can deliver tails; existing calls keep their defaults. Native read/status/handle
failures retain original and secondary evidence. Successful exit does not erase
a stream error. All candidate, failed-partial and helper-manifest files are kept
on success, failure, cancellation and uncertainty: this primitive deletes no
scratch artifacts and writes no source/control/publication/journal files.

## Diagnostics and readiness

The parser observes streaming chunks independently of the runner's bounded byte
prefix. It incrementally decodes UTF-8, frames CR/LF and the final unterminated
line, and feeds existing progress/input-decode classifiers. Framing retains at
most 65,536 characters per line; probe stdout at most 65,536 bytes. An oversized
line is discarded through its real delimiter, not split into invented messages.
Invalid/split-incomplete UTF-8, overflow, callback failure, missing native EOF or
collected bytes bypassing observation explicitly make diagnostics incomplete.
Known degradation survives incompleteness; otherwise a reencode cannot claim
clean input. Stream copy retains `not_checked`, never decoded-source cleanliness.

`candidate_ready` requires successful whole-job exit, complete streaming/EOF,
successful native cleanup, no explicit execution failure and a nonempty candidate.
The result separately reports `media_validation=not_checked` and
`publication=unpublished`. A degraded reencode may be execution-ready, as in the
existing synchronous finalizer; that is not a #28 correction or validation proof.

An actual installed-binary probe found that FFmpeg `-n` refuses an occupied
output **with exit code 0**, leaving its bytes unchanged while stderr says
`Error opening output file`. Consequently zero exit plus an existing file is
insufficient: before-resume collision fencing and bounded recognition of explicit
tool execution failures prevent false readiness. Fatal tool evidence and final
parser errors are interpreted before cleanup so secondary cleanup cannot replace
the first failure. Decode degradation is classified separately.

## Regression development and actual verification

Evidence/config/state/temp roots are entirely disposable and outside Git:
`C:\Users\Leandro\TikREC-tests\issue52-assembly-20261004`.
`run.py` redirects APPDATA/LOCALAPPDATA/XDG configuration/state/TEMP/TMP and
pytest basetemp, imports the isolated worktree and disables pytest cache.
Windows x64 build 26200; existing Python 3.12.10 / SQLite 3.49.1;
existing FFmpeg/FFprobe `N-124716-g054dffd133-20260531`. No upgrade/dependency.

- Characterizations before extraction: **34 passed / 17 subtests, 0.39 s**;
  same selection after structure extraction: **34 / 17, 0.35 s**.
- Initial new-boundary regressions: **12 failed, 0.34 s**, because the requested
  modules did not exist. This is an absent-API baseline, not twelve reproduced
  defects in the old synchronous path.
- Intermediate logs retain two Windows environment-variable setup errors from
  an oversized pytest parameter ID (fixed by short IDs), and a state double that
  incorrectly confirmed exit during its simulated running interval (fixed).
- The expanded pre-correction focused run exposed the real collision gap:
  **165 passed / one failed / 17 subtests**. Related **1,217 passed / two failed /
  six skips / 17 subtests, 135.80 s** and full **2,157 passed / two failed /
  seven skips / 19 subtests, 238.88 s** also exposed the removed legacy nominal-rate
  injection alias. Both failures were fixed; the existing capture test was kept.
  Independent exact-job guards cleaned all disposable children after failures.
- Corrected focused delivery: **198 passed / 17 subtests, 8.25 s**
  (`focused-delivery.log`). Includes assembly/parser, unchanged process/R6–R7,
  synchronous finalizer/frame-rate/decode/progress and direct capture tests.
- Related delivery: **1,222 passed / six skips / 17 subtests, 230.89 s**
  (`related-delivery.log`): assembly/process/finalization/frame-rate/decode/progress,
  capture/journal/lifecycle/live/writer/recovery/retention and validation.
- Full isolated delivery: **2,162 passed / seven skips / 19 subtests, 152.73 s**
  (`full-delivery.log`), including 47 added cases over the accepted 2,115 baseline.

Portable state tests cover both commands, phase ordering, fresh authorization,
cancellation before run/authorization/after resume/between probes, unknown exit
with reachable owner/no successor, collisions, unchanged source/sibling/control
bytes, failed partials, missing candidate, parser overflow/UTF-8/EOF/accounting,
callback/cleanup first-error ordering, malformed/oversized probe refusal without
fallback and a simulated forty-second running interval without an assembly
deadline. The simulation is not a native elapsed-time benchmark.

Real Windows regressions use contained disposable children and independent exact
Job Object guards: blocked suspended authorization cancellation; running/repeated
cancellation with preserved partial/tail; final stderr released after collection
but before exit observation; three native child phases with degradation beyond
the retained prefix and final split UTF-8; failed partial/exit 7; native query
uncertainty with retained owner and explicit reconciliation; secondary exact-handle
cleanup failure; and candidate creation during authorization without overwrite.
R4–R7, owner-death, descendants, last handle, nesting, identity, stream and capture/
journal/lifecycle/retention regressions are preserved. No failed test leaves
uncontrolled children.

## Actual generated media

Two short ordered AVC/AAC FLVs use the existing local fixture recipe. Matching
64×64 AVC uses one owned FFmpeg. Differing 64×64 / 80×64 AVC uses two owned
FFprobes then FFmpeg; target 80×64, nominal rate 10/1, existing filter timing and
libx264/AAC settings. Each generated result has **12 video frames**, identical
per-frame PTS/duration/dimensions and media facts to the synchronous comparison.
This is a fixture comparison, not universal output-byte identity.

Both sources pass existing retained-part decoding and packet-DTS checks; both
candidates pass existing packet-DTS and deep-output validation. Native children
have exit 0, zero job members, both EOFs and released controls. Requested final
destinations remain absent. No session/journal is consumed or completed.

Focused delivery native identities (historical observations, never launch/kill
authorization):

| Path / phase | Retained PID / creation FILETIME | Exit / active / EOF |
| --- | --- | --- |
| Copy assembly | 62644 / 134356020351516308 | 0 / 0 / both complete |
| Reencode first rate probe | 48048 / 134356020358569064 | 0 / 0 / both complete |
| Reencode second rate probe | 26164 / 134356020359026347 | 0 / 0 / both complete |
| Reencode assembly | 50748 / 134356020359495732 | 0 / 0 / both complete |

| Artifact | Bytes / SHA-256 |
| --- | --- |
| 64×64 source part | 8,823 / `880bf089561569627028361e96a834c4e083bcea6e8952043c1d8127214cce97` |
| Differing 80×64 source part | `49a199fcef6abaad2e75d555329a41b384843dc94c2adc17c81d6bf23321671b` |
| Copy candidate | 17,883 / `e43c1036c8e824c0b7498f6b5a7cff330147d5f0d49b361d74d0471bd6610586` |
| Reencode candidate | 16,855 / `675817cf334dbce51ee8efd41559f3ec1ead86ca9deb9648caa7363734326d6c` |

All source FLV and co-located raw/arrival/control fixture hashes are unchanged:
raw `0b2fe41617dd5441dbd4799a87657d6952c50dc3b954703456c88d469395b7f8`;
arrival `099baa3f2b834c86add67ac489d861ffef688781abc1fd92691a3811a529e9ee`;
session `e6aeb6b311171168fd388af333af9293b39a481205039801ea23c71e5b45a292`;
connections `b4909342d3495ec884bd986865c4efb78608c9dd733f085318c2bbf7e87902fc`.
These co-located controls/raw/arrival files are disposable hash-preservation
stand-ins, not a real capture inventory or raw-to-retained correspondence proof.
Detailed commands/identities/hashes are retained as each media test's
`assembly-evidence.json`. Degraded-source classification is separately exercised
by controlled diagnostic fixtures, not inferred from clean generated validation.

## Remaining gates and safe next action

This completes only the internal media-execution boundary. No full A1–A20 service
case or deployed Scheduled Task gate is passed. Durable attempts/launch persistence,
native sealed-input authority, successor/restart orchestration, validation policy,
publication receipts/promotion, settlement/retry, queue scheduling/service/API/
monitor/bootstrap/storage/retention-reader/destructive-recheck/migration/cutover
remain later reviewed work. Existing schema 3, schema-1/2 refusal, H/history/FIFO/
stop/admission/eight-unit accounting and capture/raw contracts are unchanged.

No production access/state/config/media mutation, restart, retention execution,
#48 polling, watchdog/resource/priority policy, benchmark, remote worker, runtime/
dependency upgrade, release/tag or merge. Primary `main` remains `fe28327c` with
42 unrelated artifacts preserved. Generated local fixtures do not establish
natural recording/source health or #28/#48 acceptance; no LIVE was manufactured.

Final isolated verification passed. After normal task-only commit/push, stop for
project-manager review (GPT-6.1 Sol — High). No owner product decision is pending;
do not automatically start a worker or use journal-owned production inputs.
