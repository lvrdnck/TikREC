"""Nonblocking polled Windows pipes; no reader threads or unbounded line buffering."""

import ctypes as C

from .owned_process_api import D, H, Security, check


class NativeStreams:
    """Own only NUL stdin and the two diagnostic pipes needed by this child."""

    def __init__(self, api):
        self.api, self.child, self.readers = api, [], {}
        self.eof = set()

    def open(self, retained_stdin=None):
        """Create inheritable child endpoints and noninheritable parent readers."""
        security = Security(C.sizeof(Security), None, True)
        if retained_stdin is None:
            stdin = self.api.CreateFileW("NUL", 0x80000000, 3, C.byref(security), 3, 0x80, None)
        else:
            duplicate = H()
            current = self.api.GetCurrentProcess()
            # Only READ access is inherited; write and rename authority stays local.
            check(self.api.DuplicateHandle(current, retained_stdin, current, C.byref(duplicate),
                                           0x80000000, True, 0))
            stdin = duplicate.value
        if stdin == C.c_void_p(-1).value:
            raise C.WinError(C.get_last_error())
        self.child.append(stdin)
        for name in ("stdout", "stderr"):
            read, write = H(), H()
            check(self.api.CreatePipe(C.byref(read), C.byref(write), C.byref(security), 0))
            # Track both endpoints before the next potentially failing native call.
            self.readers[name], self.child = read.value, [*self.child, write.value]
            check(self.api.SetHandleInformation(read, 1, 0))
        return self.child

    def close_child(self):
        """Release parent copies of child endpoints after creation, permitting EOF."""
        errors = []
        for handle in tuple(self.child):
            try:
                check(self.api.CloseHandle(handle))
                self.child.remove(handle)
            except BaseException as error:
                errors.append(error)
        if errors:
            errors[0].process_cleanup_errors = errors[1:]
            raise errors[0]

    def read(self, name, maximum=8192):
        """Read only already available bytes; silence/no newline cannot block the owner."""
        if name in self.eof:
            return b""
        handle, available = self.readers[name], D()
        if not self.api.PeekNamedPipe(handle, None, 0, None, C.byref(available), None):
            if C.get_last_error() in {109, 233}:
                self.eof.add(name)
                return b""
            raise C.WinError(C.get_last_error())
        size = min(maximum, available.value)
        if not size:
            return b""
        buffer, count = C.create_string_buffer(size), D()
        check(self.api.ReadFile(handle, buffer, size, C.byref(count), None))
        return buffer.raw[:count.value]

    def close(self):
        """Attempt every endpoint release, retaining failed handles for another close."""
        errors = []
        try:
            self.close_child()
        except BaseException as error:
            errors.extend((error, *getattr(error, "process_cleanup_errors", ())))
        for name, handle in tuple(self.readers.items()):
            try:
                check(self.api.CloseHandle(handle))
                del self.readers[name]
            except BaseException as error:
                errors.append(error)
        if errors:
            errors[0].process_cleanup_errors = errors[1:]
            raise errors[0]
