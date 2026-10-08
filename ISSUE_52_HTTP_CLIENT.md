# Issue #52 — isolated HTTP/client compatibility

## Authority and current status

[PM decision 6056452748](https://github.com/lvrdnck/TikREC/issues/52#issuecomment-6056452748) accepts review `b9189ae0` and the implemented Windows runtime at accepted R14–R15 baseline `26cc0e7d`. This single successor is experimental/default OFF. Complex / GPT-6.1 Sol — High MODEL GATE and owner PROCEED recorded. #52 OPEN/SINGLE ACTIVE, #48 OPEN/PAUSED, #28 unresolved; owner decisions None.

**COMPLETE FOR PM REVIEW:** this bounded transport/client slice. Final frozen native Windows suites: **83 focused / 360 related passed**, no skips; both generated copy/libx264 original sessions pass normal CLI deep validation. The prior review is accepted, not repeated; overall #52/deployment acceptance is not claimed. Execution evidence is in `C:\Users\Leandro\TikREC-tests\issue52-http-client-20261008`; development failures are preserved separately from final frozen results. The exact normally pushed Refs #52 delivery is recorded in #52's reconciled current checkpoint/comment. PM review only next; no automatic successor.

## Implemented contract

`IsolatedRecordingHTTPServer` in `tikrec/service_http_runtime.py` takes an already constructed passive `IsolatedServiceRuntime` plus explicit matching `RecordingAdmission`, `AutomationCoordinator` and `CreatorMonitor`. Their media/storage/automatic-state paths belong to the caller's isolated composition. Legacy/backend arguments conflict before binding/work. The listener binds before runtime/monitor start. No catalog/job-store/legacy recovery authority is implicitly created; ordinary `serve` and configuration never select this class.

Only this backend advertises `durable_finalization_v1`. Route names, start fields and 202 acceptance stay; two slot IDs stay. `active_count`, `available_slots`, `available` and additive `capture` describe physical capture bindings. `admission_available`/fixed `admission_reason` describe permission to start: eight artifact units may leave two physical slots free while new admission refuses. Additive `finalization` reports counted units/tasks, the single worker and fixed paused reasons. Unknown counts are null. `/recordings` keeps exactly two current/latest slot snapshots, at most eight `finalization_sessions` tasks and at most eight `outstanding_sessions` owners. The latter includes retained empty-capture evidence with no assembly task, so reuse cannot hide those counted/pinned owners. Every session retains immutable `origin_slot_id`.

Authenticated `GET /sessions/UUID` addresses original capture/finalization/terminal history by canonical UUID across slot reuse/restart; it never exports all history. Invalid UUID is 400, unknown 404. Capture closure, publication, no-assembly/empty, failure or a free slot cannot expose completed MP4 output. Only audited owned terminal success/recovery release evidence exposes `output_completed=true` and `final_output_path`; this is durable historical completion evidence, not a guarantee against later external deletion. Closed/restarted unmeasured byte counters are null.

Singular status/stop retains ambiguity across all outstanding owners (409). Targeted live-capture stop only signals that capture. Finalization-only UUID returns 202 `capture_already_closed` without changing assembly or replacement capture. Completed/unknown UUID stop is 404. No new HTTP control fields, automatic retries or recovery authority exist.

`RemoteClient.status(session_id=None)` preserves the original `/recording` call when omitted. `tikrec remote status --session-id UUID` validates UUID, checks `/health` capability and uses only `/sessions/UUID`. An older server without that capability returns an explicit unsupported error; there is no latest-slot fallback. Returned UUID must match. Old clients may still read ordinary routes, but `active=false` or slot reuse cannot mean MP4 success on the isolated backend; compatibility is additive on wire, intentionally different in phase meaning.

Transport uses allowlisted identity/counter/state/path/reason projections and a 65,536-byte response ceiling. Local paths are capped at 1,024 UTF-8 bytes and both output/parts paths are checked before start acceptance; monitoring/selected creator projections are capped at 100. Existing bearer/bind/origin/body/redirect protections remain. Arbitrary exception text, stderr, signed transports, SQLite/internal capabilities and controls never serialize. At most 16 non-daemon request owners are retained. Every request/disconnect cleans SQLite on its original thread; failed teardown holds the thread/object for a later explicit shutdown retry. The supplied monitor's original thread is likewise retained across lost startup acknowledgement/SQLite cleanup. Shutdown fences HTTP/callback starts and requests original UUID capture stops before waiting on uncertain request/monitor owners. Listener close and fixture repair do not establish safe product exit; startup errors retain the primary exception and attach reachable server/shutdown state. Listener-close failure preserves the socket and reports incomplete transport even when runtime authority retirement is confirmed.

Schema 10, accepted R1–R15, two captures/one finalizer/eight units, original raw/session/control/H evidence, original automation acceptance/raw preferences and creator-only reload, exact-once accounting and narrow prepared-success recovery remain unchanged. A small optional CreatorMonitor thread factory observes native ownership without altering default scheduling/resolution policy.

## Verification evidence

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
