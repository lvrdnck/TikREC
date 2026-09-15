# TikREC current state

Last reviewed: 2026-09-15. This is a short handoff record, not a replacement
for [ROADMAP.md](ROADMAP.md), [SPEC.md](SPEC.md), [SERVICE.md](SERVICE.md),
[SESSION_MANIFEST.md](SESSION_MANIFEST.md), or
[CONNECTION_LOG.md](CONNECTION_LOG.md).

## Release and target

- **Current released package:** v0.4.0.
- **Development target:** v0.5 environment survival/resumability. The release
  code is largely implemented, but real-world recovery verification and release
  documentation/version work remain before declaring v0.5 complete.

## Completed v0.5 work

- Durable service job intent, canonical public room identity, explicit retained
  session continuation, conservative startup reconciliation, and bounded patient
  network recovery are committed in `b6f190b` through `35d69fc`.
- `a384dd3` adds crash-during-FFmpeg finalization reconciliation: it preserves
  only a proven nonempty encoder partial under a collision-safe evidence name,
  then re-finalizes retained parts. Output/partial collisions and other ambiguous
  artifacts remain blocked without mutation.

See the v0.5 sections of ROADMAP.md and SERVICE.md for the exact lifecycle and
security constraints. The roadmap/docs still describe deeper finalization
reconciliation as pending; they need an intentional status update once the
completed `a384dd3` slice and its remaining verification boundary are agreed.

## Completed raw-arrival diagnostic slice

The previously preserved work is complete as a separate diagnostic change. It
is **not** v0.5 finalization reconciliation:

- `RawCopy` now writes a best-effort `connection-NNNN.arrivals.jsonl` beside an
  optional byte-exact raw copy. It records one paired wall/monotonic reference,
  per-chunk byte offset/count/monotonic elapsed time, and EOF/timeout/error at
  the HTTP read boundary.
- HTTP reads prefer `read1()` so already buffered bytes are preserved and timed
  before a later stall/disconnect. Direct and LIVE capture include the sidecar
  filename as `raw_arrivals` in the associated `connections.jsonl` record.
- Tests cover direct/LIVE propagation, raw-copy logging, partial-byte preservation,
  timeout/reset/EOF boundaries, diagnostic-failure isolation, the existing
  fallback behavior, and legacy positional `ConnectionRecord` compatibility.

This is diagnostic evidence work for the unresolved source-versus-writer replay
corruption investigation in SPEC.md, and it supports later reconnect-gap/
conditional redundant-capture investigation (issue #8 / v0.6.5). It does not
change finalization policy, session schema, or automatic-resume decisions.

The persistent contract is documented in CONNECTION_LOG.md and summarized in
SPEC.md and README.md. ROADMAP.md records it only as diagnostic groundwork; it
does not claim reconnect-gap reduction or simultaneous capture is implemented.

## Verification status

- Focused raw-arrival/capture/resume regression suite: 145 passed.
- Full offline suite: 703 passed using a unique repository-local pytest base
  temp. This safely bypassed the inaccessible shared Windows pytest temp root;
  the task-created directory was removed after the run.
- Real resumed-media, crash/reboot, and outage deployment validation remain
  outstanding; media correctness requirements remain in SPEC.md.
- A real opt-in raw-copy comparison also remains useful but does not block this
  instrumentation commit. On a suitable public LIVE, compare sidecar byte ranges
  with the `.raw` file and `connections.jsonl`; if a replay/stall occurs, align
  it with parser timestamp-replay evidence. Confirm diagnostics remain linked
  and recording continues. A normal run cannot prove the replay defect's cause.

## Exact next step

Do not begin another roadmap feature as part of this slice. The next separately
approved task should reassess v0.5 release closure from real recovery evidence
and current docs; the raw-copy comparison can be scheduled when a suitable LIVE
is available.

## Durable decisions and risks

- Public LIVE only; no authentication, private signing, future-LIVE monitoring,
  or user-data-destructive recovery.
- Automatic resume requires the same canonical room ID and valid retained
  evidence; ambiguous outputs/partials are preserved and blocked.
- Raw copies are best-effort and must never interrupt capture. Arrival timestamps
  describe local read/processing boundaries, not provable source-byte arrival.
- The diagnostic changes HTTP read behavior only when reading any HTTP source,
  while sidecar I/O occurs only with explicit raw copying. Offline regression
  coverage passes; real raw-copy comparison remains evidence, not a commit gate.
