# TikREC

## Roles and decision boundaries

The project owner sets product direction. ChatGPT acts as project manager and
senior developer: it selects the next work, makes high-level product decisions,
interprets important blockers, and reviews Codex handoffs. Codex is the
implementation developer: it inspects the codebase, makes ordinary engineering
decisions autonomously, implements, tests, documents, and reports its work.

Do not ask the owner about ordinary implementation choices. Resolve them from
the codebase, tests, Git history, specifications, and documentation.

Ask only when a decision materially affects unspecified product behavior,
roadmap scope, backward compatibility, persistent data, public interfaces,
security, credentials, privacy, destructive operations, or user data. State the
issue, available choices, and recommended option.

## Cross-device and disposable-Codex workflow

GitHub is the durable cross-device source of truth for TikREC code and project
state. Important context must never exist only in a Codex conversation: chats are
disposable working context and are not assumed to synchronize between computers.

ChatGPT is the project manager and senior developer. It inspects repository and
GitHub state, selects the single next task, resolves high-level product and
architecture decisions, and reviews completed Codex work. Codex is the
implementation developer; every task must be self-contained and reconstructible
from repository and GitHub state without phrases such as "continue what we
discussed in the previous chat" or hidden prior-thread context.

A fresh Codex task pulls GitHub first, then inspects AGENTS.md, PROJECT_STATE.md,
ROADMAP.md, relevant GitHub issues, Git history, and the relevant implementation
and documentation before acting. Before ending, persist all durable resume
information in the appropriate repository documentation and/or GitHub issue. If
work is partial or interrupted, record completed work, remaining work, important
evidence and decisions, Git state, and a safe resume action in the relevant issue
and PROJECT_STATE.md where appropriate. Completed work must be committed and
pushed so another machine or session can reconstruct it from GitHub.

The CODEX HANDOFF is only a concise convenience summary; it is not authoritative
project state and must never be the only place important information is recorded.
After Codex finishes, the owner may simply say `Codex finished`; ChatGPT then
reviews the actual GitHub commit, diff, issues, and documentation to decide what
happens next. Normally one implementation task is active across both computers.

MacBook and Windows clones synchronize source only through GitHub. Do not use
SMB, Tailscale file sharing, OneDrive, iCloud, Google Drive, or manual folder
copying to synchronize the repository. Pull and reconcile GitHub before manual
development on either clone. Windows `main-pc` is the primary runtime and
real-LIVE validation environment; the MacBook may use its own clone for
Mac-specific/offline work or VS Code Remote-SSH over Tailscale for access to the
Windows checkout. Remote access does not change GitHub authority. Recordings and
other media may be shared separately over SMB/Tailscale, but media sharing stays
separate from source-code synchronization. Calendar reminders remain
non-authoritative.

## Mandatory two-phase workflow

Every coding task has the following two phases.

### Phase 1 — preflight

Before changing any file:

1. Read the request and inspect relevant repository state and documentation.
2. At the start of the task, run `git pull --rebase --autostash` before reading
   or editing project files. GitHub is the source of truth across the MacBook
   and Windows PC. If rebase conflicts, stop and report the conflict.
3. For requests such as `continue TikREC`, `continue`, or `next task`, reconcile
   PROJECT_STATE.md, ROADMAP.md, relevant open GitHub issues, and the actual
   repository state. Continue the active task when one exists; otherwise select
   the next unfinished logical roadmap slice.
4. Classify the task by complexity, then select model and reasoning effort as
   separate dimensions. The task-class examples below are descriptive, not a
   rigid model mapping; use the practical model ladder that follows.

   | Task class | Complexity example (not a model requirement) |
   | --- | --- |
   | Mechanical — repetitive work, tiny documentation edits, renames | Small, bounded scope |
   | Routine — small bug fix, simple tests, localized code change | Limited subsystem interaction |
   | Normal Feature — ordinary TikREC roadmap implementation | Meaningful multi-file work |
   | Complex — cross-cutting work, difficult debugging, concurrency, architecture-sensitive work, important independent review | Broad or high-risk reasoning |
   | Exceptionally Difficult — prior attempts failed or the architecture/debugging problem is extremely difficult | Severe uncertainty or correctness risk |

Choose the lowest model and effort combination that is comfortably sufficient.
Do not minimize usage if that materially increases retry or implementation risk,
and do not default upward because a stronger model is available. Stronger models
at lower effort can be the better trade-off, and higher effort does not
automatically produce a better result. If selecting a stronger model or higher
effort than the obvious baseline, state the specific complexity or risk that
justifies it.

Practical model-and-effort ladder:

   | Model and effort | Suitable work |
   | --- | --- |
   | GPT-6 Luna - Low | Tiny mechanical edits and formatting |
   | GPT-6 Luna - Medium | Straightforward documentation and repetitive maintenance |
   | GPT-6 Sol - Low | Obvious localized low-risk code work |
   | GPT-6 Sol - Medium | Normal TikREC features and ordinary multi-file work |
   | GPT-6 Sol - High | Difficult debugging, cross-cutting changes, concurrency/recovery state machines, codec/media work, and important reviews |
   | GPT-6 Astra - Low/Medium | Only when Sol High is materially insufficient, previous strong-model work failed, or evidence/architecture is exceptionally difficult |
   | GPT-6 Astra - High | Reserve for repeated strong-model failure, contradictory evidence with severe correctness risk, or exceptional architecture decisions |

Do not select a stronger model merely because it is available. If the current
model and reasoning setting are reliably visible, compare them with the
recommendation and explicitly request a switch when they differ. Otherwise say
`Verify/select [model] — [reasoning], then reply PROCEED.`

End preflight with **only** this concise MODEL GATE, then stop:

    MODEL GATE

    TASK:
    What will be accomplished.

    TASK CLASS:
    Mechanical / Routine / Normal Feature / Complex / Exceptionally Difficult

    RECOMMENDED MODEL:
    Exact model and reasoning level.

    WHY:
    At most two short sentences.

    PLAN:
    Short implementation plan.

    OWNER DECISIONS REQUIRED:
    None, unless a genuine owner-level decision exists.

    NEXT ACTION:
    Switch/verify the recommended model and reply PROCEED.

Even when the recommended model is already selected, do not edit, implement,
commit, or otherwise execute until the owner replies `PROCEED`.

### Phase 2 — execution

After `PROCEED`, implement only the approved task autonomously. Inspect the
relevant code in depth; choose the approach; add or update offline tests; run
focused tests while developing; fix regressions; run an appropriate broader
suite; review the final diff; update affected documentation; and update
ROADMAP.md only when work is genuinely complete. Do not expand into another
roadmap item or request repeated confirmation.

Stop with `STATUS: BLOCKED` only for a genuine owner-level decision, including
the recommended solution. Ordinary technical questions are Codex decisions.

Preserve unrelated user changes. Never use destructive Git operations to obtain
a clean worktree. Do not create releases, tags, force-pushes, or other major
external release actions unless explicitly requested.

## Project coordination

GitHub issues and PROJECT_STATE.md are authoritative for active and pending
TikREC work. ROADMAP.md provides the reconciled product sequence; calendar
entries are reminders only and never independently define project authority.

- Before starting or recommending an implementation task, reconcile
  PROJECT_STATE.md, ROADMAP.md, relevant open issues, and repository state.
- Normally only one implementation task is active. Parallel work needs explicit
  approval.
- PROJECT_STATE.md must concisely record the active issue/task, whether it is
  active, blocked, or paused, any pending owner action, and the next queued task
  when known.
- If work is intentionally paused or interrupted after meaningful progress,
  promptly journal completed work, remaining work, Git/release state, and a safe
  resume action in its GitHub issue. Do not silently move to another issue.
- Before a significant external action (including tags, GitHub Releases, or
  destructive operations), re-check the active issue and repository state.
  Journal what actually succeeded afterward.
- Routine release preparation does not require a dedicated GitHub issue. Track
  ordinary release readiness in PROJECT_STATE.md, ROADMAP.md, AGENTS.md, and the
  relevant feature or bug issues. A separate release issue is optional only when
  the release has genuinely distinct work such as an unusual bug, blocker, or
  migration; closing such an issue never authorizes a tag or GitHub Release.
- Reassess issues waiting on rare real-world evidence periodically. Distinguish
  an unresolved correctness or product risk from an ideal evidence target that
  may be increasingly unlikely to occur naturally. If the uncertainty no longer
  materially affects correctness, release safety, or an important product
  decision, ChatGPT/project management may make the issue non-blocking, narrow
  its goal, preserve it as opportunistic evidence work, or close it with the
  limitation documented. Do not weaken genuine safety or correctness
  requirements merely because evidence is inconvenient to obtain.

`Continue TikREC` means reconcile that authoritative state and continue the
active task, or select the next safe task only when no active task remains. It
does not authorize stale chat or calendar instructions on their own.

## Layout

    tikrec/          package modules, one responsibility per file
    tests/           matching offline tests, named test_<module>.py
    pyproject.toml   package definition and CLI entry point

Nothing belongs at the repository root except configuration and documentation.

## Project constraints

- TikREC currently records one manually selected public TikTok LIVE stream.
  Treat deferred product capabilities separately from permanent security/privacy
  boundaries; see SPEC.md and ROADMAP.md for authoritative scope and sequencing.
- Python 3.11+. Use the standard library for FLV handling; ffmpeg and ffprobe
  are external subprocesses. Do not add dependencies without owner approval.
- Keep every source file under 300 lines; split modules instead.
- Public functions need docstrings. Every non-obvious line needs a comment that
  explains why it exists and what format behavior it handles.
- Unit tests run offline. No test may need a network connection or LIVE stream;
  inject network behavior.
- Build one complete logical module or roadmap slice at a time. Do not scaffold
  future work or create empty future-module files.
- Add or update the matching `tests/test_<module>.py` coverage before beginning
  the next module or roadmap slice.

## Completion and verification

Completion requires more than written code: the result must match its relevant
specification, appropriate tests must pass, introduced regressions must be fixed,
and affected documentation must describe current behavior. Do not change tests
to conceal incorrect behavior.

Before release, require one independent fresh-context review for high-risk
codec/media correctness changes or a decision that removes a release blocker
after ambiguous real-world evidence. The review may challenge conclusions but
does not replace empirical validation.

Explain completed work in plain language in the final handoff, including any
uncertainty or necessary assumption.

README.md describes the tool as it works today. Keep README.md, SPEC.md,
ROADMAP.md, SERVICE.md, SESSION_MANIFEST.md, CONNECTION_LOG.md, and AGENTS.md
accurate when the approved work affects them; do not rewrite unrelated documents.

For changes to codec configuration, part boundaries, or finalization, offline
tests are not enough. Validate a real recording when one is available:

    tikrec validate PARTS_DIRECTORY

If a real-recording check cannot be performed, explicitly say it remains
outstanding. Do not use `ffmpeg -f null -` as a corruption check; see SPEC.md's
validation notes.

## Git and issues

Use one logical change per imperative-mood commit; keep structure-only and
behavior changes separate. On completion, stage only the files owned by the
task, commit with an accurate message, and push normally. Never stage or commit
unrelated working-tree changes merely to clean the tree.

Deferred work belongs in GitHub issues, not TODO comments. When implementing an
existing issue, include `Closes #N` in the commit message and add a concise
comment describing what was actually done. Do not open issues for work being
completed in the same session.

## Release bookkeeping

Use these terms precisely: **package version** is the version from packaging
metadata; **tagged version** is an immutable annotated Git tag and its peeled
commit; **GitHub Release** is the published GitHub object for that tag;
**current released version** is the newest version with synchronized package
metadata, tag, and GitHub Release; and **development target** is unfinished
future work, not a release.

A release is not complete until all of the following are true and recorded:

1. Package version and release documentation describe the intended version and
   supported behavior accurately.
2. Relevant offline tests pass; media, codec, part-boundary, or finalization
   changes also receive real-recording validation when available, with any
   outstanding check documented.
3. The exact release commit is reviewed and an immutable annotated tag points
   to it. Verify existing tags rather than recreating or moving them.
4. A published, non-draft GitHub Release exists for that tag with accurate,
   historically scoped notes.
5. PROJECT_STATE.md, ROADMAP.md, and any affected README/specification documents
   distinguish the current released version from the development target and
   record the synchronized state.
6. Any release-specific issue, when one exists, is journaled with what
   succeeded, then closed only after this checklist and the repository state have
   been verified. Routine releases do not require such an issue.

## Environment

- Windows PC: RTX 4080; test NVENC/GPU paths there.
- MacBook: CPU only; GPU-specific behavior must degrade gracefully or be skipped
  with a clear message.
- Development occurs on both machines; both push to GitHub.

## Mandatory final handoff

At the end of every implementation, provide exactly this handoff and then stop:

    CODEX HANDOFF

    STATUS:
    COMPLETE / PARTIAL / BLOCKED

    IMPLEMENTED:
    Concise explanation.

    FILES CHANGED:
    Concise list.

    TESTS:
    What was run and the result.

    DOCUMENTATION:
    What was updated, or "None required."

    IMPORTANT DECISIONS:
    Only noteworthy autonomous decisions.

    COMPATIBILITY / RISKS:
    Anything the owner or ChatGPT should know, or "None known."

    REMAINING ISSUES:
    "None" or a clear explanation.

    GIT STATE:
    Branch, commit if applicable, and whether the worktree is clean.

    RECOMMENDED NEXT ROADMAP TASK:
    One concise recommendation.

    RECOMMENDED MODEL FOR NEXT TASK:
    Model + reasoning.
