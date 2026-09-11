import importlib.util
import json
import os
import unittest

SPEC = importlib.util.spec_from_file_location(
    "immich_stats_transform",
    os.path.join(os.path.dirname(__file__), "..", "plugins", "immich-stats", "src", "transform.py"),
)
transform = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transform)


class TransformTest(unittest.TestCase):
    def test_missing_idx_returns_error(self):
        self.assertIn("error", transform.run({}))
        self.assertIn("error", transform.run({"IDX_0": {}}))
        self.assertIn("error", transform.run({"IDX_0": None}))

    def test_happy_path(self):
        statistics = {
            "photos": 10,
            "videos": 2,
            "usage": 1073741824,
            "usageByUser": [
                {
                    "userName": "me",
                    "photos": 10,
                    "videos": 2,
                    "usage": 1073741824,
                    "quotaSizeInBytes": 2147483648,
                }
            ],
        }
        version = {"major": 1, "minor": 100, "patch": 0, "prerelease": "rc1"}
        about = {"version": "v1.100.0", "build": "123", "licensed": True, "nodejs": "v20"}
        license_data = {"key": "val"}

        out = transform.run(
            {"IDX_0": statistics, "IDX_1": version, "IDX_2": about, "IDX_3": license_data}
        )
        self.assertNotIn("error", out)
        self.assertEqual(out["total_assets"], 12)
        self.assertEqual(out["usage_human"], "1.0 GB")
        self.assertEqual(out["version_full"], "1.100.0-rc1")
        self.assertEqual(out["usage_by_user"][0]["quota_human"], "2.0 GB")
        self.assertEqual(out["license"], license_data)

    def test_format_bytes_edges(self):
        self.assertEqual(transform.format_bytes(0), "0 B")
        self.assertEqual(transform.format_bytes(1023), "1023 B")
        self.assertEqual(transform.format_bytes(1024), "1.0 KB")


if __name__ == "__main__":
    unittest.main()
