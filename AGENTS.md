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

A minimal command-line tool that records a single TikTok LIVE stream to
disk from a URL supplied manually. See SPEC.md for the full design.

This is a rewrite. The previous version is not in this repo — I will paste
relevant files from it into the conversation when the format behaviour
matters. Do not go looking for it on disk.

## Layout

    tikrec/          the package — one file per module
    tests/           one test file per module, named test_<module>.py
    pyproject.toml   package definition and CLI entry point

Nothing lives at the repo root except configuration and documentation.
Module order and responsibilities are defined in SPEC.md.

## Constraints

- Python 3.11+. Standard library only for FLV handling.
- ffmpeg and ffprobe as external binaries, invoked via subprocess.
- No new dependencies without asking me first.
- No file over 300 lines. Split the module instead.
- Every non-obvious line gets a comment explaining *why* it exists and
  what format behaviour it handles. If you can't explain why a line is
  there, don't write it.
- Tests run offline. No test may require network access or a live stream.

## Definition of done

A module is finished only when all of these are true:

- It does what SPEC.md says for that module, and nothing beyond it
- Its tests exist in `tests/test_<module>.py` and pass offline
- Public functions have docstrings; non-obvious lines have why-comments
- The file is under 300 lines
- It is committed with a message describing the change, and pushed

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

## Environment

- Windows PC: has the RTX 4080, so NVENC and any GPU path is tested here.
- MacBook: CPU only. Anything GPU-specific must degrade gracefully or
  be skipped with a clear message.
- Development happens over VS Code Remote-SSH into the PC.