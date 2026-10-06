# Issue #52 — durable same-attempt manifest completion

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

## Verification

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
