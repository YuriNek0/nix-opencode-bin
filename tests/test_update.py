import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update


class UpdateTests(unittest.TestCase):
    def test_v1_selection_paginates_and_ignores_other_releases(self):
        def release(tag, prerelease=False):
            return {"tag_name": tag, "draft": False, "prerelease": prerelease}

        first = [release("v2.0.30")] * 98 + [
            release("v1.20.0", True), release("v1.9.0")]
        with patch.object(update, "fetch_json", side_effect=[first, [release("v1.19.2")]]):
            self.assertEqual(update.latest_v1(), "1.19.2")

    def test_numeric_stable_versions(self):
        self.assertGreater(update.version_key("2.0.30"), update.version_key("2.0.9"))
        with self.assertRaises(ValueError):
            update.version_key("2.0.31-beta")

    def test_unchanged_release_does_not_download(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hashes.json"
            original = '{"version": "2.0.30"}'
            path.write_text(original)
            with patch.object(update, "prefetch_hash") as prefetch:
                for version in ["2.0.30", "2.0.9"]:
                    self.assertIsNone(update.prepare_update(path, version, {}))
                prefetch.assert_not_called()
            self.assertEqual(path.read_text(), original)

    def test_failed_verification_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hashes.json"
            original = json.dumps({"version": "2.0.9"})
            path.write_text(original)
            with patch.object(update, "prefetch_hash", return_value="wrong"):
                with self.assertRaises(ValueError):
                    update.prepare_update(path, "2.0.30", {"linux": "https://example.test"},
                                          {"linux": "expected"})
            self.assertEqual(path.read_text(), original)

    def test_missing_v2_asset_rejected(self):
        with self.assertRaises(KeyError):
            update.v2_metadata({"name": "cli", "distribution": "opencode",
                                "channel": "latest", "active": True,
                                "version": "2.0.30", "metadata": {"files": {}}})

    def test_download_failure_leaves_both_files_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            v1 = root / "hashes-v1.json"
            v2 = root / "hashes.json"
            v1.write_text('{"version": "1.19.1"}')
            v2.write_text('{"version": "2.0.9"}')
            originals = [v1.read_text(), v2.read_text()]
            with (patch.object(update, "ROOT", root),
                  patch.object(update, "latest_v1", return_value="1.19.2"),
                  patch.object(update, "fetch_json", return_value={}),
                  patch.object(update, "v2_metadata", return_value=(
                      "2.0.30", {"linux": "https://example.test"}, {"linux": "expected"})),
                  patch.object(update, "prefetch_hash", side_effect=["hash"] * 4 + [RuntimeError("download failed")])):
                with self.assertRaises(RuntimeError):
                    update.main()
            self.assertEqual([v1.read_text(), v2.read_text()], originals)


if __name__ == "__main__":
    unittest.main()
