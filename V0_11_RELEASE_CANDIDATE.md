# v0.11.0 storage release candidate — verification (2026-10-08)

**READY FOR PM PUBLICATION REVIEW.** No concrete preparation blocker was demonstrated. This is not publication/deployment approval. Exact historical base: `ebf501c4153d104921ff63e69f4cfe0f262d713e`; branch `codex/v0.11-storage-release`. The exact final normally pushed candidate commit is recorded in #52's release checkpoint. No tag, release, merge or registry upload occurs here.

Authority: [complete PM decision 6058707202](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6058707202). Storage preparation is the sole active task; #52/#48 remain OPEN/PAUSED. Complex / GPT-6.1 Sol — High gate and owner PROCEED recorded; owner implementation decisions None. This continuation retains history and is not a new independent #52 acceptance conversation; B3 remains outstanding and no #52 review is repeated.

## Scope and provenance

Verified new worktree `C:\Users\Leandro\.codex\worktrees\v0.11-storage-release\TikREC`, branch above, origin `https://github.com/lvrdnck/TikREC.git`, common Git directory `C:\Users\Leandro\dev\TikREC\.git`. Branch/path collisions were absent before creation. Initial non-destructive upstream pull in the audited #52 worktree was already current; the deliberate historical release branch was then created at the exact base, not pulled from main. Primary checkout's existing untracked test directories were preserved; no source/configuration/environment/service/media from the newer installation was used.

Published v0.10.0 peeled commit `dfb81b683a89d01f55d70291fb5cdcfead654976` is an ancestor of this base. Its immutable annotated tag object remains `014fa0b785f77c6b42ffe73a86ba28b00126a4ff`; the existing GitHub Release remains published/non-draft/non-prerelease. Only this candidate package becomes **0.11.0**. Version metadata in `pyproject.toml` remains dynamically sourced from `tikrec.__version__`, with Python >=3.11, no runtime dependencies and `tikrec = tikrec.cli:main`.

The published-to-base delta is 108 files / 14,004 insertions / 418 deletions, including **49 product-source files**. [Release notes](RELEASE_NOTES_v0.11.0.md) describe storage health/admission, conservative retention planning, creator protection, exact-confirmation local deletion, audit/result safety and accepted identity/lifecycle/recovery fixes. Linux detour commits are retained historically but their runtime additions were reverted before this base; Windows-only support and POSIX destructive refusal apply.

Preparation changes from the exact base: `tikrec/__init__.py` version only; exactly two literal version assertions in `tests/test_capture.py`/`tests/test_manifest.py`; scoped README/SPEC/SERVICE/RETENTION_CLI/AGENTS/PROJECT_STATE/ROADMAP and two release documents. No packaging correction or dependency addition was needed. Every other product/test/script file and `pyproject.toml` is unchanged. No #30/#48/#52 source is imported, removed from the accepted base or cherry-picked. The unchanged #51 report is reused, not relabelled as new real-media execution.

## Actual validation

Existing native interpreter: `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`; base uv CPython **3.11.15 / Windows AMD64**, SQLite **3.53.1**, pytest **9.1.1**, pip **24.0**, setuptools **79.0.1**. Each selection records actual cwd/Git/base/import/version, exact commands/PIDs, isolated environment paths and before/after hashes. Actual source import is this release worktree. APPDATA/LOCALAPPDATA/XDG config/state/TMP/TEMP are new disposable directories under `C:\Users\Leandro\TikREC-tests\v0.11-storage-release-20261008`; inherited TIKREC_TOKEN is removed. Existing ffmpeg/ffprobe/tooling are not upgraded. Tests use only generated disposable fixtures, including deletion fixtures; no user-media retention or LIVE/production validation occurs.

| Check | Actual result |
| --- | --- |
| Focused package-version and emitted-manifest assertions | 2 passed. |
| One complete isolated Windows offline suite (`tests`, `-vv -ra`, no cache provider, disposable basetemp) | **1,731 passed / 7 skipped / 19 subtests passed; 79.76 s pytest (80.41 s launcher)**. No failures. |
| Compilation / whitespace diff | `compileall` on package/tests/scripts and `git diff --check` passed. |
| Source CLI | 30 root/subcommand help paths and version passed through the existing `tikrec.cli` entry module; version `tikrec 0.11.0`. |
| Local wheel | Built with existing pip/setuptools, `--no-index --no-deps --no-build-isolation`. All 105 package-module names/bytes match the candidate; METADATA, entry_points and every wheel RECORD digest/size verified. No later isolated journal/runtime/HTTP/automatic-raw module exists. |
| Isolated installed-wheel smoke | New `venv --without-pip`; existing pip targets only that disposable interpreter, installs the local wheel with no dependencies/index/compile. Distribution/import/version/entrypoint and all 105 installed module hashes match. Actual installed executable version plus root/serve/retention-delete/remote-status/monitor help pass. |
| Compatibility/defaults smoke | Installed defaults have no saved config/monitors, reserve 10 GiB, age disabled. Later `automatic_raw_copy_creators` config is refused with exit 1. Remote status has no UUID option; monitor has no automatic raw-copy command. Neither service launch nor deletion is invoked by smoke. |

Seven skips: unavailable symlink privilege (policy lock and retention plan), native POSIX delete/preview refusal and Linux path semantics, plus two open-file replacement cases unsupported on Windows. Windows native safety tests run in the complete suite; skips are preserved and do not assert validation on another platform.

**223 package/test/script/metadata hashes** are identical before/after and across focused, full, final CLI/compile and wheel-smoke selections. Raw full-manifest SHA-256: `aff145ad9f461567a8607f9a776ffb41f8f1ee9b4f3429e57eb689944fe0eca2`. Final documentation adds actual results only; frozen executable/test bytes remain unchanged through commit. Test provenance HEAD is the exact base while those three reviewed version-only files are working changes; final commit comparison binds these frozen bytes to the pushed candidate. No full-suite repeat was needed after results/coordination-only documentation.

Preserved harness corrections, not product failures: first source help invocation used unsupported `python -m tikrec` (no `__main__` in the historical package); corrected to existing `python -m tikrec.cli`. The successful first wheel build's metadata verifier initially assumed LF-only headers; Windows CRLF was valid. Corrected header parsing and verified/installed the **same** successful wheel rather than rebuilding/replacing it. Original logs/manifests remain in `checks` and `wheel`; final results are in `checks-final` and `wheel-smoke`.

## Artifact and installed identity

- Wheel: `C:\Users\Leandro\TikREC-tests\v0.11-storage-release-20261008\wheel\artifacts\tikrec-0.11.0-py3-none-any.whl`
- SHA-256: **`7cf87363cde6ce9817b79c4c7eb86fe37a3e77bcf564cde91019aadec7e902ca`**
- Size: **207,542 bytes**; `tikrec-0.11.0-py3-none-any.whl`.
- Installed interpreter: `C:\Users\Leandro\TikREC-tests\v0.11-storage-release-20261008\wheel-smoke\installed-env\Scripts\python.exe`
- Installed import: `C:\Users\Leandro\TikREC-tests\v0.11-storage-release-20261008\wheel-smoke\installed-env\Lib\site-packages\tikrec\__init__.py`
- Installed console entry: `C:\Users\Leandro\TikREC-tests\v0.11-storage-release-20261008\wheel-smoke\installed-env\Scripts\tikrec.exe`; `tikrec = tikrec.cli:main`.
- Evidence: full logs, selections, provenance, source/test hashes, artifact/installed identity and exact commands under `C:\Users\Leandro\TikREC-tests\v0.11-storage-release-20261008`. Artifact is local only, not uploaded to a registry/release or committed as source. Task-path process census finds no surviving Python/ffmpeg/ffprobe process after checks.

## Accepted evidence and remaining limits

[#51 report](ISSUE_51_RETENTION_VALIDATION.md) already records the accepted independent public CLI review and one native Windows real-media deletion (COMPLETE/0, 12 audit events, five intended paths removed, 753 unrelated entries unchanged), followed by reconciliation of the unrelated Gracie move. Storage/retention behavior is byte-identical to that accepted base. Its real-media authorization remains consumed; #51 stays closed and no fresh user-media validation/deletion is claimed. Fixed-drive NTFS/cooperative-filesystem and power-loss limits remain.

The package is a historical feature set, not a replacement for the owner's newer development installation. Strict newer-config refusal, unsupported #52 state, restart-selected creator configuration, two slots occupied through finalization and admission-only disk checks are documented in the release notes. #52 pilot gates B1/B2/B3 remain paused; #48 natural evidence and #28 attribution remain unresolved, outside this release. No production access/change/restart, LIVE, migration, upgrades, later-feature cherry-picks, destructive user-media action, main merge, force-push, tag, GitHub Release or registry publication occurred.

**Next action: PM review the exact pushed storage candidate and these scoped release notes for separately authorized publication.** No feature successor or publication starts automatically. Refs #52; all existing history and the flagged earlier closure message remain untouched.
