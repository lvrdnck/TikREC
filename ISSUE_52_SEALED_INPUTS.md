# Issue #52 — native sealed-input read protection

## Current manifest-completion boundary — 2026-10-06

[PM decision 6012406322](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6012406322) accepts `0ca6144a` publication
and authorizes this single internal slice; earlier accepted foundations remain accepted.
Only completion-capable original acquisition grants the read-only `session.json`
owner DELETE rights. Only its exact local journal-prepared predecessor/successor
chain permits declared staging/history names; every other input/control/inventory
check remains strict. No close/reopen, original-H hash rewrite or release occurs.
See [control guard contract](ISSUE_52_MANIFEST_COMPLETION.md).

## Historical accepted guarded-publication contract — 2026-10-06

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

## Historical accepted validation extension — 2026-10-05

[PM decision 6000035417](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6000035417)
accepts `ee884bdc` assembly. The [same-candidate validation contract](ISSUE_52_CANDIDATE_VALIDATION.md)
adds only explicit retained-native validation authority and append-only schema-6
evidence; schemas 1–5 remain refused/preserved without migration. Original H,
accounting/input preservation, exact job ownership and R1–R10 remain accepted.
Candidate validation is the only additional cancellation-aware long reader phase;
generic readers stay finite and arbitrary post-candidate launches stay refused.
No publication, settlement, retry/adoption, service wiring or production change.
Earlier checkpoint/schema statements below are historical evidence within their
recorded limits. #52 OPEN/SINGLE ACTIVE; #48 OPEN/PAUSED; next action: PM review.

## Historical connected use — 2026-10-05

Current schema is 5. [PM decision 5999162236](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5999162236)
accepts `58e40084` and authorizes the [internal assembly adapter](ISSUE_52_JOURNAL_ASSEMBLY.md).
It claims through the coordinator and retains the distinct `ClaimedInputs`
capability through shared planning, durable probes/writer and exact same-attempt
scratch sealing. The queued-only API below stays strict. Native input proof,
original H independence, accounting/pins and cooperative namespace limits remain
unchanged. Earlier schema/checkpoint/next-task statements below are historical.

## Acceptance checkpoint - 2026-10-04

[PM review 5982869804](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5982869804)
**accepts `44711e65`**. Its original queued-only API/native proof limits remain
strict. The subsequent [durable-attempt slice](ISSUE_52_DURABLE_LAUNCH.md) adds a
separate claimed-input protocol with explicit receipt-scoped revision advances,
independent original H validation and attempt-time durable marker observation.
Current schema is 4; schema-3 scope/results below are historical accepted evidence.
Durable attempt/launch and claimed protection are implemented for review; scratch/
queued assembly/publication/settlement/service/retention/migration/cutover remain
unimplemented gates. No automatic integration or full-service/media-hash claim.

## Historical authority and scope

2026-10-04: [PM review 5981877279](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-5981877279)
accepted `2d6896ce` and the separate `c22c482f` extraction, selecting only this
internal read guard. The existing isolated `codex/capture-journal-handoff` was
pulled/reconciled; AGENTS MODEL GATE / PROCEED selected GPT-6.1 Sol — High.
Accepted R4–R7/assembly reviews were not repeated. #52 stays OPEN/SINGLE ACTIVE,
#48 OPEN/PAUSED, #28 unresolved; no owner product decision is pending.

This connects an explicitly addressed original H seal to verified held readers.
It does not connect the queue to assembly, claim work, authorize a child, allocate
scratch, publish, settle or retry. The only child operations added are disposable
test readers. The public finalizer, synchronous CLI/service and schema 3 stay
unchanged; schema-1/2 refusal and historical receipts remain intact.

## Implemented contract

`acquire_sealed_inputs(authority, session_id, expected_revision=...,
expected_seal_hash=...)` requires the explicit existing `CaptureAuthority`.
The guard uses its known catalog, retained catalog/root identity and cooperative
owner lock; there is no default path, catalog search, initialization, alternative
database or token-based authority. The short read-only journal projection audits
the catalog and atomically reads the addressed session, immutable intent/seal,
task/unit, artifact/room claims, absence of a capture binding, queue entry and H
receipt. Only the original H-committed queued owner (task revision 1, no attempt
or token) is accepted. Exact expected session revision/seal, canonical H arguments
and result, retained claims and numeric inventory ordering must agree. This is
an input precondition, not a queue eligibility or launch decision. Later claimed
or retried states need a separately reviewed adapter; this guard refuses them.

Lock order is compatible root writer lease -> authority lock -> short SQLite
read. Native input/control reads and enumeration run outside that lock and
transaction. Target projection is checked before/after acquisition and each
explicit `revalidate()`. Valid changes to other sessions do not invalidate the
target. The lease does not reserve a capture slot or outstanding-work unit.
The already-existing 64-byte lifecycle lock is pinned and checked before using
the existing compatible lease; missing/short locks refuse without creating or
extending one. This does not implement a new retention reader or executor.

`ReadProtection` is distinct from capture's `NativeHandle`: files request
`GENERIC_READ` and only `FILE_SHARE_READ`, `OPEN_EXISTING`, no-follow flags and
NULL security attributes. Normal readers may reopen explicit paths; conflicting
data-write/delete access refuses. Handles are noninheritable. Parent/root pins
use attribute access and read/write sharing without delete sharing, permitting
disjoint cooperative capture. Capture closure still uses zero sharing; catalog
`shared=True` still permits writes and supplies only identity stability.
The access/share mechanism is described by
[Microsoft CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

The guard reopens every sealed FLV, raw file, arrival sidecar, connections log and
manifest, plus the pending marker. Native fixed-volume GUID/component identity,
file ID/volume serial/size/last-write stamp, single-link status and object kind
must match. Controls are read through held handles, bounded to 1 MiB, and checked
against stored SHA-256 values. The complete namespace is enumerated before and
after verification, bounded to the seal's 4,096 artifacts plus marker. Missing,
extra, partial, redirected, multiply-linked or changed evidence refuses; no
control successor or repair is inferred. Accepted raw warnings/remnants remain
in the immutable snapshot without claiming raw completeness.

Held marker bytes must have the exact supported fields, literal assembly/empty
disposition agreeing with the seal, Boolean raw policy, original intent/seal,
catalog native/file binding, session/generation and H operation/revision receipt.
Marker control validation precedes receipt lookup in the existing inspector,
preserving R5's refusal ordering. The guard validates against the receipt from
its atomic target projection. **Schema 3 stores a seal digest, not an immutable
marker-byte hash.** `marker_sha256` is only a lease-local snapshot, checked again
while held; it is not a new stored field or crash-recovery guarantee.

`revalidate()` returns frozen `SealedInputEvidence` with intent/seal, ordered FLV
paths and bindings. Its validity is lease-scoped. Closed/unacquired use refuses.
Revalidation and close serialize; repeated concurrent close is idempotent after
confirmed release. Callers must retain this guard until every reader's whole-job
exit is proved and final revalidation succeeds. This primitive neither owns
children nor automatically guesses when releasing their protection is safe.

Native owners are allocated before opening/validating. Exact handles are cleared
only after native close succeeds. Partial acquisition attempts all cleanup;
`SealedInputError` exposes the original failure, secondary diagnostics and guard.
Failed native/lifecycle cleanup leaves possibly retained owners reachable via
`retained`, marks the guard unusable and does not claim successful release.
Independent releases continue after another failure; subsequent explicit close
can retry retained owners. Lifecycle acquisition failures expose a retained
file/descriptor instead of hiding it. A body exception stays first and receives
the guard/secondary cleanup evidence. No failure changes journal ownership,
accounting, evidence bytes or source-resume permission.

## Actual verification

Final isolated results (Windows build 26200 x64, Python 3.12.10, SQLite 3.49.1,
existing FFmpeg/FFprobe `N-124716-g054dffd133-20260531`):

| Selection | Actual result | Seconds |
| --- | --- | --- |
| New guard tests | 58 passed, 2 skipped | 14.65 |
| Marker-order correction plus guard | 68 passed, 2 skipped | 22.81 |
| Focused guard/native/bridge/journal/process/assembly/lifecycle | 434 passed, 2 skipped | 91.03 |
| Related capture/session/process/assembly/finalization/recovery/live/retention/writer/part/validation/automatic | 1,365 passed, 8 skipped | 166.79 |
| Full isolated offline suite | 2,220 passed, 9 skipped, 19 subtests passed | 177.20 |

Tests were added first. The corrected absence baseline had **two failures / one
shared-mode characterization pass**; absent guard imports explain those failures.
The earlier broad baseline had a hash helper incorrectly reading the locked
lifecycle file and one fixture `session.json` rename access-denied error. The
helper was corrected; no capture behavior/test was weakened to hide that error.
Development runs then reached 58 passes. The first complete verification found
**seven existing R5 ordering failures** (427 focused, 1,358 related, 2,213 full
passes). The marker refactor had looked up receipts before rejecting invalid/
seal-mismatched dispositions. Restoring control validation before receipt lookup
fixed that regression; all final selections above were rerun against the same
corrected source. R4–R7 tests remain unchanged. No final failures remain.

All run environments redirect APPDATA, LOCALAPPDATA, XDG_CONFIG_HOME,
XDG_STATE_HOME, TMP/TEMP and pytest basetemp to fresh disposable folders;
PYTHONPATH points to the isolated checkout rather than the deployed editable one. Pytest
cache is disabled. Logs and fixtures are preserved outside the checkout at
`C:\Users\Leandro\TikREC-tests\issue52-sealed-input-20261004`, with final run
names `focused-corrected`, `related-corrected`, `full-corrected`. Full command is
`python -m pytest tests --basetemp <fresh-disposable-directory> -q -p no:cacheprovider`
under those redirected environments. Focused uses `test_sealed_inputs*`,
`test_capture_handoff*`, `test_capture_fence`, `test_session_journal*`,
`test_owned_process*`, `test_unpublished_assembly*`, `test_assembly_diagnostics`
and `test_lifecycle_lock`. Related additionally covers capture/session,
finalization/recovery/live/retention/writer/part/validation/automatic and the raw
CLI regressions. All new package/test modules are below 300 lines; diff whitespace
checks pass. Existing POSIX/platform skips plus two symlink-privilege skips are
reported, not treated as native passes.

Disposable fixtures are committed through the actual CaptureBridge and journal,
with locally generated 64×64 AVC/AAC FLV, real raw/arrival files and real controls.
These are not the assembly report's co-located stand-ins. Tests cover addressed
revision/seal/catalog/unknown or missing journal, pre-H/empty refusal, marker
missing/invalid/disposition/revision/seal/operation/catalog/field/type conflicts,
added/removed/changed media/raw/arrival evidence, same-size/restored-stamp control
hash tampering, optional raw-warning remnants, case aliases, hard links, reparse
points, conflicting opens, guard lifetime and target transitions. Refusals
preserve evidence, target state, capacity and unrelated ownership.

Actual Windows tests prove compatible reads, refused append/delete/rename access,
denied parts-directory rename, noninheritable controls and a real privilege-free
junction refusal. Direct symlink fixtures are skipped when Windows denies their
creation privilege; that limitation is explicit. Directory child creation is
possible while pinned and is detected by revalidation. Deterministic barriers
prove filesystem work does not hold the authority lock; another disjoint actual
capture can reserve/complete H under the compatible root lease. Retention's
exclusive lifecycle acquisition is refused until guard release.

Fault tests cover partial acquisition, failure immediately after native open,
CloseHandle failure, lifecycle acquisition/file teardown, original body failure,
retry of retained exact owners and concurrent revalidation/close. Existing
R4–R7, owner death/descendants/nesting/streams/cancellation and assembly tests
remain in the focused/related/full selections.

The bounded read-only FFprobe fixture uses two `OwnedProcess` children through
the existing `validate_part` runner injection: frame decoding and packet-DTS.
Each child has explicit fixture authorization, exact identity, zero job members,
exit 0, both stream EOFs and no prefix truncation/error. The guard is held through
exit and final revalidation. A separate native-event reader proves writes/deletes
remain refused during execution and final-tail delivery; another preserves
protection when native lifetime queries temporarily become unknown. Independent
exact-job fixture guards prevent orphan disposable children. Another actual child
checks that the native control identities were not inherited.

Source, raw, arrival, manifest, connections, marker and database hashes are
unchanged; requested final MP4 is absent. The guard/readers never claim or assemble
queued work. One disposable stale-target regression invokes the existing journal
claim operation solely to invalidate the read proof; it launches no media task.
The 20-second FFprobe test wait is a fixture bound, not assembly or
watchdog policy. Generated matching-copy and differing-libx264 assembly regression
fixtures are rerun separately with existing part/packet-DTS/deep validation,
unchanged source/stand-in hashes and absent requested final destinations.

### Focused delivery native/media observations

The actual H fixture is session `73a845fb-cc77-4c98-af66-fdda52936061`, revision
`4`, seal digest
`0b074c3cd3d5128d7abde51826b5d200df2fe114ace47f7026f207fd38353d7f`.
These are disposable historical observations, never fresh authority to launch
or terminate a child. Both readers used the installed absolute FFprobe path.

| Read-only child | PID / creation FILETIME | Exit / active / EOF / dropped |
| --- | --- | --- |
| Existing part frame-decoding check | 61408 / 134356057604173348 | 0 / 0 / both complete / 0 |
| Existing packet-DTS check | 32868 / 134356057605039646 | 0 / 0 / both complete / 0 |

Both children had no first or secondary process error and released their controls
before guard release. Native-event reader and unknown-query regressions used
independent exact-job guards as well. Each full/related run created separate
fresh fixture identities rather than reusing this catalog.

| Preserved artifact | Bytes where useful / SHA-256 |
| --- | --- |
| Generated source and actual raw | 8,823 / `880bf089561569627028361e96a834c4e083bcea6e8952043c1d8127214cce97` |
| Actual retained FLV | 8,515 / `ba3bd1029bbfdb81065eadd09902b0c54a32dd11abb184a9f31b630fff61f51a` |
| Actual arrivals | `0d33345e70e29c665f4db5ea7b4c6e0e876c83067b5e0e9f6201c1a86a9d503a` |
| Actual connections | `dacb329046e142b24ce8f46e4a18bbd81815800e8abe9c7522f1c9e2859ddc65` |
| Actual manifest | `f9e36f1c6d3ae5e564780d1eeca8e5aed8809bd9a202da53f53e09574237a620` |
| Marker (lease-local hash) | `142e9168cb3e10184294d21fd10a72f59ce17fddad91ed6f3c6960ec4d734887` |
| Catalog bytes | `f82bb41468a12b55d46c444a0705393224d9af9a27de887da185f4d750acd060` |

Hash equality is observed before/after the complete held-reader operation.
Lifecycle lock files are excluded from byte hashing because they carry OS byte
locks; their identity/size/compatible lease behavior is checked separately.
`sealed-reader-evidence.json` retains the complete test-local details.

The separate matching/differing AVC regression rerun again produced the previous
17,883-byte copy candidate (`e43c1036c8e824c0b7498f6b5a7cff330147d5f0d49b361d74d0471bd6610586`)
and 16,855-byte reencode candidate
(`675817cf334dbce51ee8efd41559f3ec1ead86ca9deb9648caa7363734326d6c`).
Each has 12 video frames and matching synchronous PTS/duration/dimensions, passes
existing part, packet-DTS and deep-output validation, and preserves all source/
stand-in hashes. This is separate synthetic assembly regression evidence; no
sealed queued fixture was assembled and no natural-recording check was performed.

## Proof limits and remaining gates

This adds partial A7/A8/native-read evidence only. It is not whole-media hashing,
decoder validation performed by the guard, raw-to-retained semantic provenance,
power-loss certification, real-LIVE health or full A1–A20/Scheduled Task acceptance.
The fixture hashes/validators are independent test evidence, not stored seal
guarantees. No pre-existing or production recording was inspected or consumed.

Native sharing excludes ordinary conflicting data-write/delete access while held.
Windows sharing does not exclude every attribute/extended-attribute operation;
size/write-time identity can be reproduced by a sufficiently capable external
writer before acquisition. Media changed with restored metadata can escape a
metadata-only seal. Whole-media hashes are not stored. The native API and trusted
caller must behave according to their contracts; arbitrary privileged writers,
injected callbacks that stall, external filesystem interference and compromised
processes are outside this proof.

Directory pins deny deletion/rename but permit new children. Complete repeated
inventory checks detect changes at observed boundaries; they do not provide an
atomic filesystem namespace snapshot. Cooperative authority/lifecycle ownership,
no out-of-band namespace writers and explicit revalidation remain necessary.
Existing case aliases are accepted only when native identity matches; redirects
and multiple links are refused. The guard does not repair controls or infer a
future authorized successor after an unexplained hash change.

Durable attempt/child-launch persistence, claimed-phase guard lifetime protocol,
scratch ownership, queue scheduling, validation/publication receipts and promotion,
settlement/retry, service/API/monitor/bootstrap/storage/watchdog/resource policy,
retention integration/destructive recheck, migration/cutover and deployment gates
remain separate reviewed work. `UnpublishedAssembly` still takes explicit trusted
inputs; this slice does not wire it to the guard or queue.

No production access/state/config/media changes, restart, retention execution,
#48 polling, dependencies/runtime upgrades, resource policy, release/tag, remote
worker or merge/cutover. #48's Gracie-only raw/Ward-OFF policy and natural-evidence
criteria remain intact; #28 unresolved; #13/#8 unstarted. Stop after task-owned
commit/push for PM review, recommended GPT-6.1 Sol — High.
