"""Independent bounded reporting failures; diagnostics never own cleanup decisions."""
import json
import sys


class DisabledConsole:
    """Quarantine the failed stream, including CPython's final implicit flush."""

    def __init__(self, original):
        self.original = original  # Retain the stream; dropping it could run a failing destructor.

    def write(self, text):
        """Discard further output after the channel's exact failure has been saved."""
        return len(text)

    def flush(self):
        """Never implicitly retry the failed channel during interpreter retirement."""


class Reporting:
    """Keep each channel's exact first failure and disable further writes to it."""

    def __init__(self):
        self.errors = []
        self.disabled = set()

    def write(self, diagnostics, event, **values):
        """Attempt independent sinks once; return the exact earliest new failure."""
        first = None
        for channel in ('disk', 'console'):
            if channel in self.disabled or channel == 'disk' and diagnostics is None:
                continue
            if channel == 'console' and event in {'observation', 'stop'}:
                continue
            try:
                # Only fixed channel/type summaries cross the sanitized receipt boundary.
                summary = [{'channel': c, 'type': type(e).__name__} for c, e in self.errors]
                payload = {**values, **({'reporting_failures': summary} if summary else {})}
                if channel == 'disk':
                    diagnostics.emit(event, **payload)
                else:
                    stream = sys.stdout
                    print(json.dumps({'event': event, **payload}, allow_nan=False), file=stream, flush=True)
            except BaseException as error:
                # Two channels, one retained exception each: no unbounded retry diagnostics.
                self.disabled.add(channel)
                self.errors.append((channel, error))
                if channel == 'console' and sys.stdout is stream:
                    sys.stdout = DisabledConsole(stream)
                if first is None:
                    first = error
        return first
