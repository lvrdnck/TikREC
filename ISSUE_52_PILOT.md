# Issue #52 — foreground pilot B1/B2

[PM B1/B2 contract 6059481487](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6059481487). R18–R19 accepted by [PM 6062251355](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6062251355). **B3 PASS — READY TO REQUEST RESTRICTED NATURAL-LIVE AUTHORIZATION**, including independent R16/R17 PASS for candidate `1ca8d20556232ec678434762a0befd000276bfe3`. [Fresh provenance, 53 pilot/58 native passes, 16 deep validations and explicit retained-refusal limitation](ISSUE_52_B3_ACCEPTANCE.md). Experimental/default OFF, separate from published storage-only v0.11.0. B3 was PM-accepted and the owner authorized two named sources; the [natural trial ended at startup with an external launcher error](ISSUE_52_NATURAL_PILOT.md), zero starts and no LIVE evidence. PM disposition is pending; no production installation/configuration/media/credentials were accessed.

The B3 delivery in #52 records the exact **review-only checkout HEAD** required
for `$revision` below; package source remains identical to tested `1ca8d205` and
the recorded fingerprint. Do not pass `1ca8d205` against a later HEAD, derive
trust from an unknown checkout, or rewrite an existing home/marker. The review
corrected the shell variable to `$pilotHome` because PowerShell's `$HOME` is
read-only, then executed the real prompt/module recipe on an empty disposable
home and confirmed all owners retired with exit 0.

## Operator command

PowerShell, in the identified development worktree only. Use existing Windows Python 3.11+ / SQLite 3.35+, checked existing binaries, and an existing local fixed-disk parent excluded from retention. Home must be new/absent for init. Replace revision/fingerprint with reviewed candidate values in #52; do not compute trust from an unknown installation. This recipe does not authorize a natural LIVE.

```powershell
$checkout = 'C:\Users\Leandro\.codex\worktrees\capture-journal-handoff\TikREC'
$python = 'C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe'
$tools = 'C:\Users\Leandro\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-124716-g054dffd133-win64-gpl\bin'
$pilotHome = 'C:\Users\Leandro\TikREC-tests\owner-pilot-01'
$catalog = [guid]::NewGuid().ToString() # Save; reopen requires the same UUID.
$revision = '<exact reviewed checkout HEAD from the B3 delivery in issue #52>'
$sourceHash = 'ae5ade3d0390d7f0e1b5e20c856ec5257fda50f2d4847e829b39c24f52e1dfd7'
Set-Location -LiteralPath $checkout
& $python -m tikrec.pilot --checkout $checkout --revision $revision --source-sha256 $sourceHash --home $pilotHome --catalog-id $catalog --mode init --ffmpeg "$tools\ffmpeg.exe" --ffprobe "$tools\ffprobe.exe" --port 18765
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
@{operation=[guid]::NewGuid().ToString();command='shutdown'} | ConvertTo-Json -Compress | Set-Content -LiteralPath "$pilotHome\control.json" -Encoding utf8
# If complete:false, retain the SAME foreground owners. After repairing the cause:
@{operation=[guid]::NewGuid().ToString();command='cleanup'} | ConvertTo-Json -Compress | Set-Content -LiteralPath "$pilotHome\control.json" -Encoding utf8
```

Starts fence, original captures stop early, existing bounded joins/cancellation run; queued work is not drained. Last shutdown must report `complete:true` before safe exit. Listener closure is insufficient. Each operation needs a new nonce; no implicit cleanup retry or previous-operation replay on reopen. Incomplete stays supervised; some unsupported failures require PM correction, not repeated cleanup. In particular, pre-configuration refusal can preserve an unsealed original capture lease indefinitely: B3 reproduces this on corrected oversized input, with no supported confirmed-exit procedure. Preserve the same supervisor/home and return to PM; fixture process termination is not an operator remedy. Do not arbitrarily kill, close stale numeric descriptors, delete/reset state, manually finalize owned paths or edit SQL. Exit 0 = confirmed requested stop; 2 = startup/supervision failure with confirmed retirement; 3 = confirmed envelope/unsupported stop. Incomplete never exits as safe.

Known reopen uses SAME home/catalog/fingerprint and reviewed source/tool identities, `--mode reopen`. Missing/redirected/unknown state refuses; no auto-init/migration/legacy import. Supported: queued and eligible prepared-success release. Earlier reserved/running/blocked attempts pause, preserve original units/claims/evidence, and stop the pilot. This is reduced availability, never completion/refund.

## Fixed supervised envelope

| Limit | Implementation |
| --- | --- |
| Capacity | Accepted schema 10, two captures/one FIFO finalizer/eight outstanding units. Additionally eight lifetime session intents per catalog, including completed history; slot reuse/reopen never resets allowance. |
| Per capture | 120 seconds at cooperative source checks, four connections, 64 MiB total original ingress, 16,384 chunks, 4,000 tags; chunk <=64 KiB, tag <=1 MiB, codec header <=4 KiB, AVC first-SPS positive dimensions: long edge <=1920 / short edge <=1080 in either orientation. Stop original bridge before further raw writes. |
| Room-end/retry policy | Inherit `capture_live`: three offline checks, 5-second confirmation spacing, 1-second base failure backoff. No product pilot overrides; fixture acceleration is test-only. Finite ingress/connection/time limits remain interrupted outcomes. |
| Whole active run | 900 seconds under foreground supervision, manual starts only, isolated empty automation/monitor set, no retention. |
| Free-space headroom | >=16 GiB launch/every admission, shared local catalog/media volume. Unknown refuses. Once/second observe actual media/state/free; <=8 GiB free, >=6 GiB media, >=512 MiB state or uncertain runtime triggers early original-session stop. |
| Candidate writer | Pilot-only `-fs 268435456` included before original launch hash. Mux threshold, **not exact quota**. Within 16 MiB of threshold or larger refuses BEFORE validation/publication. Sealed unpublished bytes allow original local cleanup; outstanding unit stays held. Legacy default has no limit option. |
| Inventory | <=100,000 inspected objects; redirection refuses/stops. No shared production roots/external writers. |

Planning allowance/session: 128 MiB FLV parts (64 MiB ingress + bounded repeated headers), 64 MiB raw, 16 MiB arrivals, 32 MiB control/logs, 272 MiB MP4/candidate (including 16 MiB mux-overrun allowance) =512 MiB. Eight lifetime sessions =>4 GiB plus 512 MiB catalog reserve/helper slack below media 6 GiB. Publication moves candidate instead of duplicating full output. Launch at 16 GiB / stop at 8 GiB reserves teardown/catalog writes and overlapping tails.

Existing resolver/transport calls can add timeout/cleanup grace to the cooperative 120-second source cutoff. Independent foreground 900-second stop still fences original captures; unresolved native work remains supervised/incomplete, never a time-guaranteed safe exit.

These allowances assume checked trusted binaries, bounded AVC/AAC input consistent with its declared codec headers and promptly returning trusted hooks. They are not a filesystem quota or guarantee against malicious tools, power loss, arbitrary external writers or unconstrained input. The small-cap empirical overrun is recorded below. No unattended/shared-root activation is supported. In-flight checks are independent of admission; no uncertain receipts/units are silently refunded.

Rollback means confirmed stop and preservation of the whole isolated home: schema-10 catalog, marker/automation/control, raw/arrivals/parts/manifests/scratch/output and original hashes. Leave legacy roots/services untouched. Never point older code at it, downgrade/migrate/reset/delete it, or broaden recovery. Known reopen only in supported states; otherwise retain evidence and stop for PM.

## Historical B1/B2 implementation and evidence at `2aa72096`

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
#52's delivery comment. **Next: PM correction review, then separate fresh-context B3 acceptance for the
exact whole candidate/operating scope; then seek natural-LIVE pilot authorization.**
No automatic successor or production action. #48 stays paused; #51 closed/passed;
#28 unresolved; storage-only v0.11 publication remains finished and separate.

## R18–R19 correction evidence — 2026-10-08

Corrected source/test commit **`928a6e5655dfcac9ee7d6f19cb60fd47dfcbdbfb`** on `codex/capture-journal-handoff`;
final documentation candidate is the exact commit in #52's R18–R19 delivery.
The command above requires that final candidate's exact HEAD and corrected
normalized package fingerprint **`ae5ade3d0390d7f0e1b5e20c856ec5257fda50f2d4847e829b39c24f52e1dfd7`**. Do not use the old fingerprint,
mutate an old marker/home, reset a catalog or migrate old evidence to reopen it.
Existing pilot homes and earlier evidence remain preserved. Only `pilot_limits.py`
product source changes; schema/journal/runtime/ownership/default serve stay intact.

R18 real AVC/AAC parser controls: 640x1280, 720x1280, 1080x1920 boundary,
1920x1080, 1280x720 and 64x64 pass with original tags/raw intact. Actual 1922x1080,
1082x1920, 2560x1440 and 1280x1280 refuse before configuration yield; truncated
AVC/no-SPS records refuse. Three additional explicit parser-fact doubles check
nonpositive dimensions; required real generated-media cases retain the real parser
and dimension extraction. No resize/rotate/rendition selection or resource increase.

Actual authenticated loopback command: 640x1280 portrait copy and
1280x720 ->720x1280 differing configuration use the existing copy/libx264 plans.
Old finalization is held while both new captures advance; original UUID status,
old-UUID no-op stop, targeted stop, singular ambiguity, original raw/source/control/H
and FIFO completion assertions pass. All six original sessions pass normal deep
validation. The fixture originals and protected pre-finalization controls/H remain
unchanged, including preserved predecessor manifest identity.

R19 normal composition with no fixture injection omits all three policy options
and inherits **3 / 5.0 / 1.0**. Actual command observes live -> lone offline ->
transient -> same-room live -> three confirmed offline results. At the original
first confirmation barrier, capture stays active and output incomplete. Recorded
wait requests are **[0, 5, 1, 0, 5, 5] seconds**; room-status confirmation flags
are **[false, false, false, true]**. Only the test helper's cancellable waiter
accelerates time; no product policy values are shortened. Two original raw source
connections and the final output pass ordinary deep validation.

| Frozen run | Actual result |
| --- | --- |
| Unchanged `2aa72096` baseline | **10 failed / 9 passed**, 165.46 s pytest; 166.06 s harness. All 209 package files match the original Git source, blob `fa4fe7b0618a23f9719b6e2f0ffb2a1031313968` for pilot limits. |
| correction-focused | **51 passed / no skips**, 230.00 s pytest; 230.59 s harness. Real geometry/policy plus pilot limits/command/restart/identity. |
| correction-related | **124 passed / no skips**, 253.90 s pytest; 254.47 s harness. Exact eleven modules/argv in provenance: LIVE/control/recovery, confirmation/bound identity, capture/H media, HTTP actual accept/UUID, runtime shutdown and SQLite connections. |

Baseline failures reproduce all three portrait refusals, nonpositive dimensions,
normal policy overrides, missed portrait copy/configuration-change completion and
premature finalization after one offline observation. The rejected initial portrait
baseline also reports **incomplete shutdown after explicit cleanup retry**; its
ambiguous pre-configuration ownership remains retained. Two identified disposable
Python fixture processes (wrapper/interpreter for that one command) were forcibly
terminated and recorded in `baseline/forced-disposable-cleanup.json`. That is NOT
confirmed owner retirement or an operator workaround. Baseline homes/logs remain.
No accepted ownership/runtime design is altered to hide this failure; unsupported
or uncertain state still requires preserve-state supervision/PM handling.

Corrected focused command logs: 22 launches, 19 final `complete:true` shutdown
receipts (including exact native/SQLite repair and explicit retry), three refusals
before constructing owners. **15 generated original-session deep validations**:
eight original pilot cases plus six geometry overlap sessions and one policy case.
Original hashes are retained in each validation JSON and plan record. No forced
fixture termination in either corrected final run; zero remaining task processes
is recorded separately after both runs. No production/user-media/LIVE access.

Evidence root **`C:\Users\Leandro\TikREC-tests\issue52-pilot-r18-r19-20261008`**:
`baseline-source-proof.json`, all three run directories with exact argv/interpreter/
cwd/Git/import provenance and frozen raw manifests, `focused-retirement-validation.json`,
`static-checks.json` and final retirement/candidate proof. Same **511** source/test/
script/pyproject raw hashes before/after both corrected runs; manifest SHA-256
**`bf96f478021bf38474c1af8610f327aa70ede161e6e406bc291a3660160092ba`**.
510 Python files compile; changed source/helper maximum 188 lines. Pilot help,
ordinary CLI version (unchanged development metadata 0.10.0) and diff checks pass.
Native interpreter/tools are those documented above; disposable environment roots
and no inherited token/configuration are retained. No full historical suite/review
was repeated. Refs #52. **Stop for PM correction review; B3 remains separate.**
