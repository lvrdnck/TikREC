# Issue #52 — durable scratch and unpublished-candidate ownership

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

## Verification

- Focused ownership/journal/coordinator run: **33 passed**.
- Related suite: **2,289 passed, 9 skipped, 19 subtests passed; 2 failed**.
  Both failures are existing `test_live.py` expectations for relative
  `final.parts`; on this host the configured default Videos directory resolves
  that path to `C:\Users\Leandro\Videos\final.parts`. They do not exercise the
  scratch changes.
- Full offline suite: **2,289 passed, 9 skipped, 19 subtests passed; 2 failed**
  in 195.19 seconds. Both failures are the same `test_live.py` relative-versus-
  absolute `final.parts` path expectation described above. The full run included
  the scratch tests before their final test-file split; the focused post-split
  run is recorded below.

The 300-line source-file limit is satisfied; the native Windows scratch suite is
split between `test_attempt_scratch_windows.py` and
`test_attempt_scratch_cleanup.py`.

## Durable references

- Implementation commit: `6fdacd37` on `codex/capture-journal-handoff`.
- [PM scope decision](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5991952747)
- [Current issue #52 design checkpoint](ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md)
- [Prior attempt/launch evidence](ISSUE_52_DURABLE_LAUNCH.md)
