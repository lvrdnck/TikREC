# v0.11.0 publication — execution and verified identity (2026-10-08)

**COMPLETE / VERIFIED.** Owner [authorization 6059131758](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6059131758) was executed for exactly `2fe6354aa508d53ce3a3452ce08743d97400fe73`, following [PM candidate acceptance](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6059047079). No new gate, permission request, acceptance review or feature task was started.

| Published identity | Verified value |
| --- | --- |
| Release | [TikREC v0.11.0](https://github.com/lvrdnck/TikREC/releases/tag/v0.11.0) |
| Release ID / node | `406770680` / `RE_kwDOUTgsvs4YPtP4` |
| Flags / time | non-draft, non-prerelease; published `2026-10-08T11:50:27Z` |
| Annotated tag object | `ef8c5215712d454855a033700116bdc8fc0906a3`; remote ref/object type `tag` verified |
| Peeled tag commit | `2fe6354aa508d53ce3a3452ce08743d97400fe73` — exact approved candidate |
| Wheel | [tikrec-0.11.0-py3-none-any.whl](https://github.com/lvrdnck/TikREC/releases/download/v0.11.0/tikrec-0.11.0-py3-none-any.whl) |
| Asset ID / size | `621682513` / **207,542 bytes** |
| SHA-256 | **`7cf87363cde6ce9817b79c4c7eb86fe37a3e77bcf564cde91019aadec7e902ca`** |

Before writes: verified release worktree/root/branch/origin/common Git directory, clean reviewed HEAD, own-release upstream already current, current coordination/owner authorization and absent local/remote tag/Release. Original wheel's exact size/hash, all 105 module bytes against the candidate, METADATA/entrypoint/RECORD and all 223 frozen executable/test/script/metadata files were verified. No rebuild/substitution or package installation occurred.

Created and normally pushed one annotated tag at the approved SHA. Created one non-prerelease draft with the reviewed storage notes converted to publication wording, uploaded the original wheel without clobber, downloaded/verified its bytes, then published non-draft/non-prerelease and marked latest. Rechecked remote annotated object and peel, final flags/body/asset ID/size/digest, and downloaded the published asset again. Both downloads match the approved original exactly. Draft-only temporary `untagged-*` URLs are preserved in the execution ledger; the published URLs above were taken from the final REST object.

The initial notes verifier paused after draft creation because it compared Windows CRLF against LF; line-normalized text was identical, not a content conflict. No artifact had been uploaded at that pause. Resumed the same matching annotated tag and draft after inspecting their state, preserving the first-attempt log; no replacement/deletion/rebuild occurred. Numeric REST Release ID is distinct from `gh view`'s GraphQL node ID.

Execution evidence: `C:\Users\Leandro\TikREC-tests\v0.11-publication-20261008`: original-wheel proof, complete command ledger, first-attempt progress/draft snapshot, remote annotated-tag/ref object, final Release object, publication progress and exact downloads:

- Draft download: `C:\Users\Leandro\TikREC-tests\v0.11-publication-20261008\download-draft\tikrec-0.11.0-py3-none-any.whl`.
- Published download: `C:\Users\Leandro\TikREC-tests\v0.11-publication-20261008\download-published\tikrec-0.11.0-py3-none-any.whl`.
- Original approved wheel: `C:\Users\Leandro\TikREC-tests\v0.11-storage-release-20261008\wheel\artifacts\tikrec-0.11.0-py3-none-any.whl`.

Accepted candidate tests are reused without rerun: 1,731 Windows passes / 7 skips / 19 subtests, two focused version checks, compile/diff/30 CLI help paths, wheel build/install smoke and 223 frozen hashes. [Historical candidate evidence](https://github.com/lvrdnck/TikREC/blob/2fe6354aa508d53ce3a3452ce08743d97400fe73/V0_11_RELEASE_CANDIDATE.md) and accepted #51 real-media report retain their limits and dates; no new full suite, LIVE or user-media deletion is claimed. #51's one deletion authorization remains consumed.

Current published/package/tagged release is v0.11.0 for the approved historical storage scope. The untouched #52 branch still advertises package 0.10.0 and includes later experimental source; that difference is explicit, not a reason to bump/install it. The actual running development installation was not inspected/changed. v0.10.0's historical annotated tag and release remain unchanged. No main merge, executable change, install, service/recorder restart, configuration/state migration, user-media deletion, upgrade, PyPI upload or #52 activation.

Documentation-only bookkeeping on `codex/v0.11-storage-release` and `codex/capture-journal-handoff` follows verification and uses Refs #52. Exact bookkeeping commits are recorded in #52's final publication checkpoint; immutable tag remains on the earlier approved candidate. Both executable/test hash sets remain unchanged (223 release files, 493 #52 files). Normal vault journal updated at task completion. #52/#48 OPEN/PAUSED; #51 CLOSED/PASSED; #28 unresolved. No task/successor selected automatically; stop after bookkeeping.
