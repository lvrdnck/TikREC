"""Read Windows metrics for handles owned by the disposable #52 experiment."""

import ctypes as c
from ctypes import wintypes as w


class Memory(c.Structure):
    """PSAPI PROCESS_MEMORY_COUNTERS_EX with native SIZE_T fields."""

    _fields_ = [("cb", w.DWORD), ("faults", w.DWORD)] + [
        (name, c.c_size_t) for name in (
            "peak_ws", "ws", "peak_paged", "paged", "peak_nonpaged", "nonpaged",
            "pagefile", "peak_pagefile", "private")]


class IO(c.Structure):
    """Win32 IO_COUNTERS reports logical process transfers, including cache."""

    _fields_ = [(name, c.c_ulonglong) for name in (
        "read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]


class GlobalMemory(c.Structure):
    """MEMORYSTATUSEX reports current available physical memory."""

    _fields_ = [("length", w.DWORD), ("load", w.DWORD)] + [
        (name, c.c_ulonglong) for name in (
            "total", "available", "total_page", "available_page", "total_virtual",
            "available_virtual", "extended_virtual")]


def _ticks(value):
    return ((value.dwHighDateTime << 32) + value.dwLowDateTime) / 10_000_000


class Metrics:
    """Query one Popen child; never enumerate, reprioritize or open other PIDs."""

    def __init__(self, process):
        self.handle = w.HANDLE(int(process._handle))
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.psapi = c.WinDLL("psapi", use_last_error=True)
        self.kernel.GetProcessTimes.argtypes = [w.HANDLE] + [c.POINTER(w.FILETIME)] * 4
        self.kernel.GetProcessIoCounters.argtypes = [w.HANDLE, c.POINTER(IO)]
        self.kernel.GetPriorityClass.argtypes = [w.HANDLE]
        self.kernel.GetPriorityClass.restype = w.DWORD
        self.kernel.GlobalMemoryStatusEx.argtypes = [c.POINTER(GlobalMemory)]
        self.kernel.GetSystemTimes.argtypes = [c.POINTER(w.FILETIME)] * 3
        self.psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, c.POINTER(Memory), w.DWORD]

    def sample(self):
        """Return lifetime CPU/IO, memory and machine counters from Win32."""
        times = [w.FILETIME() for _ in range(4)]
        if not self.kernel.GetProcessTimes(self.handle, *(c.byref(v) for v in times)):
            raise c.WinError(c.get_last_error())
        io = IO()
        if not self.kernel.GetProcessIoCounters(self.handle, c.byref(io)):
            raise c.WinError(c.get_last_error())
        mem = Memory(cb=c.sizeof(Memory))
        memory_ok = self.psapi.GetProcessMemoryInfo(self.handle, c.byref(mem), c.sizeof(mem))
        global_mem = GlobalMemory(length=c.sizeof(GlobalMemory))
        if not self.kernel.GlobalMemoryStatusEx(c.byref(global_mem)):
            raise c.WinError(c.get_last_error())
        system = [w.FILETIME() for _ in range(3)]
        if not self.kernel.GetSystemTimes(*(c.byref(v) for v in system)):
            raise c.WinError(c.get_last_error())
        return {
            "cpu_seconds": _ticks(times[2]) + _ticks(times[3]),
            "read_bytes": io.read_bytes, "write_bytes": io.write_bytes,
            "peak_working_set": mem.peak_ws if memory_ok else None,
            "private_bytes": mem.private if memory_ok else None,
            "physical_available": global_mem.available,
            "priority_class": self.kernel.GetPriorityClass(self.handle),
            # Kernel system time includes idle; subtract it when computing busy time.
            "system_total": _ticks(system[1]) + _ticks(system[2]),
            "system_idle": _ticks(system[0]),
        }


class _PdhValue(c.Structure):
    _fields_ = [("status", w.DWORD), ("value", c.c_double)]


class DiskMetrics:
    """Read system-wide physical-disk counters; not per-process disk attribution."""

    def __init__(self):
        self.api = c.WinDLL("pdh")
        self.query = w.HANDLE()
        self.api.PdhOpenQueryW.argtypes = [w.LPCWSTR, c.c_size_t, c.POINTER(w.HANDLE)]
        self.api.PdhAddEnglishCounterW.argtypes = [w.HANDLE, w.LPCWSTR, c.c_size_t,
                                                  c.POINTER(w.HANDLE)]
        self.api.PdhCollectQueryData.argtypes = [w.HANDLE]
        self.api.PdhGetFormattedCounterValue.argtypes = [w.HANDLE, w.DWORD,
                                                        c.POINTER(w.DWORD), c.POINTER(_PdhValue)]
        self.api.PdhCloseQuery.argtypes = [w.HANDLE]
        self.counters = {}
        self.error = self.api.PdhOpenQueryW(None, 0, c.byref(self.query))
        if self.error:
            return
        for name, suffix in (
            ("disk_read_bps", "Disk Read Bytes/sec"),
            ("disk_write_bps", "Disk Write Bytes/sec"),
            ("disk_queue", "Avg. Disk Queue Length"),
        ):
            handle = w.HANDLE()
            status = self.api.PdhAddEnglishCounterW(
                self.query, "\\PhysicalDisk(_Total)\\" + suffix, 0, c.byref(handle))
            if status:
                self.error = status
            else:
                self.counters[name] = handle
        self.api.PdhCollectQueryData(self.query)

    def sample(self):
        """Return available PDH values; missing counters stay explicitly absent."""
        if not self.query or self.api.PdhCollectQueryData(self.query):
            return {}
        result = {}
        for name, handle in self.counters.items():
            value = _PdhValue()
            status = self.api.PdhGetFormattedCounterValue(handle, 0x200, None, c.byref(value))
            if status == 0 and value.status in (0, 1):
                result[name] = value.value
        return result

    def close(self):
        """Release only this experiment's performance-counter query."""
        if self.query:
            self.api.PdhCloseQuery(self.query)
