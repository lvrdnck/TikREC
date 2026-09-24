# TikREC

A command-line recorder and small remote-control service for public TikTok LIVE streams.

Point it at a LIVE page, it records until the stream ends or you stop it,
reconnecting if the connection drops. Each recording produces one MP4.

This reliability-first implementation is the foundation of a broader future
livestream recording platform. Current v0.10.0 gives the persistent service
capacity for two independent public LIVE recordings; creator automation can
fill available capacity. The deployed
Eliss/Sinaloan pair passed two-slot isolation, targeted stops, media validation,
and idle restart; its second start was manual. Offline regressions cover
automatic capacity and duplicate page, room, and pending-path ownership.
A library, playback, automatic cleanup, notifications, and web workflows remain future
work. Historical Moe media attribution remains non-blocking [#28](https://github.com/lvrdnck/TikREC/issues/28);
the [forensic report](ISSUE_27_FORENSICS.md) preserves the evidence.

The current package, immutable annotated tag, published GitHub Release, and
current released version are v0.10.0.
See [PROJECT_STATE.md](PROJECT_STATE.md) for the authoritative release state.

## Usage

    tikrec live <tiktok-live-page-url> [--output FILE] [--raw-copy DIR] [--recovery-window-seconds SECONDS]
    tikrec record <direct-flv-url> --output FILE [--raw-copy DIR]
    tikrec resolve <tiktok-live-page-url>
    tikrec finalize PARTS_DIRECTORY --output FILE
    tikrec recover ROOT [--validate] [--finalize] [--json]
    tikrec validate TARGET [--deep | --standard] [--json]
    tikrec config show [--json]
    tikrec config path
    tikrec config set output-directory DIRECTORY
    tikrec config unset output-directory
    tikrec config set recovery-window-seconds SECONDS
    tikrec config unset recovery-window-seconds
    tikrec config set minimum-free-space-gib GIB
    tikrec config unset minimum-free-space-gib
    tikrec config set retention-max-age-days DAYS
    tikrec config unset retention-max-age-days
    tikrec config set validation-mode standard|deep
    tikrec config unset validation-mode
    tikrec config set debug-tracebacks true|false
    tikrec config unset debug-tracebacks
    tikrec monitor add CREATOR
    tikrec monitor remove CREATOR
    tikrec monitor list
    tikrec retention protect CREATOR
    tikrec retention unprotect CREATOR
    tikrec retention protected
    tikrec retention plan [ROOT] [--json]
    tikrec serve [--host IP] [--port PORT] [--token-file FILE] [--recovery-window-seconds SECONDS]
    tikrec remote health --server URL [--token-file FILE]
    tikrec remote status --server URL [--token-file FILE]
    tikrec remote recordings --server URL [--token-file FILE]
    tikrec remote monitor-status --server URL [--token-file FILE]
    tikrec remote start --server URL PUBLIC_LIVE_URL --output ABSOLUTE_PC_MP4_PATH [--raw-copy] [--token-file FILE]
    tikrec remote stop --server URL [--session-id UUID] [--token-file FILE]
    tikrec --version

`live` records a public LIVE page and reconnects across dropped
connections. After media has been recorded, TikREC accepts that a room ended
only after three consecutive non-live responses spaced five seconds apart. A
room that is offline on the first resolve still fails immediately. `record`
takes a direct FLV URL and is source-agnostic.
`resolve` prints the current direct FLV URL for a live page.
`finalize` stitches retained `part-*.flv` files after an interrupted or
otherwise stopped recording. It preserves those parts and refuses to overwrite
an existing output file. `validate` inspects an output file, parts directory,
or session without changing it.

`recover` begins with read-only guided interrupted-session recovery.
Give it one `*.parts` directory, or a recording root whose immediate children
are `*.parts` directories. It does not recurse or search the whole disk. TikREC
reports stored session/source identity, intended output, retained-part count,
lifecycle/finalization state, evidence consistency, and the safest next action.
Plain discovery never finalizes, resumes, repairs, renames, deletes, or updates
inspected artifacts. Active, changing, partial, malformed, or conflicting
evidence is left untouched. `--json` provides the same facts for tools. Creator
usernames are not stored in the session manifest, so TikREC reports the source
type and canonical room ID when available instead of guessing from filenames.

Add `--validate` to run TikREC's existing standard session/parts validator only
for completed or recoverable candidates whose stored evidence is consistent.
Active/uncertain or conflicting candidates are skipped before validation. The
report says whether validation ran, passed, failed, or was skipped, summarizes
up to five useful findings, and gives the safest next action. A failed or skipped
candidate makes the command exit nonzero for automation; an empty scope remains
a successful scan. `recover --validate` never changes a manifest, log, media,
output, or recovery artifact.

Add `--finalize` only when naming one specific session `*.parts` directory.
This explicit write-capable action implies standard validation, requires a safe
declared output path, rechecks that the session did not change during validation,
and then reuses TikREC's existing finalizer and manifest recovery states. It
refuses parent/root batch recovery, active or conflicting evidence, existing
outputs, encoder partials, symlinks, and missing output declarations. Success is
reported only after the non-empty output and complete session pass standard
validation. Failure or interruption preserves every retained FLV and records the
attempt safely. `--json` returns the same structured outcome. The lower-level
`tikrec finalize PARTS_DIRECTORY --output FILE` command remains supported for
manual recovery, including legacy sessions whose output cannot be inferred.
Recovery can safely assemble retained media; it cannot reconstruct bytes TikTok
never delivered.

Initial LIVE-page HTTP 404 remains a resolution failure. After TikREC has retained
media and a canonical room ID, reconnect resolution overlaps a direct public
status/transport refresh for that room with the public account identity lookup.
Fresh transport is accepted only when both identify the same saved live room;
insufficient or conflicting evidence uses the conservative full resolver. A page
404 therefore no longer discards established identity, while different-room,
three-check natural-end, and fail-closed behavior remain intact. A media-URL 404
likewise triggers bound identity re-resolution only for an established session;
no 404 response by itself means offline.

For `live`, the first Ctrl-C stops capture, clearly announces that finalization
has begun, finalizes retained parts, and exits 130 to show that recording ended
early. Matching parts are stream-copied; differing video configurations require
a re-encode that may take several minutes or longer. During encoding TikREC
reports output time instead of forwarding FFmpeg's complete diagnostic stream.
A second Ctrl-C during finalization stops FFmpeg; retained parts always remain
available.

`--raw-copy DIR` optionally saves the exact bytes received from every source
connection before FLV parsing, as `connection-0001.raw`,
`connection-0002.raw`, and so on. `connections.jsonl` identifies the raw file
for each connection. A matching `connection-NNNN.arrivals.jsonl` sidecar records
the local HTTP-read time and byte range for each returned chunk, and the
connection record names it in `raw_arrivals`. These timings diagnose where a
stall became visible to TikREC; buffering means they are not TCP/TLS packet
boundaries or exact network/server arrival times. Raw-copy and arrival-log errors
only emit warnings; recording continues. Raw copies roughly double the
recording's disk use, with additional small arrival-log overhead. See
[CONNECTION_LOG.md](CONNECTION_LOG.md) for the evidence contract and the read-only
`scripts/analyze_reconnect_gaps.py` diagnostic for retained reconnect baselines.

TikREC v0.6.0 adds that reconnect-gap analyzer and uses retained real evidence to
remove only the fixed one-second wait after a healthy media-bearing close. Three
pre-change ordinary reconnects measured 1.004--1.008 seconds of local/backoff;
the retained post-change reconnect measured 1.920 seconds total with 0.010 seconds
of local/backoff. Failure/outage backoff, patient recovery, room-end confirmation,
and fresh resolution/writer safety are unchanged. Later paired live evidence
showed the serial page/account discovery dominated resolution, so established
reconnects now overlap saved-room refresh with account verification while initial
resolution and all retry/media policies stay unchanged. Read-only live benchmarks
prove the optimized same-room branch, and two natural deployed network recoveries
subsequently reopened media through the same established resolver without an
identity, room-end, media-open, or output regression. No post-change `ordinary`
sample was captured; that narrower timing sample is useful but not a correctness
prerequisite.

An open media connection that delivers no bytes for 30 seconds is treated as a
stall. Live capture records a `stalled` connection outcome and reconnects under
the same bounded transient-failure policy used for other connection errors.

## Requirements

- Python 3.11+
- ffmpeg and ffprobe on PATH

Install with `pip install -e .`

## Configuration and local output paths

TikREC stores optional per-user configuration at
`%APPDATA%\TikREC\config.json` on Windows and
`${XDG_CONFIG_HOME:-~/.config}/TikREC/config.json` on POSIX. Use `tikrec config
path` to print the exact location, `tikrec config show [--json]` to inspect it,
and `tikrec config set/unset output-directory` to change the current recording-
directory default. `tikrec config set recovery-window-seconds SECONDS` persists
the LIVE network-recovery window; `unset` restores the built-in 900-second
default. Values must be integers from 60 through 3600 seconds. `tikrec config
set validation-mode standard|deep` persists the default for the explicit
`tikrec validate` command; `unset` restores built-in standard mode. Persisting
`standard` explicitly remains visible in `config show`. Relative directories
passed to `config set` are converted to absolute paths, and the recording
directory itself is created only when a recording first uses it.

`tikrec config set debug-tracebacks true|false` persists whether unexpected CLI
errors include Python tracebacks; `unset` restores the compatible built-in
`false`. Explicit `--debug` or `--no-debug` wins over configuration. TikREC reads
this preference only after an unexpected exception when neither flag was given,
so successful commands, help/version, and known operational errors do not start
depending on configuration merely for diagnostics. This does not change normal
progress, warning, validation, service, or remote output.

`tikrec monitor add CREATOR`, `remove`, and `list` manage an ordered opt-in list
of public TikTok creator handles in the same configuration file. `CREATOR` may
be a bare handle, `@handle`, or a standard
`https://www.tiktok.com/@handle/live` URL; TikREC normalizes it locally to a
lowercase handle and never stores the supplied URL. Duplicate additions and
absent removals fail clearly. Listing an absent configuration reports no
creators, and adding a creator does not require `output_directory`.

These configuration commands do not contact TikTok or start recording. The
persistent service snapshots the ordered list, `output_directory`, and the
automatic minimum free-space reserve (1–1024 GiB, default 10) at startup,
polls each creator in that order immediately and then 30 seconds after each
completed cycle, and keeps sanitized observations in memory. Restart the service
after configuration changes. Observation order is not scheduling priority, and
simultaneous ready LIVEs use a canonical-handle lexical tie-break. Automatic
starts require configured output storage; merely managing the list still does
not contact TikTok or record anything.

The file is strict schema-versioned JSON. Malformed JSON, unsupported versions,
wrong types, duplicate fields, and unknown top-level settings fail clearly
instead of silently changing behavior. It is not a secrets store: do not place
TikTok cookies, credentials, bearer tokens, or signed URLs in it. Operators and
tests can select one explicit file by placing `--config FILE` before the
subcommand.

`--output` is optional only for local `live`; advanced local `record`, remote
start, and manual finalize still require it. Local explicit outputs retain this
precedence:

1. An absolute `--output` is authoritative and does not read or use the
   configured output directory. Local `live` may independently read the recovery
   setting unless its CLI override is supplied.
2. A relative `--output` is placed beneath configured `output_directory`.
3. Without that setting, a relative `--output` keeps the original
   current-working-directory behavior.

When local `live` omits `--output`, a configured `output_directory` is required.
TikREC extracts only the public creator handle from the supplied standard TikTok
LIVE URL—without a network request—and creates
`creator-YYYYMMDD-HHMMSS.mp4` using local system time to one-second precision.
The leading `@` is removed and unsafe filename characters are replaced. If the
output or matching `creator-YYYYMMDD-HHMMSS.parts` directory already exists,
TikREC tries deterministic `-2`, `-3`, and later suffixes through `-1000`, then
fails rather than reusing data. Generated paths are always direct children of
the configured directory. A nonstandard URL without a safe creator identity
fails clearly.

Explicit `--output` always wins and is never automatically renamed. Paths that
escape a configured directory with `..` are rejected. Configuration does not
reinterpret remote PC paths, manual `finalize --output`, guided recovery paths,
service state, or retained sessions. There is no filename-template setting yet;
the intended v0.8 configuration/default set is otherwise complete. This convenience
names only manually started LIVEs and does not provide creator automation.

Local `live` and `serve` use the recovery window in this order: an explicit
`--recovery-window-seconds`, the configured value, then the built-in 900 seconds.
The command-line override does not read configuration merely to resolve this
setting, though relative/automatic output naming can independently require the
same file. A running service reads the value only at startup, so restart it after
changing configuration. The selected policy applies to active LIVE reconnects
and startup recovery. Its staged 1, 2, 5, 10, 10, then 30-second waits and
30-second cap are unchanged. `record` and remote start have no recovery-window
option; the remote HTTP request schema is unchanged.

Prefer a dedicated recording directory outside a source checkout. While
developing TikREC, `runs/` is the repository's ignored local recording directory:

    mkdir -p runs
    tikrec live <tiktok-live-page-url> --output runs/recording.mp4

## Remote recording on an always-on PC

The intended setup is Mac -> Tailscale -> main-pc -> TikREC service -> recording
files on main-pc. Run `tikrec serve` independently through Windows Task Scheduler
so capture continues when SSH/VS Code closes, the Mac lid shuts, or the Mac loses
network access. Launching `serve` directly inside SSH still ties the service to
that shell; Task Scheduler owns the persistent process.

The default is `127.0.0.1:8765`. Remote binding requires an explicit IP and a
bearer secret from `--token-file FILE` or `TIKREC_TOKEN`. A token file overrides
the environment. Use the same secret on the Mac. No virtualenv activation is
needed when invoking the installed executable by absolute path:

```powershell
C:\Users\Leandro\dev\TikREC\.venv\Scripts\tikrec.exe serve --host 100.x.y.z --token-file C:\Users\Leandro\TikREC-secrets\token.txt
```

On the Mac (replace the address and username):

```sh
tikrec remote health --server http://main-pc:8765 --token-file ~/.config/tikrec/token.txt
tikrec remote monitor-status --server http://main-pc:8765 --token-file ~/.config/tikrec/token.txt
tikrec remote start --server http://main-pc:8765 https://www.tiktok.com/@username/live --output 'C:\Users\Leandro\Videos\name.mp4' --token-file ~/.config/tikrec/token.txt
tikrec remote status --server http://main-pc:8765 --token-file ~/.config/tikrec/token.txt
tikrec remote recordings --server http://main-pc:8765 --token-file ~/.config/tikrec/token.txt
tikrec remote stop --server http://main-pc:8765 --token-file ~/.config/tikrec/token.txt
tikrec remote stop --server http://main-pc:8765 --session-id UUID --token-file ~/.config/tikrec/token.txt
```

`remote monitor-status` reports each configured handle as `pending`, `live`,
`offline`, or `unknown`, plus cycle timing. Only an explicit resolver offline
result becomes `offline`; network, access, malformed-data, missing-identity, and
unexpected failures remain `unknown` with fixed categories. A LIVE result may
include its public room ID. Signed media URLs and arbitrary remote error text are
discarded and never enter status. Observations reset to pending on service restart.

Each observation also has a current admission result. Non-LIVE creators are
`not_applicable`. A LIVE is `skipped/recording_slot_unavailable` when neither of
the two service slots can safely accept work because of recording, recovery,
finalization, blocked state, or shutdown. It is
`blocked` when output storage is unconfigured or unavailable, free space is below
the configured unattended reserve (10 GiB by default), or the bounded name search is exhausted;
otherwise it is `ready`. Ready status exposes only the local candidate MP4 and
matching `.parts` paths, observed free bytes, and the current threshold. Admission
uses the nearest existing parent for a not-yet-created output directory and never
creates or reserves anything. It is recalculated on each status request and does
not affect manual starts, recovery, or the existing recording pipeline.

After each complete monitoring cycle, the service may start up to the number of
currently available slots, with a built-in cap of two. Armed/ready creators are
attempted sequentially in canonical-handle lexical order. Admission, the 10 GiB
floor, and collision-safe naming are rechecked before every start; capacity-
exhausted creators remain eligible for a later cycle. An already-owned LIVE is
suppressed without consuming a new room claim, and selection continues to the
next eligible creator. Other synchronous failures conservatively end the cycle.
A fresh resolution must prove the exact room ID observed by the monitor before
the session directory or
media source opens. Manual HTTP starts remain authoritative and unbound.

An accepted automatic start consumes that creator/room until monitoring proves
the creator offline or observes a different room ID. Unknown observations do not
re-arm it, so a failed, completed, or manually stopped automatic job cannot loop
back into the same LIVE every polling cycle. This suppression and the narrow
pending-start crash window are stored atomically in a separate strict service
state file beside `job.json`. Corrupt or ambiguous automation state disables only
automatic starts; monitoring and safe manual controls remain available.

Monitoring status adds fixed automation fields for operational/block state,
armed or same-room-suppressed creators, ordered `selected_creators`, and one
entry in `started_recordings` per accepted output/session. Compatibility singular
fields are populated only when exactly one selection/start is the whole result.
Signed transport, credentials, response bodies, and arbitrary exception text
never enter automation state or status.

For an owner-authorized diagnostic recording, add `--raw-copy` to `remote start`.
The service then places `connection-NNNN.raw` and matching
`connection-NNNN.arrivals.jsonl` files directly in the recording's matching
`<stem>.parts` directory, beside `connections.jsonl`, `session.json`, and the
retained FLVs. The opt-in survives safe service recovery; ordinary remote starts
remain disabled by default and do not pay the roughly doubled storage cost.

Up to two service recordings may be active; local standalone `live` and `record`
remain single invocations. `remote recordings` reports capacity and both stable
slots. `remote recordings` shows only the latest job in each slot; historical
session evidence remains in that recording's parts directory. Legacy
`remote status` and empty `remote stop` remain useful with zero or one current
recording, but fail clearly when multiple current recordings make a singular
answer ambiguous; use `remote stop --session-id UUID` then. Stop closes/retains
only that session's active FLV part, finalizes its output, and writes its
own `session.json`.
It never sends a kill signal to FFmpeg. A stopped job reports `completed` with
`interrupted: true`; `final_output_path` identifies an actual finalized output.
Capture/finalizer failure preserves retained parts for `tikrec finalize`.

See [SERVICE.md](SERVICE.md) for the API contract, secret handling, Windows Task
Scheduler settings, startup recovery, and deployment verification. There is no
Web UI or media-download endpoint in the current service. TikREC v0.5.0 provides
the environment-survival and resumability foundation documented below, v0.6.0
adds the bounded reconnect-gap work described above, v0.7.0 adds the guided
recovery commands, the v0.8.0 release adds the per-user configuration/default
behavior documented above, and the v0.9.0 release adds opt-in creator
monitoring and single-slot automatic recording. The v0.10.0 release
adds bounded two-recording service ownership, independent durable slots and
targeted stop, aggregate status, capacity-aware automation, and fail-closed
LIVE/path arbitration. It also includes bounded crash-part recovery and truthful
retained-input decode health. Tag and GitHub Release records are maintained in
[PROJECT_STATE.md](PROJECT_STATE.md).

The service persists each slot's latest explicitly started job. After an unexpected
process death and Task Scheduler restart, it checks each job against retained
parts/session evidence before accepting new recordings. Automatic resume applies
only to the explicitly-started prior LIVE, proven by the same canonical room ID.
It preserves the job/session ID and old FLV files, increments resume_count, and
starts a fresh connection and the next numbered part. Normal reconnects continue;
a later different room is never connected by a resumed recording.

Confirmed offline or a different LIVE ends the prior session and safely finalizes
its retained parts when output is missing. A prior stop request or finalizing job
skips TikTok resolution and retries only safe finalization. Completed jobs do not
restart; an idle maintenance restart stays idle. This never means monitor this
username and record the next LIVE.

During an established LIVE or startup reconciliation, temporary DNS/internet,
timeout, connection-reset, and HTTP 408/425/429/5xx failures enter patient recovery.
Waits are 1, 2, 5, 10, 10, then 30 seconds, capped at 30 seconds, for up to 15
minutes from the first transient failure. Retry-After can increase a wait to that
cap. Status reports `state=recovering_network`, `recovery_state=recovery_wait`,
attempt/countdown/elapsed fields; health/status stay readable and starts return
409. Stop or service shutdown wakes retry waits and finalizes retained media.
Same-room recovery continues into fresh parts; offline/different-room evidence
ends the prior LIVE. A healthy media-bearing EOF re-resolves immediately; patient
failure waits and offline confirmation retain their existing timing.

Exhaustion reports `failed`, `recovery_reason=outage_timeout`, retains all parts,
and leaves output unfinalized because room end is unproven. The service permits a
new explicit job; restart never relaunches an exhausted job. A crash during an
unfinished outage preserves non-terminal intent and starts a fresh recovery window
on reconciliation. Malformed identity/storage also blocks starts with a fixed safe error.
A nonempty FFmpeg partial is automatically preserved under a collision-safe
session evidence name and all retained parts are re-finalized only when durable
job and manifest state prove finalization was running. Unproven, empty,
nonregular, colliding, or output-coexisting partials need manual assessment.
Existing output is preserved and accepted only with matching committed completion
and bounded media evidence; ambiguous output is never replaced. Real abrupt-
restart, temporary-outage, graceful-stop/finalization, retained-session, and deep-
output deployment validation have passed on preserved evidence.

A hard service stop can leave the active writer file named
`.part-NNNN.flv.partial`. Startup recovery accepts only the canonical next part
proven by matching durable recording intent, manifest identity/lifecycle, paths,
counts, artifact inventory, output absence, FLV structure, and decoder/DTS checks.
It preserves the exact original under a session/index evidence name, separately
copies either the complete file or its last parser-proven complete-tag prefix,
then resumes with a fresh connection and next part. Every unowned, conflicting,
malformed, empty, colliding, or nonregular partial remains untouched and blocks.
Issue #14's repeat real deployment validation passed; operators must not rename,
truncate, or delete crash evidence.

State lives at %LOCALAPPDATA%\TikREC\job.json on Windows and
${XDG_STATE_HOME:-~/.local/state}/TikREC/job.json elsewhere, independent of the
working directory. Use the same task account and one service instance. Existing
v0.4 recordings with no durable job are not inferred from directories or usernames.
Internal generic resume APIs remain available; no resume CLI/remote endpoint is added.

## How it works

The stream is written as numbered FLV parts intended to be independently
decodable. A known unresolved exception is a source timestamp replay: retained
replay intervals can contain malformed H.264 that fails decoding even in a
freshly initialized decoder. TikREC preserves that evidence and warns that the
affected part may not validate. A new part starts when the video codec
configuration changes or when a dropped connection is re-established. Parts
are then stitched into a single MP4 — losslessly when the configurations match,
re-encoded when they don't.

Each live recording, and each direct recording using `--raw-copy`, writes
`connections.jsonl` alongside the parts. Connection records contain wall-clock
timings, the preceding gap, per-part timestamp diagnostics, and the optional
raw-copy and raw-arrival filenames. Live recordings also contain `room_status` event records
during end confirmation. Each event has a timestamp, the raw TikTok room-status
value, and whether that response reached the confirmation threshold. A live
response that cancels confirmation is recorded too. Coalesced `network_recovery`
boundaries summarize outage entry and outcome without logging every retry wait.

Every recording session also writes `session.json` alongside the parts. It is
an atomically updated, high-level summary of the session lifecycle, result,
paths, part and connection counts, interruption/finalization state, and optional
codec and resolution information. It complements the lower-level
`connections.jsonl`; see [SESSION_MANIFEST.md](SESSION_MANIFEST.md) for the
schema and lifecycle.
Successful mixed-configuration finalization also records bounded input-decoder
health in `finalization.input_decode`. Decoder warnings can mark that health
`degraded` while capture and finalization remain `completed`. Stream copy is
`not_checked`; an injected finalizer without diagnostics is `unknown`.

## Validating a recording

    tikrec validate path/to/recording.mp4
    tikrec validate path/to/recording.mp4 --deep
    tikrec validate path/to/recording.mp4 --standard
    tikrec validate path/to/recording.parts
    tikrec validate path/to/recording.parts/session.json --json

For retained parts, validation checks that each file is readable and non-empty,
contains recognizable video, decodes through FFprobe, and has valid stored
packet DTS. Missing, malformed, or duplicate DTS fails validation; a decreasing
DTS is a warning because it is known TikTok source behavior. Missing audio is
also a warning so a valid video-only source is not labeled corrupt.

For a completed output, validation checks readability, FFprobe inspection,
video and optional audio streams, container information, and a positive finite
duration. `--deep` additionally decodes the complete output and can take
significant time and CPU for a long recording. Retained parts always receive
the full decode check, with or without `--deep`. When `session.json` is present
validation also checks the actual part count, declared output, finalization
state, and available codec/resolution metadata. Older parts directories without
a manifest remain supported.

The standalone command selects its mode in this order: explicit `--deep` or
`--standard`, configured `validation_mode`, then the built-in `standard`.
Supplying either flag avoids reading configuration merely to choose the mode;
without a flag, malformed configuration fails clearly. `recover --validate`
and the pre/post checks used by `recover --finalize` intentionally remain fixed
to standard mode because they are recovery safety checks, not a convenience
preference. TikREC does not automatically validate after recording.

An interrupted, failed, or still-recording session is not corrupt merely
because it is incomplete or has no final MP4. Human and JSON reports distinguish
retained-part media checks, recorded finalization input-decoder health, final
output inspection, and deep output decode. Each can be `not_checked` when its
evidence is unavailable or that check was not run. Visual integrity is always
`not_checked`: a decodable re-encoded MP4 can still contain damaged source
pictures. Session completeness and output availability remain separate, and a
clean output never overrides retained-part errors. The legacy `media_integrity`
JSON field is the aggregate checked-media result for compatibility. Validation
is read-only: it never finalizes, repairs, renames, deletes, or rewrites media or
session metadata. It is a structural health check, not exhaustive media
forensics.

Exit 0 means validation passed, exit 1 means one or more checks failed, and
invalid command usage keeps argparse's exit 2. `--json` emits the same result
with stable finding levels and codes. The legacy
`scripts/validate_parts.py` command remains as a compatibility wrapper over the
same validator.

Note that `ffmpeg -f null -` is *not* a valid check here — see the
validation notes in SPEC.md for why.

## Scope

**Current checkout:** Local standalone commands record one public LIVE per
invocation. The persistent service owns a fixed pool of two independent jobs,
each with its own worker, stop event, durable intent, recovery, retained media,
finalization, and result. Creator automation can fill both slots while retaining
the configurable per-start reserve (10 GiB by default), room binding, collision-safe naming, and durable
same-room suppression. It does not authenticate to TikTok, notify the owner,
automatically delete media, or provide a library/Web UI/playback. Unreleased
v0.11 development adds a read-only age-retention plan and explicit creator
protection; it does not delete, move, or rename any artifact.

**Release state and future product:** v0.10.0 is the current published release.
Its reviewed release commit passed real simultaneous deployed validation,
offline verification, and package build/install checks.
Library/history/playback, a web interface, notifications, and retention execution remain
future work.

`tikrec retention protect CREATOR` keeps a canonical creator on an independent
protected list; removing monitoring does not remove this protection. Optional
`retention-max-age-days` accepts 1–3650 days and is disabled when unset.
`retention plan [ROOT]` reads only immediate `.parts` session children of the
selected directory (or configured output directory). It uses the durable
session end time, validates completed output and retained evidence, and reports
`eligible`, `retained`, `protected`, `ineligible`, or `needs_attention` with a
reason. Legacy sessions without a proven creator and uncertain evidence never
become eligible. This is an advisory plan only; automatic deletion does not exist.
The planner checks competing session/output claims even for rejected candidates,
whole-root stability, terminal chronology, output aliases, and proven local-only
storage. A saved plan is never permission
to delete; future cleanup would require fresh validation and separate approval.

**Permanent boundary:** TikREC will not bypass authentication, CAPTCHA,
entitlements, access controls, or private request signing, and will not support
covert surveillance or destructive handling of user recordings/evidence. A
separately designed future authenticated mode may use authorization explicitly
supplied by the user while respecting platform controls. See SPEC.md and
ROADMAP.md.

## Design

[SPEC.md](SPEC.md) — architecture, module responsibilities, validation
notes and the reasoning behind past fixes.
[ROADMAP.md](ROADMAP.md) — workflow-driven direction for future releases.
[SERVICE.md](SERVICE.md) — remote API and Windows Task Scheduler deployment.
[SESSION_MANIFEST.md](SESSION_MANIFEST.md) — `session.json` schema and lifecycle.
[PROJECT_STATE.md](PROJECT_STATE.md) — concise current development handoff.
[AGENTS.md](AGENTS.md) — working rules.
