# Issue #48 — deployed automatic raw-copy validation

## Current result (2026-10-03)

**Deployment and Gracie-only startup opt-in PASSED; natural recording gate
OUTSTANDING. #48 remains OPEN / explicitly PAUSED.** Implementation
`3b8d8bf0` and structure extraction `130d495d` are deployed. No capture code was
changed during this gate. v0.10.0 remains current released/package version;
v0.11.0 remains unreleased.

The owner explicitly authorized automatic raw-copy for **`gracie.kf` only**, with
**`wardsimons` OFF** and monitored creators exactly **`wardsimons`, `gracie.kf`**.
That authorization remains in force; do not restore Eliss. Raw capture roughly
doubles storage. No manual LIVE start/stop, media/evidence mutation, retention,
other roadmap implementation, task-definition change or release/tag action.

The owner accepted the 2026-10-03 partial checkpoint and explicitly paused #48
to start #52 Stage 1 as the single active investigation. All natural-recording
acceptance criteria and the approved policy remain unchanged. Resume when
qualifying natural evidence exists, or credible missed-LIVE evidence warrants
source-access investigation. Unknown/unverifiable is not proof of offline.
Older instructions below to repeat a bounded check are historical and
superseded by this sequencing decision; #52 performs no #48 search/polling.

## Read-only natural-recording check — PARTIAL (2026-10-03)

Bounded observations ran at **12:30:09–12:31:35 UTC** (14:30–14:31 CEST),
monitoring cycles **2663 → 2666**, after fresh GitHub synchronization and
reconciliation. **No qualifying Gracie recording was found; #48 stays OPEN.**

### Runtime and policy reconciliation

- Current listener PID **16480**, creation **2026-10-02T12:32:54.1650210Z**,
  differs from deployment PID 63796. Scheduled Task last-run time is
  **2026-10-02T12:32:54Z**, consistent with that later process launch. The task
  XML hash and host-visible config hash exactly match the deployed checkpoint;
  no task/config rollback, restart or write was performed in this pass.
- The reason/initiator of that intervening launch is unproven: Task Scheduler's
  Operational event log is disabled. This is a provenance limitation, not proof
  of a #48 regression. The approved saved policy remains only `gracie.kf`, with
  monitored order `wardsimons`, `gracie.kf`; Ward stays OFF.
- Storage/configuration are `ok`, automation operational, no pending claim,
  no active worker, two available slots, no shutdown or current recovery state.
  Config, task, both current jobs and automation were stable between snapshots.
  Free storage at the final check: **413,283,373,056 bytes**, reserve 10 GiB.
- During the persisted bounded check both creators reported
  `unknown / unverifiable`. No automatic start was selected.
  This does not establish that Gracie was offline throughout, only that this
  monitor did not verify a LIVE during those cycles.

### Existing evidence search and Ward negative control

- Read the manifests of **all 54 immediate `.parts` directories** in the
  configured host-visible Videos root; **zero unreadable/missing manifests**,
  **zero Gracie sessions with a start after policy activation**. The latest
  Gracie session is `55dc7b01-4a85-45c1-aa63-0cec1a0ab0c4`, room
  `7691910970859342623`, started **2026-10-02T03:44:57.478753Z**, completed
  before activation. It cannot satisfy #48 regardless of existing media files.
  Search scope is the configured local output root/current jobs, not an archive
  catalog or proof that no recording could exist elsewhere.
- Current slot 1 legitimately differs from the deployment's old terminal Ward
  job. Post-activation Ward session **`712580b5-6b56-4ff6-9306-1fe614f6367a`**,
  room **`7692051357494151968`**, started **2026-10-02T12:49:43.473980Z**,
  ended **13:00:06.299413Z**, is failed/inactive with **raw-copy OFF**.
  Its durable job and manifest UUID/room/output/parts agree; no stop intent,
  resume, recovery or interruption. No raw/arrival files exist; both numbered
  connection records have null raw/arrival references. Automation consumed that
  Ward room. These facts support the negative control; consumed-room history
  alone is not a complete accepted-start provenance log.
- Ward's retained manifest identifies anonymous stream unavailability, TikTok
  status **4003110**, on resolution. Finalization is `not_started`, not completed.
  This is a recorded source-resolution failure, not evidence of a raw-policy
  defect or a successful final-output check. No repair or unrelated investigation
  was performed. Slot 2 remains the historical completed Eliss job; Eliss is not
  in monitoring and was not restored.

### Unavailable acceptance criteria and safe next action

There is no post-activation Gracie job/session to establish automatic-start
provenance, accepted `raw_copy_enabled=true`, room/slot ownership, nonempty raw
and arrival sidecars, connection references, coherent byte ranges or progressing
Gracie capture. No suitable Gracie artifact exists for this gate's read-only
`tikrec validate`/finalization checks. None is claimed as passed. Existing older
Gracie completion and Ward OFF evidence do not substitute for these criteria.

**Next:** keep the approved policy and service untouched. On another bounded
read-only pass, first look for an ongoing or completed natural automatic Gracie
recording and use its existing evidence. No restart, config write, forced
reconnect, manual LIVE, repeated opt-in authorization or terminal wait is needed
when normal active evidence is sufficient. #52 stays queued; #28 is unresolved.

Local metadata-only evidence:
`C:\Users\Leandro\TikREC-evidence\issue-48-natural-20261003` contains `before.json`,
`final.json`, `runtime.json`, `candidate-search.json`, `ward-negative-control.json`,
`summary.json`, reusable `capture.ps1` and `checksums.json`. No credentials or
media were copied. Checksum index SHA256:
`b44f28e0ca019f900b18af93a912015f44136addc15269d76822d4729cfc2597`.
No production code changed; no offline suite reran. Actual checks were public
service status, control hashes, all local session manifests and Ward's existing
connection metadata, with read-only bounded cycle observations.

## Safe deployment and activation

All times below are UTC (CEST = UTC + 2 hours).

1. Fresh preflight found both slots naturally completed, inactive, available,
   with no stop request or recovery state. Ward's session
   `9d3720f4-0123-4fcf-917d-4546d754be9d` had naturally ended at 368,927,854
   recorded bytes; slot 2 retained completed historical Eliss session
   `268a8cbd-34be-4b9b-ba84-6c848f69ad47`. Historical ownership does not mean
   Eliss is monitored.
2. Baseline snapshots at **11:09:32** / cycle **260** and **11:10:26** / cycle
   **261** proved both jobs, config and automation byte-stable. Health/storage
   were good, two slots available. Original PID **18660**, creation
   **2026-10-02T08:48:25.1583120Z**. A final public idle check immediately
   preceded ending the idle Scheduled Task.
3. At **11:10:28**, started the unchanged **TikREC Service** task once after
   confirming the old process absent. New supporting-code PID **61104**,
   creation **2026-10-02T11:10:28.4337220Z**. The existing editable install imports
   this checkout; no installation or deployment definition changed. Health,
   storage and normal monitoring passed, with exact original config, task XML,
   both jobs and automation hashes unchanged.
4. A fresh idle check at **11:11:40** / cycle **3** preceded the normal CLI:
   `tikrec --config \\localhost\C$\Users\Leandro\AppData\Roaming\TikREC\config.json monitor raw-copy enable gracie.kf`.
   Command returned **0** at **11:11:41**. Raw preference became exactly
   `gracie.kf`; monitored order stayed `wardsimons`, `gracie.kf`. Removing only
   the serialized new property reproduces the exact previous config bytes;
   all unrelated setting values are identical. No redirected desktop config or
   manual JSON editing was used.
5. Because policy is startup-selected, a final idle check preceded the required
   second activation restart at **11:11:44**, with unchanged task definition.
   New active-policy PID **63796**, creation
   **2026-10-02T11:11:44.4280260Z**. Both completed durable jobs and automation
   remained byte-identical. Health/storage and monitoring configuration were
   `ok`; two slots available, no stop/recovery/startup capture. Both creators
   initially reported offline. Normal CLI lists confirmed only Gracie opted in
   and the exact Ward/Gracie monitored order.

The first restart loaded support before saving the new field, avoiding the old
strict reader's rejection. The second activated the saved startup policy. Neither
restart interrupted a recording or changed task/bind/token/output/recovery settings.

| Evidence | SHA256 |
| --- | --- |
| Original config | `8f35fd61beb58fc35ae4d824598454dc3623cd9315464085ee195764c6303d10` |
| Active Gracie-only config | `1e24d284af2b9abb15d37a3dd378f60deb72af3322f49a839e68c423f42ff1d2` |
| Unchanged task XML, normalized LF UTF-8 | `266910f1379c1cced9ec19789e6140bf2077df68b0133f73300b621927371bf8` |
| Unchanged slot-1 job | `35f56b78d8797f84fdd918fa2eaecb17194ccc3f81752d79a008777702f948c4` |
| Unchanged slot-2 job | `e69bae8a17e43bb22363c65bcc454407b4d2814b3e0ab01d6e39bd564e790931` |

## Natural automatic recording gate and safe resume

Deployment alone does not prove raw/arrival evidence from a real automatic
recording. Leave #48 open until a naturally occurring Gracie recording establishes:

- Accepted automatic Gracie start, durable `raw_copy_enabled=true`, matching
  creator/room/session/slot/job ownership and normal output/`.parts` paths.
- Nonempty `connection-NNNN.raw`, corresponding arrival sidecar and correct
  `connections.jsonl` references under the existing CONNECTION_LOG.md contract.
- Normal retained FLV/session/output lifecycle and increasing recording progress,
  with no duplicate, stop request, recovery or ownership regression.
- Only Gracie remains opted in; Ward's future automatic starts remain raw OFF.

Final read-only observation at **11:15:45 UTC**, completed cycle **8**, retained
PID 63796/creation time, exact active config and task hashes, both completed job
hashes and automation unchanged. Both creators remained offline, two slots
available, storage/configuration healthy. No automatic recording started during
observation, so real raw/arrival/connection and media validation were unavailable.
The active Gracie-only policy is preserved for the next natural opportunity.

No terminal wait is required if sufficient evidence is already proven during
normal active capture. Do not force a reconnect or manufacture a LIVE to obtain
closed connection references. Preserve all media and captured evidence.

**Resume:** inspect the already-running policy-selected service and config read
only, then capture a natural automatic Gracie opportunity. No further restart,
config change or authorization request is needed for the approved policy. If
the service/config differs, reconcile before proceeding. #52 stays queued;
#13/#28/#8 are separate and not started.

## Evidence and verification

Metadata snapshots and timestamped actions are preserved at
`C:\Users\Leandro\TikREC-evidence\issue-48-deployed-20261002`: `before.json`,
`before-stable.json`, `code-loaded.json`, `before-opt-in.json`,
`opt-in-saved.json`, `policy-active.json`, reusable `capture.ps1` and
`actions.txt`, plus `normal-cycle-check.json`, `final.json` and `checksums.json`.
Checksum index SHA256:
`d8adb5fc63fe4a4abf19a44680aace57bc025d79e58f94d0a665c760d842b71a`.
They include process identity, task XML hash, config and durable
control hashes/documents, public health/storage/slots/monitoring; no token or
recording bytes are copied.

Existing implementation evidence: 166 focused, 634 broader / 2 subtests,
**1,783 full Windows offline passes / 19 subtests**, seven platform skips.
No code changed or offline suite reran for this deployment/config/documentation
gate. Verification uses the public service/CLI and read-only control metadata.
