import io
import json
import urllib.error
import unittest
from urllib.parse import parse_qs, urlparse

from openfx.youtube_search import search_youtube_videos


class FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")

    def read(self, size=-1):
        return self.body[:size] if size >= 0 else self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def payload():
    return {
        "items": [{
            "id": {"kind": "youtube#video", "videoId": "AbCdEf12345"},
            "snippet": {
                "title": "Synthetic Forex lesson",
                "channelTitle": "Example Channel",
                "publishedAt": "2025-02-03T12:00:00Z",
            },
        }]
    }


class YouTubeSearchTests(unittest.TestCase):
    def test_returns_provenance_records_without_assuming_license(self):
        seen = {}

        def opener(request, timeout):
            seen["url"] = request.full_url
            seen["headers"] = dict(request.header_items())
            seen["timeout"] = timeout
            return FakeResponse(payload())

        records = search_youtube_videos(
            "forex pivots", api_key="test-api-key", max_results=5,
            region_code="gb", relevance_language="en", opener=opener,
        )
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["source_id"], "yt-AbCdEf12345")
        self.assertEqual(record["source_type"], "video")
        self.assertEqual(record["license_status"], "unknown")
        self.assertEqual(record["access_method"], "official_api")
        self.assertEqual(record["published_date"], "2025-02-03")
        self.assertEqual(seen["timeout"], 20)
        params = parse_qs(urlparse(seen["url"]).query)
        self.assertNotIn("key", params)
        self.assertEqual(
            next(value for name, value in seen["headers"].items() if name.lower() == "x-goog-api-key"),
            "test-api-key",
        )
        self.assertEqual(params["q"], ["forex pivots"])
        self.assertEqual(params["regionCode"], ["GB"])

    def test_requires_api_key(self):
        with self.assertRaisesRegex(ValueError, "YOUTUBE_API_KEY"):
            search_youtube_videos("forex", api_key="")

    def test_rejects_invalid_result_limit(self):
        with self.assertRaisesRegex(ValueError, "1 to 50"):
            search_youtube_videos("forex", api_key="key", max_results=51)

    def test_rejects_malformed_api_response(self):
        with self.assertRaisesRegex(RuntimeError, "malformed video result"):
            search_youtube_videos(
                "forex", api_key="key",
                opener=lambda request, timeout: FakeResponse({"items": [{"id": {}}]}),
            )

    def test_api_error_does_not_echo_api_key(self):
        secret = "never-print-this-key"

        def opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 403, "Forbidden", {}, io.BytesIO(b"quota exceeded")
            )

        with self.assertRaises(RuntimeError) as context:
            search_youtube_videos("forex", api_key=secret, opener=opener)
        self.assertNotIn(secret, str(context.exception))
        self.assertIn("HTTP 403", str(context.exception))


if __name__ == "__main__":
    unittest.main()
