# Source ingestion and transcript quality boundary

## Implemented foundation

- `openfx/source_registry.py` validates stable source IDs, HTTPS URLs, source type, author/date metadata, rights-review status, access method, collection timestamp, and optional SHA-256 content hash. It can validate and atomically save/load a local registry.
- `openfx/transcript_import.py` imports authorized local VTT, SRT, and plain-text files; it preserves timestamps when present, strips subtitle markup, creates deterministic segment IDs, and hashes the exact imported text. It rejects malformed or out-of-order subtitle cues and caps local files at 10 MiB.
- A source marked `reviewed_permitted` must include a reference explaining the permission/license decision.
- Transcript segments must reference a registered source and record extraction method, optional timestamps, confidence, and a SHA-256 hash of the exact text.
- `openfx/transcript_quality.py` compares a reference transcript with extracted text and flags missing/changed numeric tokens, changed negation tokens, and low token similarity.
- `openfx/evidence.py` validates claim-to-source provenance and requires exact quoted text for source claims; source-confirmed claims require a human-verified review status.
- Empty examples are available at `data/source_registry.example.json` and `data/claim_register.example.json`; schemas are in `schemas/source-registry-v1.schema.json` and `schemas/claim-register-v1.schema.json`.

## Important limits

These modules validate records and import local transcript files; they do **not** discover videos, download media, obtain captions, run speech recognition, or prove that a transcript is correct. The transcript fidelity checker is a heuristic triage tool, not a semantic verifier. Human review against the original source remains necessary for important rules, numbers, dates, negation, speaker attribution, and timestamps.

A public URL does not automatically grant permission to download, copy, transcribe, or redistribute its content. Keep the rights status as `unknown` until reviewed. Use only authorized source methods and respect site terms, copyright, access controls, and rate limits.

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

The next phase is an authorized connector for source discovery and transcript acquisition. It should be provider-specific, rate-limited, rights-aware, provenance-preserving, and tested against synthetic adversarial fixtures before it is allowed to ingest real sources. No crawler or speech-to-text provider is enabled by this repository change.
