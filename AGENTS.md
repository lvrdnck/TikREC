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

## Mandatory two-phase workflow

Every coding task has the following two phases.

### Phase 1 — preflight

Before changing any file:

1. Read the request and inspect relevant repository state and documentation.
2. At the start of the task, run `git pull --rebase --autostash` before reading
   or editing project files. GitHub is the source of truth across the MacBook
   and Windows PC. If rebase conflicts, stop and report the conflict.
3. For requests such as `continue TikREC`, `continue`, or `next task`, inspect
   ROADMAP.md and the actual repository state, then select the next unfinished
   logical roadmap slice.
4. Classify the task and select the lowest suitable model:

   | Task class | Default model |
   | --- | --- |
   | Mechanical — repetitive work, tiny documentation edits, renames | GPT-5.6 Luna — Medium |
   | Routine — small bug fix, simple tests, localized code change | GPT-5.6 Terra — Medium |
   | Normal Feature — ordinary TikREC roadmap implementation | GPT-5.6 Sol — Medium |
   | Complex — cross-cutting work, difficult debugging, concurrency, architecture-sensitive work, important independent review | GPT-5.6 Sol — High |
   | Exceptionally Difficult — prior attempts failed or the architecture/debugging problem is extremely difficult | GPT-6 Astra — High |

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
