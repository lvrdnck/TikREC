# TikREC remote recording and startup recovery

Mac -> Tailscale -> main-pc -> TikREC service -> files on main-pc.

One worker records independently of HTTP clients. Launch the service independently
of SSH so disconnecting the remote shell does not end capture.

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
| `GET /health` | none | 200: service, version, available, active, shutting_down, recovery_state, recovery_reason |
| `GET /recording` | none | 200: idle or current/latest job snapshot |
| `POST /recording/start` | `{"url":"https://www.tiktok.com/@username/live","output":"C:\\Users\\Leandro\\Videos\\name.mp4"}` | 202: job accepted; 409 if active/recovery unresolved/shutting down |
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

States are `idle`, `resolving`, `reconciling`, `recovering`, `resuming`, `recording`,
`recovering_network`, `recovery_wait`, `reconnecting`, `finalizing`, `completed`,
and `failed`. The worker uses `state=recovering_network` with
`recovery_state=recovery_wait` during patient retries. Without saved intent,
a fresh service returns `{"state":"idle","active":false}`. The latest job survives
service restart; there is no job history database.

Job snapshots contain session_id, normalized source_url, started_at/ended_at
(Unix seconds), active/state, parts_directory, output_path (requested),
final_output_path (actual result or null), stop_requested, interrupted, error,
room_id, resumed, resume_count, recovery_state, recovery_reason,
part_count (closed retained parts), reconnect_count (this process's resolution attempts after
the first), bytes_written, and elapsed_seconds (wall time, not media duration).
Bytes include heartbeat evidence for the open part during capture. The job ID
is supplied to `session.json`; manifest start time begins after resolution,
whereas job start time includes resolution. Errors are bounded, single-line,
and redact HTTP URLs. No library history or persistent job database is added.

During outages snapshots add retry_attempt, next_retry_in_seconds,
outage_elapsed_seconds, recovery_window_seconds, and network_failure_kind.
Countdown and elapsed are derived in memory from a monotonic clock. Retry attempts
count classified failures in the current episode, not a lifetime total.

Stop sets a shared Event checked around resolution, source chunks/tags, and waits.
Blocked HTTP must return or reach its existing timeout (up to 30 seconds); resolution
may perform several bounded requests. Finalization can take minutes with status
finalizing; repeated stop does not interrupt FFmpeg or release the worker early.
Stop with no retained media completes with null final_output_path and no empty
finalization; before successful resolution it creates no directory/manifest.

Remote stop reports completed/interrupted=true; the manifest uses interrupted.
Finalizer failure reports failed, retains parts, and preserves temporary cleanup.
Use `tikrec finalize PARTS_DIRECTORY --output FILE` with unused output for manual
retry. Local first Ctrl-C finalizes/exits 130; second cancels FFmpeg. Ctrl-C on
serve cooperatively stops/finalizes; ending a Scheduled Task is abrupt.

Remote commands print JSON; failed job/deferred/failed recovery or request errors
return 1, other accepted responses 0. If start loses its response, query status
before retrying; it may already be running. Closing the client does not stop it.

## Durable job intent - v0.5 implementation in progress

job_state.py is wired into serve/controller: commit acceptance before worker start,
room_id before media opens, stop before signalling its Event, and lifecycle/results
at transitions. This one latest job is separate from media-owned session.json.

Default storage is `%LOCALAPPDATA%\TikREC\job.json` on Windows (normally
`C:\Users\Leandro\AppData\Local\TikREC\job.json`), or
`${XDG_STATE_HOME:-~/.local/state}/TikREC/job.json` elsewhere. No state-file CLI
option is added. Use a consistent task account; the path is independent of the
working directory. One service process owns this store; multiple services under
one account on different ports are unsupported. A failed socket bind cannot
start a recovery worker. Pre-integration v0.4 recordings without durable intent
are never adopted by scanning storage.

Job schema version 1 contains:

| Field | Meaning |
| --- | --- |
| `schema_version` | Job schema, independently versioned from the media manifest |
| `session_id` | Canonical UUID shared with the recording session |
| `source_url` | Canonical HTTPS public LIVE page; no query or fragment |
| `output_path`, `parts_directory` | Absolute MP4 path and its matching `<stem>.parts` directory |
| `started_at`, `ended_at` | Finite nonnegative Unix seconds; end is null while active |
| `state` | resolving/recovering/reconciling/resuming/recording/reconnecting/recovering_network/recovery_wait/finalizing/completed/failed |
| `stop_requested` | Durable explicit stop intent |
| `finalization_completed` | Completed finalization guard |
| `room_id` | Canonical positive ASCII decimal public room identity, or null; no leading zeros |
| `resume_count` | Nonnegative number of recording resumes |
| `recovery_reason` | Null or a fixed machine-readable recovery reason |

Reasons are `process_restart`, `user_stop`, `room_ended`, `live_changed`,
`identity_unavailable`, `recovery_finalization`, `existing_output`,
`failed_resume`, `ambiguous_state`, `unusable_media`, `network_outage`,
`network_recovered`, and `outage_timeout`. Process restart does
not by itself prove a Windows reboot. No arbitrary error strings, service
tokens, cookies, authentication data, or signed CDN URLs belong in this record.

Writes flush/fsync complete JSON in a unique sibling temporary, close for Windows
rename, and atomically replace committed state; POSIX fsyncs the parent directory.
This prevents half-written JSON, not hardware loss. Abandoned temporaries remain
evidence and are never loaded. Malformed/duplicate/unknown/missing fields or schema
fail safely. Concurrent service-process coordination is unsupported.

Stopped, terminal, finalized, finalizing, or identity-less jobs cannot resume
capture. Reconciliation also checks same-LIVE identity and usable retained media;
non-terminal stopped/finalizing jobs need finalization assessment.

Public resolve_live returns canonical room ID plus transient signed transport;
same_live compares IDs only. Persist only room_id, never generic resolution data.

Explicit capture_tags_resume/capture_url_resume require supported manifest,
contiguous parts, no partial/output ambiguity, and one owner. Old files stay
immutable; fresh codec/keyframe/timestamp state starts the next numbered part.
live_resume.py adds saved same-room identity checks to that continuation.
Real resumed media validation remains pending; CLI/routes stay unchanged, version 0.4.0.

## Service startup reconciliation (v0.5 module, release unfinished)

`StartupReconciler` in `reconciliation.py` decides recovery independently of HTTP.
Resolver, resume capture, finalizer, store, clock, and storage/media inspection are
injectable. `recovery_session.py` validates storage; `recovery_evidence.py` appends
fixed evidence. The controller reserves recovery before HTTP accepts any start.

1. Reserve the listening address, load committed job intent, and validate it.
2. Missing intent is idle; completed/failed/finalization-completed intent is settled
   and never relaunches capture. A stopped and successfully finalized job stays done.
3. A non-terminal job occupies the slot in `reconciling`. Validate session UUID,
   source, room/output/parts paths, contiguous completed FLV parts, and connection
   evidence. Missing storage or identities and abandoned partials block recovery.
4. Existing requested output is never overwritten. Matching committed manifest
   completion plus a nonempty regular output and bounded matching codec/container/
   positive-duration inspection can settle completion. Otherwise expose ambiguity.
5. Stop-requested/finalizing jobs never resolve TikTok or resume capture. If output
   is absent and no finalizer partial exists, retry finalization of retained parts.
6. Capture-phase jobs with saved identity and explicit-resume-compatible storage
   resolve public identity with the bounded patient policy below, in the worker.
   Storage preflight is performed once before that loop. Decide using the table.
7. Persist `resuming`, process_restart reason, and incremented resume_count before
   media continuation. Preserve session/job ID, paths, saved room ID and start time.
   Finalization also commits its phase before starting the encoder.

| Startup observation | Action |
| --- | --- |
| Same room ID | Resume only the prior explicitly-started LIVE, opening a new direct FLV connection and next numbered part; no append or reused timestamp/config/keyframe state. |
| Different room ID | Never record the new LIVE automatically. Retain saved identity, treat prior LIVE as ended during downtime, and finalize its retained parts if safe. |
| Explicit `TikTokOfflineError` | Prior LIVE ended; finalize retained parts if safe. No future-LIVE monitoring or polling. |
| Transient DNS/timeout/connection/temporary HTTP failure | Keep prior identity and media, persist recovering_network/network_outage, and retry in-process with the shared bounded policy. |
| Patient recovery window exhausted | Terminal failed/outage_timeout; retain parts without finalizing, release service slot, never auto-relaunch on restart. |
| Malformed public data/programming/storage failure | Preserve evidence/media and expose fixed failure diagnostics. Remain blocked with `recovery_state=failed`; never treat this as offline. |

Automatic resume applies only to the explicitly-started prior LIVE; it never
monitors a username for the next LIVE. Username/output path prove no identity.
Signed transport never enters job state or diagnostics.

### Patient DNS/network recovery

`network_errors.py` separates terminal evidence, stop, transient transport,
malformed responses, and local errors. DNS, timeout, reset/abort/refusal,
network-unreachable, premature read EOF, and urllib-wrapped network causes retry.
HTTP 408/425/429 and 500–599 retry; permanent HTTP, malformed payloads, disk/
permission and programming errors fail. Writer errors cannot enter network recovery.

`RetryPolicy` is shared by active LIVE and startup resolution: waits of 1, 2, 5,
10, 10, then 30 seconds, capped at 30. Retry-After seconds/HTTP dates can increase
the wait up to that cap. The default window is 900 monotonic seconds from the
first transient failure. Waits are clamped to remaining time; no new retry starts
at expiry. An in-flight HTTP operation still uses its existing bounded timeout.
Policy/clocks/Event waiter are injectable; no CLI configuration is added. Healthy
EOF keeps the 1-second path and three offline checks five seconds apart. Initial
unresolved capture retains its three-failure limit. Patient capture requires an
anchored room ID; useful retained media resets an episode, same-room resolution alone cannot.

During recovery health/status work, available=false, and start returns 409.
Timeout reports failed/recovery_state=exhausted/recovery_reason=outage_timeout,
retains unfinalized parts, and releases the slot for a new explicit job. Room end
is unproven; restart never relaunches that terminal job. Direct `reconcile()` still
defaults to single-attempt typed deferred; the service supplies the patient policy.

Only meaningful transitions are committed. Job schema stays 1 with extended
enums; a crash in recovering_network leaves non-terminal intent for same-identity
reconciliation with a fresh window. No deadline/signed URL is persisted. Coalesced
network_recovery events retain counters/boundaries. Task Scheduler remains the
process/bind safety net. Successful reconnect-gap optimization belongs to v0.6.

Remote stop during recovery commits stop intent and prevents capture even if
same-room resolution is finishing. Stop/shutdown wakes patient waits immediately
and safely finalizes prior parts; blocked requests observe stop on return/timeout.
Inactive single-attempt deferred recovery retains stop intent for next startup.
A resume/preflight failure keeps non-terminal recovery and blocks new starts.

Safe recovery finalizes all retained parts without overwriting output, updating
manifest/job on success. Encoder failure retains parts and non-terminal finalizing
intent. Ambiguous/missing outputs and abandoned partials need manual assessment;
deeper crash-during-FFmpeg reconciliation remains v0.5 work. No partial is altered.

`connections.jsonl` appends `service_recovery` observations plus the shared
`capture_resume` boundary and new numbered connection records. Times describe
observed reconciliation/resume/finalization, never exact crash time or proof of a
Windows reboot. See [CONNECTION_LOG.md](CONNECTION_LOG.md).

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
   ready. On restart, this v0.5 module reconciles saved explicitly-started jobs.
   TikREC never edits Task Scheduler itself.
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

Offline tests do not prove Task Scheduler/Tailscale lifetime or playability. On a
chosen public LIVE, start from the Mac, disconnect SSH/VS Code, and confirm progress
continued. Stop remotely, wait for output, then validate parts and MP4 with
tikrec validate (--deep for output). See SPEC.md's FFprobe decoder/DTS checks and
null-muxer warning distinguishing resynthesis notices from decoder failure.

v0.4 deployment is validated; real resumed-media/crash/restart/outage checks and
deeper finalization reconciliation remain pending. Version is 0.4.0; v0.5 unfinished.
