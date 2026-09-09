# TikREC

## Git sync

This repo is worked on from two machines (MacBook and Windows PC).
GitHub is the source of truth.

- At the start of a session, run `git pull --rebase --autostash` before
  reading or editing any files.
- After completing a task, run `git add -A`, commit with a real message
  describing the change, and `git push`.
- Never force-push. If the rebase conflicts, stop and ask.
