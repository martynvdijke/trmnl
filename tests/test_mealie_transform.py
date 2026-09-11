import datetime
import importlib.util
import json
import os
import urllib.request
from unittest import mock
import unittest

SPEC = importlib.util.spec_from_file_location(
    "mealie_transform",
    os.path.join(os.path.dirname(__file__), "..", "plugins", "mealie", "src", "transform.py"),
)
transform = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transform)


class _Resp:
    def __init__(self, obj):
        self._o = obj

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        if isinstance(self._o, (dict, list)):
            return json.dumps(self._o).encode()
        return self._o.encode()


def _url_of(url):
    return getattr(url, "full_url", str(url))


def _fake(mapping):
    def _open(url, *a, **k):
        u = _url_of(url)
        for frag, payload in mapping.items():
            if frag in u:
                return _Resp(payload)
        raise AssertionError("unexpected url: %s" % u)

    return _open


def _input(url=None, api_key=None, items=None):
    d = {"trmnl": {"plugin_settings": {"custom_fields_values": {}}}}
    if url is not None:
        d["trmnl"]["plugin_settings"]["custom_fields_values"]["url"] = url
    if api_key is not None:
        d["trmnl"]["plugin_settings"]["custom_fields_values"]["api_key"] = api_key
    if items is not None:
        d["items"] = items
    return d


def _recipes():
    return [
        {
            "id": "r1",
            "slug": "pancakes",
            "name": "Pancakes",
            "description": "Fluffy",
            "image": "pancakes.jpg",
            "recipeServings": 4,
            "recipeYield": "4 servings",
            "prepTime": "PT10M",
            "cookTime": "PT20M",
            "totalTime": "PT30M",
            "rating": 5,
            "recipeCategory": [{"name": "Breakfast"}],
            "tags": [{"name": "easy"}],
        },
        {
            "id": "r2",
            "slug": "soup",
            "name": "Soup",
            "description": "Hot",
            "image": "soup.jpg",
            "recipeServings": 2,
            "recipeYield": "2 servings",
            "prepTime": "PT5M",
            "cookTime": "PT15M",
            "totalTime": "PT20M",
            "rating": 4,
            "recipeCategory": [{"name": "Lunch"}],
            "tags": [{"name": "quick"}],
        },
    ]


class TransformTest(unittest.TestCase):
    def test_missing_url_returns_error(self):
        out = transform.run(_input(items=_recipes()))
        self.assertIn("error", out)
        # also when url not in custom_fields_values at all
        out2 = transform.run({"items": _recipes()})
        self.assertIn("error", out2)

    def test_empty_items_returns_error(self):
        out = transform.run(_input(url="https://mealie.local", api_key="", items=[]))
        self.assertIn("error", out)

    def test_happy_path_without_api_key(self):
        items = _recipes()
        url = "https://mealie.local"
        out = transform.run(_input(url=url, api_key="", items=items))
        self.assertNotIn("error", out)
        self.assertIn(out["slug"], [r["slug"] for r in items])
        self.assertIn(out["name"], [r["name"] for r in items])
        self.assertEqual(out["ingredients"], [])
        self.assertEqual(out["instructions"], [])
        # image and url based on returned recipe
        expected_recipe = next(r for r in items if r["slug"] == out["slug"])
        self.assertEqual(
            out["image"],
            f"{url}/api/media/recipes/{expected_recipe['id']}/images/{expected_recipe['image']}",
        )
        self.assertEqual(out["url"], f"{url}/recipe/{expected_recipe['slug']}")

    def test_day_index_selection(self):
        # verify result is one of the items (stable per day, not hardcoded)
        items = _recipes()
        out = transform.run(_input(url="https://mealie.local", api_key="", items=items))
        idx = int(datetime.date.today().strftime("%Y%m%d")) % len(items)
        self.assertEqual(out["slug"], items[idx]["slug"])

    def test_happy_path_with_api_key(self):
        items = _recipes()
        url = "https://mealie.local"
        idx = int(datetime.date.today().strftime("%Y%m%d")) % len(items)
        expected_slug = items[idx]["slug"]
        detail = {
            "recipeIngredient": [
                {"quantity": "2", "unit": {"name": "cups"}, "food": {"name": "flour"}, "note": "", "display": ""},
                {"quantity": "", "unit": {}, "food": {}, "note": "", "display": "salt to taste"},
            ],
            "recipeInstructions": [
                {"text": "Mix flour"},
                {"text": "Bake"},
                {"text": "  "},
            ],
        }
        captured = {}

        def fake_open(req, *a, **k):
            u = _url_of(req)
            captured["url"] = u
            self.assertIn(f"/api/recipes/{expected_slug}", u)
            return _Resp(detail)

        with mock.patch.object(urllib.request, "urlopen", fake_open):
            out = transform.run(_input(url=url, api_key="secret", items=items))

        self.assertNotIn("error", out)
        self.assertEqual(out["ingredients"], ["2 cups flour", "salt to taste"])
        self.assertEqual(out["instructions"], ["Mix flour", "Bake"])
        self.assertIn("/api/recipes/", captured["url"])

    def test_trailing_slash_no_double_slash(self):
        items = _recipes()
        url = "https://mealie.local/"
        idx = int(datetime.date.today().strftime("%Y%m%d")) % len(items)
        expected_slug = items[idx]["slug"]
        detail = {"recipeIngredient": [], "recipeInstructions": []}
        captured = {}

        def fake_open(req, *a, **k):
            u = _url_of(req)
            captured["url"] = u
            return _Resp(detail)

        with mock.patch.object(urllib.request, "urlopen", fake_open):
            out = transform.run(_input(url=url, api_key="secret", items=items))

        self.assertNotIn("error", out)
        self.assertNotIn("//api", captured["url"])
        self.assertEqual(captured["url"], f"https://mealie.local/api/recipes/{expected_slug}")

    def test_detail_fetch_failure_still_returns_card(self):
        items = _recipes()

        def failing(url, *a, **k):
            raise Exception("network fail")

        with mock.patch.object(urllib.request, "urlopen", failing):
            out = transform.run(_input(url="https://mealie.local", api_key="secret", items=items))

        self.assertNotIn("error", out)
        self.assertEqual(out["ingredients"], [])
        self.assertEqual(out["instructions"], [])
        self.assertIn(out["slug"], [r["slug"] for r in items])


if __name__ == "__main__":
    unittest.main()
