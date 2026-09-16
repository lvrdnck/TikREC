# TikREC session manifest

TikREC v0.2.0 and later write `session.json` in each new parts directory. It is
the high-level summary of one logical recording session, including explicit
continuation attempts. The existing
`connections.jsonl` remains the detailed event and connection log; neither file
replaces the other.

## Lifecycle

- Direct-FLV and supplied-tag captures initialize the manifest after creating
  the session directory and before consuming media.
- A TikTok LIVE capture initializes it only after the first successful room
  resolution. An initially offline or unresolved room therefore still creates
  no session directory.
- Live capture updates part, connection, and reconnect counts whenever an
  attempt closes. The manifest is finalized on a handled success, failure, or
  interruption and again after finalization determines its result.
- `tikrec finalize` updates a v0.2 manifest when one is present and marks that a
  manual recovery was attempted. Older parts directories without a manifest
  continue to finalize normally.
- Explicit internal resume preserves the session UUID, source type, original
  started_at and stored facts, reopens recording lifecycle, updates counts, and
  sets recovery_performed. Its capture_resume event preserves the prior result
  as evidence before source consumption. No resume_count field is added here;
  the durable service job now owns that counter.

Each update is written to `.session.json.partial`, flushed, and atomically
replaced over `session.json`. A failed update therefore leaves the preceding
complete JSON document in place. A hard process or machine stop can still leave
the last manifest status as `recording`; retained parts remain the source of
truth for v0.5 environment survival and v0.7 guided recovery tooling.

## Schema version 1

Timestamps are Unix timestamps in seconds. Durations are numeric seconds. Paths
are strings in the same absolute or relative form supplied to TikREC.

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | Manifest schema version; currently `1`. |
| `session_id` | string | Random UUID identifying the session independently of its path. |
| `tikrec_version` | string | TikREC version that created the session. |
| `source_type` | string | `tiktok_live`, `direct_flv`, or `tag_stream`. |
| `room_id` | optional string | Canonical public LIVE identity from structured resolution; absent for older/generic sessions. |
| `started_at` | number | Time the recording session was initialized. |
| `ended_at` | number or null | Time a handled capture/finalization path ended. |
| `elapsed_seconds` | number or null | `ended_at - started_at`; not media duration. |
| `status` | string | `recording`, `completed`, `interrupted`, or `failed`. |
| `parts_directory` | string | Directory containing the manifest and parts. |
| `output_path` | string or null | Requested or completed final output path. |
| `part_count` | integer | Number of retained completed FLV parts known. |
| `connection_count` | integer | Recorded source/resolution attempts for this session. |
| `reconnect_count` | integer | Attempts after the first; `max(connection_count - 1, 0)`. |
| `interrupted` | boolean | Whether capture or finalization was interrupted. |
| `recovery_performed` | boolean | Whether manual finalize or explicit capture resume attempted recovery. |
| `finalization` | object | Finalization `status` and optional `error`. |
| `media` | object | Optional final-output codec and resolution facts. |
| `error` | string or null | Redacted reason for an abnormal session result. |

`finalization.status` is one of `not_requested`, `pending`, `not_started`,
`running`, `completed`, `interrupted`, or `failed`. The pending/running values
are useful evidence when a process stops before its next atomic update.

`media` always contains `video_codec`, `audio_codec`, `width`, and `height`.
Each value is null unless FFprobe can reliably read it from a completed final
output. Failure to start FFprobe, invalid probe output, and missing media
streams do not fail the recording.

Signed CDN URLs are not stored. URLs found in failure text are replaced with
`[URL redacted]` before the error enters the manifest.

## Example

```json
{
  "connection_count": 3,
  "elapsed_seconds": 721.5,
  "ended_at": 1789135921.5,
  "error": null,
  "finalization": {
    "error": null,
    "status": "completed"
  },
  "interrupted": false,
  "media": {
    "audio_codec": "aac",
    "height": 1920,
    "video_codec": "h264",
    "width": 1080
  },
  "output_path": "/recordings/creator-20260911.mp4",
  "part_count": 2,
  "parts_directory": "/recordings/creator-20260911.parts",
  "reconnect_count": 2,
  "recovery_performed": false,
  "schema_version": 1,
  "session_id": "a738109c-a387-423f-a20b-969ecf656c4b",
  "source_type": "tiktok_live",
  "started_at": 1789135200.0,
  "status": "completed",
  "tikrec_version": "0.2.0"
}
```

The example's connection count includes the final room-status resolution
attempt recorded by live capture. `connections.jsonl` provides the detailed
outcome and timing for each numbered attempt.

## Service intent boundary (v0.5 implemented, release pending)

The new `job_state.py` storage module uses an independent job schema version 1
for explicit service intent before media storage exists. It does not change
`session.json` schema version 1 or replace its media/finalization evidence.
Public source/room identity and durable stop intent belong to that service
record; no signed CDN URL or service secret belongs in either file. Controller
persistence and service startup reconciliation are now integrated. Explicit capture resume uses existing lifecycle,
count, and recovery fields without expanding media schema 1. Existing v0.2/v0.3/
v0.4 manifests and their validation behavior are unchanged.

Structured public resolution now exposes a canonical positive decimal room_id;
it identifies the LIVE, whereas username identifies only its account. The job
record accepts canonical room-ID strings (or null) and cannot accept a
`LiveResolution` object as identity. Only its room_id may be saved; the signed
flv_url is ephemeral transport. Reconciliation refuses to claim the same
LIVE when room identity is missing, malformed, or conflicting. Media schema
version 1 accepts optional room_id without requiring it in legacy validation.

Explicit resume requires a valid supported manifest; legacy parts without one
remain finalizable but cannot continue capture. Recording manifests may lag
promoted part/connection counts; interrupted/failed manifests must match retained
parts and must not predate newer connection evidence. Path,
identity, timestamp, count, or connection-log conflicts fail without repair.
Already completed/finalizing sessions and partial artifacts are refused. This
currently includes the active writer `.part-NNNN.flv.partial` left by an abrupt
service death, even when it is structurally complete; issue #14 owns the required
evidence-preserving recovery policy.
Capture-only continuation retains the output declaration but records
not_requested finalization; an explicit finalization path must match the prior
declaration unless it was null. Completion/interruption then covers all old and
new parts and elapsed wall time from the original start, including downtime.

## Service startup recovery (v0.5 implemented, release pending)

New structured LIVE captures retain their first canonical room_id in schema 1.
Startup checks compare it with the explicit durable job; both must agree before
capture resume. Older manifests missing identity still validate and manually
finalize, but cannot prove automatic capture eligibility. Paths/UUID/counts and
connection evidence must also pass strict continuation checks.

Same LIVE resume preserves original metadata, uses begin_resume to reopen capture
and append capture_resume, and allocates the next connection and fresh numbered
part. Service resume_count belongs only to the job. Manifest counts include prior
attempts; elapsed wall time includes downtime without claiming missing media.

Offline/different-LIVE recovery and prior stop/finalizing recovery use the existing
finalizer only when output is absent. A nonempty FFmpeg temporary is eligible for
automatic recovery only when durable job state is `finalizing` and this manifest
records finalization `running`; it is atomically preserved under a collision-safe
session evidence name before every retained part is re-finalized. Empty,
nonregular, unproven, colliding, or output-coexisting partials remain untouched
and block. Recovery marks `recovery_performed`/`running` before FFmpeg and closes
the observed attempt as interrupted/completed-finalization on success, or failed
on encoder failure. End timestamps are observed reconciliation times, never
guessed crash or room-end times. Successful completion settles durable job intent.

Existing output needs matching committed finalization completion and bounded
matching media evidence. Ambiguous output/partials remain untouched. While patient
startup identity recovery waits, this manifest stays unchanged and durable intent
remains non-terminal (`recovering_network`/`network_outage` in service job state).
Active capture retains completed parts; repeated resolver-only failures coalesce
disk evidence and allocation counts are flushed when capture ends. Recovery waits
do not mark the room offline or start FFmpeg. After 15 minutes without useful
continuation or terminal room evidence, exhaustion uses existing `failed` status,
`finalization.status=not_started`, a fixed redacted failure reason, and an observed
end timestamp. Parts and any existing output remain untouched. Durable job state
is terminal `failed` with `outage_timeout`; it will not relaunch on restart.
Stop during recovery instead uses existing interrupted/finalization semantics.
No media-manifest fields or schema version change. Successfully completed jobs are
never relaunched. Finalization reconciliation is implemented; real same-room
resume and process-restart/outage deployment validation remain outstanding, and
version remains 0.4.0.

## Validation

`tikrec validate` accepts either `session.json` or its containing directory. It
checks the manifest's part count, output declaration and availability,
finalization state, and non-null codec/resolution facts against the files and
FFprobe results. Null optional media fields do not fail validation. With
`--deep`, it also fully decodes an existing completed output after validating
the retained parts.

Validation never updates `session.json`. Its report separates media integrity,
session completeness, and final-output availability, so an interrupted, failed,
or still-recording session can have healthy retained parts without being
misreported as corrupt. Persisting health history or recovering an incomplete
session is outside v0.3.0.
