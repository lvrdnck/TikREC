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

## Preserved uncommitted work

Ten files are modified (206 additions, 13 removals), plus a conditional v0.6.5
roadmap entry. The change is coherent and appears intentional, but is **not**
v0.5 finalization reconciliation:

- `RawCopy` now writes a best-effort `connection-NNNN.arrivals.jsonl` beside an
  optional byte-exact raw copy. It records one paired wall/monotonic reference,
  per-chunk byte offset/count/monotonic elapsed time, and EOF/timeout/error at
  the HTTP read boundary.
- HTTP reads prefer `read1()` so already buffered bytes are preserved and timed
  before a later stall/disconnect. Direct and LIVE capture include the sidecar
  filename as `raw_arrivals` in the associated `connections.jsonl` record.
- Tests cover direct/LIVE propagation, raw-copy logging, partial-byte preservation,
  timeout/reset boundaries, and the existing fallback behavior.

This is diagnostic evidence work for the unresolved source-versus-writer replay
corruption investigation in SPEC.md, and it supports later reconnect-gap/
conditional redundant-capture investigation (issue #8 / v0.6.5). It does not
change finalization policy, session schema, or automatic-resume decisions.

The work should remain a separate logical change from v0.5 release closure. Its
new persistent raw sidecar and `connections.jsonl` field are not yet described
in CONNECTION_LOG.md, SPEC.md, or README.md, so it is not documentation-complete.

## Verification status

- The last recorded full offline suite before this uncommitted work was 700
  tests plus 17 subtests (see the TikREC vault entry for `a384dd3`).
- Current focused run: 71 passed across `test_source`, `test_capture`,
  `test_connection_log`, and `test_live`.
- The seven `test_finalization_recovery` cases did not run because pytest lacked
  permission to enumerate `C:\Users\Leandro\AppData\Local\Temp\pytest-of-Leandro`.
  They produced setup errors, not test assertion failures. Re-run with a usable
  pytest base temp before treating the current checkout as fully verified.
- Real resumed-media, crash/reboot, and outage deployment validation remain
  outstanding; media correctness requirements remain in SPEC.md.

## Exact next step

Do not begin another roadmap feature. First decide and finish the preserved
raw-arrival diagnostic slice: review its persistent-evidence contract, document
it in the authoritative evidence/spec docs, rerun its focused and full offline
suite using an accessible pytest temp directory, and commit it separately.
Then reassess v0.5 release closure from real recovery evidence and current docs.

## Durable decisions and risks

- Public LIVE only; no authentication, private signing, future-LIVE monitoring,
  or user-data-destructive recovery.
- Automatic resume requires the same canonical room ID and valid retained
  evidence; ambiguous outputs/partials are preserved and blocked.
- Raw copies are best-effort and must never interrupt capture. Arrival timestamps
  describe local read/processing boundaries, not provable source-byte arrival.
- The uncommitted change touches HTTP read behavior and durable evidence; it
  needs a full regression run and real raw-copy comparison before release.
