"""Provenance-first registry for research sources and transcript segments.

This module validates records only. It does not crawl websites, download videos,
bypass access controls, or infer permission from public availability.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
from datetime import date, datetime, timezone
from typing import Any

SOURCE_TYPES = {"video", "transcript", "paper", "dataset", "code", "article", "other"}
LICENSE_STATUSES = {"unknown", "reviewed_permitted", "public_domain", "permission_required", "restricted"}
ACCESS_METHODS = {"manual", "user_provided", "official_api", "authorized_download"}
SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
SOURCE_FIELDS = {
    "source_id", "source_type", "url", "title", "author", "published_date",
    "license_status", "license_reference", "access_method", "collected_at_utc",
    "content_sha256", "notes",
}


def _nonempty(value: Any, field: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def validate_source_record(record: Any) -> dict[str, Any]:
    """Validate source identity, provenance, rights review, and content integrity."""
    if not isinstance(record, dict):
        raise ValueError("source record must be an object")
    if set(record) != SOURCE_FIELDS:
        missing = SOURCE_FIELDS - set(record)
        unknown = set(record) - SOURCE_FIELDS
        raise ValueError(f"source fields mismatch (missing={sorted(missing)}, unknown={sorted(unknown)})")
    if not isinstance(record["source_id"], str) or not SOURCE_ID_RE.fullmatch(record["source_id"]):
        raise ValueError("source_id must be a safe stable identifier")
    if record["source_type"] not in SOURCE_TYPES:
        raise ValueError("unsupported source_type")
    _nonempty(record["url"], "url")
    parsed = urllib.parse.urlsplit(record["url"])
    try:
        _ = parsed.port
    except ValueError:
        raise ValueError("url has an invalid port") from None
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.fragment):
        raise ValueError("url must be HTTPS, have no credentials, and omit fragments")
    if any(ord(ch) < 32 for ch in record["url"]):
        raise ValueError("url contains control characters")
    _nonempty(record["title"], "title")
    _nonempty(record["author"], "author", optional=True)
    if record["author"] is not None and not isinstance(record["author"], str):
        raise ValueError("author must be a string or null")
    published = record["published_date"]
    if published is not None:
        if not isinstance(published, str):
            raise ValueError("published_date must be YYYY-MM-DD or null")
        try:
            date.fromisoformat(published)
        except ValueError:
            raise ValueError("published_date must be a real YYYY-MM-DD date") from None
    if record["license_status"] not in LICENSE_STATUSES:
        raise ValueError("unsupported license_status")
    _nonempty(record["license_reference"], "license_reference", optional=True)
    if record["license_reference"] is not None and not isinstance(record["license_reference"], str):
        raise ValueError("license_reference must be a string or null")
    if record["license_status"] == "reviewed_permitted" and not record["license_reference"]:
        raise ValueError("reviewed_permitted requires a license_reference")
    if record["access_method"] not in ACCESS_METHODS:
        raise ValueError("unsupported access_method")
    _nonempty(record["collected_at_utc"], "collected_at_utc")
    try:
        timestamp = datetime.fromisoformat(record["collected_at_utc"].replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise ValueError("collected_at_utc must be ISO-8601") from None
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("collected_at_utc must include a timezone")
    digest = record["content_sha256"]
    if digest is not None and (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)):
        raise ValueError("content_sha256 must be a SHA-256 hex digest or null")
    if not isinstance(record["notes"], str):
        raise ValueError("notes must be a string")
    return dict(record)


def make_source_record(
    *, source_id: str, source_type: str, url: str, title: str,
    author: str | None = None, published_date: str | None = None,
    license_status: str = "unknown", license_reference: str | None = None,
    access_method: str = "manual", content: bytes | None = None, notes: str = "",
) -> dict[str, Any]:
    """Create a validated source record; unknown rights remain explicitly unknown."""
    record = {
        "source_id": source_id,
        "source_type": source_type,
        "url": url,
        "title": title,
        "author": author,
        "published_date": published_date,
        "license_status": license_status,
        "license_reference": license_reference,
        "access_method": access_method,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "content_sha256": hashlib.sha256(content).hexdigest() if content is not None else None,
        "notes": notes,
    }
    return validate_source_record(record)


def validate_transcript_segment(segment: Any, known_source_ids: set[str]) -> dict[str, Any]:
    """Validate timestamped transcript evidence and retain uncertainty/provenance."""
    required = {
        "segment_id", "source_id", "start_seconds", "end_seconds", "text",
        "extraction_method", "confidence", "text_sha256",
    }
    if not isinstance(segment, dict) or set(segment) != required:
        raise ValueError("transcript segment has missing or unknown fields")
    if not isinstance(segment["segment_id"], str) or not SOURCE_ID_RE.fullmatch(segment["segment_id"]):
        raise ValueError("invalid segment_id")
    if segment["source_id"] not in known_source_ids:
        raise ValueError("segment source_id is not registered")
    start, end = segment["start_seconds"], segment["end_seconds"]
    if start is not None and (not isinstance(start, (int, float)) or isinstance(start, bool) or start < 0):
        raise ValueError("start_seconds must be a non-negative number or null")
    if end is not None and (not isinstance(end, (int, float)) or isinstance(end, bool) or end < 0):
        raise ValueError("end_seconds must be a non-negative number or null")
    if start is not None and end is not None and end <= start:
        raise ValueError("end_seconds must be after start_seconds")
    _nonempty(segment["text"], "text")
    _nonempty(segment["extraction_method"], "extraction_method")
    confidence = segment["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    digest = hashlib.sha256(segment["text"].encode("utf-8")).hexdigest()
    if segment["text_sha256"] != digest:
        raise ValueError("text_sha256 does not match transcript text")
    return dict(segment)
