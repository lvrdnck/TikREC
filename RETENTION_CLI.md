# Owner-facing retention CLI (unreleased v0.11 development)

Windows is the sole active and planned runtime. The owner's 2026-10-01 decision
supersedes #53/#54; their unreleased Fedora/Linux additions are removed and no
Fedora gate remains. **Issue #51 is completed / PASSED** under the 2026-10-01
project-manager decision. The public retention CLI independent review gate and
Windows real-media retention validation are both PASSED. Age is restored to its
original unset state and the one-deletion authorization is consumed; #51
authorizes no further destructive validation, retry, repair or second deletion. All
Gracie, forensic, diagnostic, raw-copy, protected, ambiguous, active/recoverable
and durable-job-linked sessions remain excluded. The platform rollback performed no #51
deletion. v0.10.0 remains the current released version; v0.11.0 is unreleased
pending normal release readiness/bookkeeping. Earlier dated evidence below
describes historical validation attempts, not current authorization.

**Status: IMPLEMENTED IN DEVELOPMENT — PUBLIC CLI GATE PASSED; REAL-MEDIA
VALIDATION PASSED; #51 COMPLETED; ROOT CHANGE RECONCILED AS A.**

Read-only reconciliation (2026-10-01) identifies the exact offload command at
21:22:09.857–21:22:23.268 CEST, after retention completed and immediate scope
verification passed. The other chat restored Videos afterwards; current local
and mounted Drive copies match its source hash. Audit remains byte-for-byte
unchanged and targets only Eliss. `Unsorted` differed only in directory size;
identity/timestamps stayed unchanged, and read-only APIs reproduce both sizes.
Its historical query cause is unresolved; no content mutation is established.
Classification **A — Explained unrelated change**. The project manager accepted
the exact Eliss audit/scope proof and this reconciliation as a full #51 PASS.
No production retention defect is demonstrated. No further deletion is authorized.

### Historical validation checkpoints (superseded by the final PASS)

Earlier Windows #51 check (2026-10-01, 21:05–21:24 CEST): the naturally idle root
cleared the public age-unset plan. The approved temporary age-1 rule allowed one
ordinary non-Gracie Eliss deletion through the exact-confirmation public CLI.
It returned COMPLETE/0 with a 12-event durable audit, final MP4 last, and exact
immediate scope verification. During the later public plan, an unrelated Gracie
output disappeared from the root; all 48 remaining sessions then reported
`evidence_conflict`. Its source/destination/actor is unproven; no repair was
attempted. The deleted target is absent, but full validation remains NOT PASSED.
Age was restored to unset through the normal public config command after proven
completion. Service ownership and durable jobs remain unchanged. The attempt
allowance is consumed; safe next work is read-only reconciliation, never another
delete under the existing authorization. Details and hashes:
[ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).

Earlier Windows #51 check (2026-10-01, 20:22–20:23 CEST): configuration selects
`C:\Users\Leandro\Videos` with age unset. An active Gracie writer makes the
five-second root observations differ; the one public `retention plan --json`
exits 0 with all 49 sessions `needs_attention / evidence_conflict`. This is a
blocked advisory result, not conflict clearance or deletion authorization.
No age rule was set, candidate selected or delete command issued; no restoration
is needed. The single-deletion allowance is unused and real-media validation is
NOT PASSED. Resume only after natural inactivity/stability through fresh checks;
keep the archive and all Gracie/forensic/diagnostic/job-linked exclusions intact.
See [ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).

Earlier checkpoint:
Under issue #51's owner approval on 2026-09-30, the six manifestless test evidence
sets and three matching MP4s were preserved in an external archive with verified
hashes and metadata. The age-unset public plan still reported root-wide conflict
while live writer evidence changed. Zero uncertain claims remained afterward,
but initial/final root snapshots differed as active Eliss/Gracie partials grew.
The task stopped before setting the age rule or issuing a delete command.
The one-deletion authorization remains unused and real-media validation is
NOT PASSED; see [ISSUE_51_RETENTION_VALIDATION.md](ISSUE_51_RETENTION_VALIDATION.md).

Whole-root stability is required even for advisory eligibility: changing evidence
in one immediate claimant can invalidate the complete observation. A growing
recording may therefore make every session display `evidence_conflict` even
when all UUID/output claims are readable. Destructive execution also needs an
exclusive root lifecycle lease and refuses while a cooperative writer owns it.
Wait for natural inactivity and a stable fresh plan; do not stop recordings to
manufacture eligibility.

## Earlier #51 discovery checkpoint

The 2026-09-30 issue #51 read-only attempt used the normal public plan against
the configured Windows root. It initially found 52 immediate sessions with
`needs_attention` / `evidence_conflict`; a later snapshot found 53 after a new
Eliss recording began. Six manifestless `test*.parts` directories make root
claims uncertain, which intentionally promotes every immediate session to
`evidence_conflict` regardless of its individual classification. A separate
read-only pass found 16 current completed sessions otherwise `retained` by the
disabled age rule, 27 older/legacy sessions `ineligible` because creator
identity is absent, and four other individually conflicting sessions (three
raw-copy diagnostics and an active writer partial). No deletion was attempted. Real-media
validation is NOT PASSED; safe segregation or a clean existing root and any
age-policy change need owner direction before one candidate can be reconsidered.
Issue #39 corrected the post-append intent reporting gap found in the 2026-09-28
review. Audit append marks progress immediately after successful intent sync;
faults after append returns report an after-intent outcome. A new independent
review at `f99528f` found that a failed or interrupted CLI `COMPLETE` output write
after the executor returns incorrectly reported `PARTIAL`/exit 3 despite a
synced `completed` audit event and completed removal. Issue #40 corrected that
result boundary. The fresh review at `653f5fe` found two remaining reporting
gaps: an interrupt between successful OS intent `fsync` and the durability
callback could still
claim no intent existed, and a failed after-intent stderr diagnostic could
escape without exit `3`. Issue #41 records the sync-in-progress state before
the syscall, reports an interrupted or failed sync as uncertain `FAILED`/3,
and makes failure diagnostics best-effort. The NEW review at `cc0824d` found
that a cleanup fault after synced `completed` but before executor return still
reports `PARTIAL`/3 for a proven completed deletion. Issue #42 now publishes
proven completion in caller-owned progress immediately after `completed` sync,
before executor cleanup. Later cleanup faults retain `COMPLETE`/0 and report
their cause and operation context when diagnostics are available; faults during
the sync remain non-complete/3. The NEW review at `b8ad110` found that a
secondary audit/lifecycle cleanup fault can replace the original after-intent
execution cause in `FAILED`/`PARTIAL` output. A post-intent `SystemExit` can
also escape without exit 3 or operation context. Issue #43 now preserves the
first operation fault before audit/lifecycle cleanup, reports a later cleanup
fault separately when possible, and classifies post-intent `SystemExit` as an
incomplete exit 3 with operation context. The NEW review at `3850d8c` found
that after synced `completed`, a later cleanup fault can hide the first
post-completion interruption or cleanup error from `COMPLETE`/0 diagnostics.
Issue #44 now preserves the first post-completion operation or audit cleanup
fault before later cleanup can replace it, and reports later faults separately
when stderr works. The NEW independent review at `1b38b65` found that an
inner held-artifact cleanup fault can still replace the first post-intent
proof/removal fault before executor progress captures it. Issue #45 is the
bounded correction for that finding. It now preserves the first inner
artifact, proof, removal, or handle-entry fault before held-handle or
policy cleanup can replace it. The original type reaches the failed audit
event and the public incomplete reason; later inner cleanup faults are
reported separately when stderr works. The NEW review at 2ccf464 found that
two faults within policy-lock cleanup can still replace the first known cause
before inner preservation runs: the incomplete public reason and persisted
failed.error_type can name the later fault. Audit cleanup can also be lost
from secondary diagnostics when lifecycle cleanup subsequently fails.
Issue #46 now captures the first body or policy-lock cleanup fault before
later close, owner-release, or notification faults; later cleanup errors are
secondary diagnostics. Audit cleanup before completion is retained when
lifecycle cleanup also fails. A NEW review at `75ffb1d` found a further
audit/lifecycle teardown gap (#47): audit-entry close can mask the first
pre-intent validation fault and let a later `SystemExit` escape, while a
lifecycle unlock fault can be replaced by later handle-close failure. The
same close fault can leave the process lifecycle registry occupied after
the OS handle closes. Issue #47 now preserves the first audit-entry or
lifecycle teardown fault and records later close faults separately. The
in-process lifecycle registry and writer slot are released once even when
cleanup fails; acquisition rollback also releases partly registered ownership.
The NEW independent review at `72996a7` found a remaining pre-intent result
gap (#50): a first `SystemExit` during preview output or audit-entry validation
escapes the public command instead of returning `REFUSED`/1. Later cleanup
faults do not replace that first cause, but the owner receives no refusal
diagnostic. No intent or removal occurred in the disposable reproductions.
Issue #50 now classifies a pre-intent `SystemExit` as `REFUSED`/1, retaining
its reason, selected UUID and absolute root, and the no-operation notice.
Later audit/lifecycle faults remain secondary; broken stderr does not alter
the exit. The public CLI gate remains NOT READY until another NEW independent
review passes. Separately authorized real-media validation follows a passing gate.
The NEW independent review of `f3dd917` found no blocker after corrections
#39–#50. Six fresh disposable Windows fault probes and the native Windows,
isolated full offline, and applicable WSL/POSIX suites passed. The public CLI
gate is PASSED; that review preceded the owner authorization now recorded in
issue #51. No real-media retention deletion occurred in that review; the later
#51 attempt, reconciliation and final project-manager PASS are recorded above.
The local CLI workflow below exists in the development checkout; it is
not in the current
v0.10.0 release. v0.11.0 is unreleased. This contract is for a local, explicit
Windows workflow under the cooperative-filesystem boundary in [SPEC.md](SPEC.md).

## Commands and scope

```text
tikrec retention plan [ROOT] [--json]
tikrec retention delete SESSION_UUID [ROOT] [--confirm SESSION_UUID]
```

`plan` retains its existing name and root selection: `ROOT` is the selected
recording directory, or the configured `output_directory` when omitted. It works
on Windows and POSIX. `delete` uses the same root selection, accepts exactly one
canonical lowercase session UUID, and is the only planned destructive entry
point. It accepts neither a plan file/token nor a session directory, creator,
date range, wildcard, or multiple UUIDs. `--confirm` is a confirmation value,
not a target selector. The global `--config FILE` keeps its existing meaning.
The root and UUID are printed back before any confirmation, so an implicit
configured root cannot be mistaken for another location.

There is no HTTP, remote CLI, Web UI, service-triggered, background, scheduled,
disk-pressure-triggered, bulk, or POSIX destructive operation in this
implementation.
Automatic cleanup and release/tag work are separate future decisions.

## Read-only plan

The human display gives one row or short block per immediate `.parts` candidate:
canonical session UUID when proven (otherwise `unknown`), creator (or
`unknown`), completion/end time (or `unknown`), classification, protection
state and reason, final MP4 path, retained-parts directory, and an owner-readable
reason. It shows the safely observed regular-file count, FLV part count, and
approximate final-MP4 bytes, retained-parts bytes, and their total. Count and
bytes are `unknown` when safe, stable inventory cannot be proven;
the UI must never follow a symlink or infer missing evidence as zero bytes.
Directory overhead is excluded. The display may summarize control and recovery
evidence counts without printing low-level hashes or transport details.

The five existing planner classifications keep their meaning:

| Classification | Owner-facing explanation |
| --- | --- |
| `eligible` | Completed, unprotected session has reached the configured age threshold. |
| `retained` | Age retention is disabled or the session is not old enough. |
| `protected` | Creator is explicitly protected. |
| `ineligible` | Unsupported source, unknown creator, or incomplete session. |
| `needs_attention` | Conflicting, changing, unsafe, or insufficient evidence needs manual inspection. |

Show the more specific existing planner `reason` alongside that explanation.
`--json` preserves existing keys, including numeric `ended_at` and nullable
`protected`, and adds `file_count`, `flv_part_count`, `final_output_bytes`,
`retained_parts_bytes`, and `total_file_bytes` to each session. These new
nonnegative integer fields are `null` when unproven; human end times are
rendered in UTC. The plan is a current observation, not a
promise that a later deletion will be allowed. Neither viewing nor saving it
grants authority. The CLI must not pass its result to the executor as a deletion
authorization. Read-only planning remains available on POSIX.

## Delete preview and confirmation

On Windows, `delete` validates the syntax, root, and target and prepares a
read-only, exact-target preview. A target absent from the root or classified
other than `eligible` is refused without a confirmation prompt. The preview is
stronger than the ordinary plan: it binds the root and selected session claim,
creator, end time, final output, exact artifact names/identities/sizes and file
bytes sufficiently to detect a change between display and execution. It is a
**restrictive comparison guard only**; it never replaces the executor's fresh
whole-root planning, authorization, policy/job checks, audit validation, or
per-artifact checks. The preview should not hold the exclusive root lease while
waiting for user input.

Immediately before confirmation, print a compact summary like:

```text
Retention deletion preview — permanent
Root: C:\Recordings
Creator: @alpha                  Session: 123e4567-e89b-12d3-a456-426614174000
Ended: 2026-09-01T10:15:00Z    State: eligible (age threshold reached; not protected)
Final MP4: C:\Recordings\alpha-20260901.mp4
Retained parts: C:\Recordings\alpha-20260901.parts
Removal: about 4.2 GiB across 6 files, then the empty parts directory
Order: retained artifacts and controls first; final MP4 last
Deletion is permanent. TikREC will recheck eligibility and evidence after confirmation.
```

Unknown or unstable counts/bytes refuse deletion rather than presenting an
apparently complete preview. The displayed count and size are approximate
filesystem observations, not a promise of reclaimed disk space. Do not show
signed URLs, transport data, byte hashes, or low-level forensic fields.

Without `--confirm`, require an interactive terminal and prompt for the exact
canonical UUID shown in the summary. Compare the entered bytes after removing
only the terminal line ending: no case folding, trimming spaces, prefix match,
or generic `yes`/`--yes`. With `--confirm`, its value must exactly equal the
positional UUID; this is the explicit noninteractive path and never prompts.
Missing confirmation on noninteractive input, mismatch, EOF, and cancellation
refuse without calling the executor. No confirmation is cached or reusable.

After confirmation, the executor must derive fresh authority under its
exclusive lifecycle lease. It must compare that authority with the preview
guard and refuse if root/volume identity, all root session claims,
retention policy, selected session claim, creator, end time, output, or exact
artifact set/identity/size/bytes changed. Current job references and lifecycle
ownership must also pass fresh checks. Even
an otherwise newly eligible replacement for the same UUID is not covered by
the earlier confirmation. This comparison only vetoes deletion; it cannot
authorize something the fresh executor rejects. A later attempt requires a new
preview and confirmation.

## Refusal, audit, and result

Windows execution must fail closed on changed eligibility or protection,
active/recoverable/referenced sessions or durable jobs, changed evidence,
unsafe root/volume/artifact identity, unsafe audit history or location,
conflicting lifecycle ownership, unsupported filesystem behavior, or a failed
preview comparison. POSIX/macOS/Linux `delete` refuses before lifecycle-lock
creation, audit creation, or recording mutation with: `v0.11 destructive
retention is Windows-only; retention plan remains available`. Do not fall back
to pathname deletion. A refusal before intent sync begins reports `REFUSED`,
the reason, the target UUID/root, and `No deletion operation was started`.

The executor records a durable intent before any artifact attempt and retains
its current final-MP4-last order. The CLI reports the operation UUID and the
absolute per-root JSONL audit path after intent exists. This path is derived
from the selected root through the existing `default_audit_path` rule. The
owner can inspect that local file and filter records by `operation_id`; no new
audit command is required in this slice. The CLI never prints the entire
journal, hashes, signed URLs, or private transport data.

Report `COMPLETE` once the synced `completed` event is known, including when
later executor cleanup or normal success output fails or is interrupted. Keep
exit `0` and make one bounded stderr attempt to report `COMPLETE`, the first
post-completion operation or cleanup fault, any later cleanup faults separately,
operation UUID, and audit path. Failure of that
diagnostic channel does not change the completed result. Report `FAILED` when
intent is durable or its sync began but may have succeeded, and no removal is
known to have occurred. An interrupted or failed sync call cannot prove the
intent did not persist; report its uncertainty with operation context and exit
`3`, without claiming known durability. Report `PARTIAL` when at least one
artifact was removed or when an attempted removal/audit write leaves removal
uncertain. Both failure labels state only what is known about the audit and may
require filesystem inspection for an ambiguous final attempt. A process crash
may prevent any CLI message; the deterministic audit path remains available for
reconstruction. Never claim success from missing files alone. Do not retry,
resume, repair the journal, clean up quarantine names, or silently continue
after any failure. A later deletion decision starts from fresh eligibility and
normally refuses an incomplete session.

The private executor returns an operation ID on success and fills a caller-owned
progress record after intent, including audit path, sync-started and durable-intent
states, proven completed sync, known deletion count, possible removal or journal
uncertainty, the first operation fault before context cleanup, and secondary
inner and outer cleanup faults when present. The CLI keeps
that original failure authoritative and performs no second mutation to improve
the message. If the journal itself is unavailable, it says its state is
uncertain rather than promising an audit record exists. A failed intent write
before sync is a refusal because no artifact removal is attempted; the CLI
notes that intent durability
was not confirmed. A failed sync is uncertain rather than a proven pre-intent
refusal. Diagnostic stderr writes and flushes are best-effort and cannot change
an already determined exit result.

| Exit code | Meaning |
| --- | --- |
| `0` | Read-only plan succeeded, or one deletion reached durable `completed`. |
| `1` | Operational refusal before intent sync; no deletion operation started. |
| `2` | CLI syntax or argument error, following existing `argparse` behavior. |
| `3` | Intent sync began or removal was attempted without proven completion (`FAILED` or `PARTIAL`). |
| `130` | User interruption before intent sync; after sync begins use `3` with operation context when the process can report it. |

Diagnostics go to stderr; successful plan and completed deletion results go to
stdout. Do not overload `2` for a retention refusal or return `0` for a partial
operation. This is a human-readable contract; structured delete output is not
part of the first interface. Offline tests cover exact confirmation, root
selection, summary and plan fields, refusal categories, evidence changes after
confirmation, audit context, and exit codes on Windows and POSIX.
