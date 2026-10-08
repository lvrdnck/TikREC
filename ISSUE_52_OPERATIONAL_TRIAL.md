# Issue #52 — supervised operational-service trial, 2026-10-09

**PARTIAL evidence; operational controls and retirement PASS. Stop for PM disposition.** Owner selected only `https://www.tiktok.com/@example.creator/live` and authorized [the complete 30-minute PM decision](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6070585346). This run is a fresh-home real operational trial of the accepted normal `serve --journal-home` mode. No pilot launcher, historical review/suite/validator repeat, source change, installation or everyday recorder change occurred in this execution.

## Coordination conflict discovered during closeout

While this supervisor was running, another execution committed/pushed `e8f85c17a2cd8fe03c54568e913c1411317f5f0c` at 2026-10-08T23:24:54Z and [reported a different isolated trial](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6071037143). That record describes eight parts/seven raw connections in `operational-live-20261008T225418Z-1131e139`; this run has five parts/four raw connections in its own root below. At this launch, GitHub/worktree were clean at 7458a5ed with no durable active-trial record discovered; the concurrent documentation change was detected only after this run retired, when a guarded closeout update refused its stale R20 heading. The owner authorized a single trial, so these two execution records are a coordination conflict, not permission for a second trial. Both original records/media are preserved separately. This task did not open the other home or access existing watchers/Scheduled Tasks, and cannot corroborate its process/inventory claims. No further trial is started; PM must reconcile both records and their authority/coverage limits.

Tracked creator names use `example.creator` as a privacy alias, matching the concurrent report. Actual selected identity, evidence-root path and exact argv remain in the private local config/receipts. `<PRIVATE_TRIAL_ROOT>` is a redaction placeholder, not an existing path. Equivalent creator-control examples below use that alias and are not commands to launch another trial.

## Executable and prospective identity

Accepted executable/test commit **`aefeebe597933b963e24c641cd3dca317f5db539`**; actual launch checkout HEAD **`7458a5edf9582a80ee5a8af8e33f00037114d52e`**, branch `codex/capture-journal-handoff`, origin `https://github.com/lvrdnck/TikREC.git`, worktree `C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC`. Before reading/editing project files, verified clean worktree/own upstream; `git pull --rebase --autostash` was already up to date. All **536** source/test/packaging files match accepted Git bytes after CRLF normalization; raw hashes match before/after execution. Package fingerprint remains **`6a92803377040eb8ce8553b3f90c8ceaf437883c37d25776600e890215d70151`**. Later delivery commits change documentation only.

Actual imported `tikrec/operational_identity.py` was in that checkout. Startup receipt records native **PID 65844**, wrapper/parent **40244**, Python **3.11.15**, SQLite **3.53.1**, exact source/config/tool hashes. Existing Python: `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`. Existing media tools: the WinGet `ffmpeg-N-124716-g054dffd133-win64-gpl\bin` paths below; both version **N-124716-g054dffd133-20260531**. FFmpeg SHA-256 **`b241596c846107ef85fe5a6fb9c11146e256cbe193378c86788e0462b6ad1081`**; FFprobe **`171a9102fe291870ee4fa62e8a6814366e65247d692d5177cb2ca73567c2f3d5`**. Tool usability/libx264/AAC encode and H.264/AAC decode checks actually ran before state initialization and again at known reopen. Nothing was installed/upgraded.

Prospective evidence root: **`<PRIVATE_TRIAL_ROOT>`**. Separate new home/config/token/catalog **`7e56c7c7-c98e-44ed-b4ee-098207fe823d`**; listener selected unused loopback **49155**. High-entropy token stayed in its local file and is not logged/committed. Isolated APPDATA/LOCALAPPDATA/config/state/temp and explicit PYTHONPATH were recorded before launch. Supported persistent `serve.stdout` / `serve.stderr` handles stayed open through actual exit. Observer retained the Popen wrapper handle and the original native process handle with creation FILETIME; no timeout/finally-kill path.

## Actual commands and operating policy

The paths identify this completed home; **do not launch it again or start another trial without PM/owner disposition**. Init was run once (exit 0, no monitoring), followed by known-state reopen of exactly the same catalog. Saved `launch.json`, `observer.jsonl` and product receipts preserve exact argv/PIDs/results:

```powershell
$checkout = 'C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC'
$python = 'C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe'
$trial = '<PRIVATE_TRIAL_ROOT>'
$tools = 'C:\Users\Leandro\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-124716-g054dffd133-win64-gpl\bin'
$argsJournal = @('--config', "$trial\config.json", 'serve',
  '--journal-home', "$trial\home", '--journal-catalog-id', '7e56c7c7-c98e-44ed-b4ee-098207fe823d',
  '--token-file', "$trial\token.txt", '--host', '127.0.0.1', '--port', '49155',
  '--ffmpeg', "$tools\ffmpeg.EXE", '--ffprobe', "$tools\ffprobe.EXE")
Set-Location -LiteralPath $checkout
& $python -m tikrec.cli @argsJournal --journal-init
& $python -m tikrec.cli @argsJournal
# At 20 minutes: actual normal explicit-config command, exit 0.
& $python -m tikrec.cli --config "$trial\config.json" monitor remove example.creator
# After confirmed empty-list reload: one cooperative original-UUID HTTP stop.
& $python -m tikrec.cli remote stop --server 'http://127.0.0.1:49155' --token-file "$trial\token.txt" --session-id 'dce63e94-3575-4a58-8edc-437fea917ad7'
# End of window: actual fresh local nonce, atomically installed in original home.
$control = @{operation=[guid]::NewGuid().ToString();command='shutdown'} | ConvertTo-Json -Compress
$control | Set-Content -LiteralPath "$trial\home\control.new" -Encoding utf8
Move-Item -LiteralPath "$trial\home\control.new" -Destination "$trial\home\control.json" -Force
```

The observer sent the actual stop through the accepted `RemoteClient.stop(UUID)` route; the CLI line shows its normal equivalent, not a second invocation. Actual shutdown nonce and request/ack are in `observer.jsonl`/`control.json`. No manual recording start, acknowledgement resend, replacement UUID, other creator, source-access bypass, blind cleanup retry, manual finalization or forced exit occurred.

Initial config: schema 1, output exactly HOME/media, only `example.creator` monitored and raw-enabled, reserve **10 GiB**, retention age absent. Raw preference remains in the isolated config after normal creator removal; no creator is monitored. Two captures/one finalizer/eight outstanding units, normal 30-second monitoring, room suppression, retry, source bounds and accepted continuous headroom policy stayed unchanged. Admission 14 GiB, finalizer 12 GiB +16 MiB, capture floor 10.5 GiB; actual physical free space began about 34.24 GiB and minimum was **31.208 GiB**. No low-space/unavailable state was observed or injected; this trial proves normal observations, not pressure behavior or a hard disk quota. [Full policy](ISSUE_52_OPERATIONAL_SERVICE.md#continuous-operating-policy).

## Actual timeline and result

Times below are UTC (local Europe/Brussels date 2026-10-09, UTC+02:00). Window anchored to real service process creation, not an accelerated clock.

| Event | Actual evidence |
| --- | --- |
| Service launch | 2026-10-08T23:02:04.005Z; 30-minute window, planned creator removal at +1,200 s |
| Automatic accepted recording | Original **`dce63e94-3575-4a58-8edc-437fea917ad7`**, room **`7694424332172315406`**, raw enabled; no manual start |
| Normal creator removal | 2026-10-08T23:22:09.502Z; +1205.047 s, CLI exit 0 |
| Empty creator reload / original stop | 2026-10-08T23:22:25.188Z; +1221.016 s; one exact-UUID stop acknowledgement |
| Capture closed/H/finalizer | Durable original H/seal/queue facts; observed closed capture/running finalizer with output completion false. Five-second sampling did not capture the brief queued projection. |
| Output completed | Saved UUID status becomes completed/output_completed=true; outstanding units return to zero |
| Owned shutdown initiated | 2026-10-08T23:32:04.473Z; +1800.282 s |
| Actual exit confirmed | Observer confirmation 2026-10-08T23:32:09.607Z; +1805.594 s, original native handle wait=0/exit=0; wrapper exit 0. Product exit receipt 2026-10-08T23:32:04.562Z. |

Manifest: **1217.410649 seconds wall-clock capture**, interrupted by authorized cooperative stop, **four connections / three reconnects / five parts**. Raw files total **116,521,139 bytes**; retained FLVs **116,495,895 bytes**. **175,972** byte-arrival records cover each raw file contiguously through exact EOF, with hashes unchanged. Per-connection HTTP byte counters reset on reconnect and are not reported as cumulative session bytes. Real recording exceeded the old pilot's 120-second/64-MiB limits and service exceeded its 900-second lifetime; no finite-pilot budget was substituted.

The retained connection records contain a normal first closure, two `IncompleteRead` failures handled by existing same-owner retry, and the intentional final interruption. Source geometry changed **720×1280 → 640×1280 → 720×1280**. First-part timestamps include roughly 1.92–2-second backwards replays; warnings remain evidence. Accepted normalization/finalization completed, with **clean recorded finalization-input decode** (zero/capped-false diagnostics), without claiming complete upstream LIVE coverage.

Actual MP4: **1043.889000 seconds (17m23.889s)**, **109396856 bytes**, H.264/AAC, **720×1280**. Its media duration is shorter than wall-clock capture. Reconnects, source clocks/replays and configuration boundaries are retained; no full-stream/continuous-timeline, visually correct, multi-day or unattended guarantee is inferred.

## Read-only media and retirement verification

Actual accepted CLI `validate NEW_PARTS --deep --json` and `validate NEW_MP4 --deep --json` both exited **0**. Session: five parts checked, retained media checks/inspection/final decode/media integrity **passed**; `session_completeness=interrupted`, six `part_dts_warning` findings retained. MP4: inspection/decode/media integrity **passed**, no findings. Session reports recorded input decode **clean**; standalone output has no input-manifest context and reports **unknown**. Visual integrity **not_checked**. All **18 recording artifact SHA-256 hashes unchanged** before/after; standalone FFprobe inspection exited 0. Exact launch/stdout/stderr/exit records are prospective. No historical pilot validator or review/test suite was repeated.

Product shutdown receipt: **complete=true**, captures/finalizer/requests/monitor joined, authority released. Original **PID 65844** native handle was acquired prospectively and retained until signalled; actual `GetExitCodeProcess` returned **0**, wrapper Popen wait returned **0**. Listener then refuses connection. These facts are checked together, rather than using disappearance as proof. No incomplete cleanup or cleanup retry was needed.

After confirmed exit, immutable read-only SQLite inspection (`mode=ro&immutable=1`) preserves catalog SHA-256 and passes integrity check. **One completed session/task**, durable automatic acceptance and original H/seal/release preparation/cleanup/results, **zero units**, both original capture bindings free. **9** original durable native-child records retain actual exit and cleanup proof; no held unfinished work is labelled complete. Home/media/control/catalog/log hashes are retained locally. All **536** frozen executable/test/packaging hashes remain unchanged.

Evidence index: `evidence-index.json` references `launch.json`, accepted PM/issue snapshot, before/after 536 hashes, initialized marker, native identity/creation-time handle, **349** prospective five-second HTTP/filesize/free-space snapshots, automatic receipt/UUID phases, removal/reload/stop, actual local shutdown, process exit, immutable catalog, raw-arrival checks, two new deep validations/probe and 18 before/after artifact hashes. The first preflight helper omitted nested test files and failed its count assertion before config/home initialization or launch; recursive enumeration then verified all 536 accepted files. No service was launched by that failed check, and no runtime intervention occurred.

## Remaining disposition and boundaries

This execution is retired and its evidence closeout is complete; **stop for PM review of the actual trial evidence**. R20/engineering acceptance and restricted overlap remain accepted; #52 OPEN, #48 PAUSED, #51/published storage-only v0.11.0 complete, #28 unresolved. No installation, migration, legacy import, source/home upgrade, shared-root retention, broader unfinished-native recovery, automatic restart, everyday cutover, main/release change or closure. In this execution, existing watchers, Scheduled Tasks, configuration and recordings were not accessed or changed; no production restart/access or user-media mutation. Only the new authorized trial files were written and preserved.

Remaining limits: concurrent execution coordination/authority requires PM disposition; intentionally interrupted sample and shorter normalized media duration; source/reconnect/timestamp continuity and visual integrity not established; sustained storage-pressure/load/soak and multi-day availability unmeasured. Unsupported unsealed native/SQLite cleanup still requires retaining the original supervisor; this healthy shutdown does not broaden recovery. Further rollout/source trials require separate disposition; do not start another automatically. Schema 10, media/storage policy, ordinary serve defaults and restricted pilot remain unchanged. Refs #52.
