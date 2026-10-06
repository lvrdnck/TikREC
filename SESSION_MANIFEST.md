# TikREC session manifest

## Current guarded-publication contract — 2026-10-06

[PM decision 6010639470](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6010639470)
accepts `1e1e1cae` candidate validation, preserving accepted R1–R10/assembly.
The [publication contract/evidence](ISSUE_52_GUARDED_PUBLICATION.md) connects the
original one-shot coordinator and continuously protected candidate to its exact
claimed MP4 destination. Original acquisition narrowly adds candidate DELETE
rights; only publication-capable validation uses read-only inherited seekable
stdin. Assembly-only/validation-only defaults and arbitrary-launch refusal remain.
Schema **7** appends immutable preparation and separate observed-result evidence;
schemas **1–6 are refused/preserved unchanged**, no migration/cutover. Preparation
is not completion; native root-relative no-replace rename has no reopen/replay.
The exact local scratch-to-output successor retains all ownership. Original
assembly/candidate/validation evidence, pending manifests, accounting/claims/pins
and synchronous CLI/service defaults remain. No settlement/refund, retry/adoption,
service/production integration or release. #52 OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED;
#28 unresolved. Earlier checkpoints below are historical within their limits.

TikREC v0.2.0 and later write `session.json` in each new parts directory. It is
the high-level summary of one logical recording session, including explicit
continuation attempts. The existing
`connections.jsonl` remains the detailed event and connection log; neither file
replaces the other.


## Historical accepted issue #52 internal candidate-validation checkpoint (2026-10-05)

[PM decision 6000035417](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6000035417) accepts `ee884bdc` connected assembly. The new
[validation contract/evidence](ISSUE_52_CANDIDATE_VALIDATION.md) retains original same-attempt scratch/native/input ownership through
three fixed contained media validators and an append-only validation receipt.
The immutable candidate stays `not_checked / unpublished`; separate validation
does not publish, settle/refund, release units/raw/room/path claims or pins, or
authorize retry/adoption. Current isolated journal schema is **6**; schemas 1–5
remain refused/preserved without migration. Media manifest/connection schemas
remain 1, including intentional `finalization: pending`. Applicable candidate
inspection/decode/DTS checks do not use pending publication as a failure reason.
CLI/service behavior remains synchronous and unchanged. No service/API/monitor/
scheduler integration, production access/change/restart or cutover is included.
Full service gates remain outstanding; PM review is next.

## Historical isolated capture handoff boundary (2026-10-04)

[Review 5971119601](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5971119601)
accepted `a96bd6e9` and R1–R3, then approved capture-side integration only.
The [isolated bridge](ISSUE_52_CAPTURE_HANDOFF.md) now reuses real LIVE/writer/raw/
manifest/connection code, verifies native Windows closure and durably transfers
responsibility before journal-backed capture reuse. The finalizer stays unstarted.
Journal schema **3** adds pinned/counted admitted-empty evidence; schemas 1 and 2
are refused/preserved without migration. Media manifest/connection schemas remain 1.

Internal source-ended results preserve requested output and `finalization: pending`;
they never claim MP4 completion. Immutable pending markers bind H to the known
catalog/session/generation/operation/seal. Failed or ambiguous closure remains held.
Production CLI/service defaults and current slot lifecycle remain synchronous;
no production journal, marker, worker, API, cutover or retention change is included.
#52 stays OPEN/SINGLE ACTIVE, #48 OPEN/PAUSED and #28 unresolved. Full service
[A1–A20 gates](ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md) remain outstanding.

## Lifecycle

The isolated #52 capture-only path ends the capture timeline using the existing
completed/interrupted capture status, while keeping requested output identity and
finalization status `pending`. A completed capture status alone is never proof of
an MP4. `finalization-owner.json` is separate version-1 control intent, not a media
manifest field or independent queue authority. Its receipt must match journal H.
Proved admitted-empty capture keeps its sealed controls and claims in the journal;
discarded source tags, raw uncertainty, failed closure and recovery partials stay held.

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
- Manual finalization records its own completed recovery and output media facts;
  it does not rewrite a historically failed or interrupted capture into a
  successful capture. Validators therefore continue to expose both the recovered
  output and the original lifecycle/media evidence.
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
| `creator` | optional string | Canonical lowercase public LIVE page handle for new TikTok sessions; absent for legacy and generic sessions. |
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
| `recovery_performed` | boolean | Whether writer salvage, manual finalize, or explicit resume performed recovery. |
| `writer_recoveries` | array, optional | Fixed evidence for service-recovered active writer parts. |
| `finalization` | object | Finalization `status`, optional `error`, and optional `input_decode`. |
| `media` | object | Optional final-output codec and resolution facts. |
| `error` | string or null | Redacted reason for an abnormal session result. |

New LIVE sessions derive `creator` from the accepted public page before the
first manifest write. It is preserved through reconnect, resume, recovery, and
finalization. Existing schema-1 manifests without it remain valid and are never
rewritten merely to fill this field. When a service job and manifest both exist,
recovery rejects a mismatch between the job page and stored creator.
Fresh LIVE resume repeats that optional creator check after reloading storage
and before writing a resume boundary. Legacy creator absence stays valid and
is not inferred. Unreleased v0.11 retention planning applies stricter terminal
proof than ordinary schema-1 loading: completed capture/finalization fields,
finite coherent elapsed time, and durable event/recovery chronology must agree.
This does not change the manifest schema or historical recovery compatibility.
Startup reconciliation also repeats the optional creator/page check immediately
after its own fresh resume preflight, before appending recovery evidence,
resolving the room, or saving new job state. Read-only retention requires a
stable whole-root claim snapshot and stricter event chronology; no manifest
field is added for that advisory proof.
Writer-partial recovery likewise adds no schema field: its existing recovery
record is promoted only while the inspected manifest bytes and durable job
remain current, with source/prefix checks before the guarded write.

`finalization.status` is one of `not_requested`, `pending`, `not_started`,
`running`, `completed`, `interrupted`, or `failed`. The pending/running values
are useful evidence when a process stops before its next atomic update.

`finalization.input_decode`, when present after successful finalization, is a
fixed object with `status` (`clean`, `degraded`, `not_checked`, or `unknown`),
`diagnostic_count` (0–10,000), sorted allowlisted `diagnostic_codes`, and
`count_capped` (boolean). Mixed-configuration re-encoding decodes the inputs:
recognized H.264 errors yield `degraded` while completion remains `completed`;
no recognized errors yield `clean`. Stream copy does not decode input and uses
`not_checked`. A custom finalizer without diagnostic evidence uses `unknown`.
This optional schema-1 field contains no stderr text, URL, address, or secret.
Older schema-1 manifests without it remain valid and their evidence is unknown.

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

## Service intent boundary (v0.5.0)

**Proposed #52 service ownership correction, not integrated:** The isolated
internal journal stores capture/stop/raw intent and queued tasks across slot reuse,
but production is not wired to it; its handoff does not replace this manifest's media evidence.
Current job/manifest schemas and synchronous lifecycle below remain unchanged.
The review design specifies closed-part/control binding, a session ownership
marker, separate capture-end/status facts, idempotent publication/restart and
retention pins without retroactively changing historical timing or inventing raw
evidence. See
[ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md](ISSUE_52_CAPTURE_FINALIZATION_DESIGN.md).

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
Already completed/finalizing sessions and arbitrary partial artifacts are refused.
Service startup alone may recover the canonical next `.part-NNNN.flv.partial`
when the durable recording job, this manifest, retained files, connection counts,
room/paths, and absent output prove ownership. Generic explicit resume remains strict.
Capture-only continuation retains the output declaration but records
not_requested finalization; an explicit finalization path must match the prior
declaration unless it was null. Completion/interruption then covers all old and
new parts and elapsed wall time from the original start, including downtime.

## Service startup recovery (v0.5.0)

New structured LIVE captures retain their first canonical room_id in schema 1.
Startup checks compare it with the explicit durable job; both must agree before
capture resume. Older manifests missing identity still validate and manually
finalize, but cannot prove automatic capture eligibility. Paths/UUID/counts and
connection evidence must also pass strict continuation checks.

Same LIVE resume preserves original metadata, uses begin_resume to reopen capture
and append capture_resume, and allocates the next connection and fresh numbered
part. Service resume_count belongs only to the job. Manifest counts include prior
attempts; elapsed wall time includes downtime without claiming missing media.

An eligible active writer partial is first validated read-only through its last
complete FLV tag. A fresh writer-compatible read-only ownership check proves
the current job, manifest, optional creator, room, paths, and exact partial
before any `recovering` job-state write or media mutation. Durable job state
records `writer_partial_recovery` before the
original is atomically moved to a session/index evidence-only name. TikREC copies
the complete file, or only the parser-proven prefix before the first truncated
or malformed tag, into a separate staging file. It does not resynchronize or
repair the bad tag; normal writer structure and FFprobe decoder/DTS checks must
pass before atomic part publication. The original evidence never changes.
Optional `writer_recoveries` entries record timestamp, bare evidence/part
names, source SHA-256, source/recovered bytes, and discarded trailing bytes.
The unchanged manifest ownership fingerprint and recovered source/prefix are
rechecked immediately before recording that evidence. One coherent proof hashes
the complete source while comparing its exact recovered prefix from the same
source read; matching short reads or EOF are not proof. Path and opened-handle
identity must agree on comparable fields. Windows ctime is excluded only from
that cross-API comparison; each path and handle's full metadata, including ctime,
must stay stable during the proof. Regular/reparse protection and all other
identity checks remain enforced. Counts include only
published parts; the next resume boundary creates a fresh connection and next
part, while wall elapsed time may include downtime without claiming media coverage.
Missing/mutated evidence, duplicate indexes, collisions, incompatible lifecycle,
malformed media, symlinks/nonregular files, or any ownership conflict block.

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
Schema version remains 1; `writer_recoveries` is optional, validated evidence.
Successfully completed jobs are never relaunched. Writer-partial and finalization
reconciliation are implemented. Repeat real process-restart/outage deployment
validation passed, as did final graceful-stop/finalization and deep-output
validation. The current released package version is 0.10.0; the manifest schema
remains 1.

## Guided recovery (v0.7.0)

`tikrec recover ROOT` inspects either one explicit parts directory or only the
immediate `*.parts` children of an explicit recording root. It never recursively
searches a drive. Discovery reuses the supported manifest schema, strict retained-
part framing/numbering, connection evidence, output declaration, and completed-
output media facts. It reports plain-language lifecycle/finalization state and
whether a later recovery action can be suggested safely.

Discovery does not update this manifest or any media/recovery artifact. A
`recording` or `running` state may still be active and is left untouched. Missing,
malformed, duplicate, changing, partial, symlinked, or conflicting evidence also
fails closed. Legacy parts without `session.json` remain manually finalizable,
but discovery cannot infer their session identity or intended output safely.
Plain discovery does not start FFprobe. `tikrec recover ROOT --validate` runs the
existing standard `tikrec validate` session/parts path only for terminal
recoverable or completed candidates whose discovery evidence is consistent.
Validation results are not persisted. Active/uncertain and conflicting candidates
are skipped, and validator failures fail closed. Discovery and `--validate` do
not finalize, repair, resume, overwrite, or update anything.

`tikrec recover PARTS_DIRECTORY --finalize` is the explicit write-capable guided
action. It implies standard validation, accepts exactly one session directory,
requires a safe stored output declaration, and compares a pre-validation evidence
snapshot with freshly discovered state before writing. It then uses the existing
schema-1 recovery fields: `mark_recovery` sets `recovery_performed=true`, updates
the retained part count and declared output, and records finalization `running`;
`finish_recovery` records `completed`, `failed`, or `interrupted`, a safe failure
reason where supported, output media facts when available, and the retained part
count. The historical capture lifecycle/timestamps remain unchanged.

A successful attempt must produce a regular non-empty output and pass standard
session validation after the completed manifest update. Failed or interrupted
attempts keep all retained parts. Ambiguous evidence, active work, output/partial
conflicts, symlinks, a missing output declaration, or evidence that changes during
validation is refused before mutation. Manual `tikrec finalize PARTS_DIRECTORY
--output FILE` remains available and continues to support legacy or explicitly
chosen output paths.

## Validation

`tikrec validate` accepts either `session.json` or its containing directory. It
checks the manifest's part count, output declaration and availability,
finalization state, and non-null codec/resolution facts against the files and
FFprobe results. Null optional media fields do not fail validation. With
`--deep`, it also fully decodes an existing completed output after validating
the retained parts.

Validation never updates `session.json`. Its report distinguishes retained
input media checks, recorded finalization input decoding, final-output inspection,
optional deep output decoding, and unproven visual integrity. It also separates
session completeness and final-output availability, so an interrupted, failed,
or still-recording session can have healthy retained parts without being
misreported as corrupt. Persisting health history or recovering an incomplete
session is outside v0.3.0.
