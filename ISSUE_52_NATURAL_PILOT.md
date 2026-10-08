# Issue #52 — authorized natural-pilot execution, 2026-10-08

**NATURAL PILOT FAIL — execution refused before LIVE; no product correctness verdict.** [Owner authorization 6062963351](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6062963351) followed [PM B3 acceptance 6062854485](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6062854485). This execution used GPT-6.1 Sol — High and the existing authorization without another permission/model gate. B3 and accepted R16–R19 foundations remain accepted.

| Authorized source | Resolution / start requests | Original UUID / room | Outcome |
| --- | --- | --- | --- |
| `https://www.tiktok.com/@slayyyboo22/live` | 0 / 0 | None | Not checked or recorded; availability unknown. |
| `https://www.tiktok.com/@vibecrewkrista/live` | 0 / 0 | None | Not checked or recorded; availability unknown. |

**Consumed allowance: zero of two starts; zero per creator.** The failed startup ended this trial under the instruction that a failed operation ends further admissions. No retry, substitute, resolver polling or new recording intent followed. Unused numerical allowance is not a recommendation to replay this ended trial. Next action is PM disposition; a future trial needs a fresh operational binding, not product changes or repeated B3.

## Exact execution binding

Launch HEAD **`5cda3b95d0e1e6f079effbc37c084f8255a07744`**, normalized package-source fingerprint **`ae5ade3d0390d7f0e1b5e20c856ec5257fda50f2d4847e829b39c24f52e1dfd7`**. Repository/root/import: `lvrdnck/TikREC`, `C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC`, its `tikrec\__init__.py`; branch/upstream `codex/capture-journal-handoff` / `origin/codex/capture-journal-handoff`; origin `https://github.com/lvrdnck/TikREC.git`. Common Git directory `C:\Users\Leandro\dev\TikREC\.git` was identified, not used as the execution checkout. Before pull: clean worktree and exact HEAD. Own-upstream `git pull --rebase --autostash`: already up to date.

Existing interpreter `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`: Windows CPython **3.11.15**, SQLite **3.53.1**; native base `C:\Users\Leandro\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none`. Source/import identity checks passed. Existing runbook FFmpeg/FFprobe **N-124716-g054dffd133-20260531** passed version/capability checks at their exact WinGet paths. SHA-256: FFmpeg `b241596c846107ef85fe5a6fb9c11146e256cbe193378c86788e0462b6ad1081`; FFprobe `171a9102fe291870ee4fa62e8a6814366e65247d692d5177cb2ca73567c2f3d5`. Launch preflight free space **49,866,194,944 bytes**, above 16 GiB. Loopback `127.0.0.1:18765` was free; no listener evicted.

Reserved new absent home: `C:\Users\Leandro\TikREC-tests\issue52-natural-20261008-151715\pilot-home`; catalog UUID **`cfe9c04d-b9f0-4f18-a435-cfec484b63ed`**. Neither home nor catalog was actually created. A fresh local secret was generated under an ACL restricted to the owner and SYSTEM; no production token/configuration discovery, token argument/environment or published secret. No authenticated endpoint became ready.

## Failure and lifetime evidence

Two preliminary **idle shells only** remained in a Windows Job and were not used to launch the pilot. A Windows WMI `Win32_Process.Create` console then supplied an independent persistent foreground PowerShell: **PID 45172**, created **2026-10-08T15:19:49.795375Z**, session 1, parent PID 49264. Native `IsProcessInJob` proved **false**, and it remained alive across tool returns. Its `-NoExit` console had no harness deadline or tool-parent teardown. These were execution-facility checks, not fixtures or source substitutions.

The actual `python -m tikrec.pilot` command was invoked from the specified checkout at **15:20:06.732288Z**. **Codex's external launcher generation was wrong:** a Python string interpreted `\f` in the PowerShell tool suffixes as **U+000C**. Consequently the generated command supplied malformed FFmpeg/FFprobe paths rather than the already checked binaries. `pilot_identity.local` / `check_tools` correctly refused before secret acquisition, preflight receipt or owner construction. Foreground receipt: `failure / pilot_startup_refused / JournalError`; actual command **exit 2 at 15:20:07.0843157Z**. This is an operator launcher error, not a regression in the accepted product or evidence of the known capture-refusal problem.

The controller subsequently delivered console input at **15:20:11.444266Z**, after exit: **the pilot never received a hidden-prompt secret**. This must not be counted as successful prompt/authentication evidence. The unused secret remains local; public report/foreground JSON contain none. No resolver call, RemoteClient start/status/stop, HTTP/native/SQLite runtime construction or raw/media write occurred.

**Smallest remedy:** on a separately scoped future execution, copy the runbook's literal PowerShell command or preserve its backslashes when generating the external launcher; verify the emitted argv before invoking it. No product source/test change, constant change, installation or additional acceptance review is warranted by this failure. No corrected relaunch was made under the ended trial.

All three empty console shells were retired through normal console interruption of their idle bootstrap where needed, then PowerShell `exit`; no product supervisor was interrupted or forcibly terminated. Task census at **15:21:16.8560086Z** reports **zero remaining task shell/Python/FFmpeg/FFprobe processes**. There is no shutdown `complete:true` receipt because runtime owners were never constructed; the startup exit is not being relabeled as normal runtime cleanup. The known incomplete-shutdown limitation was neither encountered nor resolved.

## Evidence and limits

Local evidence root **`C:\Users\Leandro\TikREC-tests\issue52-natural-20261008-151715`** preserves `preflight.json`, external launcher/controller, persistent-console identity, `foreground.jsonl`, `exit.json`, fsynced nonsecret `ledger.jsonl`, before/after frozen manifests and `process-retirement.json`. **513 source/test/script/metadata files match before/after**; canonical manifest SHA-256 **`6df8cb6aeda5f3f536619d42b8faa21d5515e38fb254c72cbb26e4f9a8bea4f5`**. All package source and tests are unchanged. Local evidence hashes/native identities are recorded separately in `evidence-manifest.json`; secrets are excluded from publication.

No capture or capture/finalization overlap exists. No original UUID, room, raw/arrival/connection evidence, H seal, final MP4, returned capture capacity or deep validation exists. Both sources' LIVE availability remains **unknown**, not offline. No input/output validity conclusion can be drawn. No offline suite was rerun to fill this empirical gap. Every runbook limit remained unchanged and no real volume was filled.

Later task commits contain **documentation only**, and are distinct from the attempted exact launch HEAD above. Their checkout HEAD does not silently replace the authorization's launch revision. No existing recorder/service/Scheduled Task, production configuration/credentials/media, #48 polling, retention/deletion, migration, upgrade, merge, release change or #52 closure. Published storage-only **v0.11.0 remains untouched**. Stop for PM; no automatic successor.
