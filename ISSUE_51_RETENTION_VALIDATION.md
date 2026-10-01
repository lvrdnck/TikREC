# Issue #51 real-media retention validation evidence

## 2026-10-01 Windows single deletion and later root-change checkpoint

**Deletion: proven COMPLETE/0. Full #51 validation: NOT PASSED.**
**The one-attempt allowance is consumed; no retry or second deletion is authorized.**
Source was synchronized by `git pull --rebase --autostash` at `014f997`.
Native Windows/Python 3.12.10 used the normal `.venv\Scripts\tikrec.exe`.
No production code or tests changed, no service stop/restart/deployment occurred,
and no other roadmap issue, release or tag work started.

### Natural inactivity and admission

Public configuration confirmed `C:\Users\Leandro\Videos` and unset age.
At 21:05:39.474 and 21:05:44.677 CEST, both service slots were naturally idle,
health/storage OK, no shutdown/recovery pending, and both durable jobs completed
with finalization complete. Slot 1 retained Gracie
`ffcc2566-2085-4faa-940e-2bc177b5288c`; slot 2 retained Gracie
`05f3e981-b713-403c-9bef-198282ec5766`. Neither was a deletion candidate.
Root snapshots matched, with 49 claims, zero uncertain claimants and no partials.
The public age-unset plan (21:06:13.192–21:07:06.232) exited 0, empty stderr:
19 retained (`retention_disabled`), 27 ineligible (`creator_unknown`), and only
three known raw diagnostic sessions with individual `evidence_conflict`.
The root-wide conflict had cleared; those three diagnostics stayed excluded.

The approved public `config set retention-max-age-days 1` exited 0 at
21:07:42.950. A fresh public plan (21:07:42.956–21:08:29.052) exited 0 and
showed six eligible ordinary Eliss sessions. Every Gracie was excluded regardless
of its classification, as were legacy/unknown, raw-copy, forensic, diagnostic,
protected, active/recoverable, ambiguous and job/evidence-linked sessions.

### Exact selected evidence

Selected the smallest of the six eligible non-Gracie recordings to minimize
validation impact (end time breaks size ties). Older alternatives were larger.
No exact UUID/stem reference appeared in repository documentation/implementation
or issue #8/#13/#28/#48/#49/#52 bodies/comments. Its artifact inventory was ordinary
completed capture, without raw, forensic, diagnostic or recovery evidence;
neither durable job referenced its UUID or paths. Service was still idle.

- UUID: `044cc8c0-9be6-4da6-8d0d-fef8e85dbf79`; creator: `eliss4r.n`.
- End: `1790661733.390538` / `2026-09-29T06:02:13.390538Z`.
- Final MP4: `C:\Users\Leandro\Videos\eliss4r.n-20260929-074924.mp4`.
- Parts: `C:\Users\Leandro\Videos\eliss4r.n-20260929-074924.parts`.
- Classification: `eligible / age_threshold_reached`, unprotected.
- Four regular files: final 98,273,270 bytes; retained 98,400,273 bytes;
  total **196,673,543 bytes**, one FLV.
- Manifest: schema 1, `tiktok_live`, room `7690829544403864333`, matching UUID,
  creator/output/parts/end, completed capture/finalization, no error/interruption
  or recovery. Full manifest plus identities/modes/sizes/timestamps/link counts,
  attributes and four SHA256 values were preserved before invocation.

| File | Bytes | SHA256 |
| --- | ---: | --- |
| Final MP4 | 98,273,270 | `16472ea65e28996c3b6e7f5f7483dbc826d7fbdae55ac3a34560f4f6d939f9e5` |
| `part-0001.flv` | 98,397,652 | `d9b0993b251186eb6154b42f690bf7307cc140a59f17abc11bb4faf0fc0af04b` |
| `connections.jsonl` | 1,619 | `393a9418a91b9e2499e34b37dad5d328b70717b1253dc0324ce62bd459870cb2` |
| `session.json` | 1,002 | `7e5bf5a1b91b251ea0a42be19f7aa90be87234394e53aa2221edaad0726737e4` |

### Single public attempt and immediate verification

Exactly one invocation ran at **21:10:47.162–21:20:26.715 CEST**:

```text
tikrec retention delete 044cc8c0-9be6-4da6-8d0d-fef8e85dbf79 --confirm 044cc8c0-9be6-4da6-8d0d-fef8e85dbf79
```

No private executor call or bypass occurred. The command displayed its normal
preview, returned **COMPLETE/0**, empty stderr, operation
`29d6d5a2-34cc-4420-91cf-324b29ba8cec`. The long duration includes public
whole-root byte binding; the observed inventory had about 78 GB of regular files.
No interruption, failure, uncertainty, retry or second attempt occurred.

Audit path:
`%LOCALAPPDATA%\TikREC\retention-audit\d07cc58e2ea6cb6def5786ab70847a39ef0e205bdb7775a9304fff3175dbf331.jsonl`.
It was absent before invocation. It now has exactly **12 events**, one operation:
`intent`, five exact `attempt`/`deleted` pairs, then `completed` with count 5.
The pairs are ordered:

1. `eliss4r.n-20260929-074924.parts\part-0001.flv`
2. `eliss4r.n-20260929-074924.parts\connections.jsonl`
3. `eliss4r.n-20260929-074924.parts\session.json`
4. Empty `eliss4r.n-20260929-074924.parts`
5. **Final MP4 last:** `eliss4r.n-20260929-074924.mp4`

The intent's artifact hashes match all four pre-delete hashes. No other target,
failed event or incomplete operation appears. CLI COMPLETE/0 proves the completed
sync callback was reached; read-back audit ends in `completed`. No power-loss
test was performed against real media.

At 21:21:41.729, immediate filesystem verification found exactly those five
paths gone, no new entries, and all **753 unrelated observed entries unchanged**.
Comparison covered immediate root entries and each session subtree by identity,
size, mode, timestamps, links and attributes, plus SHA256 of session/connection
controls. Unrelated media were not rehashed. Remaining 48 claims matched the
pre-delete claims minus this target. Both jobs/slot identities were unchanged;
service remained idle and healthy. The latest Gracie MP4 still existed then.

### Later verification limitation and stop

The fresh post-delete public plan ran **21:21:41.739–21:22:28.568**, exited 0
with empty stderr, and no longer presented the deleted UUID. However, all
48 sessions were `needs_attention / evidence_conflict`. At 21:22:57.092 the
root stamp differed, and the only changed session claim was latest Gracie:
its `gracie.kf-20261001-201956.mp4` output stamp/physical identity changed from
present to absent. Its parts/control evidence was unchanged. At 21:24:47.670,
final inventory comparison against immediate verification still found only
that unrelated MP4 path missing, plus changed `C:\Users\Leandro\Videos\Unsorted`
directory metadata; no added immediate entry. Both jobs and service slots stayed
completed, healthy and available. PID 37772 / creation 11:35:56.463 CEST persisted.

This later namespace change is **not attributed** to a process or classified as
a move/deletion. No archive/destination search or repair was attempted. The
retention audit contains only the exact Eliss operation and remained byte-for-byte
unchanged. Initial exact-scope verification passed, but continued unrelated-media
stability is not established; an unconditional full-validation PASS is withheld.
No production defect is demonstrated. Stop and preserve; do not retry, repair,
clean quarantine, manually delete, alter Gracie or start another roadmap task.

Because retention mutation itself was proven complete, with no incomplete or
uncertain removal, the documented public policy restoration was safe:
`tikrec config unset retention-max-age-days` exited 0 at **21:23:38.786**.
Age is unset/disabled again. Configuration SHA256 exactly matches this resume's
original bytes: `2ac169bd603d6675b87ac9b9f875699d6f1872536354f393cc12d3bf6081dfa1`.
This differs from the earlier 20:22 checkpoint; current settings were read fresh
and unrelated owner configuration was preserved. Original manifestless evidence
archive remains in place; segregation was not repeated and its media was not opened.

**Safe resume:** #51 remains open/single active for a bounded read-only
reconciliation of the later Gracie output/`Unsorted` namespace change and its
effect on the verification gate. Preserve the completed operation and all
evidence. The old authorization is consumed; neither another deletion nor a
retry is allowed. Any new destructive validation requires new explicit owner
authorization. No owner decision is needed to inspect the existing evidence.
No production fix belongs in this validation session. v0.11.0 remains unreleased.

### Evidence storage and checks

Metadata only (no media copies) is in
`C:\Users\Leandro\TikREC-evidence\issue-51-windows-resume-20261001-210539-3c037abb`.
`evidence-sha256.json` lists 29 preserved files; its SHA256 is
`44372d94e2eacf989921c114edb8fa8694721f0d93f324c20a289b80cd22f395`.
Key checksums:

| Evidence | SHA256 |
| --- | --- |
| `candidate-pre-delete.json` | `04c359b780aede8ede081118e0d994bfdb216059210f869e27dd161f460a9159` |
| `deletion-outcome.json` | `7b191392b192241cfdbe25ac19d78464125d92c17559a472e246ba25e428f127` |
| `audit-copy.jsonl` | `b719586ef87e503c0e344cf7f1fe63fc8a73e61685da3b43a1acece00e641996` |
| `post-delete-verification.json` | `19b5c08758390e46a1d0a0cc36363821b2f592c6c76f2a437ca7adcaf7b85a34` |
| `public-plan-post-delete-outcome.json` | `003fcac19b96e59071727b25e766ae747245df90817d077d233de4e065a6e43c` |
| `policy-restored.json` | `1e40d2af06e41b90d809e4f3e92b84bfb0f9c4bfc45b588b1efc27f1feaaa94f` |
| `final-read-only-checkpoint.json` | `49377497b3fc7a5849f669da995ca98a20da1f90439d945b0057bad7dba74f15` |

Runtime checks, three normal public plans, one public deletion, public policy
set/unset, exact audit progression/hash comparisons and filesystem scope checks
were run as described. Offline tests were not rerun: no implementation changed,
and the later verification conflict triggered the preservation stop boundary.

## 2026-10-01 Windows public-plan stop checkpoint

**Real-media deletion validation: NOT PASSED. No deletion attempted.**
`git pull --rebase --autostash` reported already up to date at `f6f7023`.
The approved task ran on native Windows / Python 3.12.10 through the existing
`.venv\Scripts\tikrec.exe`. The real public configuration selects the intended
`C:\Users\Leandro\Videos`; `retention_max_age_days` is unset/disabled and the
protected-creator list is empty. Configuration SHA256 before and after planning
is `02e4b5fe9fcb106d3c6b593ec7c596fc5e7eaa09976bbed33d0befc721ece507`,
also matching the previously preserved configuration. No policy was changed.

Authenticated health and aggregate recordings show two slots, one active,
one available, no shutdown and storage OK. Both durable job documents load and
match the service observations:

| Slot | Session UUID | State / retained ownership |
| --- | --- | --- |
| 1 | `ffcc2566-2085-4faa-940e-2bc177b5288c` | Recording Gracie room `7691765274030164766`; `gracie.kf-20261001-201956.mp4` / matching `.parts`; non-terminal recording intent, no stop request |
| 2 | `05f3e981-b713-403c-9bef-198282ec5766` | Completed Gracie room `7691214478142212895`; `gracie.kf-20260930-084426.mp4` / matching `.parts`; finalization completed, `room_ended`, no reconciliation required |

The jobs are in `%LOCALAPPDATA%\TikREC\job.json` and `job-2.json`.
The service listener PID remains 37772 with creation time 2026-10-01
11:35:56.463 CEST. Executable-path inspection was unavailable for that process;
the configured Scheduled Task action points to this checkout's existing CLI.
No service deployment, stop or restart was performed.

Read-only claim observations at **20:22:09.818 and 20:22:14.959 CEST** each
contain 49 immediate claims, zero uncertain claimants and internally stable
membership. The complete snapshots differ only for
`gracie.kf-20261001-201956.parts`. Its `.part-0001.flv.partial` grows from
17,471,314 to 18,173,651 filesystem bytes; nearby service counters grow from
17,523,342 to 18,181,334 bytes. Snapshot and service reads occur sequentially,
so those counters describe separate observation instants. Natural inactivity
and whole-root stability are **not established**.

One normal public `tikrec retention plan --json`, with age still unset, runs
from **20:22:15.007 to 20:23:03.100 CEST**. It exits **0**, with empty stderr,
and all **49 sessions** classified `needs_attention / evidence_conflict`.
Exit 0 means the advisory plan completed; its classifications do not clear the
root conflict. The active writer explains the observed instability, consistent
with the documented whole-root safety boundary. No production defect was shown.

The stop boundary was honored. No candidate was selected; no temporary age
rule, deletion attempt, retry, repair, quarantine cleanup, manual deletion or
second attempt occurred. Age restoration is inapplicable because policy was
never changed. After planning the same slot 1 continues recording, now at
24,602,318 reported bytes; slot 2 remains completed with the same UUID.
Health/storage remain OK. The persistent lifecycle lock's identity and metadata
are unchanged. The root-bound audit remains absent at
`%LOCALAPPDATA%\TikREC\retention-audit\d07cc58e2ea6cb6def5786ab70847a39ef0e205bdb7775a9304fff3175dbf331.jsonl`.
No deletion operation or audit intent was initiated. The preserved
`C:\Users\Leandro\TikREC-evidence\issue-51-manifestless` archive remains in
place; segregation was not repeated and its media was not opened or changed.

**Safe resume:** #51 stays open as the single active task, waiting for natural
root inactivity/stability; no owner action is pending. On the next approved
resume, recheck current configuration, service, both jobs and repeated root
observations, then require conflict clearance from a fresh public age-unset plan.
Only afterward reconsider the recorded temporary age-1 approval and at most one
ordinary eligible non-Gracie session under every original exclusion. Preserve
the exact-consent, one-attempt, no-retry and policy-restoration boundaries. The
allowance is unused. No other roadmap work, production code/test change or
release/tag action occurred. v0.10.0 is released; v0.11.0 is unreleased.

### Local metadata evidence

New metadata only (no media copies) is stored separately from the preserved
archive in `C:\Users\Leandro\TikREC-evidence\issue-51-windows-resume-20261001-202209-aed23b9a`.
The summary above is the durable GitHub resume record; the local JSON retains
the full read-only observations. SHA256 values:

| File | SHA256 |
| --- | --- |
| `observation-1.json` | `15db119608fa0d4eded7bbf232febfba0f0ddb750fa3682180a67eed50823d38` |
| `observation-2.json` | `7df3325e9d1c9ecd2fe67ab67b3e57eab0729195fa2d9aaf7efdd0c62bba2f61` |
| `observation-summary.json` | `7da12a4c8ecbe06d39b66b7cfa15fb93c79fc74985336a56b9d81d05c066df38` |
| `durable-jobs.json` | `8433474c6d633e9b33d525b395eede0936abe23f4362eabac620171e378c9ca3` |
| `control-before-plan.json` | `8cc9f6e2dcb54094d48c2ca6946df4f350c9e05b26eafa62db8b26bfd3a33ddc` |
| `public-plan-age-unset.json` | `5573676977f6b3bfbd71531041f9317090ac0021a00b6714675635701fe23688` |
| `public-plan-outcome.json` | `672f0db1daba02f025b803e85a2f50fddc12d96a2391bae807f633c76186e177` |
| `public-plan-stderr.txt` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `runtime.json` | `4e6df66a69adfea2b5595c6a361d92db19223be1a0f1032cd629821fe7952a75` |
| `runtime-after.json` | `25b513868ff89929db835bf8c7e59c78cc17f3f879c0a5327b595774f80fd7f7` |

## 2026-10-01 Windows resume checkpoint

The owner returned TikREC fully to Windows and ended Fedora/Linux runtime work.
#53/#54 are superseded and closed as not planned; their unreleased changes are
reversed with Git history preserved. No Fedora gate remains. #51 stays open as
the single active/next v0.11 task on the intended Windows root. This rollback
accessed no real media/archive/configuration/service state and attempted no
deletion or policy change. Age remains unset, the one-deletion authorization
is unused and real-media validation is NOT PASSED.

Resume only after natural inactivity and a stable public age-unset plan. Keep
the preserved archive in place and do not repeat segregation. The existing
temporary age-1 approval, one ordinary non-Gracie deletion maximum, all evidence
exclusions, exact consent, policy restoration and immediate stop on any refusal,
failure or uncertainty remain unchanged. Do not stop/restart the service or
recordings to create eligibility. Historical Fedora observations remain in Git
history and issue discussions; they do not define the current runtime.

## 2026-09-30 authorized segregation checkpoint

**Archive preservation: PASSED. Real-media deletion validation: NOT PASSED.**
No retention delete command was issued. The temporary age rule was never set;
configuration bytes remain identical to the pre-move inventory. The existing
one-session deletion allowance remains unused. v0.11.0 remains unreleased.

The source root was `C:\Users\Leandro\Videos`; the preserved archive is
`C:\Users\Leandro\TikREC-evidence\issue-51-manifestless`.
Only `test.parts`, `test2.parts`, `test3.parts`, `test4.parts`, `test5.parts`,
`test6.parts`, and existing `test3.mp4`, `test5.mp4`, `test6.mp4` were moved.
All six directories still lacked manifests; no durable job referenced the
selected paths. Exclusive read probes found no conflicting open handles.
All nine absolute source/destination paths were checked against the approved
root/archive before native PowerShell `Move-Item` operations on the same volume.
No files inside the evidence sets were renamed or rewritten.

All 19 regular files totaling 806,859,876 bytes passed SHA256 and size checks
at their new paths. Directory/file identities, modification timestamps, ctime,
attributes, modes, and link counts also matched the pre-move inventory.
The nine original source paths are absent and every archived directory has
exactly its expected file set. No Gracie path was moved or modified by this task.

## Why execution stopped

With `retention_max_age_days` still unset, the public
`tikrec retention plan --json` exited 0 but classified all 47 remaining sessions
as `needs_attention` / `evidence_conflict`. The approved procedure required a
stop at this point, before enabling the age rule or deleting any recording.

Subsequent read-only diagnostics found 48 claims and zero uncertain claimants.
Each root snapshot was individually stable and the root directory stamp matched,
but the complete snapshots differed because these active partials grew:

- Eliss `a3a8bb85-0bd1-4a6c-91b5-3bb077ec3f37`:
  `eliss4r.n-20260930-075338.parts\.part-0007.flv.partial`.
- Gracie `05f3e981-b713-403c-9bef-198282ec5766`, naturally started by the service:
  `gracie.kf-20260930-084426.parts\.part-0001.flv.partial`.

Authenticated service status showed both sessions recording in their existing
slots; no stop/restart or manual start was performed. Media continued to grow
through normal service activity. `retention_plan.py` invalidates the whole
observation when its closing root snapshot differs from the initial snapshot.
This is expected fail-closed behavior. The exclusive retention lifecycle lease
also conflicts with active cooperative writers. No production defect was
demonstrated and no production code changed.

## Safe resume under #51

Keep the archived evidence where it is; do not repeat segregation or move it
back. No owner decision is pending. Resume the single active #51 task when the
configured root is naturally idle and stable, without stopping the service or
recordings to manufacture eligibility. First run the public plan with age unset.
If a root-wide conflict remains, stop again before policy/deletion.

Only after that check passes may the recorded approval for temporary age 1 be
used through the normal configuration CLI, followed by fresh candidate discovery.
Every Gracie session is categorically excluded, as are active/recovering,
job-linked, raw-copy, forensic, diagnostic, protected, and ambiguous sessions.
At most one ordinary eligible non-Gracie session may receive one public deletion
command with exact confirmation. All original failure/result boundaries and
policy-restoration requirements from issue #51 remain in force.

## Preserved regular-file inventory

Paths below are relative to the source root and now exist at the same relative
names beneath the archive. The full timestamp/identity metadata is preserved in
`pre-move-inventory.json`; verification is in `post-move-verification.json`.

| Relative path | Bytes | SHA256 |
| --- | ---: | --- |
| `test.parts\connections.jsonl` | 230 | `fec4e885ba2301ea1c6ef53e35d4677fe1e13d62f4edaa36d255c80332bec52d` |
| `test2.parts\connections.jsonl` | 252 | `0a6ade2df9df55f01dee9e26538aecae5d60f5f8520db326e51b80f3b24685a8` |
| `test3.parts\connections.jsonl` | 2010 | `2c20cc90f3e22b27c6c09e4eeceb9f638882dc5ad91f79ea45cff2d94e1364b5` |
| `test3.parts\part-0001.flv` | 161600897 | `9c0b6a1e5896661ae8ff1cf291de00466d1ac1e3fa87158b5e20d27552846462` |
| `test3.parts\part-0002.flv` | 6971897 | `d349d7d61c281f4aa7958544f444023182b917b383256ad071533d8c989bb78c` |
| `test3.parts\part-0003.flv` | 35868827 | `3b8dd379011e224c777fec0f61c8c490d300f2f4ea029576f1877515e5c69d2a` |
| `test3.parts\part-0004.flv` | 6473379 | `0488fb7b6383838d42aec569752c447a2d9329b98eb5ec89d13b4d4483bedba7` |
| `test3.parts\part-0005.flv` | 39084306 | `cb13ba061d76ac912b1f244073aa4629502c18a45cb5ceba2b72c8e0c634fdfe` |
| `test3.parts\part-0006.flv` | 4149793 | `b8bc75d223a8e9995dd1faa82607eaa67eadd3c1e103a7ad60db7b752f6bfdca` |
| `test3.parts\part-0007.flv` | 35659066 | `5decd84322ece11d6f0d8d5e4d1e49d079a80a4b927c01d5c42518271582b207` |
| `test3.parts\part-0008.flv` | 5032588 | `d4f334a0c99beeb0e3d981e0c6f85c161cbe4801eff0f764b1fefc707d0d01b9` |
| `test3.mp4` | 308311327 | `eacf4609f6c8866def5f78dde441e2725346aacb581fa3c187e2381a7f719abd` |
| `test4.parts\connections.jsonl` | 243 | `146b5761220556a1a3c150cbc61b2a4f747180ee48854645fe8790a5f4e691ae` |
| `test5.parts\connections.jsonl` | 411 | `5016816401d304974d5b80c017918e39dc5811da54f43bddefb220b5486e92df` |
| `test5.parts\part-0001.flv` | 96467947 | `f8b0b59efb21f19b6405af5cc39ad34dbf741204d7dea1c939456a7311ce7393` |
| `test5.mp4` | 96549633 | `a1f79926c850ceb970db08f4605f10caa7cb5fde76c87c2ac42876e7af663d88` |
| `test6.parts\connections.jsonl` | 812 | `cfdc8f40c066b6ee157d5119ff31e8e8d2a9a63676b609d6c39b36979c694602` |
| `test6.parts\part-0001.flv` | 5346055 | `1ad810400e883f072962d3636c58e778f526424617a185d8c97eb2e7abcc9b46` |
| `test6.mp4` | 5340203 | `7e954e14b0029ef2b07f31053fddc077e3d734e26b0b996687dd6f0584861045` |

## Local metadata evidence checksums

All files below are in the archive directory.

| File | SHA256 |
| --- | --- |
| `pre-move-inventory.json` | `116849eff280a6e9942dd3b2d99ebee1fc437c48177a33c5694418d80514dc37` |
| `post-move-verification.json` | `eba05bbd6d96a6b6b0ae3becd65f00bb70075a2d280303a7ecf694034ae42773` |
| `plan-after-segregation-age-unset.json` | `dae99ca987f04962c059aaa9468ce02371dc6d38d5022b8d034ad617128aec1c` |
| `post-segregation-root-diagnostic.json` | `36c84b3bb2c6c929407e963a5764b01d7c464784c627a14a6c4d68db90e3d479` |
| `service-after-segregation.json` | `80277fb266fe40d46dbcfe485795aec50668c50f6e8dfb5994f1998626b68c64` |

The unchanged configuration SHA256 is `02e4b5fe9fcb106d3c6b593ec7c596fc5e7eaa09976bbed33d0befc721ece507`.
