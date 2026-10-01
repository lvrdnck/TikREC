# Issue #53 Fedora retention locality and mutation contract

## Approved implementation checkpoint (2026-10-01)

**The bounded managed-storage architecture/backend slice is implemented;
#53 stays open for fresh independent backend review and disposable Fedora
end-to-end validation.** Earlier checkpoints below describe the historical
unmanaged namespace investigation and its review, not a review of this backend.

### Owner decision and enforceable boundary

The owner approved the independent review's smallest architecture: reuse the
existing two-slot TikREC service as the sole authority under a dedicated non-login
Linux UID. A standalone broker is outside this slice. Fresh service-owned media
and state live below administrator-owned, non-writable ancestors; ordinary owner
accounts receive evidence read/traverse access without namespace/data writes.
Deployed code, Python runtime/imports, definition and token are administrator
controlled. Startup refuses an editable owner checkout, login/root identity,
non-isolated Python, capabilities, unsafe permissions/ACLs/links, ambiguous
locality or missing root-owned storage genesis. Administrator/kernel integrity
is an explicit prerequisite; matching mount snapshots are never claimed as
uninterrupted exclusion. The dedicated UID cannot mount/impersonate another UID
under the supplied unit restrictions.

`managed_provision.py` creates only new objects and refuses every existing base
or definition before mutation. Root and state are 0750, service-created files
have no group/other write permission, definition/token/code are root controlled,
and a storage UUID binds genesis to the canonical root. No legacy adoption or
ownership conversion exists. See [FEDORA_MANAGED_STORAGE.md](FEDORA_MANAGED_STORAGE.md)
for the layout, administrator preparation, unit/sysusers templates and eventual
verified-copy/import constraints. Original media, manifests/session identity,
old/new path/hash ledger, durable job references and old root-bound audit history
must be preserved by that separate future protocol.

### Service coordination and Linux mutation

- Opt-in `serve --managed-storage` wires protected config, both durable slot jobs,
  automation and audit before service recovery/monitoring. Output is limited to
  immediate visible MP4 children of the fixed root. Existing capture/recovery/
  finalization lifecycle leases and state promotion reserve a shared service gate.
  Starts reserve admission before job persistence/worker launch; monitoring skips
  a blocked cycle without disabling future automation.
- Retention obtains exclusive admission and requires both slots/workers naturally
  quiescent, no other process using the service UID, and no writable media file
  descriptor or mapping. It never stops a recording to permit deletion. The
  singleton lock, pinned root/ancestor identities, permissions, state/root trees
  and locality are rechecked throughout mutation; policy/jobs/root/audit paths
  are fixed to the protected authority. Advisory locks coordinate trusted code;
  kernel ownership and service admission provide the exclusion boundary.
- Linux holds no-follow artifact and parent descriptors, verifies authorized
  identities and SHA256 bytes/empty membership, quarantines with
  `renameat2(RENAME_NOREPLACE)`, then checks identity/proof again before pinned-parent
  unlink/rmdir. No-replace protects destination occupancy; ownership plus service
  exclusion protect the source name through removal. Parent fsync precedes
  `deleted`. The original schema-1 outside-root audit, first-failure precedence,
  retained/control-files-first and final-MP4-last order remain. An interrupted or
  failed operation preserves remaining/original/private evidence and cannot
  silently retry, repair or claim completion.
- Authenticated bounded POST preview/delete/policy routes reuse the existing
  service. The public `retention delete UUID --server URL --token-file FILE`
  displays exact target facts, requires exact UUID consent and submits once.
  The preview digest only vetoes changed fresh authorization. Policy requests
  accept age/protect/unprotect values without selectable roots/commands/state.
  A missing/interrupted/malformed delete response yields uncertainty/3 and no
  retry; display failure preserves a proven service result. Ordinary services
  expose no managed endpoint; unmanaged Linux/macOS deletion still refuses.

### Verification and limits

Tests exercise actual native Linux kernel permissions and mutation primitives
in WSL Ubuntu, using exclusively disposable `/var/lib/tikrec-53-disposable-*`
roots and separate service UID 60031 / ordinary reader UID 60032. The fixture
injects installed-runtime verification because the test checkout is deliberately
untrusted deployment code; all actual ownership, exclusion, locality, process/
resource, pinned mutation and durability checks remain active. Runtime rejection
is separately tested. No test accesses configured real media or needs LIVE/network.

Native probes prove the reader can read evidence but cannot write, unlink,
rename/substitute files/directories, create late children, replace root/ancestors,
impersonate the service UID, signal it or access its process descriptors.
Owner attempts run before every mutation and after held-byte proof. Tests cover
unsafe root/state/definition/artifact ownership, missing genesis, state redirects,
pinned root replacement, both real controller slots capturing fresh disposable
parts under the service UID, writer/policy/lifecycle exclusion, UID children,
writable descriptors/mappings, occupied file/directory quarantine destinations,
wrong bytes, late children, private substitution after proof, original/private
reappearance, job/policy changes, interruption, failed parent sync, first error
versus native close fault, audited order and final MP4 last. Remote/API tests cover
strict bounded JSON, authentication integration, exact consent, preview veto,
fixed authoritative paths, single submission, lost responses and truthful output.

The full cross-platform run exposed existing Windows-only destructive fixtures
and four POSIX test assumptions: path separators, audit entry sync occurring
before append, directory enumeration order, and an unrelated finalize test that
attempted filesystem inspection before its intended malformed-config assertion.
Tests now preserve Windows assertions and use the separate native managed fixture
for Linux destruction; no production behavior was weakened to pass those cases.
The configured Windows temporary directory also refused pytest cleanup, so all
runs use unique disposable basetemps and isolated APPDATA/XDG_CONFIG_HOME.

Final isolated offline results on the completed source:

| Runtime | Full suite | Focused final verification |
| --- | --- | --- |
| Windows Python 3.11.15 / pytest 9.1.1 | 1,752 passed, 91 skipped, 19 subtests, 75.91 s | CLI outcome/delete/automation: 68 passed, 1 skipped |
| WSL Ubuntu native Linux Python 3.14.4 / pytest 9.1.1 | 1,563 passed, 280 skipped, 19 subtests, 34.41 s | Managed native mutation + owner CLI: 30 passed |

Windows full command: `python -m pytest -q --tb=short -p no:cacheprovider
--basetemp=.tmp/issue53-win-full-final`, with APPDATA set to
`.tmp/issue53-config-full-final` for this process only. Native command: WSL root,
`/var/tmp/tikrec-53-test-runtime/bin/python -m pytest
/mnt/c/Users/Leandro/dev/TikREC/tests -q --tb=short -p no:cacheprovider
--basetemp=/var/tmp/tikrec-53-linux-full-final`, with
`XDG_CONFIG_HOME=/var/tmp/tikrec-53-isolated-config`. The Linux run reads the same
Windows checkout; no repository synchronization by folder copying occurs.
The disposable pytest runtime adds no TikREC package dependency.

The WSL unit parser reported only expected development-checkout permissions and
the absent `/opt/tikrec/venv/bin/python`; full `systemd-analyze verify` is not
passed because this task did not install/activate a production runtime. A real
root-owned isolated installation, Fedora/Btrfs and systemd sandbox integration,
SELinux policy if needed, FFmpeg/FFprobe child behavior, real-LIVE recording and
power-loss behavior remain unverified. Existing offline Windows handle/mutation
tests run on Windows. No physical storage-durability claim is made.

**Safe next action:** review the exact pushed backend commit independently in a
fresh context, then provision a purely disposable Fedora managed installation and
exercise both slots, owner controls, refusal/fault paths and audit end to end.
Do not restart/replace the real service or import existing media. #51 remains
paused / NOT PASSED, its real age policy untouched/unset and deletion allowance
unused; all Gracie/forensic/evidence exclusions remain. v0.10.0 is released,
v0.11.0 unreleased. This Windows clone was initially tracked-clean and retains
its pre-existing untracked test directories; unrelated Fedora clone changes were
not touched. No other roadmap issue, release/tag, or real-media deletion occurred.

## Independent review checkpoint (2026-10-01)

Fresh independent review of `f712eb2` confirms the locality correction as a
bounded read-only observation and the Linux pathname-mutation gap, with no
introduced code blocker reproduced. The expanded investigation covers available
file/directory delegations and sampled mount ABA limits. The smallest recommended
architecture is the existing TikREC service under a protected dedicated identity;
a standalone broker is optional. See
[ISSUE_53_FEDORA_RETENTION_REVIEW.md](ISSUE_53_FEDORA_RETENTION_REVIEW.md).
No architecture was implemented. #53 remains open and #51 remains paused.

## Outcome (2026-10-01)

**Locality correction implemented; native Linux destructive retention remains
blocked on an architectural safety boundary. #53 stays open.** Fedora is the
intended runtime. Returning to Windows is not the resolution for #53 or #51.
No real-media deletion, age-policy change, or service stop/restart occurred.
#51 remains paused / real-media NOT PASSED, with its one-deletion authorization
unused. An independent fresh-context retention review is required before any
future #51 Fedora validation; locality success alone cannot resume deletion.

## Actual Fedora evidence and correction

The public `.venv/bin/tikrec retention plan --json` originally exited 1 with
`retention root locality could not be proven` for `/home/leandro/Videos/TikREC`.
The real mount table has these relevant entries:

```text
43 1 0:35 /root / ... - btrfs /dev/nvme0n1p6 ... subvolid=256,subvol=/root
59 43 0:35 /home /home ... - btrfs /dev/nvme0n1p6 ... subvolid=257,subvol=/home
```

Held descriptors for `/`, `/home`, and the configured root report mount IDs
43, 59, and 59 respectively. Their `fstat` devices are 0:37, 0:52, and 0:52.
All three `fstatfs` calls report Btrfs magic `0x9123683e`. The original
`retention_locality.py` compares the selected mount's 0:35 with the path's 0:52
and refuses. This is a genuine Btrfs identity-model mismatch, not an unknown
filesystem or a path-specific exception. Linux's [Btrfs getattr implementation](https://raw.githubusercontent.com/torvalds/linux/master/fs/btrfs/inode.c)
sets the returned device from the subvolume root's anonymous device.

The correction retains visible mount ancestry, stacking/duplicate/cycle checks,
and the supported local-filesystem restriction. Native Linux observations now
open every component relative to a held parent with `O_PATH | O_NOFOLLOW`, reject
non-file/non-directory endpoints, and compare the opened identities with the
named components. Sampled mount tables must agree; observed changes refuse.
This does not prove uninterrupted stability or detect mount/unmount ABA between
samples.
The descriptor's [kernel mount ID](https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html)
must match the selected visible mount. Only actual Btrfs `fstatfs` evidence can
justify Btrfs's distinct subvolume device; other device mismatches still refuse.
Native volume identity includes mount ID and the observed device, so a nested
Btrfs subvolume cannot silently become the same authorized volume. Missing
kernel evidence, links/redirection, replacement, remote/network/overlay/FUSE,
ambiguous topology, and incompatible devices remain fail-closed. This observation
is read-only and does not claim to seal a pathname against later mutation.

After correction the normal public command exits 0 with:

```json
{
  "retention_max_age_days": null,
  "root": "/home/leandro/Videos/TikREC",
  "sessions": []
}
```

The actual root remains empty. The watcher remains healthy and idle in both
slots, with age unset. It was not restarted to load new code; existing runtime
processes continue with their already imported modules until a separately
appropriate restart. No such restart is part of this correction. Monitoring
continues, but the latest Gracie observation is `unknown` / `unverifiable`; this
health check does not establish successful LIVE resolution or recording.

## Why a pathname backend cannot satisfy the current contract

The existing Windows primitive holds the artifact without data/delete sharing,
then renames and deletes through that exact handle. The Linux requirement must
cover a non-cooperating process with namespace/data access, not merely TikREC
writers honoring the lifecycle lock. Ordinary recordings currently live in
owner-writable directories under the same UID as the application.

A deterministic counterexample on disposable Linux files and directories is:

1. Open object A no-follow; hold its parent; verify A's inode and file hash.
2. Another same-UID process renames A aside and installs object B at the name.
3. The held descriptor still refers to A, but `unlinkat(parent, name, ...)`
   removes B. The same failure works after quarantine proof at a private name.

Repeated checks only move the race to the gap before the final syscall.
[unlinkat](https://man7.org/linux/man-pages/man2/unlink.2.html) is name-relative and
provides no expected-inode comparison or `AT_EMPTY_PATH` artifact-handle removal.
The native tests verify empty-path unlink is rejected for files and directories.
[renameat2 with RENAME_NOREPLACE](https://man7.org/linux/man-pages/man2/rename.2.html)
atomically protects the destination, but does not bind the source to a previously
held descriptor. The counterexample also substitutes the source before rename.

An open parent protects where a relative operation runs; it does not prove that
parent is still the authorized root. Moving/replacing the parent/root lets a
later relative unlink act in the detached tree. Nonempty-directory removal
refuses late children, but an empty substituted directory remains removable.
[Advisory locks](https://man7.org/linux/man-pages/man2/fcntl_locking.2.html) do not
prevent same-UID namespace replacement or data writes after a hash. Linux
[file leases](https://man7.org/linux/man-pages/man2/F_SETLEASE.2const.html) cover
regular-file open/truncate and can be forcibly broken; they do not supply a
file-and-directory conditional namespace deletion primitive.
[linkat AT_EMPTY_PATH](https://man7.org/linux/man-pages/man2/link.2.html) can add a
file link, not remove its original name; directory hard links are unavailable.
Newer file/directory delegations are also available on this Fedora kernel.
Independent native review confirms they provide revocable namespace exclusion,
but the holder's own unlink breaks protection; releasing it before deletion
reopens substitution, and forced break can revoke it. See the
[delegation interface](https://man7.org/linux/man-pages/man2/F_GETDELEG.2const.html)
and the independent review's native counterexample. They do not provide atomic
release-and-expected-object removal.
A same-UID 0700 quarantine directory does not exclude another same-UID process.
Notifications and private unpredictable names are detection/privacy tools, not
an atomic identity predicate.

Thus the tested Linux userspace primitives do not implement the current contract
in an owner-writable, concurrently replaceable namespace. This is a scoped
technical conclusion, not a claim that all possible Linux architectures are
incapable of safe deletion. No Linux mutation backend was shipped. The production
platform gate, Windows backend, executor ordering, audit intent/publication,
policy/job/root guards, and failure reporting remain unchanged. No audit intent
was created against real media. Retained/control-before-final-MP4 ordering and
failure boundaries remain Windows implementation guarantees, not newly validated
Linux deletion behavior.

## Narrowest safe Fedora architecture to evaluate

Retain the corrected read-only public workflow and the mutation refusal now.
A possible future native backend needs enforceable exclusion of other writers
for the entire proof/mutation interval. The independent review recommends using
the existing TikREC service under a dedicated non-login identity, owning the root
and protected mutation-controlling ancestors, with trusted code/configuration/
state and read-only owner access. A standalone broker remains an optional larger
design. A protected mount namespace is additional hardening, not a replacement
for ownership. The service would create recordings under that
ownership from inception, mediate all namespace/data writes, quiesce/revoke
writers before proof, prevent leaked writable descriptors and alternate links,
and hold exclusive authority through final policy/job/root revalidation and
mutation. Merely moving existing owner-writable files into a private directory
or changing permissions does not revoke already open descriptors.

Only after that ownership model is established could pinned no-follow directory
handles, verified kernel mount/subvolume identities, no-replace quarantine,
held-file hashes, intent-before-mutation, directory fsync-before-deleted audit,
ordered removal, and first-failure preservation form a safe Linux implementation.
Recovery and interrupted operations would still preserve evidence with no retry.

This is a design prerequisite, not an approved or implemented broker. Introducing
another service identity, storage ownership/migration, access mediation, and
installation privileges affects deployment and persistent user data. It requires
an owner architecture decision and independent review. No installation, ownership
change, media relocation, kernel module, or threat-model relaxation was attempted.
A new kernel conditional-removal/namespace-exclusion primitive could instead be
evaluated if genuinely available; ordinary dirfd unlink cannot substitute for it.

## Verification and limits

- Focused retention suite: **274 passed, 273 skipped**.
- Full offline suite with isolated temporary `XDG_CONFIG_HOME`: **1,552 passed,
  278 skipped, 19 passed subtests**.
- The first non-isolated full run had two LIVE CLI diagnostic-path assertions
  fail because they read the owner's configured output directory. The isolated
  run passed without changing those unrelated tests or owner configuration.
- Native synthetic-topology and no-follow tests cover Btrfs device evidence,
  mismatches, remote/overlay/FUSE, hidden/stacked/orphan/cyclic mounts, links,
  parent/root/final replacement, unavailable evidence, and descriptor cleanup.
- Disposable cross-process counterexamples cover original/private substitution,
  occupied destinations, source substitution before rename, writes after hash,
  late directory children, detached parents/roots, and empty-path unlink refusal.
- Public deletion against one disposable fixture refuses before audit/lifecycle
  creation and preserves every retained artifact, final MP4, and configuration.
- Windows behavior/tests were not modified. Native Windows execution was not
  available; Windows-only skips do not count as new Windows validation.
- The full suite includes unrelated pre-existing Fedora test corrections, which
  remain uncommitted and are not included in the #53 commit.

No other roadmap task was started. #53 remains the single active blocker for
#51 and v0.11. A fresh independent retention review must assess the locality
change and this feasibility evidence before architecture work or real-media
validation can advance. v0.10.0 remains released; v0.11.0 remains unreleased.
