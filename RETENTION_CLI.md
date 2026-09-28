# Owner-facing retention CLI (unreleased v0.11 development)

**Status: IMPLEMENTED IN DEVELOPMENT — NEW PUBLIC REVIEW PENDING.**
Issue #39 corrected the post-sync intent reporting gap found in the 2026-09-28
review. Audit append marks progress immediately after successful intent sync;
a later exception or interruption reports an after-intent outcome. Failed
intent sync keeps the documented pre-intent result. A new independent review
at `f99528f` found that a failed or interrupted CLI `COMPLETE` output write
after the executor returns incorrectly reported `PARTIAL`/exit 3 despite a
synced `completed` audit event and completed removal. Issue #40 corrected that
result boundary. Repeat a NEW fresh-context review before real-media validation.
The local CLI workflow
below exists in the development checkout; it is not in the current
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
to pathname deletion. A refusal before durable audit intent reports `REFUSED`,
the reason, the target UUID/root, and `No deletion operation was started`.

The executor records a durable intent before any artifact attempt and retains
its current final-MP4-last order. The CLI reports the operation UUID and the
absolute per-root JSONL audit path after intent exists. This path is derived
from the selected root through the existing `default_audit_path` rule. The
owner can inspect that local file and filter records by `operation_id`; no new
audit command is required in this slice. The CLI never prints the entire
journal, hashes, signed URLs, or private transport data.

Report `COMPLETE` only after the executor returns and the synced `completed`
event is known. If normal success output fails or is interrupted after that
return, keep exit `0` and make one bounded stderr attempt to report `COMPLETE`,
the original output cause, operation UUID, and audit path. Failure of that
diagnostic channel does not change the completed result. Report `FAILED` when
an intent exists but no removal is known
to have occurred. Report `PARTIAL` when at least one artifact was removed or
when an attempted removal/audit write leaves removal uncertain. Both failure
labels state that the audit preserves the known event sequence and may require
filesystem inspection for an ambiguous final attempt. A process crash may
prevent any CLI message; the deterministic audit path remains available for
reconstruction. Never claim success from missing files alone. Do not retry,
resume, repair the journal, clean up quarantine names, or silently continue
after any failure. A later deletion decision starts from fresh eligibility and
normally refuses an incomplete session.

The private executor returns an operation ID on success and fills a caller-owned
progress record after intent, including audit path, durable-intent state, known
deletion count, and possible removal or journal uncertainty. The CLI keeps the
original failure and performs no second mutation to improve the message. If
the journal itself is unavailable, it says its state is uncertain rather than
promising an audit record exists. A failed intent write is a refusal because no
artifact removal is attempted; the CLI notes that intent durability was not
confirmed.

| Exit code | Meaning |
| --- | --- |
| `0` | Read-only plan succeeded, or one deletion reached durable `completed`. |
| `1` | Operational refusal before intent; no deletion operation started. |
| `2` | CLI syntax or argument error, following existing `argparse` behavior. |
| `3` | Intent/attempt occurred without proven completion (`FAILED` or `PARTIAL`). |
| `130` | User interruption before intent; after intent use `3` with operation context when the process can report it. |

Diagnostics go to stderr; successful plan and completed deletion results go to
stdout. Do not overload `2` for a retention refusal or return `0` for a partial
operation. This is a human-readable contract; structured delete output is not
part of the first interface. Offline tests cover exact confirmation, root
selection, summary and plan fields, refusal categories, evidence changes after
confirmation, audit context, and exit codes on Windows and POSIX.
