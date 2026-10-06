# Issue #52 — durable guarded same-attempt publication

## Current manifest-completion boundary — 2026-10-06

[PM decision 6012406322](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6012406322) accepts `0ca6144a` publication
and authorizes this single internal slice; earlier accepted foundations remain accepted.
Publication base `0ca6144a` is accepted. This report remains the historical
publication evidence within its stated limits. The authorized single successor is
[durable manifest completion](ISSUE_52_MANIFEST_COMPLETION.md), with fresh live
output/control proof and retained accounting; terminal settlement remains deferred.

## Authority — 2026-10-06

[PM decision 6010639470](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6010639470)
accepts `1e1e1caeca6586a37313bcb4631c4c0d231ddf48` candidate validation and
authorizes this single internal publication slice. Accepted R1–R10, assembly and
validation foundations remain accepted. The isolated Windows worktree was pulled
before inspection, current and clean; MODEL GATE / PROCEED selected GPT-6.1 Sol —
High, Complex, owner decisions None. Earlier delivery checkpoints are historical.

#52 remains OPEN / SINGLE ACTIVE; #48 OPEN / PAUSED (Gracie-only raw/Ward OFF);
#28 unresolved. Use `Refs #52`, preserve pushed history and the flagged historical
`Closes #52`. Delivery stops for PM review, with no automatic successor.

## Connected live authority

`JournalPublication` owns the accepted `JournalValidation` and original
`AttemptCoordinator`, claiming at most one sealed FIFO session. An empty queue
returns `None`; repeated invocation is refused. It explicitly selects publication
rights at original candidate acquisition. Only the candidate receives DELETE
access in addition to its existing read/write access; helpers do not. Existing
assembly-only zero-sharing and validation-only read-sharing defaults remain.

A native probe demonstrated that ordinary FFprobe/path opens cannot coexist with
the retained DELETE owner. Publication-capable validation therefore uses exactly
three fixed FFprobe commands with `-fd 0 fd:` and the original candidate's seekable
native file object as stdin. A noninheritable parent owner remains continuously
held. `DuplicateHandle` passes only GENERIC_READ to the contained suspended child;
the normal explicit handle-inheritance list and creation-time Job Object apply.
No pathname reopen, adoption, independent subprocess, temporary media copy or
write/rename authority is passed to a validator. Hashing and duplicate stdin share
a cursor; it is rewound after the final pre-resume proof while still suspended.

The existing readability prerequisite is proved through that retained descriptor
only for this explicit phase. Inspection/container/video/duration/audio warning,
full decode and packet-DTS checks reuse accepted semantics. Ordinary CLI/service
readability checks, finite readers, validation-only command vectors and pending
manifest handling remain unchanged. Diagnostics, EOF, exact job cleanup and
bounded long-validation cancellation retain their accepted contracts.

`CandidatePublication` requires the completed successful live validator, original
coordinator/scratch/candidate handle and descriptor, and a single local allocation.
It cannot be reconstructed from a journal view. Validation-only defaults and
historical passed receipts do not grant publication capability. Fresh checks bind
the exact original H, input seal/marker, immutable assembly/writer/candidate and
complete validation chain, all scratch artifacts, destination claim and pinned
parent. Candidate bytes are SHA-256 checked through the same descriptor.

## Durable preparation and separate observed result

Schema 6 cannot honestly append publication facts to its immutable candidate or
validation tables. Authorized minimal **schema 7** adds only immutable/keep-triggered
`publication_preparations` and `publication_results`, plus version/fingerprint.
Schemas **1–6 are refused and preserved unchanged**, without migration/cutover.
The schema-6 fixture is frozen verbatim from accepted `1e1e1cae`.

Preparation commits before any native move and records session, token, owner,
original H operation/revision, seal/marker hashes, original candidate (including
writer execution), exact validation authority/receipt, complete artifact inventory,
workspace, exact claimed output path/native namespace and parent native stamp.
The directory stamp's volume/file ID binds its native object; mutable directory
last-write time is not treated as immutable after child creation/rename.

The separate observed result binds preparation operation/hash, destination native
identity and the unchanged candidate's native file ID/size/write stamp/SHA-256.
It is appended only after rename and complete post-operation proof. The candidate,
assembly and validation rows remain immutable historical `not_checked / unpublished`
evidence. A preparation with no result reports uncertainty; it never means completed
publication. Reopen reads committed facts only and does not inspect paths to infer
success or reconstruct an owner.

## Native no-replace transition and exact successor

`NtSetInformationFile(FileRenameInformation)` acts on the original DELETE-capable
candidate handle, relative to the original pinned output-parent handle, with
`ReplaceIfExists=FALSE`. There is no release/reopen, pathname-parent resolution,
overwrite, copy, fallback reencode or uncertain-operation replay. Microsoft documents
[no-replace and root-relative rename fields](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info).
The implementation refuses unsupported native results, cross-volume/parent/claim
conflicts, aliases/reparse/multiple links, collisions and stale identities. Only
local fixed storage and an immediate already-reserved MP4 name are admitted.

Cancellation's local gate and a short journal read fence serialize revocation
against the one native operation. Scans, hashes, waits and caller hooks remain
outside the fence. Cancellation may win before rename; if rename wins, later
cancellation prevents fresh result authority and retains the moved file.

After a confirmed native return, the local capability models only this exact
candidate-to-output successor. The original handle/descriptor remain open with
write/delete protection. Generic scratch checks remain strict. Only that local
successor accepts candidate absence in scratch, checks every unchanged helper and
complete remaining inventory, and verifies the same file object at the exact output
namespace. Unexpected replacement, extra scratch files, size/stamp/hash/link drift
or parent changes are rejected before/after preparation, rename and result commit.

An uncertain native return is never repeated: the original possibly-moved owner
stays reachable even if its local pathname metadata has not advanced. First errors
remain distinct from bounded secondary journal/cleanup errors. Preparation/result
acknowledgement loss reconciles the exact operation once, without reissuing it;
unavailable reconciliation remains failure even if historical facts committed.

## Retained accounting and limits

Observed publication does not complete the manifest or session/task, settle/refund,
release a unit, raw/room/path claims or local/durable pins, or delete retained
evidence. `close()` revokes execution and closes proven child controls but returns
incomplete cleanup while original input/workspace/helper/output owners remain.
Source/raw/arrival/control/original-H and unrelated bytes stay unchanged. Unknown
validation lifetime stays pinned and cannot prepare publication. Two disjoint
capture bindings remain available; cancellation controls only the exact owned job.

Filesystem observations and SQLite commits are separate. Commit-window namespace
changes can leave immutable historical records for previously observed proof;
post-commit revalidation rejects live success, retaining owners without granting
retry/adoption. Directory pins deny rename/deletion but do not prevent new children.
This is cooperative namespace and process-death evidence, not an atomic filesystem/
SQLite snapshot, power-loss or adversarial privileged-writer guarantee.

## Verification

Final delivered source/test tree: **no failures**.

| Suite | Result | Seconds | Log |
| --- | --- | ---: | --- |
| Focused — 5 modules | 72 passed | 308.48 | `focused-delivery.log` |
| Related — 78 modules | 755 passed, 2 skipped, 17 subtests passed | 599.82 | `related-delivery.log` |
| Full — all tests | 2529 passed, 9 skipped, 19 subtests passed | 955.95 | `full-delivery.log` |

All **388 source/test SHA-256 hashes remain unchanged** across these final runs;
`source-test-hashes-delivery.json` and `final-tree-verification.json` retain the
inventory/results. All task-owned Python modules are under 300 lines; whitespace
review passes. Every focused new-path/schema check executes on Windows; broader
skips retain existing platform/environment limits. Accepted R1–R10 and connected
assembly/validation, synchronous CLI/service and original `test_live.py` assertions
pass under explicitly isolated defaults. No assertion or product default is weakened.

External disposable evidence root: `C:\Users\Leandro\TikREC-tests\issue52-publication`.
Earlier validation/scratch/assembly evidence directories are preserved.

The exact 5 focused and 78 related module lists are retained in
`focused-delivery-files.txt` / `related-delivery-files.txt`; full runs all `tests`.
Every suite uses its own new `--basetemp` and empty APPDATA/XDG_CONFIG_HOME under
that evidence root, explicit worktree PYTHONPATH and unbuffered output. The
interpreter is `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`.
Installed FFmpeg/FFprobe are explicit absolute paths under the existing WinGet
FFmpeg package. Native validator fixtures use the existing Windows .NET compiler;
no runtime/dependency is installed or upgraded. Commands capture pytest's exit
code before displaying logs. Completed basetemps are evidence, never reused.

Connected copy output: **17,883 bytes / 66 packets**,
`564dc75486b06c55dfe12ab6acaeccd3eeaaba46f1d53374943323a8f9ee24af`.
Connected libx264 output: **16,855 bytes / 67 packets**,
`675817cf334dbce51ee8efd41559f3ec1ead86ca9deb9648caa7363734326d6c`.
Both preserve exact native file ID/size/write stamp and SHA-256 through promotion,
with passed inspect/decode/DTS receipts. Original source/raw/arrival/control/H,
input seals/claims and unrelated hashes remain unchanged. Task/unit/pins remain.

Coverage includes collisions before preparation and inside the actual native
rename boundary, hard-link destination aliases, native replacement/write/parent
rename refusal, injected identity/parent/volume drift, complete inventory changes,
held-descriptor byte changes with restored FILETIME, corruption/decode/diagnostic/
UTF-8/observer/EOF failures, descendants/unknown lifetime/native cleanup, first
plus secondary faults, cancellation on both sides of validation resume and the
publication fence, exact preparation/result acknowledgement loss and unavailable
reconciliation, immutable rows and refusal of repeated/historical authority.
Tests permit two disjoint capture bindings and prove unrelated-job survival.
Actual fixture storage is one local fixed volume; wrong-volume refusal uses
injected conflicting native identity, without accessing another media volume.

Eleven real `TerminateProcess` supervisor deaths cover pre-preparation, preparation
before/after commit, post-preparation, pre-fence, immediately before/after the
native rename (including before local successor acknowledgement), post-native,
and result before/after commit/post-result. Independent supervisor/job handles
prove exit. Read-only reopen preserves database bytes and reports committed facts
only, including promoted-but-unconfirmed states, without adoption/retry/refund.
`publication-media-evidence.json`, eleven `publication-death-evidence.json` files,
suite logs and frozen hash inventories retain the evidence outside Git.

### Development evidence and corrections

- Added connected publication regressions before implementation; unchanged accepted
  code fails collection because the publication module does not exist. This is an
  absent-feature baseline, not a regression attributed to accepted foundations.
- Native probe: ordinary path readers fail against DELETE ownership, while all three
  FFprobe checks succeed with seekable retained stdin. No runtime/dependency upgrade.
- The first connected run exposed the legacy path-readability prerequisite. The
  explicit descriptor proof now supplies that check without changing defaults.
- The next run exposed shared cursor advancement by pre-resume hashing; rewind after
  the final proof corrected it. Both actual copy/libx264 candidates then validated
  and moved; two assertions required canonical JSON list/tuple comparison.
- A compatibility command named a nonexistent test module and collected no tests.
  The corrected command uses the actual module inventory. Default native creation
  calls retain their prior signature for existing portable state doubles.
- A documentation script hit the Windows default text encoding; no project-state
  changes occurred in that failed pass. The inserted design note was corrected
  and all Markdown now decodes as UTF-8. No frozen source/test file changed.
- Corrected development compatibility/fault selection: **67 passed**, 108.29 s;
  includes existing portable process and standalone assembly regressions.
- Development selections: 46 publication/schema checks passed (141.97 s), including
  eleven real supervisor deaths; 19 connected lifetime checks passed (57.01 s).
  Later added immutable/native-pin/default-capability/commit-window regressions are
  included in the final suites; earlier selections are not final delivery evidence.

## Remaining gates and safe resume

Only disposable generated queued/sealed media is accessed. Natural-recording
validation, power-loss, full A1–A20, service and Scheduled Task acceptance remain
outstanding. No production access/change/restart, service/API/monitor/scheduler
wiring, manifest completion, settlement/refund, retry/adoption, retention execution,
#48 polling, migration/cutover, dependencies/runtime/resource-policy changes, merge,
release or tag. No `ffmpeg -f null -` corruption check is used.

Next: PM review of this partial slice. Pull this isolated branch and reconcile the
latest issue decision/report; historical records alone never authorize replay.
