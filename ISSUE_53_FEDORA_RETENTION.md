# Issue #53 Fedora retention locality and mutation contract

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
named components. The mount table must remain unchanged during the observation.
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
for the entire proof/mutation interval. One route is a dedicated storage broker
under a distinct security identity, owning the root and its mutation-controlling
ancestors in a protected mount namespace. It would create recordings under that
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
