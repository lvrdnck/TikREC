# Issue #52 — durable same-attempt manifest completion

## Acceptance and successor boundary — 2026-10-06

[PM decision 6014913888](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6014913888)
accepts `df954dd2` R11 and the `580104fc` manifest foundation as corrected. This
supersedes the historical pending-review/no-successor statements below. Their
baseline, development and final-suite evidence remain preserved unchanged.
The newly authorized explicit [owned settlement path](ISSUE_52_OWNED_SETTLEMENT.md)
can release only after fresh live completion proof and confirmed exact cleanup;
`JournalManifest` itself keeps its accepted retained-task default. Manifest schema 1,
original H/capture truth, R11 connection ownership and SQLite thread affinity remain.

## Historical correction R11 — accepted by 6014913888

[PM finding 6013777280](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6013777280)
requires exception-safe manifest-fence teardown on reviewed `580104fc`; manifest
completion is not yet accepted for successor integration. Its protocol and prior
R1–R10/assembly/validation/publication acceptance remain unchanged. Owner decisions
None; schema 8 stays byte-for-byte unchanged. This correction grants no settlement,
release, retry/adoption or integration authority.

`ManifestFenceConnection` owns the exact reader returned to the manifest fence.
Entry/body failure remains the same original exception object/type. Rollback and
close are independent one-attempt operations; their separately tagged errors follow
the existing 32-diagnostic/dropped-count convention. Successful body plus failed
teardown raises the first cleanup error and never appends a later success step.
Confirmed close clears only the reader owner, even if rollback failed. An
unconfirmed close retains the exact connection explicitly on the primary error and
original manifest capability, independent of garbage collection. Adapter errors
carry bounded secondary diagnostics and their dropped count.

Connected `close()` attempts one rollback/close pair on that exact retained reader
and reports its cleanup/retention separately. No native create/write/rename/flush
is repeated. SQLite's existing thread affinity is unchanged: cleanup from a wrong
thread remains unconfirmed/retained until the owning thread confirms close. Native
manifest/output/control/workspace owners, intermediate durable facts, running task,
unit/claims and pins remain retained; reader cleanup is not task settlement.
Hashes/scans/hooks remain outside the short native fence.

### R11 baseline and development evidence

Regressions call the actual repository fence and connected generated Windows path
before runtime edits. Main unchanged-code baseline: **36 failed / 4 passed** in
89.81 seconds; supplemental exact-thread/catalog-writer selection: **3 failed /
40 deselected** in 8.76 seconds. These expose the missing behavior rather than
relabeling the historical full suites below. The portable teardown matrix isolates
only the owner checker on a minimal file-backed SQLite fixture; connected tests use
the actual schema-8 catalog, original ownership and native control transitions.

`baseline-writer-proof.json` records Windows SQLite **3.53.1**, DELETE journal:
rollback injection replaced the original body exception, skipped close and left
`in_transaction=true`. The competing writer's bounded commit failed with
`database is locked`; independently closing that exact reader let the same pending
INSERT commit exactly once without replay. This is injected proof, not a claim of
a natural production incident. The new connected competing-writer regression uses
a fixture-only no-change UPDATE to a disjoint real catalog binding and verifies
exactly one execution/unchanged claims.

Development run: **41 passed / 2 failed** in 116.74 seconds. Both failures were
in the new catalog-writer fixture, which referenced `revision` rather than the
actual binding column `generation`. Corrected that column without weakening the
exact-one-execution or unchanged-binding assertions. The corrected writer/thread
selection passed **3 tests / 40 deselected** in 8.94 seconds.

All final isolated suites passed on the same **408-file frozen source/test tree**:

| R11 suite | Actual result | Seconds |
| --- | --- | --- |
| Focused (eight modules) | 171 passed | 752.77 |
| Related (87 modules) | 934 passed / 2 skipped / 17 subtests passed | 1281.31 |
| Full (`tests`) | 2,695 passed / 9 skipped / 19 subtests passed | 1585.39 |

No final failures; all **408 source/test hashes unchanged after every run**.
All 43 R11 regressions and seventeen existing actual supervisor-death cases pass.
`final-tree-verification.json` and each suite's frozen-check JSON record the proof;
`source-test-hashes-delivery.json`, module lists and complete delivery logs remain.
Schema-8 definitions match reviewed `580104fc` exactly after normal Git line-ending
normalization; no persistent schema change. Related overlaps focused/full only
with independently isolated paths, configuration, catalogs, events and jobs.
Delivery uses a normal task-owned `Refs #52` commit/push; **PM review only next**.
Manifest completion remains unaccepted for successor integration until PM accepts
the correction. Terminal settlement/release is planned later, not authorized now.
Every suite uses new separate APPDATA/XDG_CONFIG_HOME and basetemp, explicit
isolated-worktree PYTHONPATH and the unchanged installed Hermes Python runtime.
Existing Windows FFmpeg/FFprobe/.NET native fixture tools are reused. Module-list
files, complete logs, frozen hashes and verification JSON remain outside the repo.
No previously completed basetemp/configuration or earlier evidence is reused.
R11 evidence root: `C:\Users\Leandro\TikREC-tests\issue52-r11-manifest-fence`.
`r11-catalog-fault-evidence.json` records 22 connected fault snapshots: no
installed success row, byte-identical recoverable original manifest, unchanged
published MP4 hash and retained running task/units/claims. These are read-only
post-fixture facts; live native retention is asserted before independent fixture
cleanup. `r11-positive-media-evidence.json` confirms the successful copy/libx264
regression hashes match reviewed `580104fc` outputs below. The full diagnostic,
cleanup/cancellation and one-operation acknowledgement regressions remain included.
Historical evidence in `issue52-manifest-completion` remains preserved. No runtime/
dependency upgrade, schema/resource-policy change or production access/change/
restart is made.


## Authority and scope

[PM decision 6012406322](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6012406322)
accepts publication base `0ca6144a155a3e8de6b2f306901c8ed8fa3140bd` and authorizes
this single internal slice. Accepted R1–R10, assembly, validation and publication
remain accepted. #52 stays OPEN / SINGLE ACTIVE; #48 OPEN / PAUSED (Gracie-only
raw/Ward OFF); #28 unresolved. Owner decisions: None. This report records the new
contract and evidence; historical slice results remain in their original reports.

`JournalManifest` explicitly selects completion rights before the original
`AttemptCoordinator` claims one sealed FIFO session. It connects the existing
assembly, three owned validators and publication to `ManifestCompletion` without
releasing/reopening inputs, candidate, output or original controls. No scheduler,
CLI/service/API/monitor wiring, terminal settlement or restart adoption is added.

Publication-only, validation-only, assembly-only and synchronous defaults remain.
Only completion-capable original acquisition adds DELETE to the read-only
`session.json` owner. Other input/control rights remain unchanged; validators
still inherit only the published candidate's read access through retained stdin.
The successor alone is created with write/read/rename access. Historical receipts,
arbitrary paths, failed/revoked owners and repeat capability construction cannot
grant a new control write.

## Exact control protocol

1. Revalidate live publication, exact original coordinator/handles, original H,
   seal/marker/claims, complete input/scratch inventories and output ID/size/stamp/
   SHA-256. Require the same observed publication operation and validation chain.
2. Commit immutable preparation before creating any artifact. Bind session,
   attempt, owner, original H/revision/seal/marker, complete publication evidence,
   predecessor native identity/size/stamp and exact predecessor/successor bytes
   with SHA-256. Recoverable bytes are base64 in immutable journal evidence.
   Declare precisely `.tikrec-manifest-TOKEN.successor.json` and
   `.tikrec-manifest-TOKEN.original.json` in the original pinned parts directory.
3. Native root-relative `NtCreateFile(FILE_CREATE)` creates the exact stage and
   returns its owner together. Existing names are refused. Retain the owner before
   proof can fail. Write one complete bounded JSON document through its descriptor,
   require flush, then verify bytes/native metadata and append `staged` evidence.
4. Rename the original read-only manifest handle to its declared history basename
   using native no-replace semantics. Keep the same handle, original file ID,
   length, write stamp and bytes. Verify and append separate `preserved` evidence.
5. Rename the same staging handle to the now-absent `session.json`, again no-replace.
   Revalidate all evidence, require another same-descriptor flush, and append
   `installed` proof with `required_flushed=true`. Revalidate after acknowledgement.

Native creation and renames use the original pinned parent. See Microsoft's
[root-relative FILE_CREATE contract](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile)
and [no-replace rename contract](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info).
No in-place truncation, pathname reopen, foreign-file overwrite, replacement
fallback, native replay, rollback over another file, source repair or evidence
deletion occurs. Legacy `.session.json.partial` atomic-write behavior is unchanged.

The original strict guard remains the default. Only the exact local prepared
capability recognizes its declared stage/history/current-manifest chain. It checks
every original artifact/control, immutable original manifest content at history,
unchanged pending marker/H, exact staged/installed bytes and complete namespace
before/after observations. Output proof continues through the original candidate
handle/descriptor. Original H/seal/control hashes are never rewritten.

There is an explicit interval with no `session.json` between preservation and
installation. Preparation, staging, preservation and observed installation are
different committed facts. File operations and SQLite transactions are separate;
this is not an atomic filesystem/SQLite snapshot or a power-loss guarantee.
Read-only reopen reports committed facts and uncertainty without inspecting paths
to infer success, reconstructing native owners, adopting or repeating writes.

## Manifest truth and retained accounting

Media manifest schema remains **1**. Pure completion building changes only
`finalization.status` to `completed`, carries safe existing `input_decode` evidence,
and sets optional `media` facts already established by the owned inspection.
Prior finalization errors and capture errors remain preserved. Session/creator/
room/source/path identity, original capture status, all capture timestamps/counts,
raw intent/warnings, interruption and recovery evidence remain unchanged.

Completion-capable validation retains its existing inspection result and assembly
diagnostic classification in its new immutable report, before validation receipt
commit. No extra probe is launched and no accepted receipt is mutated. The
completion audit requires that classification to match immutable candidate writer
execution (using accepted copy normalization). Copy remains `not_checked`; degraded input stays degraded even when
re-encoding produces a validated output. Unknown optional facts stay null. Clean
output does not prove clean source media or resolve #28.

Accepted H currently admits completed/interrupted capture with no capture error;
this slice does not relax that rule to admit failed captures. Connected tests cover
interrupted capture. Pure builder tests additionally prove preservation of prior
capture/finalization errors, failed status, warnings and unknown media facts.

Task/session remain running/counted. The unit, raw/room/path claims, original input,
control/history, output, workspace/helper and local/durable pins stay retained.
No settlement/refund callback, finalizer release or retention permission is granted.
`close()` revokes execution/cleans proven children and returns false while owners
remain; cleanup evidence separately exposes predecessor/successor retention.

Cancellation/revocation fences every new control create/write/rename/flush and
journal authority. Hashes/scans/hooks stay outside the short native fences. First
failures remain separate from secondary journal/native cleanup diagnostics. Unknown
outcomes retain exact possibly-live owners. A lost acknowledgement permits one
bounded lookup of that exact operation, followed by fresh proof, never reissuance.
Commit-window drift can leave a historical record; post-commit checks refuse live
success and grant no retry/adoption. Directory pins do not prevent new children.

## Isolated schema

Authorized minimal **schema 8** adds only immutable/keep-triggered
`manifest_preparations` and `manifest_steps` plus version/fingerprint. Ordered
staged/preserved/installed rows bind exact operations, revisions and preparation
hashes. Existing assembly/candidate/validation/publication evidence remains
immutable. Schemas **1–7 remain refused/preserved unchanged**, no migration,
production catalog or cutover. The schema-7 fixture is frozen from accepted
`0ca6144a`; its source matches that commit after line-ending normalization.

## Historical reviewed 580104fc verification

All final isolated suites passed on the same frozen source/test tree:

| Suite | Actual result | Seconds |
| --- | --- | --- |
| Focused (six modules) | 128 passed | 578.86 |
| Related (85 modules) | 891 passed / 2 skipped / 17 subtests passed | 1320.88 |
| Full (`tests`) | 2,652 passed / 9 skipped / 19 subtests passed | 1484.87 |

No final-suite failures. All **404 source/test hashes** are unchanged after each
run, including the seventeen actual supervisor-death cases. The final proof is
retained in `final-tree-verification.json`; development failures remain below.

Generated connected copy output: **17,883 bytes / 66 packets**, SHA-256
`564dc75486b06c55dfe12ab6acaeccd3eeaaba46f1d53374943323a8f9ee24af`;
manifest media is H.264/AAC, 64×64, with `input_decode=not_checked`.
Generated connected libx264 output: **16,855 bytes / 67 packets**, SHA-256
`675817cf334dbce51ee8efd41559f3ec1ead86ca9deb9648caa7363734326d6c`;
manifest media is H.264/AAC, 80×64, with `input_decode=clean`.
These match accepted publication output hashes. An additional real encoder run
with injected recognized input diagnostics preserves `degraded` beside passed
owned output validation. Interrupted capture remains interrupted with unchanged
capture timestamps/counts. Original manifest history is byte-identical to the
immutable preparation and original H control hash.

`manifest-media-evidence.json` retains the two connected receipts/media/hashes.
Seventeen `manifest-death-evidence.json` files retain committed facts, original
hashes and pinned/counted state after actual `TerminateProcess` supervisor death:
preparation before/after commit, exclusive stage creation before local return,
complete write, staging commit before/after, original preservation before/after
native return, preservation commit, installation before/after native return,
post-install flush and installation result before/after commit/post-result.

Coverage also includes wrong/tampered predecessor, forged/historical/failed live
authority, parent/identity/volume conflicts, complete input/output inventory drift,
held successor changes with restored native FILETIME, late native stage/history/
manifest collisions, first native write/flush/partial-proof failures plus secondary
journal diagnostics, uncertain native results without replay, cancellation on
both sides of validator resume and control boundaries, install-vs-cancel fence,
acknowledgement loss/unavailable lookup/fresh-proof drift, complete diagnostics/EOF,
descendants/unknown lifetime/native cleanup and immutable-row refusal. Two disjoint
capture bindings remain available; an unrelated native job survives cancellation.
Source/FLV/raw/arrival/connection/marker/original-H/unrelated hashes, media and
accounting/claims/pins are asserted unchanged. No whole-session source-cleanliness
or #28 resolution is claimed. Wrong volume uses conflicting native identity
injection; fixture storage is one local fixed volume.
External disposable evidence root:
`C:\Users\Leandro\TikREC-tests\issue52-manifest-completion`.
Earlier slice evidence is preserved. Each suite uses separate new empty APPDATA/
XDG_CONFIG_HOME, explicit worktree PYTHONPATH and basetemp. Installed Python,
FFmpeg/FFprobe and Windows .NET native-fixture compiler are reused without upgrades.
The related and full runs overlap with separate configuration roots, fixture paths,
events, jobs and catalogs; each owns its disposable cleanup.

Commands use the installed Hermes Python 3.11 runtime with
`python -m pytest <module-list> -q --basetemp=<new-disposable-directory>`; full uses
`tests`. `focused-delivery-files.txt` and `related-delivery-files.txt` retain the
exact six/85-module selections. `focused-delivery.log`, `related-delivery.log` and
`full-delivery.log` retain complete output. `source-test-hashes-delivery.json` binds
the frozen 404-file tree; suite verification JSON records compare actual bytes.
The existing journal evidence bound also applies to packed preparation: an
oversized control chain is refused before staging, never partially installed.

### Development evidence

- New connected tests fail collection on unchanged accepted publication code:
  completion adapter absent. This is an absent-feature baseline, not an accepted
  foundation regression.
- First development run: 6 passed, 2 failures. Corrected test expectations for
  libx264's established 80-pixel width and authorized journal schema 8.
- Second selection: 53 passed, 4 failures. The secondary persistence injection
  targeted `owned_attempt`, while candidate retention reads `scratch`; corrected
  that target without changing the first-failure or secondary-diagnostic assertions.

- Lifetime/death development selection: 22 passed, 39 failed. The new audit
  incorrectly compared copy's public `not_checked` directly to accepted sealed
  `unknown`, preventing control preparation and downstream death barriers. Corrected
  that compatibility mapping and bound the public class to declared copy/encoder
  authority; original candidate evidence is unchanged.
- Corrected completion/authority/first-failure/install-cancel selection: **25 passed**
  in 110.68 seconds. Final runs include the additional native partial-proof tests.

## Remaining limits and safe resume

Only generated disposable queued/sealed media is accessed. Natural-recording,
power-loss, complete A1–A20 and service/Scheduled Task acceptance remain outstanding.
No production access/change/restart, scheduler/service/API/monitor integration,
settlement/refund/release, retry/adoption, retention, #48 polling, migration/cutover,
dependencies/runtime upgrades, resource-policy work, merge, release or tag.

After delivery: PM review only; no automatic successor. Pull/reconcile this isolated
branch and the latest PM decision/report. Preserve history and use `Refs #52`.
