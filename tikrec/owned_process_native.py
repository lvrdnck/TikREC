"""Creation-time private Job Object containment, never create-then-assign or breakaway."""

import ctypes as C
import subprocess

from .owned_process_api import Accounting, D, ExtendedLimits, H, ProcessInfo, S, StartupEx, check, creation_identity, identity, kernel
from .owned_process_streams import NativeStreams


class NativeChild:
    """Retain exact process/thread/job handles until whole-job exit is proved."""

    def __init__(self):
        self.api, self.job, self.process, self.thread = kernel(), None, None, None
        self.streams, self.initial = NativeStreams(self.api), None

    def create(self, executable, arguments, cwd, fault):
        """Associate the suspended child with its private job inside CreateProcessW."""
        fault("before_job")
        self.job = check(self.api.CreateJobObjectW(None, None))
        # An unnamed, noninheritable job is private; the service never joins it.
        check(self.api.SetHandleInformation(self.job, 1, 0))
        fault("after_job")
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, no breakaway.
        check(self.api.SetInformationJobObject(self.job, 9, C.byref(limits), C.sizeof(limits)))
        observed = ExtendedLimits()
        check(self.api.QueryInformationJobObject(self.job, 9, C.byref(observed), C.sizeof(observed), None))
        if observed.basic.flags != 0x2000:
            raise ValueError("private job kill-on-close containment unavailable")
        fault("after_limits")
        standard = self.streams.open()
        size = S()
        self.api.InitializeProcThreadAttributeList(None, 2, 0, C.byref(size))
        if not size.value:
            raise C.WinError(C.get_last_error())
        attributes = C.create_string_buffer(size.value)
        check(self.api.InitializeProcThreadAttributeList(attributes, 2, 0, C.byref(size)))
        try:
            jobs, inherited = (H * 1)(self.job), (H * 3)(*standard)
            # JOB_LIST removes the owner-death orphan gap. Unsupported attributes
            # or incompatible nesting fail creation; there is no uncontrolled fallback.
            check(self.api.UpdateProcThreadAttribute(attributes, 0, 0x2000D, jobs, C.sizeof(jobs), None, None))
            check(self.api.UpdateProcThreadAttribute(attributes, 0, 0x20002, inherited,
                                                     C.sizeof(inherited), None, None))
            fault("after_attributes")
            startup, info = StartupEx(), ProcessInfo()
            startup.info.cb, startup.info.flags = C.sizeof(StartupEx), 0x100  # USESTDHANDLES.
            startup.info.stdin, startup.info.stdout, startup.info.stderr = standard
            startup.attributes = C.cast(attributes, H)
            command = C.create_unicode_buffer(subprocess.list2cmdline([str(executable), *arguments]))
            fault("before_create")
            # CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW.
            check(self.api.CreateProcessW(str(executable), command, None, None, True, 0x08080004,
                                           None, str(cwd), C.byref(startup), C.byref(info)))
            self.process, self.thread = info.process, info.thread
            fault("after_create")
            member, flags = C.c_int(), D()
            check(self.api.IsProcessInJob(self.process, self.job, C.byref(member)))
            check(self.api.GetHandleInformation(self.job, C.byref(flags)))
            if not member.value or flags.value & 1:
                raise ValueError("created child lacks private noninheritable job ownership")
            self.initial = identity(self.api, self.process)
            if self.initial[0] != info.pid or self.initial[2].casefold() != str(executable).casefold():
                raise ValueError("created process identity conflicts with executable")
            fault("after_identity")
        finally:
            import sys
            original = sys.exc_info()[1]
            try:
                self.api.DeleteProcThreadAttributeList(attributes)
            except BaseException as cleanup:
                if original is None:
                    raise
                original.process_cleanup_errors = [*getattr(original, "process_cleanup_errors", ()), cleanup]
        self.streams.close_child()

    def verify(self, expected):
        """Reject stale identity or membership before acting on this retained owner."""
        member = C.c_int()
        if identity(self.api, self.process) != expected:
            raise ValueError("owned native process identity changed")
        check(self.api.IsProcessInJob(self.process, self.job, C.byref(member)))
        if not member.value:
            raise ValueError("owned process job membership changed")

    def resume(self):
        """Resume the exact initial thread only from its one owned suspension."""
        previous = self.api.ResumeThread(self.thread)
        if previous == 0xFFFFFFFF:
            raise C.WinError(C.get_last_error())
        if previous != 1:
            raise ValueError("unexpected initial-thread suspension identity")

    def status(self):
        """Require process signaling AND zero whole-job active members for exit proof."""
        accounting = Accounting()
        check(self.api.QueryInformationJobObject(self.job, 1, C.byref(accounting), C.sizeof(accounting), None))
        if self.process is None:
            return None, accounting.active
        # Image/membership queries need a live process. The held object and its
        # immutable creation identity remain checkable after exit; membership was
        # established atomically and verified before resume, with no breakaway.
        if self.initial is not None and creation_identity(self.api, self.process) != self.initial[:2]:
            raise ValueError("owned native process creation identity changed")
        wait = self.api.WaitForSingleObject(self.process, 0)
        if wait == 0xFFFFFFFF:
            raise C.WinError(C.get_last_error())
        if wait not in {0, 258}:
            raise ValueError("unexpected native process wait status")
        code = D()
        if wait == 0:
            check(self.api.GetExitCodeProcess(self.process, C.byref(code)))
        return code.value if wait == 0 else None, accounting.active

    def terminate(self):
        """Terminate only this owned job; no executable name, PID or service handle."""
        check(self.api.TerminateJobObject(self.job, 1))

    def close(self):
        """Release every native handle, retaining failures for bounded later cleanup."""
        errors = []
        try:
            self.streams.close()
        except BaseException as error:
            errors.extend((error, *getattr(error, "process_cleanup_errors", ())))
        for name in ("thread", "process", "job"):
            handle = getattr(self, name)
            if handle is not None:
                try:
                    check(self.api.CloseHandle(handle))
                    setattr(self, name, None)
                except BaseException as error:
                    errors.append(error)
        if errors:
            errors[0].process_cleanup_errors = errors[1:]
            raise errors[0]
