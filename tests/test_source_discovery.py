import tempfile
import unittest
from pathlib import Path

from meeting_ai.nodes.source_discovery import derive_run_id, find_latest_media


class SourceDiscoveryTest(unittest.TestCase):
    def test_prefers_filename_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = root / "Screen_Recording_20260429_172841_Zoom.mp4"
            newer = root / "Screen_Recording_20260430_101010_Zoom.mp4"
            older.write_text("older")
            newer.write_text("newer")

            self.assertEqual(find_latest_media(root), newer)
            self.assertEqual(derive_run_id(newer, "auto"), "zoom_20260430_101010")


if __name__ == "__main__":
    unittest.main()
