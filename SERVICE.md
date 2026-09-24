# TikREC remote recording and startup recovery

Mac -> Tailscale -> main-pc -> TikREC service -> files on main-pc.

Two bounded workers record independently of HTTP clients and of each other.
Launch the service independently of SSH so disconnecting the remote shell does
not end capture.

This document describes the released v0.10.0 service plus unreleased v0.11.0 storage-status development.
Per-user recovery-window, monitored-creator, and output-directory configuration are
selected at startup; guided recovery remains a local CLI addition. The service
can own and automatically fill a fixed capacity of two independent recordings.
Library, download, retention, notification, and browser-control capabilities
remain outside this slice. v0.10.0 is the current published release.

## Bind and secret

`tikrec serve` defaults to `127.0.0.1:8765`. `--host` accepts an explicit IPv4 or
IPv6 address (`localhost` means `127.0.0.1`). Every non-loopback bind, including
an explicit wildcard, requires a token; prefer the PC's Tailscale IP. `--port`
accepts 1–65535. The client accepts a hostname such as `main-pc` or an IP.

`--recovery-window-seconds SECONDS` overrides the configured LIVE recovery
window for this service process. Otherwise `serve` uses the optional strict
per-user `recovery_window_seconds`, then the built-in 900 seconds. Accepted
values are integers from 60 through 3600. Configuration is read once at startup;
restart the service after changing it. This setting is not part of remote start
or the HTTP API.

The same startup snapshots `monitored_creators`, `output_directory`, and
`minimum_free_space_gib` (strict integer 1–1024, default 10). An empty
creator list and a missing output directory are both valid; the former starts no
polling worker, while the latter reports unattended admission as blocked. With no
explicit recovery-window override, normal strict configuration validation applies
to the whole document. With an explicit override, the service still validates
JSON/schema/unknown fields plus the creator list, output directory, and reserve, while
unrelated known validation/debug preferences remain lazy so they cannot
needlessly defeat the override. Malformed fields needed by the running service
fail startup explicitly. Configuration changes require a service restart.

Run configuration commands in the same host filesystem view used by the
Scheduled Task. Packaged desktop development environments can redirect writes
under `%APPDATA%` while still displaying the conventional path; a successful
`monitor list` in that environment is therefore not proof that the task-visible
file changed. The 2026-09-22 main-pc deployment detected this by comparing the
fresh service snapshot with the CLI result, then used TikREC's normal CLI with
an explicit UNC spelling of the same host file and verified the restarted
service listed both creators. Do not compensate by editing JSON or by changing
the task definition.

Use `--token-file FILE` or `TIKREC_TOKEN`. Files override the environment and may
end with a newline. Tokens must be 16–512 printable ASCII characters without
spaces; use a randomly generated secret with at least 32 characters. Empty or
invalid configured tokens are rejected. Token values are never printed, passed
to capture, or written into session metadata. If a token is configured, all
all endpoints require `Authorization: Bearer SECRET`, including loopback.

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
requests are refused. The current service has no accounts, TLS termination,
TikTok credentials, shell commands, executable-path options, or file serving.

Python's [HTTP server documentation](https://docs.python.org/3.11/library/http.server.html)
describes its limited production security. TikREC supplies a narrow custom
handler, bounded JSON bodies/read timeouts, and token checks; it is still scoped
to trusted-network control rather than public hosting.

## API contract

All normal responses are JSON. POST bodies require `application/json`, exactly
one Content-Length, and 1–8192 bytes; transfer encoding is unsupported.

| Request | Body | Result |
| --- | --- | --- |
| `GET /health` | none | 200: service/version plus capacity, active count, available slots, shutdown state, and per-slot recovery summaries |
| `GET /recording` | none | 200: compatible idle/current/latest snapshot when unambiguous; 409 directs multiple current jobs to `/recordings` |
| `GET /recordings` | none | 200: capacity, active count, available slots, and one sanitized status per stable slot |
| `GET /monitoring` | none | 200: sanitized observations, admission, and automatic-selection/re-arm status |
| `POST /recording/start` | `{"url":"https://www.tiktok.com/@username/live","output":"C:\\Users\\Leandro\\Videos\\name.mp4","raw_copy":true}` (`raw_copy` optional) | 202: one free slot atomically accepted the job; 409 if capacity is unavailable or another current slot owns the LIVE |
| `POST /recording/stop` | `{}` or `{"session_id":"UUID"}` | 202: sole/targeted job stop requested; empty body is 409 when multiple current jobs are ambiguous; unknown/non-active session is 404 |

Start accepts `url` and `output` string fields plus optional boolean `raw_copy`.
Omitted or false keeps diagnostics disabled. True writes each raw connection and
arrival sidecar directly in the matching `<stem>.parts` directory so raw bytes,
retained media, connection evidence, manifest, and final output share one session
location. The flag is durable across safe service recovery and never changes
capture/retry policy; diagnostic I/O failures remain warnings. LIVE URLs must use
`tiktok.com` or `www.tiktok.com` and `/@username/live`; query/fragment metadata
is discarded and HTTPS/www is normalized. Signed CDN URLs are rejected as
inputs and never appear in normal status. Output must be an absolute `.mp4`
path on the service machine. Existing output or `<stem>.parts` is rejected;
capture also rechecks to prevent accidental session reuse.
The internal automatic expected-room guard is not an HTTP field; callers cannot
choose or override it.

The manager rejects cross-slot output or `.parts` path collisions and duplicate
normalized public LIVE pages under one allocation lock. Creator handle spelling
is case-equivalent for page ownership, including existing mixed-case durable jobs
and temporary unreadable status; accepted source URLs retain their spelling.
Each controller exposes only current session/page/proven-room and accepted
local output/parts paths under its lock. The manager refreshes those facts
within allocation so restored owners, manual jobs that later prove a room, and
pending paths remain protected if rich status fails. Path ownership begins at
start acceptance, before either target must exist on disk. A partial read
cannot erase a known claim; if current identity or required path ownership is
still unknown, new allocation fails with a bounded 409 busy response. If both
rich status and narrow ownership are unreadable on the first observation,
`ambiguous_state` health or a failed health read cannot prove the slot empty;
allocation stays closed. An invalid narrow `current=true` identity also stays
unknown even if an
earlier health read showed availability. A reliable narrow `current=false` can
prove a corrupt slot has no current session, leaving a healthy other slot
available. Later healthy reads
restore ordinary capacity without retaining an unknown-owner marker.
For automatic starts it also reserves the expected canonical room in memory for
the accepted session, closing the interval before its worker publishes proven
room identity. Another current slot cannot claim that room. Settlement or slot
reuse releases the reservation; unreadable status cannot prove release. Expected
room identity is not added to durable job state before resolution. A duplicate
returns a fixed 409 conflict without creating a new session. `session_id` is the
per-recording control identity; `slot_id` is the stable `slot-1`/`slot-2` owner
in aggregate status. A targeted
stop validates a canonical UUID and signals only its owning controller.

Malformed input returns 400, missing authentication 401, browser-origin
requests 403, unknown endpoints 404, absent/duplicate length 411, oversized or
empty body 413, unsupported content type 415, and worker launch failure 500.
Start acceptance is asynchronous: a later resolver, capture, or finalizer
failure appears in job status. These failures do not shut down the service.

## Creator monitoring status

The service polls the startup creator snapshot sequentially in configured order.
It starts the first cycle promptly, never overlaps cycles, and waits 30 seconds
after every completed cycle before beginning the next. Failure for one creator
does not skip later creators. Configured order is deterministic observation
order, not scheduling priority.

`GET /monitoring` and `tikrec remote monitor-status` report the configured poll
interval, whether the worker/cycle is active, cycle count and last start/end
times, plus each handle's state and observation time. State begins `pending` and
becomes `live` only from a structured public LIVE resolution, `offline` only
from explicit `TikTokOfflineError`, or `unknown` for all insufficient evidence.
The only unknown reasons are fixed categories (`transient`, `unverifiable`, or
`unexpected`). A LIVE may include canonical public `room_id`; signed media URLs,
cookies, credentials, and arbitrary remote messages never enter the snapshot.

Observations are memory-only and reset on restart. The monitor does not create or
change durable job, session, or connection evidence. It continues while manual
recordings are active without reserving or altering recording capacity and
publishes only complete-cycle notifications outside its lock. Shutdown blocks
new automatic starts, wakes the cycle wait, and joins the monitor after any
current bounded resolver call.

Each creator includes a fresh admission object when monitoring status is read.
Detection states other than `live` are `not_applicable`. A LIVE is
`skipped/recording_slot_unavailable` whenever no healthy slot remains after
manual recording, startup recovery, finalization, blocked state, or shutdown.
A later request may become ready if the creator is still LIVE and capacity has
returned; there is no queue.

An available slot still requires startup-configured `output_directory`. Missing
configuration is `blocked/output_directory_unconfigured`; failed stat/disk
inspection is `blocked/storage_unavailable`; observed free space below the
configured reserve (10 GiB by default) is `blocked/low_free_space`; and exhausting
the bounded output-name search is `blocked/output_name_unavailable`. Exact-floor
space is sufficient. For an output directory not yet created, admission inspects
its nearest existing parent and creates nothing. A ready result includes the
collision-safe `creator-YYYYMMDD-HHMMSS[-N].mp4` candidate, matching `.parts`
path, observed free bytes, and the response-level threshold.
The response field is `minimum_free_bytes`; each admission object always has
`state`, `reason`, `free_bytes`, `output_path`, and `parts_directory`, using null
for facts that do not apply or could not be established safely.

Authenticated `/health` includes a sanitized `storage` summary with `state`,
`free_bytes`, `minimum_free_bytes`, and `warning_free_bytes`. States are `ok`,
`warning`, `blocked`, `unconfigured`, and `unavailable`. Warning begins below
`max(20 GiB, 2 × configured reserve)`; blocked begins below the reserve.
The probe is read-only, uses the nearest existing output parent, and exposes
neither local paths nor probe errors. This policy only gates automatic starts.

Admission is advisory and non-mutating: it stores no decision, reserves no name,
and never calls the controller by itself. The coordinator reruns allocation
immediately before each automatic attempt, while manager/controller capacity and
collision checks remain authoritative. The floor does not apply to manual
API starts, local commands, recovery, or finalization. Fixed reasons prevent
filesystem exceptions and signed transport from entering status.

After each completed cycle, the service attempts armed/ready creators sequentially
in canonical-handle lexical order until current capacity, capped at two, is
exhausted. Configured observation order is not priority. Admission and free space
are refreshed before each claim. Remaining ready creators report
`skipped/capacity_exhausted` and are reconsidered on a later completed cycle. A
synchronous start failure conservatively stops further attempts in that cycle,
except a duplicate-current-LIVE conflict: its pending claim is cleared without
consuming a room, fixed `suppressed/duplicate_live_owned` status is reported,
and later eligible creators are reconsidered against refreshed capacity in the
same cycle. At most one schema-1 pending claim exists at any instant.

The automatic worker passes the detected canonical room ID through an internal
controller boundary. Before a session directory or first media connection, a
fresh structured resolution must identify that exact room. Missing, offline,
changed, or unverifiable identity fails without opening media for another room.
Manual starts use the unchanged page-based behavior. Once any automatic start is
accepted, that creator/room is consumed even if recording later fails or the
owner stops it. Repeated same-room observations remain suppressed; explicit
offline re-arms, unknown does not, and a different canonical room is eligible.

The response-level `automation` object reports fixed operational/block state,
latest completed cycle, ordered selections, and `started_recordings` entries with
creator/room/session/slot and safe local output facts. Legacy singular fields are
non-null only when one result is the complete truth.
Each creator has an `automation` object with fixed state/reason, `armed`, and the
consumed public room ID where applicable. These fields contain no signed media,
credentials, response bodies, or arbitrary exceptions.

## Job status and stop

States are `idle`, `resolving`, `reconciling`, `recovering`, `resuming`, `recording`,
`recovering_network`, `recovery_wait`, `reconnecting`, `finalizing`, `completed`,
and `failed`. The worker uses `state=recovering_network` with
`recovery_state=recovery_wait` during patient retries. Without saved intent,
a fresh slot returns `{"state":"idle","active":false}`. Each slot's latest job
survives service restart; there is no job history database.

Job snapshots contain session_id, normalized source_url, started_at/ended_at
(Unix seconds), active/state, parts_directory, output_path (requested),
final_output_path (actual result or null), stop_requested, interrupted, error,
room_id, resumed, resume_count, raw_copy_enabled, recovery_state, recovery_reason,
part_count (closed retained parts), reconnect_count (this process's resolution attempts after
the first), bytes_written, and elapsed_seconds (wall time, not media duration).
Bytes include heartbeat evidence for the open part during capture. The job ID
is supplied to `session.json`; manifest start time begins after resolution,
whereas job start time includes resolution. Errors are bounded, single-line,
and redact HTTP URLs. This service version adds no library history or persistent
job database.

`GET /recordings` wraps one such snapshot per stable slot with aggregate capacity
facts. A later job in a reused slot replaces the earlier snapshot even though
the earlier output, `session.json`, and `connections.jsonl` remain on disk;
this endpoint is not a history catalog. `GET /recording` returns the sole
current owner, or the latest settled result when none is current; it refuses
ambiguity rather than hiding a second current job. Empty stop follows the same
rule. Explicit session stop considers
only current active/recovery/finalization ownership and never signals another slot.

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

## Durable job intent - v0.5.0

job_state.py is wired into each serve/controller slot: commit acceptance before worker start,
room_id before media opens, stop before signalling its Event, and lifecycle/results
at transitions. Each latest job is separate from media-owned session.json.

Default storage is `%LOCALAPPDATA%\TikREC\job.json` on Windows (normally
`C:\Users\Leandro\AppData\Local\TikREC\job.json`), or
`${XDG_STATE_HOME:-~/.local/state}/TikREC/job.json` elsewhere. Slot 2 uses the
deterministic sibling `job-2.json`; a v0.9 installation with only `job.json`
therefore starts with an empty second slot and no migration. No state-file CLI
option is added. Use a consistent task account; the path is independent of the
working directory. One service process owns both stores; multiple services under
one account on different ports are unsupported. Each store is loaded and
reconciled only by its owning controller. Corrupt state blocks only that slot and
is preserved. Two interrupted stores claiming one output/parts path fail the
second closed before recovery workers start. A failed socket bind cannot start a
recovery worker. Pre-integration recordings without intent are never adopted by
scanning storage.

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
| `raw_copy_enabled` | Boolean owner opt-in for co-located raw/arrival diagnostics |

Reasons are `process_restart`, `user_stop`, `room_ended`, `live_changed`,
`identity_unavailable`, `recovery_finalization`, `existing_output`,
`failed_resume`, `ambiguous_state`, `unusable_media`, `network_outage`,
`network_recovered`, `outage_timeout`, and `writer_partial_recovery`. Process restart does
not by itself prove a Windows reboot. No arbitrary error strings, service
tokens, cookies, authentication data, or signed CDN URLs belong in this record.
When a job has a parts directory, `/recording` and each `/recordings` slot
derive `input_decode_health` from its session manifest after capture stops.
The fixed summary contains status, capped diagnostic count, allowlisted codes,
and the cap flag; missing or malformed evidence appears as `unknown`. Active
jobs also report `unknown` until finalization finishes. The job schema is
unchanged, and no raw FFmpeg messages enter status or durable job intent.

Writes flush/fsync complete JSON in a unique sibling temporary, close for Windows
rename, and atomically replace committed state; POSIX fsyncs the parent directory.
This prevents half-written JSON, not hardware loss. Abandoned temporaries remain
evidence and are never loaded. Malformed/duplicate/unknown/missing fields or schema
fail safely. Legacy schema-1 jobs that predate only `raw_copy_enabled` load it as
false; missing lifecycle/identity safety fields still fail closed. Concurrent
service-process coordination is unsupported.

Stopped, terminal, finalized, finalizing, or identity-less jobs cannot resume
capture. Reconciliation also checks same-LIVE identity and usable retained media;
non-terminal stopped/finalizing jobs need finalization assessment.

Public resolve_live returns canonical room ID plus transient signed transport;
same_live compares IDs only. Persist only room_id, never generic resolution data.
An initial LIVE-page HTTP 404 remains a terminal resolution failure and creates no
recording. Once capture owns retained media and a canonical room ID, bound
resolution overlaps that ID's public room status/transport refresh with current
public account identity verification, without requiring the username LIVE page
to remain HTTP 200. The fast transport is accepted only when both identify the
saved live room; all insufficient evidence uses the conservative full resolver.
A proven saved-room offline status enters the existing three-observation room-end
confirmation, a different current live room keeps existing live-changed behavior,
and unprovable state fails closed with retained media. A media-source HTTP 404
after established capture requests this identity refresh; the status code alone
never proves room end.

Explicit capture_tags_resume/capture_url_resume require supported manifest,
contiguous parts, no partial/output ambiguity, and one owner. Old files stay
immutable; fresh codec/keyframe/timestamp state starts the next numbered part.
live_resume.py adds saved same-room identity checks to that continuation.
Startup additionally has a narrow writer-partial recovery step described below;
ordinary explicit resume and completed-part discovery still reject partials.
That recovery change did not alter CLI/routes. The current package version is
0.10.0.

## Durable automatic-start state - v0.9.0

The service owns `%LOCALAPPDATA%\TikREC\automation.json` on Windows or
`${XDG_STATE_HOME:-~/.local/state}/TikREC/automation.json` elsewhere, beside
`job.json`. This runtime state is separate from per-user configuration and media
evidence. Schema 1 contains only a sorted object of canonical creator handles to
consumed canonical room IDs and either null or one pending claim with creator,
room ID, absolute MP4 candidate, matching `.parts` candidate, and the prior safe
service job ID when one exists.

Immediately before automatic controller start, a flushed atomic replacement
records the claim. Synchronous rejection clears it; accepted start promotes the
room to consumed and clears it. On startup, an exactly matching durable job
in either slot promotes the claim. The selected slot's unchanged prior identity
or a still-idle slot can prove the claim stale; every other result is ambiguous
and disables automatic starts. All current jobs are also inspected when a manual
recording may already own an observed creator/room. A corrupt/unreadable
file or required write failure also disables automation without deleting the
file, starting capture, or preventing safe manual/read-only service operation.
Abandoned temporary files are ignored. No signed media URL, cookie, token,
credential, TikTok response body, or arbitrary exception belongs in this file.

## Service startup reconciliation (v0.5.0)

`StartupReconciler` in `reconciliation.py` decides recovery independently of HTTP.
Resolver, resume capture, finalizer, store, clock, and storage/media inspection are
injectable. `recovery_session.py` validates storage; `recovery_evidence.py` appends
fixed evidence. The controller reserves recovery before HTTP accepts any start.

1. Reserve the listening address, load committed job intent, and validate it.
2. Missing intent is idle; completed/failed/finalization-completed intent is settled
   and never relaunches capture. A stopped and successfully finalized job stays done.
3. A non-terminal job occupies the slot in `reconciling`. Validate session UUID,
   source, optional manifest creator against the durable source page,
   room/output/parts paths, contiguous completed FLV parts, and connection
   evidence. Missing storage or identities and arbitrary partials block recovery.
4. The exact canonical next writer partial is eligible only for an active recording
   job/manifest with matching identity, paths/counts, absent output/finalizer temp,
   one regular artifact, and valid writer FLV structure. Fresh read-only
   writer-compatible preflight rechecks current job, manifest bytes,
   creator/room/paths, and exact partial ownership. Recheck the job after slow
   inspection, condition the recovery-state transition on its old durable
   value, and verify job/manifest/source again at each preservation, staging,
   and publication boundary. Persist
   `recovering/writer_partial_recovery` before moving bytes. Atomically preserve the
   original under `.tikrec-writer-crash-SESSION-part-NNNN.evidence`, copy only its
   parser-proven complete prefix, pass normal structure plus FFprobe decoder/DTS
   checks, and atomically publish `part-NNNN.flv`. On the first truncated or
   malformed tag, exclude that tag and all following bytes from the new copy;
   never resynchronize or repair framing. A prefix without valid media still
   blocks. Immediately before appending manifest recovery evidence, recheck its
   unchanged ownership fingerprint and the actual recovered source/prefix,
   including after slow hashing/prefix comparison. The manifest promotion itself
   conditionally checks its original bytes and current job/media ownership.
   Manifest evidence records source SHA-256 and discarded byte counts.
   Recovery interrupted after preservation or publication is safely retryable.
5. Existing requested output is never overwritten. Matching committed manifest
   completion plus a nonempty regular output and bounded matching codec/container/
   positive-duration inspection can settle completion. Otherwise expose ambiguity.
6. Stop-requested/finalizing jobs never resolve TikTok or resume capture. If output
   is absent and no finalizer partial exists, retry finalization of retained parts.
7. Capture-phase jobs with saved identity and explicit-resume-compatible storage
   resolve public identity with the bounded patient policy below, in the worker.
   Resolution is bound to the saved canonical room ID, so a username LIVE-page
   404 can be checked against direct room status and current-account identity
   without inventing an offline result. Fresh storage preflight rechecks the
   optional manifest creator against the accepted public page and the proven
   room before recovery evidence, resolution, or durable resume-state writes.
   Decide using the table.
8. Persist `resuming`, process_restart reason, and incremented resume_count before
   media continuation. Preserve session/job ID, paths, saved room ID and start time.
   Finalization also commits its phase before starting the encoder.

| Startup observation | Action |
| --- | --- |
| Same room ID | Resume only the prior explicitly-started LIVE, opening a new direct FLV connection and next numbered part; no append or reused timestamp/config/keyframe state. |
| Different room ID | Never record the new LIVE automatically. Retain saved identity, treat prior LIVE as ended during downtime, and finalize its retained parts if safe. |
| Explicit `TikTokOfflineError` | Prior explicitly started LIVE ended; finalize retained parts if safe. This recovery decision does not control the independent creator monitor. |
| Transient DNS/timeout/connection/temporary HTTP failure | Keep prior identity and media, persist recovering_network/network_outage, and retry in-process with the shared bounded policy. |
| Patient recovery window exhausted | Terminal failed/outage_timeout; retain parts without finalizing, release service slot, never auto-relaunch on restart. |
| Malformed public data/programming/storage failure | Preserve evidence/media and expose fixed failure diagnostics. Remain blocked with `recovery_state=failed`; never treat this as offline. |

The deployed 2026-09-23 Eliss recovery exercised the malformed-tail branch
after an unexpected Windows shutdown. The original 31,380,072-byte writer
partial was preserved byte-for-byte as deterministic crash evidence; only its
31,247,682-byte parser-proven prefix was published after structure, full
decoder, and DTS validation. The 132,390 discarded bytes were all zero and
were recorded in the manifest. The same saved room and session resumed with a
new connection and part; the service did not invent media for the downtime.
This observation supports an interrupted buffered/filesystem write but does
not establish a defect in normal writer operation.

Automatic resume applies only to the explicitly-started prior LIVE; that recovery
path never monitors a username for the next LIVE. The independent read-only
monitor cannot resume or start recordings. Username/output path prove no identity.
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
Policy/clocks/Event waiter are injectable. Local `live` and `serve` accept the
same bounded CLI override and otherwise use configuration then 900 seconds. The
service applies its startup-selected policy to both active capture and startup
reconciliation; it does not hot-reload configuration. Healthy
media-bearing EOF re-resolves immediately; patient failure waits retain this policy,
and the three offline checks remain five seconds apart. Initial unresolved capture
retains its three-failure limit. Patient capture requires an anchored room ID;
useful retained media resets an episode, same-room resolution alone cannot.

During recovery health/status work, available=false, and start returns 409.
Timeout reports failed/recovery_state=exhausted/recovery_reason=outage_timeout,
retains unfinalized parts, and releases the slot for a new explicit job. Room end
is unproven; restart never relaunches that terminal job. Direct `reconcile()` still
defaults to single-attempt typed deferred; the service supplies the patient policy.

Only meaningful transitions are committed. Job schema stays 1 with extended
enums; a crash in recovering_network leaves non-terminal intent for same-identity
reconciliation with a fresh window. No deadline/signed URL is persisted. Coalesced
network_recovery events retain counters/boundaries. Task Scheduler remains the
process/bind safety net.

### v0.6 reconnect-gap scope

The read-only reconnect-gap analyzer separates ordinary reconnects from outage,
restart/resume, room-end, and other recovery boundaries. Three pre-change
ordinary reconnects measured a fixed 1.004--1.008 seconds of local/backoff, so a
healthy media-bearing close now proceeds directly to fresh resolution. Retained
post-change evidence measured a 1.920-second total gap with 0.010 seconds of
local/backoff, verifying that the fixed wait collapsed. Failure/outage backoff,
the patient recovery policy above, room-end confirmation, stop behavior, fresh
URL resolution, and writer/part safety are unchanged. The single post-change
sample does not justify retry, resolver, or HTTP changes.

Issue #18 later supplied strict paired live evidence that serial page/account
discovery materially dominated established resolution. Issue #19 therefore
changes only the established bound resolver: saved-room room/info and public
account lookup run concurrently, and the transport is accepted only when both
prove the saved live room. Initial resolution and retry, backoff, media-open,
writer, finalization, room-end, and rendition policies remain unchanged. Read-
only live measurement reduced the bound median from 0.942 to 0.366 seconds.
Zoraida then proved deployed natural-end behavior, and Luhpol supplied two natural
media-bearing network recoveries through the same established resolver at 0.419
and 0.397 seconds. No qualifying `ordinary` reconnect occurred, but the rare-
evidence reassessment found no remaining safety or correctness risk that justifies
making that exact timing classification a release prerequisite.

Remote stop during recovery commits stop intent and prevents capture even if
same-room resolution is finishing. Stop/shutdown wakes patient waits immediately
and safely finalizes prior parts; blocked requests observe stop on return/timeout.
Inactive single-attempt deferred recovery retains stop intent for next startup.
A resume/preflight failure keeps non-terminal recovery and blocks new starts.

Safe recovery finalizes all retained parts without overwriting output, updating
manifest/job on success. Encoder failure retains parts and non-terminal finalizing
intent. A nonempty finalizer temporary is recoverable only when durable job state
is `finalizing`, manifest finalization is `running`, and output is absent. It is
atomically preserved under a collision-safe session evidence name before all
retained parts are re-finalized. Empty/nonregular/unproven temporaries, evidence
name collisions, and coexisting output/temporary artifacts remain untouched and
block for manual assessment.

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
   establish its address. This launches controls, configured monitoring, and
   automatic recording for creators that pass room identity, slot, storage, and
   free-space safety checks.
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

To stop the sole current recording, use `tikrec remote stop`; with multiple
current recordings, list them with `remote recordings` and pass the intended
`--session-id UUID`. Poll aggregate status for terminal results. Do not use Task
Scheduler **End** or `Stop-ScheduledTask` for recording stop. For service
maintenance, first gracefully stop all recordings and wait for completion, then
end the idle task. Restart it after updating the checkout.
TikREC does not create or modify scheduled tasks automatically.

## Issue #8 raw-copy validation workflow

Deploy the current checkout only while the service is idle, using the existing
editable-install and Scheduled Task procedure above. For one owner-authorized
public LIVE, choose a new output whose MP4 and matching `.parts` directory do not
exist, then use the normal remote service path with the diagnostic opt-in:

```powershell
$Tikrec = 'C:\Users\Leandro\dev\TikREC\.venv\Scripts\tikrec.exe'
$Server = 'http://100.123.31.16:8765'
$TokenFile = 'C:\Users\Leandro\.tikrec-service-token'
$LiveUrl = 'https://www.tiktok.com/@REPLACE_CREATOR/live'
$Output = 'C:\Users\Leandro\Videos\REPLACE_ISSUE8_NAME.mp4'

& $Tikrec remote health --server $Server --token-file $TokenFile
& $Tikrec remote start --server $Server $LiveUrl --output $Output --raw-copy --token-file $TokenFile
& $Tikrec remote status --server $Server --token-file $TokenFile
& $Tikrec remote recordings --server $Server --token-file $TokenFile
```

Allow normal capture and natural source behavior; do not manufacture a replay,
corruption, or network fault. Poll status without stopping a healthy recording.
After natural completion, preserve the MP4 and entire `.parts` directory
read-only. If `connections.jsonl` records a timestamp replay, the same directory
must contain that connection's named `.raw` file and `.arrivals.jsonl` sidecar;
compare raw and retained FLV tag bytes around the recorded positions before any
repair attempt. If no replay occurs, retain or dispose of the ordinary session
only under the owner's normal evidence policy and repeat on a later authorized
LIVE. Never enable this storage-heavy option for routine recordings by default.

## Deployment verification still required

Offline tests do not prove Task Scheduler/Tailscale lifetime or playability. On a
chosen public LIVE, start from the Mac, disconnect SSH/VS Code, and confirm progress
continued. Stop remotely, wait for output, then validate parts and MP4 with
tikrec validate (--deep for output). See SPEC.md's FFprobe decoder/DTS checks and
null-muxer warning distinguishing resynthesis notices from decoder failure.

v0.4 deployment is validated. The first v0.5 abrupt Task Scheduler restart test
on 2026-09-16 preserved durable intent/media but exposed the writer-partial gap.
Issue #14 now implements that policy and passes 728 tests plus 19 subtests; the
original artifact was not used as a fixture or modified. The 2026-09-19 repeat
deployment test passed: the exact 7,874,881-byte crash source was preserved, the
equal complete prefix was published, and the same session/room resumed through a
fresh connection and `part-0002.flv`; both recovered and first resumed parts passed
decoder/DTS checks. A later isolated source-configuration part had H.264 decoder
errors and remains preserved without a recovery-code change. Network-outage and
final graceful-stop/deep-output validation phases were kept separate.

The temporary-network-outage phase passed later on 2026-09-19. A loopback HTTPS
CONNECT proxy carried TikTok page/API resolution and the media CDN while the
service control client bypassed proxies over Tailscale. Terminating only the proxy
left the service responsive, closed a valid 6,293,414-byte first part, and exposed
durable `recovering_network` state with fixed session, room, part, and byte counts
through the staged waits. After about 93 seconds, restoring the proxy automatically
matched the saved room and resumed into a fresh growing second part without a new
start. Both the closed pre-outage part and the active post-reconnect media passed
FFprobe decoder/DTS checks. The coalesced recovered boundary intentionally remains
open until the successful connection closes and turns its writer partial into a
completed retained part. Final graceful-stop/finalization, retained-session, and
deep-output validation subsequently passed on that preserved session. Remote stop
closed connection 8 and retained parts 2--4, recorded the open recovery boundary
as `user_stop`, finalized all four parts, and produced a 1,200.636-second H.264/AAC
MP4. The retained session, every FLV's decoder/DTS checks, and deep MP4 validation
all passed without findings. The proxy was retired and the Scheduled Task restarted
healthy, available, and idle without proxy configuration.

That restart exposed and fixed one status-only accounting defect: an inactive
controller now takes the maximum durable reconnect count from `session.json`, so
completed status retains its 7 reconnects across a service restart. Active status
still uses in-memory allocations and does not open the manifest while capture may
atomically replace it on Windows. The current package version is 0.10.0.

The 2026-09-23 v0.10 deployed two-slot gate used an existing automatically
started, #29-recovered Eliss session in slot 1 and an owner-manually-started
Sinaloan session in slot 2. Both retained bytes independently increased. Legacy
singular status/empty stop returned HTTP 409 while both were active. A targeted
Sinaloan stop finalized only slot 2 while Eliss remained recording and grew;
Eliss was later stopped by its own UUID. Both final MP4s passed standard and
deep validation. Sinaloan's retained session passed; Eliss's retained session
reported H.264 errors in parts 3/5 and timestamp warnings in part 8, all
captured before Sinaloan began. Its manifest and service expose the same
`degraded` input health while the final MP4 deep-decodes. The #29 crash
evidence and recovered part remained byte-identical through completion.
After both jobs completed, one idle restart reloaded both durable slots without
relaunch, preserved all 18 settled media/evidence file hashes, and retained
the monitored pair and bearer-authentication boundary. The manual second start
demonstrates deployed concurrency and isolation, not automatic second-slot
selection. At that gate, separate independent review remained required before
release preparation; it subsequently passed on corrected `a9c172f`.
