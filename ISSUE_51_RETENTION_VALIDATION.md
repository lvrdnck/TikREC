# Issue #51 real-media retention validation evidence

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
