"""
Data Collection Module
Initial support for authorized local file discovery and metadata collection.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("openfx.data_collection")

SUPPORTED_EXTENSIONS = {
    ".txt", ".csv", ".json", ".xml", ".pdf",
    ".docx", ".xlsx", ".jpg", ".jpeg", ".png",
    ".mp3", ".wav", ".mp4", ".mov"
}


def calculate_sha256(file_path: Path) -> str:
    """Calculate a file's SHA-256 hash for integrity and deduplication."""
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def collect_local_metadata(source_directory: str) -> list[dict]:
    """
    Discover supported files in a user-provided local directory.

    This function records metadata only. It does not upload files,
    access remote systems, or extract private information.
    """
    root = Path(source_directory).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {root}")

    records = []

    for file_path in root.rglob("*"):
        # Do not follow symlinks: a symlink inside the selected folder could
        # otherwise expose metadata for files outside the authorized root.
        if file_path.is_symlink() or not file_path.is_file():
            continue
        try:
            resolved_path = file_path.resolve(strict=True)
            resolved_path.relative_to(root)
        except (OSError, ValueError):
            logger.warning("Skipping file outside or unavailable under source root: %s", file_path)
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            stat = resolved_path.stat()

            record = {
                "file_name": file_path.name,
                "relative_path": file_path.relative_to(root).as_posix(),
                "file_type": file_path.suffix.lower(),
                "file_size_bytes": stat.st_size,
                "modified_time_utc": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "sha256": calculate_sha256(resolved_path),
                "collection_time_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "collection_method": "authorized_local_file_scan",
                "content_extracted": False,
            }

            records.append(record)

        except (OSError, PermissionError) as error:
            logger.warning("Could not inspect %s: %s", file_path, error)

    logger.info("Discovered %d supported files in %s", len(records), root)
    return records


def save_metadata(records: list[dict], output_path: str) -> None:
    """Save collected metadata as a JSON file."""
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8") as output:
        json.dump(records, output, ensure_ascii=False, indent=2)

    logger.info("Saved %d metadata records to %s", len(records), destination)
