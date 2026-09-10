# TikREC

## Git sync

This repo is worked on from two machines (MacBook and Windows PC).
GitHub is the source of truth.

- At the start of a session, run `git pull --rebase --autostash` before
  reading or editing any files.
- After completing a task, run `git add -A`, commit with a real message
  describing the change, and `git push`.
- Never force-push. If the rebase conflicts, stop and ask.

## What this is

A command-line tool that records a single public TikTok LIVE stream to
disk from a URL supplied manually. See SPEC.md for the full design,
module responsibilities, and scope boundaries.

## Layout

    tikrec/          the package — one file per module
    tests/           one test file per module, named test_<module>.py
    pyproject.toml   package definition and CLI entry point

Nothing lives at the repo root except configuration and documentation.

## Constraints

- Python 3.11+. Standard library only for FLV handling.
- ffmpeg and ffprobe as external binaries, invoked via subprocess.
- No new dependencies without asking me first.
- No file over 300 lines. Split the module instead.
- Every non-obvious line gets a comment explaining *why* it exists and
  what format behaviour it handles. If you can't explain why a line is
  there, don't write it.
- Unit tests run offline. No test may require network access or a live
  stream. Network behaviour is tested through injected functions.

## Definition of done

A module is finished only when all of these are true:

- It does what SPEC.md says for that module, and nothing beyond it
- Its tests exist in `tests/test_<module>.py` and pass offline
- Public functions have docstrings; non-obvious lines have why-comments
- The file is under 300 lines
- It is committed with a message describing the change, and pushed

## Media correctness

Passing unit tests do not prove a recording is playable. A module that
touches codec configuration, part boundaries, or finalization is not
proven until a real recording decodes cleanly:

    ffmpeg -v error -i part-0001.flv -f null -

No output means clean. An AAC configuration bug once produced a ~99%
audio decode failure rate while 53 unit tests passed over it. When you
finish such a module, say explicitly that this check is still outstanding.

## Commit style

One logical change per commit. Imperative mood, no "wip".
Structure changes commit separately from behaviour changes.

## How to work with me

I am learning this codebase as we build it, so pace matters more than
speed.

- Build one module at a time, in the order given in SPEC.md.
- Write the tests for a module before starting the next one.
- After each module, explain in plain language what you wrote and how it
  works, before moving on.
- Flag anything you were unsure about or had to guess.
- Do not scaffold ahead. Do not create empty files for future modules.
- Wait for me to say continue.
- When troubleshooting or testing, give me one terminal command at a time.
  Full implementation tasks are fine as a single instruction.

## Environment

- Windows PC: RTX 4080, so NVENC and any GPU path is tested there.
- MacBook: CPU only. Anything GPU-specific must degrade gracefully or
  be skipped with a clear message.
- Development happens on either machine; both push to GitHub.

## Keeping the docs true

README.md, SPEC.md and AGENTS.md must describe the repo as it actually is.

At the end of a module or issue, check whether anything you built
contradicts them — a module that doesn't exist, a command that changed,
a status list that's out of date, a rule that turned out to be wrong.
If so, say what's stale and propose the edit. Do not edit these files
without asking.

README.md in particular describes what the tool does today, not what it
will do. Any new or changed command belongs there.  

## Issues

Deferred work lives in GitHub issues, not in code comments or TODOs.

- When we agree to defer something, open an issue rather than leaving a
  TODO in the source.
- When working an issue, reference it in the commit message with
  "Closes #N" so it closes on push.
- Do not open issues for things we're about to do in the same session.


When closing an issue, comment on it with what was actually done —
especially if the approach differs from what the issue proposed, or if
the issue's premise turned out to be wrong. A commit link alone is not
enough; the issue should be readable on its own in six months.