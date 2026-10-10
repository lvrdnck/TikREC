# TikREC — Repository Instructions

## Ownership and scope
- The owner sets product direction. ChatGPT coordinates the roadmap, resolves
  high-level product/architecture decisions, and reviews implementation handoffs.
- Codex implements the selected task: inspect, decide ordinary engineering
  details, implement, verify, document, commit, push, and report.
- Prioritize a stable, polished product usable by external users and capable of
  earning first revenue. Flag optional work that creates substantial maintenance
  or time demands, especially when it risks distracting from flight training.
- Complete one approved logical slice. Do not scaffold future modules or expand
  into another roadmap item. Parallel implementation needs explicit approval.
- Resolve routine choices from code, tests, history, and specifications. Ask only
  for consequential unspecified product behavior or changes to roadmap scope,
  compatibility, persistent data, public interfaces, security, privacy,
  credentials, or destructive operations. Present options and a recommendation.

## Durable state and documentation
- GitHub is the durable cross-device source for code and project state. Chats,
  calendar reminders, and handoffs are convenience context, not authority.
- PROJECT_STATE.md and relevant GitHub issues describe active/pending work;
  ROADMAP.md supplies product sequence; SPEC.md defines supported behavior and
  distinguishes deferred features from security/privacy boundaries.
- Before selecting work or handling `continue TikREC`, reconcile those sources
  with actual repository state. Resume an active task before choosing another.
  Report consequential contradictions instead of silently choosing a source.
- For a clearly scoped request, read applicable instructions, relevant state,
  implementation, and documentation. Avoid a full documentation sweep.
- Read SERVICE.md for service behavior, SESSION_MANIFEST.md for manifests, and
  CONNECTION_LOG.md for connection logging when the task touches those areas.
- Obtain setup and test commands from current README.md, pyproject.toml, and CI;
  do not invent commands or claim they ran without execution evidence.
- Keep README.md about current behavior. Update only affected documents.
  Update ROADMAP.md completion only when its acceptance criteria are met.
- PROJECT_STATE.md records the active task/issue, active/blocked/paused status,
  pending owner action, next task when known, and a safe resume action.
- Record durable decisions and meaningful partial progress in the relevant issue
  and PROJECT_STATE.md where appropriate. Include evidence, remaining work, Git
  state, and a safe resume action. Never leave essential context only in chat.
- Derive current versions from package metadata, annotated tags, GitHub Releases,
  and project state. Do not hard-code a current release version in this file.

## Read-only requests
- Audits, explanations, and reviews requested as read-only do not authorize
  edits, pulls/rebases, commits, pushes, issue comments, or vault journaling.
- Inspect existing local/remote state with read-only operations. Report if the
  checkout may be stale. A read-only audit does not need a MODEL GATE.

## Implementation workflow

### Preflight and MODEL GATE
1. Read applicable instructions and inspect Git status, branch, upstream, relevant
   project state, and the request. Preflight is inspection only: do not pull,
   rebase, edit, stash, commit, or push before approval.
2. Define one task, its acceptance criteria, a short plan, and owner decisions.
3. Select an exact model and reasoning effort using the table below. Choose the
   lowest combination comfortably sufficient; explain any escalation.
4. End preflight with the MODEL GATE below, then wait for `PROCEED`, even if the
   recommended model is already selected. A direct instruction explicitly
   waiving this gate takes precedence. Approval applies to this task only.

| Model and reasoning | Suitable work |
| --- | --- |
| GPT-6 Luna — Low | Tiny mechanical, deterministic edits |
| GPT-6 Luna — Medium | Documentation and bounded low-risk maintenance |
| GPT-6.1 Sol — Low | Small, contained, low-risk code fixes |
| GPT-6.1 Sol — Medium | Ordinary features and multi-file implementation |
| GPT-6.1 Sol — High | Difficult debugging, concurrency/recovery, codec/media, important reviews |
| GPT-6 Astra — Medium | Exceptional investigation when Sol High is insufficient |
| GPT-6 Astra — High | Repeated strong-model failure or severe correctness uncertainty |

- Model capability and reasoning effort are separate choices. Do not escalate
  simply because a stronger option exists, or recommend the unspecified Default.
- Prefer GPT-6.1 Sol to older Sol versions when available. Older models are
  access-related fallbacks only. Verify available choices rather than guessing.
- Above High is escalation-only after a failed strong-model attempt or an
  explicit ChatGPT assessment of exceptional correctness risk.
- If the active model/effort is reliably visible, compare it with the recommendation.
  Otherwise ask the owner to verify it. Do not claim to switch models yourself.

```text
MODEL GATE
TASK: What will be accomplished and its acceptance criteria.
TASK CLASS: Mechanical / Routine / Normal Feature / Complex / Exceptionally Difficult
RECOMMENDED MODEL: Exact model — reasoning effort.
WHY: At most two short sentences.
PLAN: Short implementation plan.
OWNER DECISIONS REQUIRED: None, or the consequential decision and recommendation.
NEXT ACTION: Switch/verify the recommended model and reply PROCEED.
```

### Execution after PROCEED
1. Synchronize the intended branch with GitHub before implementation. Inspect
   tracked edits, staged files, local commits, and untracked files first.
2. Use `git pull --rebase` only when the tracked worktree is clean and the target
   branch/upstream are correct. Do not use `--autostash` automatically. Preserve
   unrelated untracked files and check for path collisions before synchronization.
   If local changes or conflicts prevent safe synchronization, report the exact
   state and a safe recovery recommendation; do not reset, clean, or discard work.
3. After synchronization, recheck whether the approved task/state changed. If its
   scope or acceptance criteria materially changed, report before implementing.
4. Implement the approved slice, verify it proportionately, fix introduced
   regressions, review the diff, and update affected documentation/state.
5. Commit/push task-owned work under the policy below. Report any actual blocker
   without silently switching tasks. Do not request repeated approval for
   ordinary engineering choices inside the approved scope.

## Code and runtime constraints
- Follow the existing layout: tikrec/ for package modules, tests/ for matching
  test_<module>.py files, and pyproject.toml for packaging/CLI definitions.
  Keep the repository root for configuration and documentation.
- Python 3.11+. Use the standard library for FLV handling; ffmpeg and ffprobe are
  external subprocesses. New dependencies require owner approval.
- Keep each source file under 300 lines; split by coherent responsibility.
- Document public functions. Explain non-obvious invariants, format assumptions,
  and recovery behavior with useful comments rather than narrating obvious code.
- Add/update matching offline tests for changed behavior before moving on.
  Unit tests must not require network access or a LIVE stream; inject network
  behavior. Keep explicitly authorized real-LIVE validation separate.
- Windows `main-pc` is the recording/service runtime and real-LIVE validation
  environment. Test NVENC/GPU paths on its RTX 4080.
- Do not create Fedora/Linux runtime work or deployment gates. Preserve existing
  portable helpers; MacBook work, when applicable, is offline/client development
  or remote access. CPU-only environments must skip/degrade GPU paths clearly.
- Synchronize source through GitHub, never shared-folder/cloud-drive copying.
  Media may be shared separately over SMB/Tailscale. Remote access does not
  change GitHub authority. Verify the actual environment before running commands.

## Verification and completion
- Completion means the relevant specification and acceptance criteria are met,
  appropriate checks pass, introduced regressions are fixed, and affected
  documentation reflects actual behavior. Never alter tests to conceal defects.
- Run focused checks during implementation, then broader checks justified by
  affected interfaces and regression risk. Avoid repeating successful checks
  without a new change or unresolved concern. Report unavailable checks.
- Codec configuration, part boundaries, and finalization changes also need
  real-recording validation when evidence is available:
  `tikrec validate PARTS_DIRECTORY`
- Offline tests do not substitute for empirical media validation. Report missing
  real-recording evidence explicitly. Do not use `ffmpeg -f null -` as a
  corruption check; follow SPEC.md validation guidance.
- Before release, obtain an independent fresh-context review for high-risk
  codec/media changes or removal of a release blocker after ambiguous evidence.
  A review does not replace empirical validation or authorize parallel implementation.
- ChatGPT may reassess issues waiting on rare evidence: preserve genuine
  correctness/release risks, but document when an ideal evidence target can become
  non-blocking, narrower, opportunistic, or closed. Codex must not silently waive it.

## Git and issues
- Commit completed implementation and necessary resume state; push normally so
  another session can reconstruct work. Stage explicit task-owned paths only.
  Preserve unrelated edits and untracked outputs; a clean worktree is not required.
- Use one logical change per imperative-mood commit. Separate structure-only
  refactors from behavior changes. Never force-push or rewrite shared history.
- For an existing issue, describe actual work in a concise issue comment. Use
  `Closes #N` only when all issue acceptance criteria are met; partial work uses
  a non-closing reference and records what remains.
- Deferred work belongs in issues, not TODO comments. Do not open an issue just
  for work being completed in the same session.
- If commit, push, or issue updates fail, report what succeeded and what remains.
  Do not claim synchronization or completion of bookkeeping without verification.
- Releases, tags, destructive operations, and other major external release actions
  need an explicit request. An implementation approval or closed issue is not
  release authorization. Recheck active issue/repository state before those actions.

## Release bookkeeping
- Distinguish package version, annotated tag and peeled commit, published GitHub
  Release, current released version, and unfinished development target.
- A release is complete only after verifying and recording all of the following:
  1. Package metadata and release documentation match intended supported behavior.
  2. Relevant offline checks pass; applicable real-recording checks and outstanding
     limitations are recorded under the verification rules above.
  3. The exact release commit is reviewed and has an immutable annotated tag.
     Verify existing tags; never move or recreate them.
  4. A published, non-draft GitHub Release exists for that tag with accurate notes
     scoped to that release's historical behavior.
  5. PROJECT_STATE.md, ROADMAP.md, and affected specifications/README distinguish
     synchronized released state from the development target.
  6. Any release-specific issue records successful actions and closes only after
     the checklist and repository state have been verified.
- Routine release preparation does not need a separate issue. Use existing
  state/feature/bug records; create a release issue only for distinct work such
  as an unusual blocker or migration. Journal actual external actions afterward.

## Vault and final handoff
- Follow global vault journaling instructions and the vault's own AGENTS.md.
  Journal meaningful outcomes at completion; new notes still require explicit
  approval. The vault supplements, and never replaces, repository/GitHub state.
- Finish each implementation with this concise handoff. Report evidence and
  uncertainty plainly; the handoff must not be the only durable record.

```text
CODEX HANDOFF
STATUS: COMPLETE / PARTIAL / BLOCKED
IMPLEMENTED: Result in plain language.
FILES CHANGED: Task-owned files.
TESTS: Commands/checks, outcomes, and unavailable validation.
DOCUMENTATION: Updated records, or None required; vault result if applicable.
IMPORTANT DECISIONS: Noteworthy autonomous decisions only.
COMPATIBILITY / RISKS: Material risks/assumptions, or None known.
REMAINING ISSUES: Blockers/unfinished work, or None.
GIT STATE: Branch, commit, push result, and remaining unrelated changes.
RECOMMENDED NEXT ROADMAP TASK: One recommendation from reconciled state.
RECOMMENDED MODEL FOR NEXT TASK: Exact model — reasoning effort.
```
