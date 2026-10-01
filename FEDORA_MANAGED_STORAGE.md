# Fedora managed storage (unreleased issue #53 development)

The owner approved the independent #53 review's smallest architecture: the
existing two-slot service owns new managed recordings under a dedicated non-login
UID. Implementation is complete; fresh independent backend review and disposable
Fedora end-to-end validation are still required before real-media deletion or #51
resume. This task did not deploy, restart, replace or stop the real service,
import legacy media, or delete a real recording.

## Protected layout

| Location | Owner / mode | Purpose |
| --- | --- | --- |
| `/opt/tikrec`, environment and installed package | root; no group/other writes | Trusted executables, dependencies and imports |
| `/etc/tikrec`, unit and storage definition | root; no group/other writes | Administrator-controlled deployment |
| `/etc/tikrec/token` | root:`tikrec-readers`, 0640 | Authenticated owner control |
| `/var/lib/tikrec` and its ancestors | root; no group/other writes | Prevent recording/state root replacement |
| `/var/lib/tikrec/recordings` | `tikrec`:`tikrec-readers`, 0750 | Fresh managed media |
| `recordings/.tikrec-managed.json` | root:`tikrec-readers`, 0440 | Storage UUID and canonical root |
| `/var/lib/tikrec/state` | `tikrec`:`tikrec-readers`, 0750 | Authoritative config, two jobs, automation and audit |

Only the dedicated UID has namespace/data write permission. The reader group
grants read/traverse access without UID impersonation. Access/default ACLs,
writable ancestors, symlinks, special files, multiply linked files and ambiguous
or unsupported volumes refuse. A service-owned leaf beneath owner-writable home
ancestry is ineligible. Do not grant ordinary accounts sudo/run-as, ptrace,
writable descriptors/aliases, executable overrides, or writable import hooks.
Administrator/kernel integrity and trusted service code remain prerequisites.
Ownership is the security boundary; advisory locks coordinate trusted actors.

Startup requires native Linux, the dedicated nonzero UID with `nologin`/`false`
shell, isolated Python, zero effective/permitted/ambient capabilities,
non-dumpable execution and no new privileges. Runtime/import locations, loaded
modules and installed package files must be administrator controlled. Root and
ancestor identities are pinned. The root-owned definition and genesis marker
must agree. Existing owner-writable media is never adopted automatically.

## Administrator preparation after the review gates

These instructions were not executed against the real service in this task.
Source synchronization between computers continues through GitHub only.

1. Select an immutable reviewed GitHub commit. Install Python 3.11+, FFmpeg and
   FFprobe from trusted Fedora packages. Create root-owned 0755 `/opt/tikrec` and
   `/etc/tikrec`. Install the reviewed TikREC wheel with `pip install --no-deps`
   into root-owned `/opt/tikrec/venv`. Do not use an editable installation or the
   owner's checkout/environment. TikREC adds no runtime dependency.
2. Install `deployment/tikrec-managed.sysusers.conf` under `/usr/lib/sysusers.d/`
   and run `systemd-sysusers` for that file. It defines the non-login `tikrec`
   account and `tikrec-readers`. Add the owner only to the read-only group.
   The unit runs with that group so newly created evidence is readable.
3. Obtain the isolated interpreter's `sysconfig.get_path('purelib')`, then run:

   ```sh
   /opt/tikrec/venv/bin/python -I -B -m tikrec.managed_provision \
     --code-directory /opt/tikrec/venv/lib/python3.X/site-packages
   ```

   Substitute the verified installed path. Provisioning requires root and refuses
   every existing base or definition. It creates fresh storage/state, a new UUID,
   and age-unset configuration. It never chowns, moves, rewrites or deletes legacy
   media. Failure preserves partial new provisioning for inspection; no automatic
   cleanup/adoption/retry protocol exists.
4. Create a random bearer secret in root-owned `/etc/tikrec/token`, 0640 with
   group `tikrec-readers`; protect the owner's client copy. Install the reviewed
   unit as `/etc/systemd/system/tikrec-managed.service`. The template binds
   loopback **8766**, avoiding silent replacement of the current 8765 service.
   Administrator-controlled binding may use the established LAN/Tailscale policy.
5. Run `systemd-analyze verify`. The template drops capabilities, prevents new
   privileges/namespaces, isolates the mount view, protects home/system paths,
   and permits writes to managed media/state plus private temporary storage.
   Inaccessible/opaque process evidence refuses retention; do not bypass it.
6. Complete independent backend review and disposable Fedora end-to-end
   validation before arranging production activation. Starting/switching the
   real service and legacy import remain separate work.

Managed state is `state/config.json`, `job.json`, `job-2.json`, `automation.json`
and `retention-audit/`. Output must be an immediate visible `.mp4` child of the
fixed root. Capture, startup recovery, finalization and automatic/manual starts
share the service authority. Direct owner recording, finalization, recovery or
configuration writes refuse through kernel permissions. Read-only inspection
and copying evidence to an external export destination grant no write authority
over the managed original.

## Explicit owner controls

```sh
tikrec retention delete SESSION_UUID --server http://127.0.0.1:8766 \
  --token-file CLIENT_TOKEN_FILE [--confirm SESSION_UUID]
tikrec remote retention-policy age 7 --server http://127.0.0.1:8766 \
  --token-file CLIENT_TOKEN_FILE
tikrec remote retention-policy age disabled --server http://127.0.0.1:8766 \
  --token-file CLIENT_TOKEN_FILE
tikrec remote retention-policy protect CREATOR --server http://127.0.0.1:8766 \
  --token-file CLIENT_TOKEN_FILE
```

`unprotect` uses the same policy syntax. Only validated age/protection changes
are promoted through the protected policy lock and mutation gate. Root/runtime/
state selection is not a request field. Authenticated bounded POST routes are
`/managed/retention/preview`, `/managed/retention/delete` and
`/managed/retention/policy`; ordinary services expose none of these operations.

Deletion shows the exact service root, UUID, creator, paths and byte totals;
an explicit ROOT is refused. The owner confirms the exact UUID once. A preview
digest only vetoes changed fresh proof; it is never saved authority. Each proof
holds exclusive service mutation admission and checks both slots, worker threads,
service-UID peers/children, writable media descriptors and mappings. Active or
unresolved work refuses; recordings are never stopped to make storage quiescent.
Monitoring skips mutation during exclusion and can run again afterward.

Full root/job/policy/identity/locality/byte authorization and audit durability
remain. No-follow artifact/parent descriptors stay under enforced exclusion.
`renameat2(RENAME_NOREPLACE)` preserves occupied quarantine names; held bytes,
identity and empty membership are checked before removal. The pinned parent is
fsynced before `deleted`; retained/control files precede the directory and final
MP4. First failure preserves evidence and prevents completion. No retry, repair
or stale-operation resume exists. Schema-1 audit stays outside recordings in
`state/retention-audit/SHA256(root).jsonl`, with group read and no group write.
A lost delete response is uncertain/3: preserve audit/artifacts without retry.
Windows semantics and unmanaged Linux/macOS destructive refusal remain intact.

## Legacy media and remaining gates

Legacy owner-writable sessions remain ineligible. A later approved verified
copy/import protocol must create fresh service-owned objects while preserving
originals, manifests/session identity and an old/new path/hash ledger. Adapt only
copied absolute paths and durable job references. Keep historical journals bound
to their original roots, create separate new-root history and never reuse an old
intent. Storage identity and fixed-root interfaces leave import explicit; no
import endpoint is scaffolded here.

Actual evidence and limitations are in [ISSUE_53_FEDORA_RETENTION.md](ISSUE_53_FEDORA_RETENTION.md).
Native Linux tests used disposable two-UID storage in WSL. They do not establish
a fresh Fedora/Btrfs deployment, independent review, real-LIVE capture or power-loss
validation. #53 remains open. #51 stays paused / NOT PASSED, with the real age
policy untouched and its one-deletion authorization unused.
