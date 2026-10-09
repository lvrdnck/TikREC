# Issue #52 — post-correction supervised operational trial, 2026-10-09

**Allocation CONSUMED/CLOSED; execution retired, evidence PARTIAL because actual headroom decline shortened the window.** New media, original UUID controls, final accounting and owned retirement checks pass. The planned 20-minute capture/30-minute operating envelope was not completed. Stop for PM disposition; no second trial or rollout follows.

## Authorization and executable

The owner supplied one public creator directly to the designated `path-check-20261009-a490` executor under [complete PM decision 6080216581](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6080216581). The shared allocation **`post-path-check-operational-1`** was checked across all #52 comments: only the PM proposal existed. [Prelaunch consumption checkpoint 6080319199](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6080319199) was posted/read back before config/home initialization or launch. Sole run **`post-path-check-20261009-cdc14ac0`**, catalog **`d32d68ea-932c-458f-b224-24da22f9a0fd`**, intended absent-home identity SHA-256 **`12f5f5e1726d68b6c882fcb1f5da2a7625014f5fb6f2d33f89c3644108335e97`**. This is procedural coordination, not an atomic lock. No parallel executor, replacement creator, manual start or second allowance was used.

Verified exact worktree `C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC`, branch `codex/capture-journal-handoff`, origin `https://github.com/lvrdnck/TikREC.git`, clean HEAD/own upstream **`a320aeec1ce399d485ebaf62bd44a3074953c8cb`**; `git pull --rebase --autostash` was up to date. Accepted executable/test candidate **`e78db2da7feb03411f20f54a4b4ad468e590360e`**. All **537** frozen source/test/packaging raw hashes match before and after execution. Actual imported `tikrec/operational_identity.py` and startup revision belong to this checkout; normalized 219-module fingerprint **`9da7cc3c5c9358abcb3b127c3a30d0755decd6c0c892eb775133c85d7aeaf8ad`**. This delivery changes documentation only.

Only normal headless **`serve --journal-home`** ran. Fresh explicit schema-1 config, absent native dedicated home, catalog, token file and isolated APPDATA/LOCALAPPDATA/temp/config/state paths; only the owner-selected creator monitored/raw-enabled. Private identity/path mapping is saved in `preflight.json`, `config-before.json`, actual argv and receipts. Public examples use `trial.creator` and `<PRIVATE_TRIAL_ROOT>` as redactions; the latter is not a real path. Signed URLs, token and media remain local and are not uploaded or committed. No new MODEL GATE/PROCEED was requested for this execution-only authorization.

Python launcher `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`; actual main native Python image is the existing UV CPython executable. Startup records Python **3.11.15**, SQLite **3.53.1**, native supervisor **PID 26676 / creation FILETIME 134360205467265210**, wrapper **PID 55112 / FILETIME 134360205466948816**. Original SYNCHRONIZE/QUERY_LIMITED_INFORMATION handles were acquired prospectively and retained through actual exit. Listener bound unused loopback **127.0.0.1:63622**. Existing checked FFmpeg/FFprobe version **N-124716-g054dffd133-20260531**, hashes respectively **`b241596c846107ef85fe5a6fb9c11146e256cbe193378c86788e0462b6ad1081`** and **`171a9102fe291870ee4fa62e8a6814366e65247d692d5177cb2ca73567c2f3d5`**. Normal init/reopen tool checks ran; nothing installed or upgraded.

## Actual commands and storage policy

These are historical equivalents of saved launch/control records, not permission to replay this consumed allocation. Exact private argv and selected creator are in the local evidence.

```powershell
$checkout = 'C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC'
$python = 'C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe'
$trial = '<PRIVATE_TRIAL_ROOT>' # privacy alias, not an existing path
$tools = 'C:\Users\Leandro\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-124716-g054dffd133-win64-gpl\bin'
$argsJournal = @('--config', "$trial\config.json", 'serve',
  '--journal-home', "$trial\home", '--journal-catalog-id', 'd32d68ea-932c-458f-b224-24da22f9a0fd',
  '--token-file', "$trial\token.txt", '--host', '127.0.0.1', '--port', '0',
  '--ffmpeg', "$tools\ffmpeg.EXE", '--ffprobe', "$tools\ffprobe.EXE")
Set-Location -LiteralPath $checkout
& $python -m tikrec.cli @argsJournal --journal-init # once only, actual exit 0
& $python -m tikrec.cli @argsJournal
# Earlier safety disposition, through normal explicit-config CLI:
& $python -m tikrec.cli --config "$trial\config.json" monitor remove trial.creator
# After confirmed empty creator reload, one actual RemoteClient.stop(UUID):
& $python -m tikrec.cli remote stop --server 'http://127.0.0.1:63622' --token-file "$trial\token.txt" --session-id '7211f34d-0a75-450f-b70b-bc1e3a8477b0'
# Equivalent only; the CLI stop above was not sent again.
$control = @{operation=[guid]::NewGuid().ToString();command='shutdown'} | ConvertTo-Json -Compress
$control | Set-Content -LiteralPath "$trial\home\control.new" -Encoding utf8
Move-Item -LiteralPath "$trial\home\control.new" -Destination "$trial\home\control.json" -Force
```

Reserve **10 GiB**, admission **14 GiB**, finalization **12 GiB +16 MiB**, capture cutoff **10.5 GiB**, fresh disk queries/native pins, dynamic writer budget, two captures/one finalizer/eight outstanding units and ordinary 30-second monitor/room/confirmation/retry policy were unchanged. Retention age absent. Only creator removal reloaded; the raw preference remains in this trial's config with no monitored creators.

Physical free space was **18.947 GiB** at preflight, **17.508 GiB** at first service snapshot and minimum **12.613 GiB** during 98 five-second snapshots. Actual admission refusal `low_free_space` first appears at **12:01:59Z**. At **12:03:08Z**, the operator ended the capture phase early because of this observed refusal and rapid decline, before exhausting finalization headroom; the PM decision gives earlier safety conditions priority. This was an operator safety disposition through supported controls, not a product capture-floor stop or injected disk-pressure test. New admissions were already fenced by policy; the creator was then removed and reload confirmed. No reserve was lowered, storage filled deliberately, old media removed or queued unit refunded. The cause of unrelated volume occupancy was not investigated; the measured free-space drop substantially exceeds this new trial's retained files, so it must not be attributed solely to capture. No existing watcher/task access occurred.

## Prospective timeline and actual result

UTC; real monotonic deadlines, no accelerated clock. Planned capture/operating maxima were 1,200/1,800 seconds from launch; actual safety disposition ended earlier.

| Event | Observed evidence |
| --- | --- |
| Init, then normal service launch intent | 11:55:45.254 / **11:55:46.693**; fresh init receipt/exit 0 |
| Product startup/ready | **11:55:47.776 / 11:55:47.790**; actual import/tools/config/catalog/PID/port |
| Automatic acceptance observed | **11:55:53.001**; original UUID **`7211f34d-0a75-450f-b70b-bc1e3a8477b0`**, raw true; capture manifest starts 11:55:52.728 |
| Normal creator removal | **12:03:09.139**, CLI wrapper exit 0 |
| Empty reload / original UUID stop ack | **12:03:11.226 / 12:03:11.331**; no resent stop/start |
| Capture closure/H/finalization | Manifest ends **12:03:11.337**; closed/running finalizer observed, durable original H exists |
| Completed output/accounting observed | **12:04:11.639**; output completed, zero units, both slots free |
| Fresh local shutdown installed | **12:04:11.642**; actual nonce saved |
| Product shutdown/exit receipts | **12:04:11.679 / 12:04:11.682**, complete=true / exit 0 |
| Actual native / wrapper confirmation | **12:04:12.643 / 12:04:13.889**; original retained handles signalled, native and wrapper exit 0 |

Capture **438.608500 s (7m18.609s)**, intentionally interrupted; **one connection, zero reconnects, two parts**, source geometry **720×1280 → 640×1280** within that connection. The reset progress counter was a part boundary, not a reconnect; connection evidence is authoritative. Raw **58,731,117 bytes** with **10,560** contiguous byte-arrival records through exact EOF; no trailing incomplete FLV tag. Every complete raw media occurrence (**9,524 video +10,363 audio =19,887**) matches retained payload/hash/order/rebased timestamp, with **zero omitted complete media tags**. The existing accepted finalizer normalizes the differing configurations; no manual remux/repair or media change was made.

MP4 **442.297667 s (7m22.298s)**, **92,591,989 bytes**, H.264/AAC **720×1280**, **9,524** video frames reported by FFprobe. MP4 is **3.689167 s longer** than capture wall time; this is not a loss metric. Deep decoding and frame-count agreement support this output, not complete upstream LIVE coverage or visual correctness.

## Arrival/source clocks and limits

Read-only derived analysis outside the home joins each complete FLV tag's last byte to its saved raw-copy-write arrival record. For each connection/stream and each backwards-clock segment, relative drift is `(arrival monotonic − first arrival) − (source DTS − first DTS)/1000`. Initial transport/source buffering, read fragmentation and source-clock uncertainty remain; this is not absolute network latency or exclusive receiver cost. Video/audio observations are separate and not added as independent missing intervals.

This single connection has **no video/audio DTS backsteps** and no within-stream media arrival gaps ≥1 s. Video: arrival span **437.687 s**, source span **442.186 s**, final relative drift **−4.499 s**, fitted slope **−0.001779 s/s**. Audio: **437.812 /442.192 s**, final **−4.380 s**, slope **−0.002037 s/s**. Thirty-second median drift initially catches up to roughly −3.8/−3.9 s, then settles around **−4.4 s** after the part/configuration boundary. The last ten video bins range approximately −4.457 to −4.422 s. No progressively increasing positive arrival-versus-source drift was observed in this **shorter** sample. The early burst/boundary offset does not prove a specific buffering cause.

All received complete raw media was retained, and final video frame count equals retained video-tag count. This does not prove missing upstream content never occurred before raw arrival, individual encoded picture identity, complete source audio continuity, 20-minute sustained ingestion, reconnection performance, concurrent capture or multi-day/unattended operation. This creator/room and earlier trials are not a controlled before/after comparison. Accepted loopback performance/continuity/overlap/R20 verdicts retain their previous scope; no historical analysis or validator was repeated.

## New validation, accounting and evidence limits

After complete original-owner retirement, actual `validate NEW_PARTS --deep --json` and `validate NEW_MP4 --deep --json` both exit **0**, inspection/decode/media integrity **passed**, **no findings**. Session checks both parts, recorded input decode **clean**, completeness **interrupted**, visual integrity **not_checked**. Standalone MP4 has no input-manifest context and correctly reports recorded input decode unknown. Explicit accepted tool directory was first in PATH; standalone exact-tool FFprobe also exits 0. Both successful deep validators retained actual Python native-child and wrapper handles through exit 0; FFprobe's original Popen/native wrapper handle confirms its own exit. **Nine recording artifact hashes** are identical before/after these checks.

Read-only immutable inspection of only the NEW retired catalog: integrity **ok**, one completed session/task, one durable automatic receipt, one original H, zero outstanding units, both bindings free, one released preparation/result chain. **Six** durable original native-child exit records have confirmed exit code 0 and cleanup 1. Catalog/sidecar/marker hashes remain identical across inspection. Complete product shutdown joins captures/finalizer/requests/monitor and releases authority; primary_type null, diagnostic counts zero. Original supervisor/wrapper creation identity, native signals/code, product receipt and unavailable listener are checked together; disappearance alone is not the evidence. No incomplete retirement, cleanup retry, forced exit, restart, refund or fabricated completion occurred.

External observer limitations are preserved in `observer-limitations.json`: initial prelaunch CRLF equality refusal occurred before config/home/init/launch and matching checkpoint content was proven before continuing the SAME allocation; one pre-exit manifest inspection was refused by normal native pins and succeeded only after retirement; first new validator invocation rejected serve-only tool flags with parser exit 2 before validation, then the corrected external helper performed the two deep checks. The original timed observer records “Unexpected CLI exit” after the separately documented early normal safety shutdown; this is its scheduling assumption, not a hidden product failure. First init-child handle was **conhost.exe**, not Python: init wrapper/initialized receipt exist, but native Python initialization identity was not independently captured. Main service and successful deep validator Python identities were captured correctly. No missing log is reconstructed, and these refused attempts are not labelled successful product tests.

Private evidence index includes as-launched/prepared helpers and hashes, complete PM/allocation readback, preflight/537 before-after hashes, launch intents/environments and stdout/stderr, 98 snapshots, early safety/remove/reload/UUID/finalization/shutdown records, original native/wrapper creation/exit, raw/arrival/payload clock analysis, two successful new deep checks/probe, immutable catalog/accounting and home/artifact hashes. A fresh home only was operated; all historical homes/reports/fingerprint bindings remain preserved.

## Disposition

**Single recommended next action: PM review of this safety-shortened trial and its headroom/evidence limitations.** Allocation is permanently consumed/closed and no owner remains retained. Everyday/unattended rollout HOLD; no automatic repeat or successor. The planned 20-minute/30-minute envelope remains unestablished. Unsupported post-writer/pre-H cleanup still needs the same-original-owner preservation procedure if encountered; this healthy run does not broaden recovery. #52 OPEN, #48 PAUSED, #28 separate/non-blocking, #51/published v0.11.0 complete. Schema 10, storage/media/defaults unchanged. Existing watchers/services/Scheduled Tasks/configurations/recordings were neither accessed nor changed; no installation, migration, retention, media upload, source/test change, main merge, release/tag or issue closure. Refs #52.
