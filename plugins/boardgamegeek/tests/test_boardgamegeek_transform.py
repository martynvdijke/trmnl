import importlib.util
import os
import sys
import urllib.request as urllib_request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "transform.py")

spec = importlib.util.spec_from_file_location("bgg_transform", SRC)
transform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transform)


PLAYS_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<plays username="testuser" total="2">
  <play id="1001" date="2024-03-01" quantity="1" length="60" incomplete="0" location="Home">
    <item objectid="13" objecttype="thing">
      <name>CATAN</name>
      <subtypes><subtype value="boardgame"/></subtypes>
    </item>
    <players><player name="Alice" win="1"/></players>
  </play>
  <play id="1002" date="2024-02-15" quantity="1" length="90" incomplete="0" location="Home">
    <item objectid="36218" objecttype="thing">
      <name>The Crew</name>
      <subtypes><subtype value="boardgame"/></subtypes>
    </item>
  </play>
</plays>
"""

THING_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<items>
  <item type="boardgame" id="13">
    <name type="primary" value="CATAN"/>
    <yearpublished value="1995"/>
    <image>https://example.com/catan.jpg</image>
    <thumbnail>https://example.com/catan_t.jpg</thumbnail>
    <statistics>
      <ratings>
        <average value="7.5"/>
      </ratings>
    </statistics>
  </item>
  <item type="boardgame" id="36218">
    <name type="primary" value="The Crew"/>
    <yearpublished value="2019"/>
    <image>https://example.com/crew.jpg</image>
    <thumbnail>https://example.com/crew_t.jpg</thumbnail>
    <statistics>
      <ratings>
        <average value="7.7"/>
      </ratings>
    </statistics>
  </item>
</items>
"""

COLLECTION_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<items total="2">
  <item objectid="13" collid="1">
    <name>CATAN</name>
    <yearpublished>1995</yearpublished>
    <image>https://example.com/catan.jpg</image>
    <thumbnail>https://example.com/catan_t.jpg</thumbnail>
    <stats>
      <rating value="8.0"/>
    </stats>
  </item>
  <item objectid="36218" collid="2">
    <name>The Crew</name>
    <yearpublished>2019</yearpublished>
    <image>https://example.com/crew.jpg</image>
    <thumbnail>https://example.com/crew_t.jpg</thumbnail>
    <stats>
      <rating value="9.0"/>
    </stats>
  </item>
</items>
"""


class FakeResponse:
    def __init__(self, body, status=200):
        self._body = body
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeUrlopen:
    """Context-manager-returning mock that routes by request URL."""

    def __call__(self, request, *args, **kwargs):
        url = getattr(request, "full_url", str(request))
        if "plays" in url:
            return FakeResponse(PLAYS_XML)
        if "thing" in url:
            return FakeResponse(THING_XML)
        if "collection" in url:
            return FakeResponse(COLLECTION_XML)
        return FakeResponse(b"<empty/>")


def test_runs_with_mocked_api():
    original = urllib_request.urlopen
    urllib_request.urlopen = FakeUrlopen()
    try:
        out = transform.run(
            {
                "trmnl": {
                    "plugin_settings": {
                        "custom_fields_values": {"username": "testuser"}
                    }
                }
            }
        )
    finally:
        urllib_request.urlopen = original

    assert "error" not in out, out
    assert len(out["plays"]) >= 1
    # Plays are enriched with cover art from the thing endpoint.
    assert out["plays"][0]["image"]
    assert out["plays"][0]["year"]
    # One owned game is featured and it must come from the collection.
    assert out["featured"] is not None
    assert out["featured"]["id"] in {"13", "36218"}
    assert out["owned_count"] == 2
    print("OK", out)


def test_missing_username_errors():
    out = transform.run(
        {"trmnl": {"plugin_settings": {"custom_fields_values": {}}}}
    )
    assert "error" in out


if __name__ == "__main__":
    test_runs_with_mocked_api()
    test_missing_username_errors()
    print("ALL TESTS PASSED")
