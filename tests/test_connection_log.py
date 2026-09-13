"""Optional evidence stays serializable for callers constructing older records."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tikrec.connection_log import ConnectionRecord, append_connection_record, append_room_status_record


class ConnectionLogTests(unittest.TestCase):
    def test_old_style_record_keeps_new_fields_unknown(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "connections.jsonl"
            append_connection_record(path, ConnectionRecord(1, 1.0, 2.0, None, (), "resolver_error"))
            append_room_status_record(path, 3.0, "4", False)
            record, status = [json.loads(line) for line in path.read_text().splitlines()]
        for field in ("resolved_at", "http_opened_at", "first_media_tag_at", "first_retained_media_at",
                      "last_retained_media_at", "rendition_label", "rendition_source"):
            self.assertIsNone(record[field])
        self.assertEqual(status, {"event": "room_status", "timestamp": 3.0,
                                  "status": "4", "confirmation_reached": False})


if __name__ == "__main__":
    unittest.main()
