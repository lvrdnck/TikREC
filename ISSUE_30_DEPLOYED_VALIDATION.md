# Issue #30 — deployed Windows hot-reload validation

## Current result (2026-10-02)

**PARTIAL: safe new-code load PASSED; active-session hot-reload gate NOT YET
EXERCISED.** Issue #30 stays OPEN and is the single active task. Implementation
and isolated offline verification at `e3864589` are complete; this checkpoint
changes no production code. v0.10.0 remains the current released/package version;
v0.11.0 remains unreleased.

## Owner configuration update — PASSED (2026-10-02, 11:42–11:45 CEST)

The owner replaced Eliss with Ward and retained Gracie. The intended production
tuple is now **`wardsimons`, `gracie.kf`**, in that order. Do not restore Eliss
after future validation. Normal CLI commands used the proven UNC config below:
`monitor remove eliss4r.n`, `monitor remove gracie.kf`, `monitor add wardsimons`,
then `monitor add gracie.kf`. The temporary Gracie removal/re-add was needed
because the public add command appends; all four commands completed normally.
No manual JSON edit or service restart occurred; unrelated config fields match.

- At 11:42:24/cycle 101, both slots were inactive with completed jobs. PID
  **18660**, creation **10:48:25.158312 CEST**, matches the deployment checkpoint.
- By 11:43:49/cycle 103, `/monitoring` reported exactly the new ordered tuple,
  no Eliss, and `configuration: {state: "ok", reason: null}`. The same process
  creation time was verified using normalized UTC timestamps.
- Ward was naturally LIVE and automatic policy started one new recording at
  **11:42:52.033 CEST**, session `9d3720f4-0123-4fcf-917d-4546d754be9d`,
  **slot-1**, room **`7692001759392418593`**. Output is
  `C:\Users\Leandro\Videos\wardsimons-20261002-114252.mp4`; parts are
  `C:\Users\Leandro\Videos\wardsimons-20261002-114252.parts`.
- Slot 1's authoritative `job.json` now owns that automatic session, recording
  with `stop_requested=false`, `resume_count=0`, no recovery reason and no end.
  Its old completed Gracie reference was normally superseded by a new job;
  Gracie's matching media manifest remains completed. Slot 2's completed Eliss
  durable job is byte-identical. There was no active pre-change worker to stop.
- At 11:44:58 the same Ward session/job/slot remained active, increasing from
  **15,379,770** to **27,479,204 bytes**; no stop request or recovery transition.
  One active recording and consumed-room suppression establish no duplicate
  Ward start during these observations. PID and creation remain identical.

The initial comparison script flagged ISO-string versus parsed-date comparison
and expected new-job/automation updates; normalized creation ticks match exactly,
and inspection confirms those state updates belong to the normal Ward start.
Raw snapshots and corrected final checks are preserved in
`C:\Users\Leandro\TikREC-evidence\issue-30-owner-config-20261002`
(`before.json`, `after.json`, `commands.txt`, initial `checks.json`, corrected
`final.json`, `checksums.json`). No secret, signed media URL or recording bytes
were archived.

**#30 remains OPEN/single active.** This idle-to-new-recording configuration
adoption does not prove removal continuity during an already-active session.
For the next bounded validation, freshly recheck the natural Ward recording,
capture all ownership/progress evidence, remove its creator through the normal
CLI, prove adoption and same active session/job progress, then restore exactly
**`wardsimons`, `gracie.kf`** through normal CLI commands and verify adoption/no
duplicate. Do not restart, manually start/stop a LIVE, or restore Eliss. If this
session has naturally ended, wait for another natural recording; do not
manufacture one. No other issue, retention operation or release work started.

## Phase 1 — safe load established (historical checkpoint)

All times below are CEST (UTC+02:00). Public authenticated `remote health`,
`remote recordings` and `remote monitor-status` were used, alongside read-only
Scheduled Task/CIM inspection and host-visible durable state reads.

- Old service PID **37772**, created **2026-10-01 11:35:56.463**.
- Read-only preflight at approximately 10:45 and evidence snapshots at
  **10:46:47** and **10:47:34** found both slots naturally inactive/available,
  completed, without recovery or shutdown. Monitoring advanced through cycles
  2580 and 2581; jobs, configuration and automation state were byte-identical.
- Slot 1 retained completed Gracie session
  `55dc7b01-4a85-45c1-aa63-0cec1a0ab0c4`, room `7691910970859342623`;
  slot 2 retained completed Eliss session
  `268a8cbd-34be-4b9b-ba84-6c848f69ad47`, room `7691932634922535694`.
  Both had `stop_requested=false`, `resume_count=0` and durable finalization.
- The existing editable install maps `tikrec` to this checkout. Its installer
  metadata is older, but imports resolve to current committed source; no install
  or deployment-definition change was needed.
- A fresh public idle/health check passed at **10:48:20.864** immediately before
  stopping the existing `TikREC Service` task. After verifying the old process
  was gone and the task stopped, the unchanged task was started exactly once at
  **10:48:25.120**. No recording was stopped to create this opportunity.
- New service PID **18660**, created **2026-10-02 10:48:25.158**; task launcher
  PID 57388 and intermediate Python PID 58272. No further restart is needed for
  this implementation.
- Checks at **10:48:35** and **10:49:31** found healthy storage, two available
  slots, the same completed session ownership/history and no startup capture or
  recovery. `/monitoring.configuration` was `{"state":"ok","reason":null}`,
  establishing that the new reload implementation is loaded. Automation remained
  operational and monitoring advanced through cycles 1 and 3.

### Host filesystem view and unchanged deployment

The task runs as Leandro (SID ending `1001`), Password logon, limited run level,
with no `--config` override. Its selected native path is
`C:\Users\Leandro\AppData\Roaming\TikREC\config.json`.

The desktop execution view of that conventional path contains a different,
redirected document, including `phoebelightt`. The read-only UNC spelling
`\\localhost\C$\Users\Leandro\AppData\Roaming\TikREC\config.json` exposes the
actual host file. Public `tikrec --config <that UNC path> monitor list` and the
restarted service both report exactly **`eliss4r.n`, `gracie.kf`**, in that order.
The host file and redirected document were both left unchanged. Future validation
must use the proven UNC spelling with normal public monitor commands.

The task still executes
`C:\Users\Leandro\dev\TikREC\.venv\Scripts\tikrec.exe`, with arguments
`serve --host 100.123.31.16 --port 8765 --token-file C:\Users\Leandro\.tikrec-service-token`
and working directory `C:\Users\Leandro\dev\TikREC`. Its exported XML,
including principal, triggers and settings, was identical before/after restart.
Token, bind, output root, recovery settings and configuration were unchanged.

| Unchanged evidence | SHA256 |
| --- | --- |
| Exported task XML (UTF-8, normalized LF capture) | `dd275315954d742e0aeb4a24871b9c9b280503cb504fbf143360010ecb80f8eb` |
| Host config | `fc62d32f574ecdbc255a3e0a4a41ba28e577630f2df44e82ed76fcde157f6e9e` |
| Host `job.json` | `0a0ee9b9942d8ca0abd7974a0cb6719d57ba2a33f45059e304b56e9aabd92404` |
| Host `job-2.json` | `e69bae8a17e43bb22363c65bcc454407b4d2814b3e0ab01d6e39bd564e790931` |
| Host `automation.json` | `c89fec68456a6c0cced2f39b9f171153f9fc632fafe1ad82457e43cce8748125` |

Comparisons included document bytes, size and modification timestamp for all four
state/config files. Existing job history was not rewritten by startup.

## Phase 2 — natural active recording still required (historical idle checkpoint)

At **10:50:44**/cycle 5 and **10:53:18**/cycle 10 (nearly five minutes after
startup), monitoring still had no active recording. Eliss was LIVE
in consumed room `7691932634922535694`, correctly `same_room_consumed`; Gracie
was offline. The same new PID/creation, creator tuple, healthy slots and unchanged
task/config/job/automation evidence remained intact. No monitor mutation was
performed, and no active-session continuity PASS is inferred from idle checks.

**Safe resume:** recheck the actual process, health, slots, durable jobs and host
config. The code is already loaded; do not repeat the restart for this gate.
Wait for an owner-authorized natural automatic recording. Capture PID/creation,
creator, session UUID, slot/room, output/parts paths, durable job, bytes/progress
and original ordered tuple before changing anything. Use normal public monitor
remove/add with the host-visible UNC config to remove the active creator, prove
next-cycle adoption with unchanged active session/job and continuing bytes, then
restore the exact original ordered tuple and verify normal adoption/no duplicate.
If the recording ends before removal/adoption/continuity proof, restore any
changed list and keep #30 open for another natural opportunity. If it ends only
after that proof, verify its normal terminal state while restoring the list.

No manual LIVE start/stop, manufactured eligibility, restart during capture,
retention/policy operation, other startup-setting change, production fix, other
issue implementation, tag or release is authorized by this checkpoint.

## Preserved local evidence

Metadata-only snapshots, task XML, file hashes/documents and restart timestamps:
`C:\Users\Leandro\TikREC-evidence\issue-30-deployed-20261002-1046`.
Files include `before-1.json`, `before-2.json`, `restart.txt`,
`after-load-1.json`, `after-load-2.json`, `opportunity-1.json` and
`opportunity-final.json`. Final comparisons against the initial post-load
snapshot confirmed identical process identities, task XML and all four
config/state files, including their size and modification timestamp.
No bearer secret, signed source URL or recording bytes were copied into this
archive. Existing media/evidence was not modified by validation.
