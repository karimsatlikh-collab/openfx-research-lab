"""Import authorized local VTT/SRT/plain-text transcripts into a provenance registry.

No network access, video downloading, OCR, or speech recognition is performed here.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

from .source_registry import validate_source_registry, validate_transcript_segment

_TIMESTAMP = r"(?:\d{2,}:)?\d{2}:\d{2}[.,]\d{1,3}"
_CUE_LINE_RE = re.compile(rf"^\s*({_TIMESTAMP})\s+-->\s+({_TIMESTAMP})(?:\s+.*)?\s*$")
_TAG_RE = re.compile(r"<[^>]*>")
_MAX_TRANSCRIPT_BYTES = 10 * 1024 * 1024


def _time_to_seconds(value: str) -> float:
    match = re.fullmatch(r"(?:(\d{2,}):)?(\d{2}):(\d{2})[.,](\d{1,3})", value)
    if not match:
        raise ValueError(f"invalid subtitle timestamp: {value}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    milliseconds = int(match.group(4).ljust(3, "0"))
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"out-of-range subtitle timestamp: {value}")
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def _clean_caption_text(lines: list[str]) -> str:
    text = html.unescape(" ".join(line.strip() for line in lines if line.strip()))
    text = re.sub(r"<v(?:\.[^ >]+)?\s+([^>]+)>", r"\1: ", text, flags=re.IGNORECASE)
    text = re.sub(r"\{\\[^}]+\}", "", text)
    text = _TAG_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _caption_blocks(content: str, source_id: str, fmt: str) -> list[dict[str, Any]]:
    segments = []
    previous_start = -1.0
    for block in re.split(r"\n\s*\n", content.replace("\r\n", "\n").replace("\r", "\n")):
        lines = [line.strip("\ufeff").rstrip() for line in block.split("\n")]
        lines = [line for line in lines if line.strip()]
        if not lines:
            continue
        first = lines[0].lstrip("\ufeff").strip()
        if first == "WEBVTT":
            continue
        timestamp_indices = [i for i, line in enumerate(lines) if "-->" in line]
        if not timestamp_indices:
            # Skip only actual metadata blocks. A cue identifier may itself be
            # NOTE or STYLE, and a malformed cue must never be silently omitted.
            if first in {"STYLE", "REGION"} or re.match(r"^NOTE(?:\s|$)", first):
                continue
            raise ValueError("subtitle block has no timestamp line")
        if len(timestamp_indices) != 1:
            raise ValueError("subtitle block contains multiple timestamp lines")
        index = timestamp_indices[0]
        match = _CUE_LINE_RE.fullmatch(lines[index])
        if not match:
            raise ValueError(f"malformed subtitle timestamp line: {lines[index]}")
        start = _time_to_seconds(match.group(1))
        end = _time_to_seconds(match.group(2))
        if end <= start:
            raise ValueError("subtitle cue end must be after its start")
        if start < previous_start:
            raise ValueError("subtitle cues must be ordered by non-decreasing start time")
        previous_start = start
        text = _clean_caption_text(lines[index + 1:])
        if not text:
            continue
        segments.append({
            "source_id": source_id,
            "start_seconds": start,
            "end_seconds": end,
            "text": text,
            "extraction_method": f"{fmt}_file_import",
            # This is parser confidence only, not confidence that the captions match speech.
            "confidence": 1.0,
        })
    if not segments:
        raise ValueError("no valid timestamped transcript cues found")
    return segments


def parse_transcript_text(content: str, source_id: str, fmt: str) -> list[dict[str, Any]]:
    """Parse VTT, SRT, or plain text into hashed transcript segments."""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("transcript content must be a non-empty string")
    if not isinstance(source_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", source_id):
        raise ValueError("invalid source_id")
    if not isinstance(fmt, str):
        raise ValueError("transcript format must be a string")
    if len(content.encode("utf-8")) > _MAX_TRANSCRIPT_BYTES:
        raise ValueError("transcript content exceeds the 10 MiB limit")
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    normalized_format = fmt.lower().lstrip(".")
    if normalized_format in {"vtt", "webvtt", "srt"}:
        segments = _caption_blocks(content, source_id, "vtt" if normalized_format in {"vtt", "webvtt"} else "srt")
    elif normalized_format in {"txt", "text", "plain"}:
        paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
        if not paragraphs:
            paragraphs = [re.sub(r"\s+", " ", content).strip()]
        segments = [{
            "source_id": source_id,
            "start_seconds": None,
            "end_seconds": None,
            "text": paragraph,
            "extraction_method": "plain_text_import",
            "confidence": 1.0,
        } for paragraph in paragraphs if paragraph]
    else:
        raise ValueError("unsupported transcript format; use VTT, SRT, or plain text")

    source_hash = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:10]
    output = []
    for index, segment in enumerate(segments, start=1):
        segment["segment_id"] = f"seg-{source_hash}-{index:06d}"
        segment["text_sha256"] = hashlib.sha256(segment["text"].encode("utf-8")).hexdigest()
        output.append(segment)
    return output


def import_transcript_file(path: str | Path, source_id: str, fmt: str | None = None) -> list[dict[str, Any]]:
    """Read an authorized local transcript with a 10 MiB size limit."""
    source_path = Path(path)
    size = source_path.stat().st_size
    if size <= 0 or size > _MAX_TRANSCRIPT_BYTES:
        raise ValueError("transcript file must be between 1 byte and 10 MiB")
    content = source_path.read_text(encoding="utf-8-sig")
    if fmt is not None and not isinstance(fmt, str):
        raise ValueError("transcript format must be a string")
    format_name = fmt or source_path.suffix
    return parse_transcript_text(content, source_id, format_name)


def import_transcript_into_registry(
    registry: dict[str, Any], source_id: str, content: str, fmt: str,
) -> dict[str, Any]:
    """Return a new validated registry with imported segments appended."""
    validated = validate_source_registry(registry)
    if not isinstance(source_id, str) or source_id not in {source["source_id"] for source in validated["sources"]}:
        raise ValueError("source_id must be registered before importing its transcript")
    source_record = next(source for source in validated["sources"] if source["source_id"] == source_id)
    if source_record["license_status"] in {"restricted", "permission_required"}:
        raise ValueError("source rights status blocks transcript ingestion")
    updated = json.loads(json.dumps(validated, ensure_ascii=False))
    segments = parse_transcript_text(content, source_id, fmt)
    existing_ids = {segment["segment_id"] for segment in updated["transcript_segments"]}
    if any(segment["segment_id"] in existing_ids for segment in segments):
        raise ValueError("transcript segment IDs already exist in this registry")
    for segment in segments:
        validate_transcript_segment(segment, {source["source_id"] for source in updated["sources"]})
    updated["transcript_segments"].extend(segments)
    validate_source_registry(updated)
    return updated


def import_transcript_file_into_registry(
    registry: dict[str, Any], source_id: str, path: str | Path, fmt: str | None = None,
) -> dict[str, Any]:
    """Import a bounded local transcript file into a validated registry."""
    source_path = Path(path)
    size = source_path.stat().st_size
    if size <= 0 or size > _MAX_TRANSCRIPT_BYTES:
        raise ValueError("transcript file must be between 1 byte and 10 MiB")
    content = source_path.read_text(encoding="utf-8-sig")
    if fmt is not None and not isinstance(fmt, str):
        raise ValueError("transcript format must be a string")
    format_name = fmt or source_path.suffix
    return import_transcript_into_registry(registry, source_id, content, format_name)
