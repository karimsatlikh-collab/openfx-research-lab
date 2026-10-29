"""Command-line interface for local, provenance-aware OpenFX source ingestion."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .source_registry import (
    ACCESS_METHODS,
    LICENSE_STATUSES,
    SOURCE_TYPES,
    load_source_registry,
    make_source_record,
    new_source_registry,
    save_source_registry,
)
from .transcript_import import import_transcript_file_into_registry
from .youtube_search import search_youtube_videos


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create an empty local source registry")
    init.add_argument("--output", required=True, help="registry JSON path")

    add = commands.add_parser("add-source", help="register source metadata and rights status")
    add.add_argument("--registry", required=True)
    add.add_argument("--source-id", required=True)
    add.add_argument("--type", dest="source_type", required=True, choices=sorted(SOURCE_TYPES))
    add.add_argument("--url", required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--author")
    add.add_argument("--published-date")
    add.add_argument("--license-status", choices=sorted(LICENSE_STATUSES), default="unknown")
    add.add_argument("--license-reference")
    add.add_argument("--access-method", choices=sorted(ACCESS_METHODS), default="manual")
    add.add_argument("--notes", default="")

    ingest = commands.add_parser("import-transcript", help="import an authorized local VTT/SRT/TXT file")
    ingest.add_argument("--registry", required=True)
    ingest.add_argument("--source-id", required=True)
    ingest.add_argument("--input", required=True, help="local transcript file")
    ingest.add_argument("--format", choices=["vtt", "srt", "txt"])

    search = commands.add_parser("search-youtube", help="discover public video metadata through the official API")
    search.add_argument("--registry", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--max-results", type=int, default=10)
    search.add_argument("--order", choices=sorted({"date", "rating", "relevance", "title", "videoCount", "viewCount"}), default="relevance")
    search.add_argument("--region-code")
    search.add_argument("--relevance-language")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            output = Path(args.output)
            if output.exists():
                raise ValueError("registry output already exists; refusing to overwrite")
            save_source_registry(new_source_registry(), output)
            print(f"Created empty source registry: {output}")
            return 0

        if args.command == "add-source":
            registry = load_source_registry(args.registry)
            record = make_source_record(
                source_id=args.source_id,
                source_type=args.source_type,
                url=args.url,
                title=args.title,
                author=args.author,
                published_date=args.published_date,
                license_status=args.license_status,
                license_reference=args.license_reference,
                access_method=args.access_method,
                notes=args.notes,
            )
            registry["sources"].append(record)
            save_source_registry(registry, args.registry)
            print(f"Registered source {record['source_id']} with rights status {record['license_status']}.")
            return 0

        if args.command == "import-transcript":
            registry = load_source_registry(args.registry)
            updated = import_transcript_file_into_registry(
                registry, args.source_id, args.input, args.format
            )
            save_source_registry(updated, args.registry)
            count = len(updated["transcript_segments"]) - len(registry["transcript_segments"])
            print(f"Imported {count} transcript segments for {args.source_id}.")
            print("Parser confidence describes file parsing, not transcript accuracy.")
            return 0

        if args.command == "search-youtube":
            registry = load_source_registry(args.registry)
            records = search_youtube_videos(
                args.query,
                max_results=args.max_results,
                order=args.order,
                region_code=args.region_code,
                relevance_language=args.relevance_language,
            )
            known_ids = {source["source_id"] for source in registry["sources"]}
            new_records = []
            for record in records:
                if record["source_id"] not in known_ids:
                    new_records.append(record)
                    known_ids.add(record["source_id"])
            registry["sources"].extend(new_records)
            save_source_registry(registry, args.registry)
            print(f"Discovered {len(records)} videos; added {len(new_records)} new source records.")
            print("Rights status remains unknown until each source is reviewed.")
            return 0

        parser.error("unknown command")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, UnicodeError) as exc:
        print(f"OpenFX source ingestion error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
