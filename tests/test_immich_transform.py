import importlib.util
import json
import os
import unittest

SPEC = importlib.util.spec_from_file_location(
    "immich_transform",
    os.path.join(os.path.dirname(__file__), "..", "plugins", "immich", "src", "transform.py"),
)
transform = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transform)


def _asset(**overrides):
    base = {
        "id": "abc",
        "originalFileName": "IMG_1.jpg",
        "fileCreatedAt": "2024-01-02T03:04:05Z",
        "width": 4000,
        "height": 3000,
        "exifInfo": {
            "description": "Sunset",
            "make": "Sony",
            "model": "A7",
            "lensModel": "FE 24-70",
            "iso": 100,
            "exposureTime": "1/250",
            "fNumber": 2.8,
            "fileSizeInByte": 123456,
            "city": "Amsterdam",
        },
    }
    base.update(overrides)
    # deep merge exif if overridden partially
    if "exifInfo" in overrides and overrides["exifInfo"] is not None:
        # caller already provided full value; keep as is
        pass
    return base


class TransformTest(unittest.TestCase):
    def test_empty_data_returns_error(self):
        self.assertIn("error", transform.run({"data": []}))
        self.assertIn("error", transform.run({}))
        self.assertIn("error", transform.run({"data": None}))

    def test_happy_path(self):
        asset = {
            "id": "abc",
            "originalFileName": "IMG_1.jpg",
            "fileCreatedAt": "2024-01-02T03:04:05Z",
            "width": 4000,
            "height": 3000,
            "exifInfo": {
                "description": "Sunset",
                "make": "Sony",
                "model": "A7",
                "lensModel": "FE 24-70",
                "iso": 100,
                "exposureTime": "1/250",
                "fNumber": 2.8,
                "fileSizeInByte": 123456,
                "city": "Amsterdam",
            },
        }
        out = transform.run({"data": [asset]})
        self.assertNotIn("error", out)
        self.assertEqual(out["image"], "/api/trmnl/photo/abc")
        self.assertEqual(out["title"], "Sunset")
        self.assertEqual(out["iso"], 100)
        self.assertEqual(out["width"], 4000)
        self.assertEqual(out["city"], "Amsterdam")

    def test_non_numeric_exif_becomes_zero(self):
        asset = {
            "id": "abc",
            "originalFileName": "IMG_1.jpg",
            "fileCreatedAt": "2024-01-02T03:04:05Z",
            "width": 4000,
            "height": 3000,
            "exifInfo": {
                "description": "Sunset",
                "iso": "abc",
            },
        }
        out = transform.run({"data": [asset]})
        self.assertEqual(out["iso"], 0)

    def test_title_fallback_to_original_filename(self):
        asset = {
            "id": "abc",
            "originalFileName": "IMG_1.jpg",
            "fileCreatedAt": "2024-01-02T03:04:05Z",
            "width": 4000,
            "height": 3000,
            "exifInfo": {"description": ""},
        }
        out = transform.run({"data": [asset]})
        self.assertEqual(out["title"], "IMG_1.jpg")

        asset2 = {
            "id": "abc",
            "originalFileName": "IMG_1.jpg",
            "fileCreatedAt": "2024-01-02T03:04:05Z",
            "width": 4000,
            "height": 3000,
            "exifInfo": {},
        }
        out2 = transform.run({"data": [asset2]})
        self.assertEqual(out2["title"], "IMG_1.jpg")

        asset3 = {
            "id": "abc",
            "originalFileName": "IMG_1.jpg",
            "fileCreatedAt": "2024-01-02T03:04:05Z",
            "width": 4000,
            "height": 3000,
        }
        out3 = transform.run({"data": [asset3]})
        self.assertEqual(out3["title"], "IMG_1.jpg")

    def test_bare_list_input(self):
        asset = {
            "id": "abc",
            "originalFileName": "IMG_1.jpg",
            "fileCreatedAt": "2024-01-02T03:04:05Z",
            "width": 4000,
            "height": 3000,
            "exifInfo": {
                "description": "Sunset",
                "make": "Sony",
                "model": "A7",
                "lensModel": "FE 24-70",
                "iso": 100,
                "exposureTime": "1/250",
                "fNumber": 2.8,
                "fileSizeInByte": 123456,
                "city": "Amsterdam",
            },
        }
        out = transform.run([asset])
        self.assertNotIn("error", out)
        self.assertEqual(out["image"], "/api/trmnl/photo/abc")
        self.assertEqual(out["title"], "Sunset")


if __name__ == "__main__":
    unittest.main()
