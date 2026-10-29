# Source ingestion and transcript quality boundary

## Implemented foundation

- `openfx/source_registry.py` validates stable source IDs, HTTPS URLs, source type, author/date metadata, rights-review status, access method, collection timestamp, and optional SHA-256 content hash. It can validate and atomically save/load a local registry.
- `openfx/transcript_import.py` imports authorized local VTT, SRT, and plain-text files; it preserves timestamps when present, strips subtitle markup, creates deterministic segment IDs, and hashes the exact imported text. It rejects malformed or out-of-order subtitle cues, caps content at 10 MiB, and blocks sources marked `restricted` or `permission_required`.
- `openfx/youtube_search.py` searches public video metadata through the official YouTube Data API v3; it does not download videos or captions.
- `python -m openfx.source_cli` provides local commands to initialize a registry, register source metadata, import an authorized transcript, and search YouTube metadata. The search command requires `YOUTUBE_API_KEY` in the environment; restrict that key to the YouTube Data API v3 in Google Cloud and never commit it.

- A source marked `reviewed_permitted` must include a reference explaining the permission/license decision.
- Transcript segments must reference a registered source and record extraction method, optional timestamps, confidence, and a SHA-256 hash of the exact text.
- `openfx/transcript_quality.py` compares a reference transcript with extracted text and flags missing/changed numeric tokens, changed negation tokens, and low token similarity.
- `openfx/evidence.py` validates claim-to-source provenance and requires exact quoted text for source claims; source-confirmed claims require a human-verified review status.
- Empty examples are available at `data/source_registry.example.json` and `data/claim_register.example.json`; schemas are in `schemas/source-registry-v1.schema.json` and `schemas/claim-register-v1.schema.json`.

## Important limits

These modules validate records and import local transcript files. The official API connector discovers video metadata only; it does **not** download media, obtain captions, run speech recognition, or prove that a transcript is correct. The transcript fidelity checker is a heuristic triage tool, not a semantic verifier. Human review against the original source remains necessary for important rules, numbers, dates, negation, speaker attribution, and timestamps.

A public URL does not automatically grant permission to download, copy, transcribe, or redistribute its content. Keep the rights status as `unknown` until reviewed. Use only authorized source methods and respect site terms, copyright, access controls, and rate limits.

## Example local workflow

Run these commands from the repository root. Use an authorized transcript file you already possess; the example URL is a placeholder, not a discovered source.

```bash
python -m openfx.source_cli init --output data/private/source_registry.json
python -m openfx.source_cli add-source --registry data/private/source_registry.json --source-id sample-video-001 --type video --url https://example.com/video --title "Synthetic example video" --license-status unknown --access-method user_provided
python -m openfx.source_cli import-transcript --registry data/private/source_registry.json --source-id sample-video-001 --input /path/to/authorized-captions.vtt
```

The local registry is stored under the ignored `data/private/` directory. Do not commit transcript text, personal data, credentials, or material you are not authorized to redistribute.

To discover public video metadata, first configure a restricted `YOUTUBE_API_KEY` environment variable, then run:

```bash
python -m openfx.source_cli search-youtube --registry data/private/source_registry.json --query "Saeid Khakester forex" --max-results 10 --relevance-language fa
```

The API key is not accepted as a command-line argument. Search results are metadata only and are saved with rights status `unknown`; review each source before deciding whether/how to acquire or use its transcript. YouTube API quota limits apply.


## Recommended record workflow

1. Register a source with a stable ID and the canonical HTTPS URL.
2. Record author, publication date where known, source type, collection method, rights status, and rights evidence/reference.
3. If authorized text/media is supplied, hash the exact bytes and preserve the original unchanged.
4. Import an authorized transcript with `parse_transcript_text(content, source_id, "vtt" | "srt" | "txt")` or `import_transcript_file(path, source_id)`. Parser confidence is not evidence that the captions match the spoken words.
5. Compare extracted text against a human-checked reference when one is available.
6. Resolve every high-risk warning manually. Store source-confirmed statements separately from interpretations and hypotheses.
7. Record candidate statements in the claim register with their classification and exact evidence. Group suspected conflicts for manual review rather than assuming an automated detector proved a contradiction.
8. Do not convert transcript text into trading rules until evidence, uncertainty, and rule interpretation have been reviewed.

## Next implementation boundary

The next phase is an authorized transcript/caption acquisition connector. It should be provider-specific, rate-limited, rights-aware, provenance-preserving, and tested against synthetic adversarial fixtures before it is allowed to ingest real sources. The current YouTube connector searches metadata only; no video downloader or speech-to-text provider is enabled.
