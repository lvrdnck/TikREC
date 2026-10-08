"""Retain the supplied monitor's exact native thread and SQLite teardown ownership."""

from threading import Event

from .service_runtime_capture import retain_thread_after_error


class MonitorOwner:
    """Observe existing monitor execution without another monitor or scheduling policy."""

    def __init__(self, server):
        self.server, self.thread = server, None
        self.owner = {'retry': Event()}
        self.original = server.monitor._thread_factory

    def factory(self, **options):
        """Capture the constructed object before start can lose its acknowledgement."""
        target = options['target']
        def run():
            try:
                target()
            except BaseException as error:
                self.server.runtime.record_error(error)
            finally:
                self.server.requests.cleanup(self.owner)
        options['target'] = run
        self.thread = self.original(**options)
        return self.thread

    def start(self):
        """Reuse the accepted monitor start while retaining partial native startup."""
        monitor = self.server.monitor
        monitor._thread_factory = self.factory
        try:
            monitor.start()
        except BaseException as error:
            if not retain_thread_after_error(self.server.runtime, self.thread, error):
                self.thread = None
            raise
        finally:
            monitor._thread_factory = self.original

    def join(self, timeout):
        """Retry cleanup on the original monitor thread and require a confirmed join."""
        self.owner['retry'].set()
        try:
            if self.thread is not None:
                self.thread.join(timeout)
                if self.thread.is_alive():
                    return False
            self.server.monitor.join()
            return True
        except BaseException as error:
            self.server.runtime.record_error(error)
            return False
