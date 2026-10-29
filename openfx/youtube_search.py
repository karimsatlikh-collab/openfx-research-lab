"""Official YouTube Data API v3 search connector (metadata only).

This connector does not download videos or captions. Results remain rights-unknown
until a human reviews the source and applicable license/permissions.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .source_registry import make_source_record

_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
_ORDERS = {"date", "rating", "relevance", "title", "videoCount", "viewCount"}


def search_youtube_videos(
    query: str,
    *,
    api_key: str | None = None,
    max_results: int = 10,
    order: str = "relevance",
    region_code: str | None = None,
    relevance_language: str | None = None,
    timeout_seconds: int = 20,
    opener: Callable[..., Any] | None = None,
) -> list[dict[str, Any]]:
    """Search public video metadata through the official API and return source records."""
    key = (api_key or os.environ.get("YOUTUBE_API_KEY", "")).strip()
    if not key:
        raise ValueError("provide api_key or set YOUTUBE_API_KEY in the environment")
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError("query must be a non-empty string of at most 500 characters")
    if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= 50:
        raise ValueError("max_results must be an integer from 1 to 50")
    if order not in _ORDERS:
        raise ValueError("unsupported YouTube search order")
    if region_code is not None and (
        not isinstance(region_code, str) or not re.fullmatch(r"[A-Za-z]{2}", region_code)
    ):
        raise ValueError("region_code must be a two-letter country code")
    if relevance_language is not None and (
        not isinstance(relevance_language, str) or not re.fullmatch(r"[A-Za-z-]{2,12}", relevance_language)
    ):
        raise ValueError("relevance_language must be a language tag")
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 3 <= timeout_seconds <= 60:
        raise ValueError("timeout_seconds must be an integer from 3 to 60")

    params = {
        "part": "snippet",
        "type": "video",
        "q": query.strip(),
        "maxResults": str(max_results),
        "order": order,
        "safeSearch": "moderate",
        "key": key,
    }
    if region_code:
        params["regionCode"] = region_code.upper()
    if relevance_language:
        params["relevanceLanguage"] = relevance_language
    url = _ENDPOINT + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "OpenFX-Source-Registry/1.0"},
        method="GET",
    )
    open_url = opener or urllib.request.urlopen
    try:
        with open_url(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"YouTube API returned HTTP {status}.")
            headers = getattr(response, "headers", None)
            if headers is not None and hasattr(headers, "get_content_type"):
                if headers.get_content_type() != "application/json":
                    raise RuntimeError("YouTube API response is not JSON.")
            body = response.read(2_000_001)
    except urllib.error.HTTPError as exc:
        # Never echo the request URL; it contains the API key query parameter.
        raise RuntimeError(f"YouTube API returned HTTP {exc.code}.") from None
    except urllib.error.URLError:
        raise RuntimeError("YouTube API connection failed.") from None
    if len(body) > 2_000_000:
        raise RuntimeError("YouTube API response exceeds the 2 MB limit.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("YouTube API returned invalid JSON.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise RuntimeError("YouTube API response has an invalid schema.")

    records = []
    for item in payload["items"]:
        if not isinstance(item, dict):
            raise RuntimeError("YouTube API returned a malformed search item.")
        video_id = item.get("id", {}).get("videoId") if isinstance(item.get("id"), dict) else None
        snippet = item.get("snippet")
        if not isinstance(video_id, str) or not _VIDEO_ID_RE.fullmatch(video_id) or not isinstance(snippet, dict):
            raise RuntimeError("YouTube API returned a malformed video result.")
        title = snippet.get("title")
        author = snippet.get("channelTitle")
        published_at = snippet.get("publishedAt")
        if not isinstance(title, str) or not title.strip() or not isinstance(author, str) or not author.strip():
            raise RuntimeError("YouTube API video metadata is incomplete.")
        published_date = published_at[:10] if isinstance(published_at, str) and len(published_at) >= 10 else None
        record = make_source_record(
            source_id=f"yt-{video_id}",
            source_type="video",
            url=f"https://www.youtube.com/watch?v={video_id}",
            title=title,
            author=author,
            published_date=published_date,
            license_status="unknown",
            license_reference=None,
            access_method="official_api",
            notes="Discovered through YouTube Data API v3; license/permission not independently reviewed.",
        )
        records.append(record)
    return records
