# Issue #52 — isolated HTTP/client compatibility

## Authority and current status

[PM correction decision 6057613070](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6057613070) retains the HTTP/client direction but withholds acceptance of `316503578dec55cabeded9e0d7d77472a4f5bb46` pending R16–R17. Accepted R1–R15, `b9189ae0`'s bounded implemented-runtime review and schema 10 remain accepted. This single correction is experimental/default OFF. Complex / GPT-6.1 Sol — High MODEL GATE and owner PROCEED recorded. #52 OPEN/SINGLE ACTIVE, #48 OPEN/PAUSED, #28 unresolved; owner decisions None.

**R16–R17 COMPLETE FOR PM REVIEW:** unchanged `31650357` reproduced R16 and both R17 gates through actual Windows loopback acceptance before runtime edits. Final correction suites: **103 focused / 229 related passed**, no skips, on identical frozen bytes; both generated copy/libx264 original sessions pass normal CLI deep validation. The original **83 focused / 360 related passes** and two validations remain valid historical reported evidence for their selections. New evidence: `C:\Users\Leandro\TikREC-tests\issue52-http-r16-r17-20261008`; historical delivery: `C:\Users\Leandro\TikREC-tests\issue52-http-client-20261008`. The accepted runtime review is not repeated; overall #52/deployment acceptance is not claimed. Exact normally pushed Refs #52 correction commit is recorded in #52's current checkpoint/comment. PM review only next; no automatic successor.

## Implemented contract

`IsolatedRecordingHTTPServer` in `tikrec/service_http_runtime.py` takes an already constructed passive `IsolatedServiceRuntime` plus explicit matching `RecordingAdmission`, `AutomationCoordinator` and `CreatorMonitor`. Their media/storage/automatic-state paths belong to the caller's isolated composition. Legacy/backend arguments conflict before binding/work. The listener binds before runtime/monitor start. No catalog/job-store/legacy recovery authority is implicitly created; ordinary `serve` and configuration never select this class.

Only this backend advertises `durable_finalization_v1`. Route names, start fields and 202 acceptance stay; two slot IDs stay. `active_count`, `available_slots`, `available` and additive `capture` describe physical capture bindings. `admission_available`/fixed `admission_reason` describe permission to start: eight artifact units may leave two physical slots free while new admission refuses. Additive `finalization` reports counted units/tasks, the single worker and fixed paused reasons. Unknown counts are null. `/recordings` keeps exactly two current/latest slot snapshots, at most eight `finalization_sessions` tasks and at most eight `outstanding_sessions` owners. The latter includes retained empty-capture evidence with no assembly task, so reuse cannot hide those counted/pinned owners. Every session retains immutable `origin_slot_id`.

Authenticated `GET /sessions/UUID` addresses original capture/finalization/terminal history by canonical UUID across slot reuse/restart; it never exports all history. Invalid UUID is 400, unknown 404. Capture closure, publication, no-assembly/empty, failure or a free slot cannot expose completed MP4 output. Only audited owned terminal success/recovery release evidence exposes `output_completed=true` and `final_output_path`; this is durable historical completion evidence, not a guarantee against later external deletion. Closed/restarted unmeasured byte counters are null.

Singular status/stop retains ambiguity across all outstanding owners (409). Targeted live-capture stop only signals that capture. Finalization-only UUID returns 202 `capture_already_closed` without changing assembly or replacement capture. Completed/unknown UUID stop is 404. No new HTTP control fields, automatic retries or recovery authority exist.

`RemoteClient.status(session_id=None)` preserves the original `/recording` call when omitted. `tikrec remote status --session-id UUID` validates UUID, checks `/health` capability and uses only `/sessions/UUID`. An older server without that capability returns an explicit unsupported error; there is no latest-slot fallback. Returned UUID must match. Old clients may still read ordinary routes, but `active=false` or slot reuse cannot mean MP4 success on the isolated backend; compatibility is additive on wire, intentionally different in phase meaning.

Transport uses allowlisted identity/counter/state/path/reason projections and a 65,536-byte response ceiling. Local paths are capped at 1,024 UTF-8 bytes and both output/parts paths are checked before start acceptance; monitoring/selected creator projections are capped at 100. Existing bearer/bind/origin/body/redirect protections remain. Arbitrary exception text, stderr, signed transports, SQLite/internal capabilities and controls never serialize. Every request/disconnect cleans SQLite on its original thread; failed teardown holds the thread/object for a later explicit shutdown retry. The supplied monitor's original thread is likewise retained across lost startup acknowledgement/SQLite cleanup. Shutdown fences HTTP/callback starts and requests original UUID capture stops before waiting on uncertain request/monitor owners. Listener close and fixture repair do not establish safe product exit; startup errors retain the primary exception and attach reachable server/shutdown state. Listener-close failure preserves the socket and reports incomplete transport even when runtime authority retirement is confirmed.

Schema 10, accepted R1–R15, two captures/one finalizer/eight units, original raw/session/control/H evidence, original automation acceptance/raw preferences and creator-only reload, exact-once accounting and narrow prepared-success recovery remain unchanged. A small optional CreatorMonitor thread factory observes native ownership without altering default scheduling/resolution policy.

## R16–R17 ownership correction

Only `service_http_requests.py` and `service_http_runtime.py` change product source.
The isolated server registers each exact native socket in `get_request()` before
verification/start/refusal. Its accept boundary preserves real stdlib
`handle_request()`/`serve_forever()` selection and native listener acceptance, but
replaces the generic exception fallback that could close a worker's socket from
the accept thread. Direct start errors still raise the exact primary exception;
ordinary accept-loop exceptions are recorded privately. Interruptions propagate
after retaining ownership. A worker remains solely responsible for its socket
and SQLite until cleanup and its actual native join are proved.

Total ownership is bounded to **16 worker owners plus one acceptance/refusal
reserve (17)**. Known prestart/refused sockets stay registered until close succeeds.
Any pending accepted/socket-only owner pauses further native acceptance, even if
all older workers retire; later clients remain in the finite OS backlog and may
wait/time out. A ready paused listener waits up to 50 ms or an ownership-change
signal per iteration. No background close retries or automatic client retries
exist. `requests.join(..., closing=True)` or `shutdown_components()` explicitly
retries socket-only owners; workers retry on their original thread. A trusted
direct `process_request` caller retains its own connection on a reserve-unavailable
RuntimeError; it cannot evade the bound. Integrated shutdown fences native
acceptance first; a registered acceptance still in verification holds the barrier
until its transfer resolves. Listener closure alone cannot prove safe exit.

Unchanged-source Windows baseline (actual full disposable isolated runtime,
CPython 3.11.15, SQLite 3.53.1): **3 failed / 3 passed in 1.66s**. Both source and
all 490 then-present source/test hashes remain unchanged through the run; the
reviewed request blob is exactly `0b3345977d977804728ac6381f4f380786854ecf`.
R16 retained a live worker but its socket was already closed by MainThread before
release. Both R17 gates lost the failed socket owner: error escaped, two fallback
closes ran, join and integrated shutdown reported complete/authority released
while the exact refused native socket remained open. This demonstrates the
disposable false retirement barrier; it is not a production data-loss claim.
Ordinary startup and both successful-close refusal controls passed. Baseline
fixture repair separately retired the lost sockets; it is not product retirement.

New connected tests retain ordinary/direct/known-prestart controls and add actual
Windows TCP coverage for started/unconfirmed startup, primary plus secondary
socket/SQLite errors, repeated explicit cleanup, both refusal gates, the finite
reserve and paused accepts, in-flight verification, real continuous accept-loop
shutdown and early original-UUID capture stop. Exact native socket descriptors,
worker/accept-loop joins and original SQLite close thread IDs are asserted.
Independent fault repair and deferred native-start fixture repair are labelled;
only successful explicit product cleanup afterward establishes retirement.

## R16–R17 verification evidence

All serial runs use the verified existing native interpreter
`C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`,
base uv CPython **3.11.15 / Windows AMD64**, SQLite **3.53.1**. Each run records
actual cwd/root/branch/origin/common Git directory, HEAD `31650357` and actual
worktree `tikrec.__file__`, plus before/after SHA-256 for every source/test file.
`TIKREC_TOKEN` is removed; APPDATA/LOCALAPPDATA/XDG config/state/TMP/TEMP point
to separate disposable directories beneath the evidence root. Only local
generated media and ephemeral Windows loopback sockets are used; existing
ffmpeg/ffprobe are unchanged. No production data/runtime or installation is used.

| Selection | Actual result | Frozen files | Interpretation |
| --- | --- | ---: | --- |
| baseline-accept | 3 failed / 3 passed in 1.66s | 490 | R16 and both R17 gates reproduced before runtime edits; ordinary-start and successful-refusal controls pass. Request blob verified. Byte-exact source/reproducer snapshots retained in `baseline-reproducer`, with matching baseline hashes. |
| development-one | 22 passed in 10.90s | 490 | Corrected reproductions plus direct-request and lifecycle controls. |
| development-two | 1 failed / 33 passed in 27.24s | 492 | Continuous-loop fixture observed worker entry before accept-thread startup-error recording; wait for that actual acknowledgement diagnostic instead. Product source unchanged for this fixture repair. |
| development-three | 1 failed / 19 passed in 8.47s | 492 | Capture-stop fixture assumed completed retirement immediately after release. Join the exact asynchronous capture before the explicit bounded shutdown retry; product source unchanged for this fixture repair. No performance guarantee inferred. |
| development-four | 20 passed in 8.42s | 492 | All new loopback cases pass, including interrupted/unconfirmed native startup. |
| focused-final-frozen | 103 passed in 265.65s, no skips | 492 | All ten HTTP modules plus RemoteClient/CLI, including copy/libx264, original raw/H/UUID, eight-unit accounting, targeted stop and restart completion. |
| related-final | 229 passed in 697.09s, no skips | 492 | Relevant 24-module legacy service/monitor/automation/admission/storage and runtime ownership/shutdown/recovery regression selection. |

Both final 492-entry manifests equal each other and delivery source/test bytes.
Of the initial HTTP delivery's 488 existing files, **486 are unchanged**; only
the two isolated HTTP ownership/composition source modules change. Four new
test/helper files add 20 cases. Accepted runtime/journal/media/monitor/automation/
admission, client/CLI/default service source, package metadata and schema 10
remain unchanged. Canonical committed-file/remote equivalence is separately
verified in `delivery-verification.json`, accounting for normal CRLF conversion.

Read-only normal `python -m tikrec.cli validate PARTS_DIRECTORY --deep --json`
passes for both new final connected original sessions at
`focused-final-frozen/pytest/test_http_client_old_uuid_two_0/media/old.parts`
(copy) and `_1/media/old.parts` (libx264): both return 0/passed, no findings or
stderr. Ten original files per session and all 492 source/test hashes remain
unchanged (`media-validation/verification.json`). No natural/deployed recording
was authorized or accessed; that acceptance remains outstanding.

`process-retirement.json` records zero remaining task-tagged Python/ffmpeg/ffprobe
processes after serial tests and validation. This command-line census alone
does not identify anonymous inherited-pipe children; passing exact native
disposable Job guards separately require zero members and confirmed child exit.
New loopback tests assert native accepted/client/listener retirement, actual
worker/accept-loop joins and original SQLite close thread IDs. Fixture fault
repair and separately supervised cleanup are not product safe-exit guarantees;
unconfirmed owners explicitly report incomplete shutdown until actual retry
retirement is proved. No prior independent runtime review is selected again.

The related selection contains these 24 modules (each `tests/test_NAME.py`):

```text
service service_job service_configuration service_reload
monitoring monitoring_reload monitoring_reload_capacity admission storage_status
automation automation_capacity automation_recovery automation_state
service_runtime service_runtime_automation service_runtime_capacity
service_runtime_connections service_runtime_faults service_runtime_threads
service_runtime_shutdown service_runtime_recovery service_runtime_restart
service_runtime_h_readiness service_runtime_finalizer_retirement
```

Every serial selection executes `-m pytest <modules> -vv -p no:cacheprovider
--capture=tee-sys --basetemp <selection>/pytest`. Exact selections, provenance,
environment, hashes, full failures/output and results are retained under their
labelled evidence directories. Existing client/CLI regressions run in the focused
selection; unchanged recording modules and the three historical independent
acceptance-review modules are not mechanically repeated.

## Historical initial HTTP delivery verification

Native interpreter: `C:\Users\Leandro\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`; base uv CPython 3.11.15 (Windows AMD64), SQLite 3.53.1. Every run verifies the exact isolated cwd/Git root, branch/origin/common Git directory, accepted parent `b9189ae0` and actual `tikrec.__file__` import. Existing ffmpeg/ffprobe are used; no dependency/runtime installation or upgrade. Final runs strip `TIKREC_TOKEN` and use explicit disposable APPDATA/LOCALAPPDATA/XDG configuration/state/TMP/TEMP roots.

Final delivery selections pass on identical frozen source/test bytes. Every selection below preserves its own hashes before/after, actual interpreter/cwd/Git/import provenance and disposable configuration/temp roots:

| Selection | Actual pytest result | Frozen files | Interpretation |
| --- | --- | ---: | --- |
| development-one | 54 passed in 15.90s | 482 | First HTTP/client/CLI faults and legacy calls. |
| development-two | 3 failed, 10 passed in 24.57s | 483 | Fixture mistakes: unknown-room manual starts reused the same creator while prior artifact ownership remained; the accepted guard correctly refused. Distinct creator/proved-room fixture identities fix the tests without changing runtime ownership. |
| development-three | 2 failed, 22 passed in 162.35s | 484 | Fixture compared all H receipts before/after adding seven sessions; addressed original identity/receipt preservation plus eight total H receipts replaces that invalid whole-history equality. |
| development-four | 1 failed, 20 passed in 52.81s | 487 | Collision fixture read a nonexistent `claimed.intent` key before writing; explicit disposable requested output fixes the injection. |
| focused-final (pre-refinement) | 78 passed in 212.64s | 487 | Passing prior implementation snapshot, not the delivery freeze. |
| shutdown-control-before-fix | 1 failed in 1.29s | 487 | Actual new-adapter defect: unfinished request cleanup delayed cooperative capture stop. Early original-UUID stop fixes this while retaining incomplete shutdown/authority ownership. Accepted runtime foundations are unchanged. |
| final-refinement | 10 passed in 52.31s | 488 | Corrected stop during incomplete shutdown, admitted-empty visibility and prepared-success UUID restart/recovered terminal reporting. |
| focused-delivery (fixture correction required) | 1 failed, 81 passed in 316.91s | 488 | Windows native socket methods are read-only; a delegating fault socket now retains the original listener while injecting the intended close failure. No runtime source changed for this fixture correction. |
| focused-delivery-corrected (barrier correction required) | 1 failed, 81 passed in 332.23s | 488 | One writer's 90s source barrier expired while the fixture waited for all six older finalizations before stop; its guarded needs-attention stop correctly did not pretend to signal a retired writer. Hold both writers through the addressed old session's completion, stop/release them, then verify all eight FIFO results. This is not a latency/performance acceptance claim. |
| prestart-close-control-before-fix | 1 failed in 0.64s | 488 | Actual new-adapter defect: secondary socket-close failure masked the known prestart error and discarded the socket owner. Preserve the original error and retain that non-started/socket owner until explicit close retry confirms retirement. |
| prestart-close-corrected | 16 passed in 10.43s | 488 | Exact prestart error/socket retention and original startup/listener/request/shutdown controls pass; final focused selection follows on identical source/test bytes. |
| focused-final-frozen | 83 passed in 302.00s, no skips | 488 | Final connected HTTP/runtime/fault/ownership/recovery plus RemoteClient/CLI selection; unchanged frozen bytes before/after. |
| related-final | 360 passed in 690.75s, no skips | 488 | Appropriate 32-module legacy/service/client/CLI/monitoring/automation/accepted-runtime selection on the identical final freeze; no duplicate independent review. |

Both final source/test manifests contain the same 488 hashes and match delivery bytes. Of 475 accepted predecessor files, 470 remain byte-identical; only remote/control CLI/monitoring source and their two client/CLI tests change. Thirteen new files provide the HTTP modules/helper/tests. Accepted runtime/journal/media/automation/admission/default-service source and package metadata remain unchanged. Git-canonical committed-file/remote equivalence is separately recorded in `delivery-verification.json`, accounting for normal CRLF conversion; the worktree is clean after normal push.

Additional read-only `python -m tikrec.cli validate PARTS_DIRECTORY --deep --json` on `focused-final-frozen/pytest/test_http_client_old_uuid_two_0/media/old.parts` (copy) and `_1/media/old.parts` (libx264) returns 0 / passed for both, no findings/stderr. Both sessions are complete with present output, retained-media checks, final-output inspection and full decode passed. Ten original files per session and all 488 source/test hashes remain unchanged (`media-validation/verification.json`). Recorded finalization input decode is not_checked for copy and clean for libx264; visual integrity remains not_checked. No authorized natural recording was available within this no-production task, so natural/deployed validation remains outstanding.

`process-retirement.json` records zero remaining task-tagged Python/ffmpeg/ffprobe processes after all serial runs and validation. Command-line census alone does not identify anonymous inherited-pipe media children; passing exact native disposable Job guards separately assert zero members and confirmed child exit. Request/monitor/capture/finalizer joins and SQLite retirement are asserted by connected tests and independent fixture cleanup. Fixture repair is never promoted into a product safe-exit claim. Contracts, concise PROJECT_STATE/ROADMAP/#52 and normal vault journal accompany delivery; no prior runtime review is repeated.

Final focused selection is all seven `tests/test_service_http_*.py` modules plus `test_remote.py` and `test_control_cli.py`. The broader selection is these 32 modules (each `tests/test_NAME.py`):

```text
service service_job service_configuration service_reload
monitoring monitoring_reload monitoring_reload_capacity admission storage_status
automation automation_capacity automation_recovery automation_state
recording recording_manager recording_ownership recording_startup recording_worker recording_network
service_runtime service_runtime_automation service_runtime_capacity service_runtime_connections
service_runtime_faults service_runtime_threads service_runtime_shutdown service_runtime_recovery
service_runtime_restart service_runtime_h_readiness service_runtime_finalizer_retirement
remote control_cli
```

Each serial selection uses the verified native interpreter with `-m pytest <modules> -vv -p no:cacheprovider --basetemp <disposable-selection>/pytest`; configuration/state/temp environment variables above point to that selection's disposable directories. The three prior independent-review `service_runtime_acceptance_*` modules are not selected. Legacy construction/routes/reload/automation and underlying ownership/restart regressions are appropriate to the changed HTTP/monitor/client integration; no unchanged whole-suite or duplicate independent review is claimed.

## Connected verification map

| Requirement | Connected test modules / assertions |
| --- | --- |
| One explicit authority, reserve listener first, conflicting legacy arguments, startup/teardown | `test_service_http_lifecycle`: construction rejection, actual listener collision, native runtime/request/monitor start acknowledgement loss, monitor join and listener-close faults; exact primary errors and incomplete results survive. |
| Original queued UUID and two progressing replacements; copy/libx264, eight units and admission | `test_service_http_runtime`: generated whole-tag writer barriers and increasing measured bytes, six old artifact tasks plus two captures, fixed backlog refusal; two physically free slots still refuse at eight units. |
| Stable terminal/restart truth and exact-once narrow recovery | `test_service_http_runtime`, `test_service_http_recovery`: original UUID before/after completion/restart, prepared-success restart through a real recovery barrier, recovered terminal reporting loss, original intent/seal/H/raw and exactly one normal or recovered return. |
| Targeted/ambiguous stop | `test_service_http_runtime`, `test_service_http_projection`: singular 409 across old artifact/replacement ownership, finalization-only no-op, only addressed capture signalled, completed/unknown 404 and canonical-invalid 400. |
| Truthful empty/failure/publication/output reporting | `test_service_http_projection`, `test_service_http_faults`: retained empty evidence visible across reuse, no-assembly is not MP4 completion, actual collision and catalog/output refusal, publication without release is false, audited terminal success survives reporting failure, forged memory flag refuses. |
| Original automatic acceptance/raw identity | `test_service_http_monitor`: automatic native-start acknowledgement loss with raw OFF/ON, two replacements using opposite raw preferences, original durable claim reconciliation and UUID identity, same coordinator monitoring fact. Legacy reload regressions preserve creator-only rules. |
| Sanitized bounded authenticated wire/client/CLI | `test_service_http_faults`, `test_service_http_projection`, `test_remote`, `test_control_cli`: actual byte-backed HTTP parser/serializer/client, five protected routes, malformed controls/UUID, fixed errors, arbitrary nested data omitted, response/creator bounds, older capability refusal and mismatched UUID refusal without fallback; original call shape preserved. |
| Exact original-thread teardown | `test_service_http_faults`, `test_service_http_monitor`, `test_service_http_requests`: request/disconnect and monitor SQLite close faults retain exact live thread; socket close fault retries there; 16-request bound, prestart versus started uncertainty, cooperative capture stop still happens during incomplete shutdown. |

Disposable fixture cleanup independently repairs injected faults and retires retained test owners. That cleanup is never evidence that an earlier product `complete=false` result was safe; tests assert both facts separately.

## Remaining boundaries

This task cannot close #52. PM review follows push. Production/default activation, migration/cutover, retention, broader unfinished recovery, natural-recording/deployed/power-loss acceptance, resource/performance policy, actual non-Windows runtime validation, #48 polling, merge/version/tag/release remain separate gates. Generated Windows media and byte-backed actual HTTP parsing/serialization are disposable offline evidence, not a deployed service/LIVE acceptance claim.
