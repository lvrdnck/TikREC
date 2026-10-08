# Issue #52 — foreground pilot B1/B2

[PM contract 6059481487](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6059481487). **B1/B2 PASS — complete for PM review.** Experimental/default OFF, separate from published storage-only v0.11.0. B3 fresh-context acceptance and separately authorized natural-LIVE pilot remain outstanding. No production installation/configuration/media/credentials were accessed.

## Operator command

PowerShell, in the identified development worktree only. Use existing Windows Python 3.11+ / SQLite 3.35+, checked existing binaries, and an existing local fixed-disk parent excluded from retention. Home must be new/absent for init. Replace revision/fingerprint with reviewed candidate values in #52; do not compute trust from an unknown installation. This recipe does not authorize a natural LIVE.

```powershell
$checkout = 'C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC'
$python = 'C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe'
$tools = 'C:\Users\Leandro\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-124716-g054dffd133-win64-gpl\bin'
$home = 'C:\Users\Leandro\TikREC-tests\owner-pilot-01'
$catalog = [guid]::NewGuid().ToString() # Save; reopen requires the same UUID.
$revision = '<exact reviewed candidate commit from issue #52>'
$sourceHash = 'fb71c4e1d41a32de50a88999c2b8ffec5c8480451b943a8c4660947879dca351'
Set-Location -LiteralPath $checkout
& $python -m tikrec.pilot --checkout $checkout --revision $revision --source-sha256 $sourceHash --home $home --catalog-id $catalog --mode init --ffmpeg "$tools\ffmpeg.exe" --ffprobe "$tools\ffprobe.exe" --port 18765
```

Enter a fresh 24–256-character printable ASCII non-whitespace secret at the non-echoing prompt. No argument/environment token, production configuration discovery or secret logging. Save ready receipt: actual root/revision/fingerprint/interpreter/SQLite/backend/schema/catalog UUID/path/media/automation/port/control. Wrong branch/root/origin/revision/source/state/catalog refuses. Binaries undergo version and required libx264/AAC encoder/H264/AAC decoder checks. Source fingerprint normalizes CRLF to LF; frozen evidence separately hashes raw files.

Manual authenticated control uses the existing RemoteClient with explicit endpoint/token and no config loader. In another PowerShell window, enter Python interactively (so getpass has a terminal):

```powershell
Set-Location -LiteralPath $checkout
& $python
```

```python
import getpass
from tikrec.remote import RemoteClient
client = RemoteClient('http://127.0.0.1:18765', token=getpass.getpass('Pilot secret: '))
print(client.health())
# Only after separate pilot authorization: choose public URL and NEW output.
# started = client.start('https://www.tiktok.com/@CHOSEN_CREATOR/live', r'EXACT_PILOT_HOME\media\chosen.mp4', raw_copy=True)
# print(started)  # Save original session_id.
# print(client.status('ORIGINAL_SESSION_UUID'))
# print(client.stop('ORIGINAL_SESSION_UUID'))
```

This is the rehearsed HTTP route. UUID lookup never substitutes a reused slot. Closed-old UUID stop leaves replacement captures alone; singular stop with two captures is ambiguous. `active=false` means capture closure; only `output_completed=true` proves durable publication/manifest/release. Output must be an immediate new `.mp4` in the reported pilot media root.

Ctrl+C or a fresh local nonce requests shutdown:

```powershell
@{operation=[guid]::NewGuid().ToString();command='shutdown'} | ConvertTo-Json -Compress | Set-Content -LiteralPath "$home\control.json" -Encoding utf8
# If complete:false, retain the SAME foreground owners. After repairing the cause:
@{operation=[guid]::NewGuid().ToString();command='cleanup'} | ConvertTo-Json -Compress | Set-Content -LiteralPath "$home\control.json" -Encoding utf8
```

Starts fence, original captures stop early, existing bounded joins/cancellation run; queued work is not drained. Last shutdown must report `complete:true` before safe exit. Listener closure is insufficient. Each operation needs a new nonce; no implicit cleanup retry or previous-operation replay on reopen. Incomplete stays supervised; some unsupported failures require PM correction, not repeated cleanup. Do not arbitrarily kill, close stale numeric descriptors, delete/reset state, manually finalize owned paths or edit SQL. Exit 0 = confirmed requested stop; 2 = startup/supervision failure with confirmed retirement; 3 = confirmed envelope/unsupported stop. Incomplete never exits as safe.

Known reopen uses SAME home/catalog/fingerprint and reviewed source/tool identities, `--mode reopen`. Missing/redirected/unknown state refuses; no auto-init/migration/legacy import. Supported: queued and eligible prepared-success release. Earlier reserved/running/blocked attempts pause, preserve original units/claims/evidence, and stop the pilot. This is reduced availability, never completion/refund.

## Fixed supervised envelope

| Limit | Implementation |
| --- | --- |
| Capacity | Accepted schema 10, two captures/one FIFO finalizer/eight outstanding units. Additionally eight lifetime session intents per catalog, including completed history; slot reuse/reopen never resets allowance. |
| Per capture | 120 seconds at cooperative source checks, four connections, 64 MiB total original ingress, 16,384 chunks, 4,000 tags; chunk <=64 KiB, tag <=1 MiB, codec header <=4 KiB, AVC first-SPS declared dimensions <=1920x1080. Stop original bridge before further raw writes. |
| Whole active run | 900 seconds under foreground supervision, manual starts only, isolated empty automation/monitor set, no retention. |
| Free-space headroom | >=16 GiB launch/every admission, shared local catalog/media volume. Unknown refuses. Once/second observe actual media/state/free; <=8 GiB free, >=6 GiB media, >=512 MiB state or uncertain runtime triggers early original-session stop. |
| Candidate writer | Pilot-only `-fs 268435456` included before original launch hash. Mux threshold, **not exact quota**. Within 16 MiB of threshold or larger refuses BEFORE validation/publication. Sealed unpublished bytes allow original local cleanup; outstanding unit stays held. Legacy default has no limit option. |
| Inventory | <=100,000 inspected objects; redirection refuses/stops. No shared production roots/external writers. |

Planning allowance/session: 128 MiB FLV parts (64 MiB ingress + bounded repeated headers), 64 MiB raw, 16 MiB arrivals, 32 MiB control/logs, 272 MiB MP4/candidate (including 16 MiB mux-overrun allowance) =512 MiB. Eight lifetime sessions =>4 GiB plus 512 MiB catalog reserve/helper slack below media 6 GiB. Publication moves candidate instead of duplicating full output. Launch at 16 GiB / stop at 8 GiB reserves teardown/catalog writes and overlapping tails.

Existing resolver/transport calls can add timeout/cleanup grace to the cooperative 120-second source cutoff. Independent foreground 900-second stop still fences original captures; unresolved native work remains supervised/incomplete, never a time-guaranteed safe exit.

These allowances assume checked trusted binaries, bounded AVC/AAC input consistent with its declared codec headers and promptly returning trusted hooks. They are not a filesystem quota or guarantee against malicious tools, power loss, arbitrary external writers or unconstrained input. The small-cap empirical overrun is recorded below. No unattended/shared-root activation is supported. In-flight checks are independent of admission; no uncertain receipts/units are silently refunded.

Rollback means confirmed stop and preservation of the whole isolated home: schema-10 catalog, marker/automation/control, raw/arrivals/parts/manifests/scratch/output and original hashes. Leave legacy roots/services untouched. Never point older code at it, downgrade/migrate/reset/delete it, or broaden recovery. Known reopen only in supported states; otherwise retain evidence and stop for PM.

## Implementation and evidence

Dedicated `python -m tikrec.pilot` composes the existing passive runtime/admission/HTTP once. Native state pins and attached startup owners remain reachable with exact Windows close guards; original error type wins. Ordinary serve/configuration remain legacy. Pilot-only ingress/writer limits do not add a scheduler or change media algorithms. Byte-limit refusal records sealed **unvalidated/unpublished** bytes, skips every validator/publication, closes original local owners, and retains unfinished accounting; default wrappers retain their original failure behavior.

Final focused: **32 passed, no skips, 159.55 s pytest** (161.44 s harness). Eight original sessions pass normal CLI `validate --deep --json`: six overlap outputs, one prepared-success and one queued reopen. Copy/libx264 use the actual module/accept loop: old finalization held while BOTH replacement byte counts advance; original UUID status/stop, singular ambiguity and automatic FIFO completion. Original fixture/raw/control/H/seal hashes/identities preserved; raw OFF stays OFF.

Read-only injected free-space observations prove launch/admission refusal and in-flight stop without filling a volume. Missing tools, wrong source/home/catalog, occupied native listener and invalid/missing identity paths refuse. Real protected native startup retains first ValueError through failed cleanup then repaired explicit retry. SQLite close evidence proves original creator thread. Queued shutdown does not drain/replay prior control; prepared success uses only accepted recovery; unsupported phase preserves rows/media/units without publish/refund.

| Run | Actual result | Interpretation / correction |
| --- | --- | --- |
| development-one | 20 passed / 1 failed; 84.81 s | Injected SQLite fixture used wrong HTTP thread name; corrected. |
| development-two | 3 passed / 2 failed; 205.55 s | Occupied listener raises PermissionError (OSError subtype); assertion corrected. Capped writer retained unsealed scratch/incomplete shutdown. |
| development-three | 7 passed / 1 failed; 208.63 s | Sealing alone still retained wrapper pins; narrow pilot refusal cleanup corrected. Identity/queued checks passed. |
| development-four | 11 passed; 42.10 s | Corrected cap/native-startup retry/pin/lifetime checks. |
| final-focused | 32 passed; 159.55 s | Final frozen command/limits/identity/restart checks. |

Earlier failed capped-writer helpers needed **identified disposable fixture process termination**, separately recorded in `forced-disposable-cleanup.json`. This is NOT product retirement/rollback evidence. No production/recorder process touched. Final command cases retire normally through product shutdown; force termination is absent from the operator procedure.

FFmpeg `-fs 131072` produced **270,767 bytes** (139,695 overrun). Final test checks original hashed launch threshold, sealed unvalidated/unpublished candidate, no validation/settlement/output, counted unfinished unit and confirmed local shutdown. Therefore `-fs` is a soft mux threshold with planning slack, never an exact quota. Evidence: `C:\Users\Leandro\TikREC-tests\issue52-pilot-20261008`. Actual native loopback accept loop/module command; generated AVC/AAC copy/libx264 media only. Private seams replace source resolution/bytes, read-only free observations, secret input and exact barriers/faults, retaining the product command/envelope/parser/raw/runtime/HTTP/start/status/stop/shutdown path.

No LIVE/user-media deletion, accepted runtime-review repetition, redundant full suite, production access, installation, default activation, migration, broader recovery or release. This continued context cannot satisfy B3.


Final related: **233 passed, no skips, 557.67 s pytest** (558.38 s harness).
HTTP actual accept-loop/bounds/faults/lifecycle, runtime shutdown/thread/connection/
finalizer retirement, original native authority/handles, assembly/default failed
validation/publication/manifest retention, legacy control CLI/RemoteClient and
storage/admission selected for changed guard/budget/composition scope. Exact 19-file
selection and argv are preserved in `final-related/result.json` and `provenance.json`;
no broader accepted review or full suite was mechanically repeated.

Both final serial runs freeze the SAME **509 files**: package/tests/scripts Python
plus pyproject. Raw manifest SHA-256 **11f01e298bb573edfa6ffe1f9bbadb05d9787d4bcec61fea0a63a7cee9c2714d**;
normalized package-source fingerprint **fb71c4e1d41a32de50a88999c2b8ffec5c8480451b943a8c4660947879dca351**.
508 Python files compile; changed source max 188 lines. Pilot help, normal CLI
help/version (0.10.0 development metadata) and diff check pass. Final frozen bytes
still match after documentation edits. No source/test edit occurred during runs.
`candidate-checks.json` preserves CLI/compile/hash/validation results;
`final-focused/fifo-proof.json` proves actual completion matches each immutable
catalog queue order. Final task-path Python/FFmpeg/FFprobe census is zero;
`process-retirement.json` supplements product joins/exact native Job cleanup.

Windows CPython 3.11.15, SQLite 3.53.1, existing interpreter
`C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`;
actual imports from this worktree. FFmpeg/FFprobe N-124716-g054dffd133-20260531;
SHA-256 b241596c846107ef85fe5a6fb9c11146e256cbe193378c86788e0462b6ad1081 /
171a9102fe291870ee4fa62e8a6814366e65247d692d5177cb2ca73567c2f3d5.
Provenance records root/branch/origin/common Git directory, interpreter/base/import,
PID, exact commands, before/after hashes. APPDATA/LOCALAPPDATA/XDG config/state/TMP/
TEMP are disposable; inherited TIKREC_TOKEN removed. Trusted offline helper calls
`runpy.run_module('tikrec.pilot', run_name='__main__')` with exact operator argv:
no substitute scheduler/constructor-only orchestration. Evidence roots/logs and
all generated originals are preserved, including development failures.

Delivery uses Refs #52 and a normal push; exact candidate commit is recorded in
#52's delivery comment. **Next: PM fresh-context B3 acceptance for this exact
candidate/operating scope; then seek separate natural-LIVE pilot authorization.**
No automatic successor or production action. #48 stays paused; #51 closed/passed;
#28 unresolved; storage-only v0.11 publication remains finished and separate.
