"""Pointer-safe Windows process/job declarations; imports perform no native I/O."""

import ctypes as C
import os


D, H, P, S = C.c_uint32, C.c_void_p, C.c_void_p, C.c_size_t


class Security(C.Structure):
    """Native inheritable standard-handle descriptor."""
    _fields_ = [("length", D), ("descriptor", P), ("inherit", C.c_int)]


class Startup(C.Structure):
    """STARTUPINFOW with exact native alignment."""
    _fields_ = [("cb", D), ("reserved", P), ("desktop", P), ("title", P),
                *[(name, D) for name in ("x", "y", "width", "height", "cols", "rows", "fill", "flags")],
                ("show", C.c_uint16), ("reserved_size", C.c_uint16), ("reserved_data", P),
                ("stdin", H), ("stdout", H), ("stderr", H)]


class StartupEx(C.Structure):
    """STARTUPINFOEXW attribute-list owner."""
    _fields_ = [("info", Startup), ("attributes", P)]


class ProcessInfo(C.Structure):
    """Exact process and initial-thread handles from creation."""
    _fields_ = [("process", H), ("thread", H), ("pid", D), ("tid", D)]


class BasicLimits(C.Structure):
    """JOBOBJECT_BASIC_LIMIT_INFORMATION; only kill-on-close is set by the runner."""
    _fields_ = [("process_time", C.c_int64), ("job_time", C.c_int64), ("flags", D),
                ("min_working", S), ("max_working", S), ("active_limit", D),
                ("affinity", S), ("priority", D), ("scheduling", D)]


class ExtendedLimits(C.Structure):
    """JOBOBJECT_EXTENDED_LIMIT_INFORMATION, including native IO_COUNTERS."""
    _fields_ = [("basic", BasicLimits), ("io", C.c_uint64 * 6),
                *[(name, S) for name in ("process_memory", "job_memory", "peak_process", "peak_job")]]


class Accounting(C.Structure):
    """Whole-job active process count, including descendants."""
    _fields_ = [("times", C.c_int64 * 4), ("faults", D), ("total", D),
                ("active", D), ("terminated", D)]


class FileTime(C.Structure):
    """Native creation FILETIME used alongside the retained handle, never a bare PID."""
    _fields_ = [("low", D), ("high", D)]


def kernel():
    """Load explicitly typed native functions only on Windows."""
    if os.name != "nt":
        raise OSError("owned subprocess runner requires Windows JOB_LIST support")
    api = C.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": (H, [P, C.c_wchar_p]),
        "SetInformationJobObject": (C.c_int, [H, C.c_int, P, D]),
        "QueryInformationJobObject": (C.c_int, [H, C.c_int, P, D, P]),
        "IsProcessInJob": (C.c_int, [H, H, P]),
        "TerminateJobObject": (C.c_int, [H, D]),
        "CloseHandle": (C.c_int, [H]),
        "SetHandleInformation": (C.c_int, [H, D, D]),
        "GetHandleInformation": (C.c_int, [H, P]),
        "CreatePipe": (C.c_int, [P, P, P, D]),
        "CreateFileW": (H, [C.c_wchar_p, D, D, P, D, D, H]),
        "PeekNamedPipe": (C.c_int, [H, P, D, P, P, P]),
        "ReadFile": (C.c_int, [H, P, D, P, P]),
        "InitializeProcThreadAttributeList": (C.c_int, [P, D, D, P]),
        "UpdateProcThreadAttribute": (C.c_int, [P, D, S, P, S, P, P]),
        "DeleteProcThreadAttributeList": (None, [P]),
        "CreateProcessW": (C.c_int, [C.c_wchar_p, P, P, P, C.c_int, D, P, C.c_wchar_p, P, P]),
        "GetProcessId": (D, [H]),
        "GetProcessTimes": (C.c_int, [H, P, P, P, P]),
        "QueryFullProcessImageNameW": (C.c_int, [H, D, P, P]),
        "ResumeThread": (D, [H]),
        "WaitForSingleObject": (D, [H, D]),
        "GetExitCodeProcess": (C.c_int, [H, P]),
        "GetCurrentProcess": (H, []),
        "DuplicateHandle": (C.c_int, [H, H, H, P, D, C.c_int, D]),
    }
    for name, (result, arguments) in signatures.items():
        function = getattr(api, name)
        function.restype, function.argtypes = result, arguments
    return api


def check(value):
    """Raise the actual Windows error before another API can overwrite it."""
    if not value:
        raise C.WinError(C.get_last_error())
    return value


def creation_identity(api, process):
    """Read stable PID/creation FILETIME even after the exact process has exited."""
    pid = check(api.GetProcessId(process))
    times = [FileTime() for _ in range(4)]
    check(api.GetProcessTimes(process, *(C.byref(t) for t in times)))
    return pid, (times[0].high << 32) | times[0].low


def identity(api, process):
    """Bind the executable while the child is suspended; image queries may fail after exit."""
    pid, created = creation_identity(api, process)
    buffer, length = C.create_unicode_buffer(32768), D(32768)
    check(api.QueryFullProcessImageNameW(process, 0, buffer, C.byref(length)))
    return pid, created, buffer.value
