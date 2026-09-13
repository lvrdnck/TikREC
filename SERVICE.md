# TikREC v0.4 remote recording

Mac -> Tailscale -> main-pc -> TikREC service -> files on main-pc.

The service owns one recording worker. HTTP requests only control that worker;
disconnecting a client does not cancel a recording. The service process must be
launched independently of SSH to survive the remote shell disappearing.

## Bind and secret

`tikrec serve` defaults to `127.0.0.1:8765`. `--host` accepts an explicit IPv4 or
IPv6 address (`localhost` means `127.0.0.1`). Every non-loopback bind, including
an explicit wildcard, requires a token; prefer the PC's Tailscale IP. `--port`
accepts 1–65535. The client accepts a hostname such as `main-pc` or an IP.

Use `--token-file FILE` or `TIKREC_TOKEN`. Files override the environment and may
end with a newline. Tokens must be 16–512 printable ASCII characters without
spaces; use a randomly generated secret with at least 32 characters. Empty or
invalid configured tokens are rejected. Token values are never printed, passed
to capture, or written into session metadata. If a token is configured, all
four endpoints require `Authorization: Bearer SECRET`, including loopback.

Store the secret outside the repo, restrict the file to your user (and the task
account if different), and copy it securely to the Mac. This avoids putting a
literal token in command arguments or shell history. Do not pass a literal
secret in a server URL. `--timeout SECONDS` controls remote requests (default 10).

This is a small trusted LAN/tailnet service. Use Tailscale ACLs and a Windows
Firewall rule restricted to intended tailnet clients; do not forward its port
to the internet. Plain HTTP relies on Tailscale for encrypted transport. The
token authorizes recording to any unused MP4 path writable by the task account;
there are no per-user permissions. The client disables environment proxies and
redirects so bearer secrets stay with the explicit server. Browser-origin
requests are refused. No accounts, TLS termination, TikTok credentials, shell
commands, executable-path options, or file serving exist.

Python's [HTTP server documentation](https://docs.python.org/3.11/library/http.server.html)
describes its limited production security. TikREC supplies a narrow custom
handler, bounded JSON bodies/read timeouts, and token checks; it is still scoped
to trusted-network control rather than public hosting.

## API contract

All normal responses are JSON. POST bodies require `application/json`, exactly
one Content-Length, and 1–8192 bytes; transfer encoding is unsupported.

| Request | Body | Result |
| --- | --- | --- |
| `GET /health` | none | 200: service, version, available, active, shutting_down |
| `GET /recording` | none | 200: idle or current/latest job snapshot |
| `POST /recording/start` | `{"url":"https://www.tiktok.com/@username/live","output":"C:\\Users\\Leandro\\Videos\\name.mp4"}` | 202: job accepted; 409 if active/shutting down |
| `POST /recording/stop` | `{}` | 202: stop requested/current snapshot; harmless when idle or repeated |

Start accepts only `url` and `output` string fields. LIVE URLs must use
`tiktok.com` or `www.tiktok.com` and `/@username/live`; query/fragment metadata
is discarded and HTTPS/www is normalized. Signed CDN URLs are rejected as
inputs and never appear in normal status. Output must be an absolute `.mp4`
path on the service machine. Existing output or `<stem>.parts` is rejected;
capture also rechecks to prevent accidental session reuse.

Malformed input returns 400, missing authentication 401, browser-origin
requests 403, unknown endpoints 404, absent/duplicate length 411, oversized or
empty body 413, unsupported content type 415, and worker launch failure 500.
Start acceptance is asynchronous: a later resolver, capture, or finalizer
failure appears in job status. These failures do not shut down the service.

## Job status and stop

States are `idle`, `resolving`, `recording`, `reconnecting`, `finalizing`,
`completed`, and `failed`. A fresh service returns `{"state":"idle","active":false}`.
Only the latest job is retained, until another start or a service restart.

Job snapshots contain session_id, normalized source_url, started_at/ended_at
(Unix seconds), active/state, parts_directory, output_path (requested),
final_output_path (actual result or null), stop_requested, interrupted, error,
part_count (closed retained parts), reconnect_count (resolution attempts after
the first), bytes_written, and elapsed_seconds (wall time, not media duration).
Bytes include heartbeat evidence for the open part during capture. The job ID
is supplied to `session.json`; manifest start time begins after resolution,
whereas job start time includes resolution. Errors are bounded, single-line,
and redact HTTP URLs. No library history or persistent job database is added.

Stop sets an Event shared with LIVE capture. Capture checks before/after
resolution, between source chunks/tags, and during retry/confirmation waits.
A blocked HTTP operation must finish or reach its existing 30-second timeout
before capture can observe the stop; resolution may perform several bounded
requests. Finalization can take minutes, and status remains `finalizing`.
Repeated stop does not interrupt FFmpeg, and no new job starts until the worker
finishes. A safe early stop with no retained media completes with null
final_output_path and does not attempt an empty finalization. Stop before first
successful resolution creates no empty parts directory or manifest.

Successful remote stop reports `completed` and `interrupted: true`; the durable
manifest uses its existing `interrupted` status. Finalizer failure reports
`failed`, leaves FLV parts untouched, and preserves existing temporary-output
cleanup guarantees. Use local `tikrec finalize PARTS_DIRECTORY --output FILE`
for manual retry with an unused output. Existing local first-Ctrl-C still
finalizes and exits 130; second Ctrl-C during local finalization cancels FFmpeg.
A local first Ctrl-C on `serve` requests cooperative capture stop and waits for
finalization before exiting. Ending a Scheduled Task is an abrupt process stop.

Remote commands print JSON. Accepted responses return 0 unless they report a
failed job, which returns 1. Request failures also return 1. If a start
request loses its response, query status before retrying: the job may already
be running. Stopping the client or closing its terminal does not stop the job.

## Durable job intent - v0.5 implementation in progress

`tikrec/job_state.py` implements storage only. It is not yet called by `serve`
or the recording controller, and no state-file CLI option exists yet. Service
crash/reboot resume and outage recovery therefore retain v0.4 behavior today.
The service-owned record is separate from the media-owned `session.json`:
explicit job intent must eventually be committed before the capture worker
starts, including when initial resolution has not created a session directory.
It is one latest job, not a history database or account-monitoring registry.

Job schema version 1 contains:

| Field | Meaning |
| --- | --- |
| `schema_version` | Job schema, independently versioned from the media manifest |
| `session_id` | Canonical UUID shared with the recording session |
| `source_url` | Canonical HTTPS public LIVE page; no query or fragment |
| `output_path`, `parts_directory` | Absolute MP4 path and its matching `<stem>.parts` directory |
| `started_at`, `ended_at` | Finite nonnegative Unix seconds; end is null while active |
| `state` | resolving/recovering/reconciling/resuming/recording/reconnecting/finalizing/completed/failed |
| `stop_requested` | Durable explicit stop intent |
| `finalization_completed` | Completed finalization guard |
| `room_id` | Canonical positive ASCII decimal public room identity, or null; no leading zeros |
| `resume_count` | Nonnegative number of recording resumes |
| `recovery_reason` | Null or a fixed machine-readable recovery reason |

Reasons are `process_restart`, `user_stop`, `room_ended`, `live_changed`,
`identity_unavailable`, `recovery_finalization`, `existing_output`,
`failed_resume`, `ambiguous_state`, and `unusable_media`. Process restart does
not by itself prove a Windows reboot. No arbitrary error strings, service
tokens, cookies, authentication data, or signed CDN URLs belong in this record.

Writes flush and fsync complete JSON in a unique sibling temporary file, close
it for Windows rename compatibility, and atomically replace committed state.
POSIX additionally fsyncs the parent directory. This prevents exposing
half-written JSON; it does not promise survival of filesystem/hardware loss.
Abandoned temporary records remain evidence and are never loaded as committed
intent. Malformed JSON, duplicate/unknown fields, missing safety fields, or an
unsupported schema fail safely. One service process owns the store; concurrent
service-process coordination is not implemented by this storage module.

Eligibility is conservative: stopped, terminal, finalized, and finalizing jobs
cannot resume capture. An active job without a saved room ID also cannot resume.
Eligibility alone does not prove that the source is the same LIVE or that
retained media is usable; those checks belong to the remaining reconciliation
work. Non-terminal stopped/finalizing jobs still need finalization assessment.

Public room identity is now available through `resolve_live()` and its frozen
`LiveResolution` result. `same_live(saved_room_id, result)` compares canonical
room IDs: equal is eligible for further reconciliation, different/missing is
false. A username names the account, not a LIVE. Signed CDN URLs are ephemeral
transport, never identity. Public discovery rejects malformed/conflicting IDs
and verifies any ID echoed by room-info against the queried ID. There is no
documented TikTok guarantee against room-ID reuse; the ID in a successful public
room-info query is the strongest identity currently available here.

Offline is a typed `TikTokOfflineError` with raw status and queried room_id.
Transient network errors and malformed public responses remain distinct typed
resolution failures. No future-LIVE polling is introduced. Result repr and
`safe_diagnostics()` omit signed transport; generic dataclass serialization is
not safe for status/state. Persist only `result.room_id` in the job record.
Job schema stays 1, with canonical room-ID validation shared with the resolver.
None of this wires startup reconciliation or capture resume into the service.

Explicit generic continuation is now implemented in `capture_resume.py` through
`capture_tags_resume` and `capture_url_resume`. These APIs require a supported
interrupted/failed/still-recording manifest, completed contiguous parts from
one, and no ambiguous partial/output state. The caller must ensure the previous
worker is gone; they do not coordinate multiple service processes. A new writer
uses the next part index and fresh codec/keyframe/timestamp state. Old FLV files
remain immutable, connection/resume evidence is appended, and requested
finalization joins every old and new part. Lightweight framing checks run
offline without mandatory codec decoding; real media validation is pending.

These APIs deliberately accept supplied tags or one direct FLV URL. They do not
re-resolve a room, prove same-LIVE eligibility, wait through an outage, or resume
the service automatically. Existing Task Scheduler startup, remote routes, and
local CLI behavior remain unchanged. A crashed job with an abandoned partial
currently fails explicit-resume preflight; no artifact is promoted or repaired.
The next v0.5 module will reconcile startup using durable job state, public room
identity, and this continuation machinery. Version remains 0.4.0.

## Windows Task Scheduler one-time setup

Install the current checkout into the PC's existing virtualenv with
`.venv\Scripts\python.exe -m pip install -e .`. FFmpeg and FFprobe must be on
the task account's PATH, as already proven on main-pc. No activated shell is
needed. Keep recordings outside the checkout and use absolute paths.

Create a task named **TikREC Service** manually:

1. **General:** select the normal recording account (Leandro); choose **Run
   whether user is logged on or not**, and save the account credentials if
   prompted. Administrator elevation is not required for TikREC itself.
2. **Triggers:** **At startup**, with a delay such as one minute to let Tailscale
   establish its address. This launches the service, not future LIVE monitoring.
3. **Actions / Start a program:** Program/script:
   `C:\Users\Leandro\dev\TikREC\.venv\Scripts\tikrec.exe`.
   Arguments (replace `100.x.y.z` with the actual PC Tailscale IP):
   `serve --host 100.x.y.z --port 8765 --token-file C:\Users\Leandro\TikREC-secrets\token.txt`.
   Start in: `C:\Users\Leandro\dev\TikREC`. Quote any argument path with spaces.
4. **Conditions:** remove idle requirements and any power/network conditions
   that would stop the service unexpectedly. Keep the always-on PC awake.
5. **Settings:** allow on-demand runs; disable **Stop the task if it runs longer
   than ...** (the scheduler otherwise defaults to a time limit). Choose **Do
   not start a new instance** when already running. Enable restart on failure,
   for example after one minute, to retry a startup bind before Tailscale is
   ready. Restarting the service does not resume a crashed recording in v0.4.
6. Save and **Run** the task. Check `remote health` from the Mac. Task Scheduler
   can display `0x41301` while the persistent task is running.

Microsoft documents the default three-day
[execution limit](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-executiontimelimit)
and [ignore-new-instance policy](https://learn.microsoft.com/en-us/windows/win32/api/taskschd/ne-taskschd-task_instances_policy).
The settings above keep the intended service lifetime independent of a shell.

To stop a recording, use `tikrec remote stop`, then poll status for a terminal
result. Do not use Task Scheduler **End** or `Stop-ScheduledTask` for recording
stop. For service maintenance, first gracefully stop the recording and wait for
completion, then end the idle task. Restart it after updating the checkout.
TikREC does not create or modify scheduled tasks automatically.

## Deployment verification still required

Offline tests cover handlers with fake sockets and injected capture. They do
not prove the actual Task Scheduler/Tailscale lifetime or media playability.
On a chosen public LIVE, start from the Mac, disconnect SSH/close VS Code, then
reconnect and confirm progress continued. Request remote stop and wait for
final output. Validate retained parts and the MP4 through `tikrec validate`
(use `--deep` for the completed output). See SPEC.md's FFprobe decoder/DTS
checks; its null-muxer warning distinguishes timestamp resynthesis notices
from actual decoder failure.

v0.5 owns crash/reboot reconciliation, persisted service jobs, automatic resume,
and broader environment-failure policy. Existing manifests and retained parts
remain durable evidence now. No release tag is created by this implementation.
