# Issue #53 independent Fedora retention review

Reviewed 2026-10-01: `f712eb283fc2d4c9c2f67207d38616ab2e795cdd`.

## Verdict and independence

**Locality PASS as a bounded read-only observation. Linux destructive refusal
PASS. No introduced code blocker was reproduced.** The ordinary Linux
pathname-mutation gap is independently confirmed. #53 is not complete: a safe
managed-storage architecture/backend still needs implementation and review.
#51 remains paused / real-media NOT PASSED; its age rule and unused one-session
authorization are unchanged. Fedora remains the intended runtime.

The review was delegated to GPT-6.1 Sol — High in a fresh agent with no inherited
conversation history. The implementation author coordinated test execution and
persisted the findings; the reviewer independently inspected source, kernel APIs
and native disposable probes. No reviewed production code or tests were modified.
No storage architecture, real-media deletion or service restart was performed.

Scope included AGENTS.md, project/roadmap state, issues #53/#51 and comments,
the complete commit diff and implementation report, locality/path proof,
planner/snapshots/inventory/byte binding, authorization, Windows mutation,
executor/preview, lifecycle/policy locks, audit/history, and relevant locality,
Linux-contract, authorization, mutation, lifecycle, policy, audit, executor,
snapshot and POSIX tests.

## Independently reproduced locality evidence

Target: Fedora 44, kernel `7.2.7-200.fc44.x86_64`.

| Path | Held mount ID | fstat device | fstatfs | Native volume identity |
| --- | --- | --- | --- | --- |
| `/` | 43 | 0:37 | Btrfs | 43:0:37 |
| `/home` | 59 | 0:52 | Btrfs | 59:0:52 |
| `/home/leandro/Videos/TikREC` | 59 | 0:52 | Btrfs | 59:0:52 |
| `/tmp` | 64 | 0:53 | tmpfs | 64:0:53 |
| `/boot` | 69 | 259:5 | ext4 | 69:259:5 |

Mountinfo reports superblock device `0:35` for the root/home Btrfs mounts.
[Linux 7.2 Btrfs getattr](https://raw.githubusercontent.com/torvalds/linux/v7.2/fs/btrfs/inode.c)
assigns the stat device from the subvolume anonymous device. The original
mountinfo/st_dev equality assumption is invalid for this observed topology.
The configured root's age-unset public plan now exits 0 with `sessions: []`.

The default native path acquires held evidence. Its component walk uses
`O_PATH | O_NOFOLLOW`, held parents and directory requirements for intermediate
components, then rejects endpoints other than regular files/directories.
Named component identities must match the held objects at the checks. Selected
mount ID must match [descriptor kernel evidence](https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html).
Visible ancestry, duplicate/orphan/cycle/hidden/stacked topology checks remain.
Only positive Btrfs type/mount evidence permits its device difference; explicit
conflicting device evidence and other filesystem mismatches still refuse.
Production logic contains no owner-path special case. Windows/macOS branches
are unchanged; native Windows/macOS execution was unavailable.

Disposable native probes confirmed:

- A nested Btrfs subvolume used mount 59 but device 0:100, producing 59:0:100,
  distinct from its authorized containing volume. The disposable subvolume was
  removed and its enclosing temporary path was confirmed absent.
- A local bind was accepted with a distinct mount-volume identity; it cannot
  silently compare equal to the authorized root volume.
- Stacked mounts refused. A persisted mount-table change also refused when
  binding a directory onto itself left device/inode unchanged.
- Tests cover unavailable evidence, descriptor cleanup, symlinks, parent/root/
  final substitution, unsupported filesystem types and ambiguous topology.

### Observation and policy qualifications

These are sampled read-only observations, not uninterrupted namespace stability
or exclusive mutation authority. In a private user/mount namespace, a bind
mount followed by unmount between the samples restored the original evidence
and was accepted. This ABA limit does not expose an enabled Linux destructive
backend. Changes after an observation are also not prevented by locality proof.
The implementation already describes observed replacement and disclaims
exclusive mutation guarantees; the implementation report has been qualified.

Explicit mountinfo/PurePath injection APIs are synthetic test evidence and do
not establish native authority. Mountinfo source/root omissions and
network-backed block-storage policy are pre-existing scope, not introduced
regressions. The proof establishes a supported visible filesystem; it does not
prove physical storage location or power-loss durability.

## Native mutation feasibility and API survey

The Linux platform gate remains before lifecycle/audit creation. Windows held
mutation, byte binding, root/policy/job checks, removal ordering, durable audit
and first-failure handling are unchanged.

Opening and hashing A does not make a later name designate A. A separate
same-UID process can move A aside and install B at the original or private name.
The held descriptor still refers to A, but dirfd-relative unlink removes B.
This persists under advisory locking and a same-UID 0700 quarantine. A held
parent can also operate in a detached tree after root/parent replacement.
No available reviewed interface supplies the needed artifact-handle/expected-
object deletion for both ordinary files and directories in that namespace.

| Interface | Why it does not close the current gap |
| --- | --- |
| [openat2](https://man7.org/linux/man-pages/man2/openat2.2.html) | Constrains opening/resolution, not subsequent unlink/rename. Native constrained opens and symlink refusal were exercised. |
| [renameat2](https://man7.org/linux/man-pages/man2/rename.2.html), [unlinkat](https://man7.org/linux/man-pages/man2/unlink.2.html) | No expected-inode predicate. No-replace protects destination occupancy, not held source identity. Empty-path artifact removal is unsupported. See [7.2 namei](https://raw.githubusercontent.com/torvalds/linux/v7.2/fs/namei.c). |
| [linkat AT_EMPTY_PATH](https://man7.org/linux/man-pages/man2/link.2.html) | Adds a file link; does not conditionally remove the original name or support directory hard links. |
| [Advisory/POSIX/OFD locks](https://man7.org/linux/man-pages/man2/fcntl_locking.2.html) | Coordination between cooperating actors, not exclusion of uncooperative namespace/data writers. |
| [F_SETLEASE](https://man7.org/linux/man-pages/man2/F_SETLEASE.2const.html) | A native read lease stayed held during name replacement and removal of B. Directory leases returned EINVAL. |
| [F_SETDELEG/F_GETDELEG](https://man7.org/linux/man-pages/man2/F_GETDELEG.2const.html) | Available here, including directory read delegations. Own mutation breaks protection; release and forced-break paths do not provide atomic authority transfer. See the native evidence below. |
| [Mount namespaces](https://man7.org/linux/man-pages/man7/mount_namespaces.7.html), [mount attributes](https://man7.org/linux/man-pages/man2/mount_setattr.2.html) | A private/read-only view does not revoke other writable aliases or descriptors. Write exclusion also blocks the executor; releasing it restores the race. Useful as architecture hardening. |
| [fanotify](https://man7.org/linux/man-pages/man7/fanotify.7.html), [inotify](https://man7.org/linux/man-pages/man7/inotify.7.html) | Namespace notifications and access permission events do not provide conditional unlink/rename authority. Detection afterward is insufficient. |
| [Immutable/append-only flags](https://man7.org/linux/man-pages/man2/FS_IOC_SETFLAGS.2const.html) | Block wanted deletion too; clearing before mutation requires exclusion and is not an atomic conditional removal operation. |
| [Landlock](https://docs.kernel.org/userspace-api/landlock.html) | Restricts the caller and descendants, not unrelated owner processes. Native ABI query returned 10. |
| [fs-verity](https://docs.kernel.org/filesystems/fsverity.html) | Regular-file content protection does not bind mutable names or protect directory removal. |
| [io_uring 7.2](https://raw.githubusercontent.com/torvalds/linux/v7.2/io_uring/fs.c) | Rename/unlink use name-based operations. Linked requests are not a namespace transaction or expected-inode predicate. |
| [Btrfs subvolume destruction](https://raw.githubusercontent.com/torvalds/linux/v7.2/fs/btrfs/ioctl.c), [UAPI](https://raw.githubusercontent.com/torvalds/linux/v7.2/include/uapi/linux/btrfs.h) | SNAP_DESTROY_V2 by ID destroys a whole subvolume, not ordinary artifacts. It cannot preserve the existing allowlist, late-child handling, per-artifact failure/audit boundaries and final-MP4-last order without a new storage architecture. |

### Directory delegations: qualification missing from the original survey

The original report discussed file leases but omitted newer file/directory
delegations. The reviewer acquired/released read delegations on disposable tmpfs
and Btrfs files/directories. A directory delegation is real revocable exclusion;
it should not be described as an unavailable interface or notification only.

On a disposable delegated directory, the holder's own unlink generated SIGIO.
F_GETDELEG reported the breaking target F_UNLCK and unlink returned EINTR.
The handler released protection, and a separate same-UID process moved A aside
and installed B before control returned. A subsequent disposable unlink removed
B while held A remained saved. Refusing on the break would preserve safety but
would not provide functioning deletion; release/recheck relocates the race.
This retry is a test counterexample, never a proposed production/#51 procedure.
[Linux 7.2 userspace lease-manager operations](https://raw.githubusercontent.com/torvalds/linux/v7.2/fs/locks.c)
have no holder-removal exemption, and the target's 45-second break timer can
revoke protection. This expanded investigation confirms the scoped refusal
conclusion rather than claiming every possible Linux architecture is impossible.

## Recommended smallest Fedora architecture

Use the existing two-slot TikREC service as the sole managed-storage authority
under a dedicated non-login UID. A separate standalone broker adds another
service/protocol without a demonstrated current need. This recommendation is
review output, not an implemented or deployment-approved architecture.

- Place the managed recording root beneath protected ancestors, for example
  `/var/lib/tikrec/recordings`, with a root-owned parent preventing owner-driven
  root replacement. A service-owned leaf under owner-writable `/home` is insufficient.
- Install service code, Python environment, unit, dependencies and import/search
  paths under trusted administrator ownership. The editable owner-controlled
  `~/TikREC/.venv` cannot be that service's trusted runtime. Exclude owner-writable
  code/configuration hooks, executable overrides and environment injection.
- Give the owner read/traverse access to media/evidence, with authenticated
  bounded inspection/export tools. No directory/file write ACL, writable alias,
  service-UID impersonation, writable descriptor export or ptrace-equivalent access.
- Protect authoritative configuration, policy lock, both durable job stores,
  lifecycle lock and external audit. Owner policy/protection changes become
  validated mediated promotions sharing the final mutation authority.
- Mediate capture, recovery, finalization, imports and retention through TikREC.
  Direct CLI writes into managed storage delegate or refuse. Exclude new mutation
  work and quiesce both slots plus every mutating child/descriptor/map before
  proof, through final removal. Advisory locks coordinate trusted participants;
  enforced ownership is the security boundary.
- Preserve pinned no-follow identities, fresh whole-root/job/policy/byte proof,
  no-replace quarantine, durable intent/attempt before mutation, pinned-parent
  fsync before deleted audit, retained/control-first and final-MP4-last order,
  first-failure preservation and evidence-preserving interruption without retry.
- Ordinary owner processes remain excluded from writes; trusted service code and
  administrator/kernel integrity remain prerequisites. Capability reduction and
  a private mount namespace harden this boundary but do not replace ownership.

### Migration and recoverability

Start new managed recordings under service ownership from inception. Existing
owner-writable sessions remain legacy evidence and outside Linux destructive
eligibility until deliberately imported/sealed. Move/chown/chmod alone cannot
revoke existing writable descriptors or aliases. Import must create fresh
service-owned objects, preserve originals, verify a coherent complete copy and
establish exclusive destination authority before any new authorization.

Preserve original manifests, session identity, and an old/new path/hash ledger.
Absolute parts/output paths and both durable job references must be adapted only
in copied control documents under an explicit migration protocol. Never silently
rewrite forensic originals or leave stale durable references after relocation.
Historical audit files remain intact and associated with their historical roots;
root strings, volume/inode fingerprints and root-hashed filenames must not be
rewritten as new-root history. Use separate new-root audit history, and never
reuse an old intent to authorize migrated objects. Active/job-linked sessions
must not be moved. Migration does not consume #51's deletion allowance.

Read-only owner access and explicit exports retain recoverability without
returning namespace write authority to the owner. Fresh backend review and
disposable end-to-end validation are still required before real-media deletion.

## Tests, reproducibility and limits

- Reviewer: 65 locality/Linux-contract/POSIX tests passed on default tmpfs, then
  65 passed on disposable `/var/tmp` Btrfs basetemp with isolated configuration.
- Coordinator: 159 focused locality/lifecycle/policy/authorization/audit/history
  tests passed, 72 skipped. Full isolated-config offline suite: 1,552 passed,
  278 skipped, 19 passed subtests. Windows skips are not fresh Windows validation.
- These workspace suites include pre-existing uncommitted Fedora corrections;
  the review does not approve or commit those unrelated changes.
- All 16 baseline dirty/configuration file hashes stayed unchanged before
  documentation updates. The watcher PID 15870 and invocation
  `a110217800574d858df22dac886890f8` remained unchanged; both slots were idle.

Successful disposable probe scripts are retained at
`/tmp/tikrec-53-review-ct81zrh8/independent-linux-probes.py` and
`/tmp/tikrec-53-review-ct81zrh8/independent-mount-probes.py`. Run from the repository
with `.venv/bin/python -B SCRIPT`; each creates its own temporary paths. Mount
operations are confined to a child user/mount namespace. These ephemeral scripts
are convenience evidence; the measured values, operation sequences, limitations
and primary source references above are the durable review record.

Nonblocking documentation qualifications were recorded and the implementation
report updated: sampled mount stability, available delegations and their gap,
and the existing service identity as the smallest recommended architecture.
Reviewed production code/tests were not changed. #53 stays open for managed
storage/backend work; #51 stays paused / NOT PASSED. No other roadmap issue was
started. v0.10.0 remains released and v0.11.0 remains unreleased.
