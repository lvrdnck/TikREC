# TikREC session manifest

TikREC v0.2.0 and later write `session.json` in each new parts directory. It is
the high-level summary of one recording attempt. The existing
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

Each update is written to `.session.json.partial`, flushed, and atomically
replaced over `session.json`. A failed update therefore leaves the preceding
complete JSON document in place. A hard process or machine stop can still leave
the last manifest status as `recording`; retained parts remain the source of
truth for future v0.4 recovery tooling.

## Schema version 1

Timestamps are Unix timestamps in seconds. Durations are numeric seconds. Paths
are strings in the same absolute or relative form supplied to TikREC.

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | Manifest schema version; currently `1`. |
| `session_id` | string | Random UUID identifying the session independently of its path. |
| `tikrec_version` | string | TikREC version that created the session. |
| `source_type` | string | `tiktok_live`, `direct_flv`, or `tag_stream`. |
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
| `recovery_performed` | boolean | Whether `tikrec finalize` attempted manual recovery. |
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

## Validation

`tikrec validate` accepts either `session.json` or its containing directory. It
checks the manifest's part count, output declaration and availability,
finalization state, and non-null codec/resolution facts against the files and
FFprobe results. Null optional media fields do not fail validation.

Validation never updates `session.json`. Its report separates media integrity,
session completeness, and final-output availability, so an interrupted, failed,
or still-recording session can have healthy retained parts without being
misreported as corrupt. Persisting health history or recovering an incomplete
session is outside v0.3.0.
