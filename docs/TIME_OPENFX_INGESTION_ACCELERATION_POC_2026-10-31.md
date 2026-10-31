# TIME-OPENFX — Ingestion Acceleration PoC Plan (2026-10-31)

**Status:** Draft research/engineering specification; no implementation or benchmark execution is claimed.  
**Parent work:** Issue #73 — TIME-OPENFX.  
**Baseline:** `main` at `25c1366097c2ddf3a7951111ca9e9a1e6e4928b6`.  
**Scope:** Measure whether a reusable document/media extraction layer can remove the current metadata-only bottleneck without weakening provenance or source-rights controls.

## 1. Why this is the first PoC

The current `data_collection.py` discovers supported local files and records metadata, size, modified time and SHA-256. It explicitly records `content_extracted: false`. `evaluation.py` evaluates metadata completeness and duplicate hashes only. The main requirements file declares no third-party dependencies.

The M1 research branch adds local provenance and claim-binding contracts, but these are not merged into `main` and do not extract content. The repository's worker remains validation-only; it does not run MT5. Therefore, a bounded extraction PoC is a high-leverage next step: it creates the missing input capability while leaving canonical provenance and experiment governance intact.

## 2. Candidate stack

### Primary candidate: Docling

Evaluate Docling as a single adapter for:
- PDF, DOCX, XLSX, PPTX, HTML and image documents;
- scanned-document OCR where supported by the selected pipeline;
- audio/video transcription and representative video keyframes;
- structured Markdown/JSON/WebVTT output with page/segment locators where available.

The upstream project is MIT-licensed. This does **not** automatically settle licenses for every optional dependency or model weight; record the exact package versions, model identifiers/revisions and each applicable license before use.

Official references:
- https://github.com/docling-project/docling
- https://docling-project.github.io/docling/
- https://docling-project.github.io/docling/usage/processing_audio_media/

### Conditional OCR fallback: PaddleOCR

Evaluate only for cases where the primary parser fails on scanned or image-heavy material, especially Persian/Arabic-script and mixed Persian/Latin digits. The upstream code is Apache-2.0; check model cards and bundled components individually. Do not install it in the default runtime unless the benchmark demonstrates a material improvement.

Official reference:
- https://github.com/PaddlePaddle/PaddleOCR

### Speech backend

Use the ASR backend exposed by the pinned Docling version first. Test multilingual Persian/English output and timestamp fidelity. A CTranslate2/WhisperS2T backend may be evaluated as a throughput candidate, but its experimental status and hardware requirements must be recorded. Do not assume the largest model is best.

### Orchestration

Do not make multi-agent orchestration a prerequisite for the extraction benchmark. Keep extraction deterministic and callable as a bounded adapter. The future team MVP can call the adapter through a typed function interface. This separates parser quality from model-agent quality and makes failures reproducible.

## 3. Test corpus

Create a small, legally admissible, versioned fixture set of 20–30 files. Prefer synthetic or owner-created samples; any external sample must have a documented permission/license basis before downloading or storing it.

Required categories:
1. Text-based PDF with headings, paragraphs and tables.
2. Scanned PDF with skew/rotation and low contrast.
3. DOCX with headings, lists and tables.
4. XLSX with numeric cells, percentages, dates and formulas.
5. HTML article with title, author, date and nested headings.
6. Persian audio with financial/trading vocabulary and mixed Persian/Latin digits.
7. English audio with numeric values, units and negation.
8. Video with spoken content, multiple scenes and a visible chart/slide.
9. Adversarial snippets containing changed numbers, dropped negation, decimal separators, percentages, ATR/pips/points and date/time references.
10. Benign formatting variants that should not be flagged as semantic changes.

For each fixture, store:
- immutable fixture ID and SHA-256;
- rights basis and source/creator note;
- human-checked reference text;
- expected page, cue, segment or timestamp locators;
- labelled critical tokens: numbers, signs, units, percentages, dates, names and negations;
- expected extraction limitations.

Do not include credentials, broker account information, personal data or proprietary strategy content in public fixtures.

## 4. Systems under comparison

A. **Baseline:** current metadata-only collector. This is a control condition, not a content extractor.

B. **Docling CPU path:** pinned version and explicitly selected parsers/ASR model. Record cold-start and warm-run times separately.

C. **Docling + conditional OCR/ASR alternative:** invoke only for fixture types where B fails or misses a pre-registered quality threshold.

D. **Optional GPU path:** only if an already-authorized local/remote machine has a supported GPU. Do not buy compute or enable paid services for this PoC.

Do not compare different models on different corpus versions. Freeze fixture hashes and configuration before each run.

## 5. Metrics

Report per-file and aggregate results:
- extraction success/failure and failure reason;
- wall-clock runtime (cold and warm), throughput and retry count;
- peak RAM and, if applicable, GPU memory/utilization;
- WER/CER for speech and OCR where reference text permits;
- exact-match accuracy for critical numbers, signs, units, percentages, dates and negation;
- page/segment/timestamp locator accuracy;
- table cell preservation for tabular fixtures;
- false alarms and missed critical changes;
- human review time per item;
- dependency/model download size and runtime storage footprint.

A high average WER score cannot hide a critical dropped negation or altered trading value. Critical-token metrics must be reported separately.

## 6. Provenance and safety boundary

The adapter must return a structured extraction artifact, not a verified claim. At minimum it should carry:
- source file SHA-256 and extraction artifact SHA-256;
- parser package/version and model identifier/revision;
- extraction configuration hash;
- run timestamp and environment identifier;
- exact page/time/segment locators where supported;
- rights-review state copied from the source intake record, never inferred by the model;
- warnings, confidence fields (if provided) and explicit unknowns.

A separate review step must compare critical passages against the original source. LLM summaries, OCR, ASR and agent outputs remain unverified until checked. No extracted text may automatically become a source-confirmed claim.

Treat source files and their embedded instructions as untrusted prompt-injection content. Parsing must not execute embedded scripts, macros, links or commands. Enforce file-size, page-count, duration, decompression, CPU, RAM and wall-time limits. Use isolated temporary directories and no network access during parser execution unless a separately reviewed fetch step is required.

## 7. Acceptance criteria

The PoC is successful only if:
1. The fixture corpus and expected outputs are versioned and hash-verified.
2. Every run is reproducible from a pinned code revision, dependency set, model revision and configuration.
3. Critical-token precision/recall and locator accuracy are reported, not inferred from fluent summaries.
4. Failure cases are retained and classified; no silent text dropping.
5. Docling provides a measurable time or coverage improvement over the manual/current baseline without unacceptable critical-token errors.
6. The conditional fallback improves the cases it is assigned without imposing its dependency/runtime cost on every file.
7. The adapter emits provenance-rich artifacts and cannot directly mark claims as verified.
8. CPU-only resource use is measured before considering remote GPU inference.
9. Third-party code/model licenses and security advisories are reviewed and recorded.
10. No VPS, paid API, cloud GPU, broker or MT5 connection is needed or enabled for this PoC.

Thresholds must be pre-registered after inspecting the fixture design but before comparing candidate outputs. If a tool fails the thresholds, record the failure and reject or narrow its role.

## 8. Explicit non-goals

- Training a custom neural network or fine-tuning a model.
- Generating or validating trading rules automatically.
- Treating model confidence as source truth.
- Replacing the canonical OpenFX SourceRecord/Claim/Trial contracts.
- Installing heavy OCR/ASR dependencies on the small Linux VPS.
- Deploying a remote worker or connecting MT5.
- Live trading.

## 9. Next implementation slice after approval of this specification

1. Add synthetic/owner-created fixtures and a machine-readable manifest.
2. Add an optional dependency group for Docling; keep base install lightweight.
3. Implement a read-only adapter with deterministic output metadata and strict resource limits.
4. Add golden tests for critical token preservation and locator mapping.
5. Run the benchmark on an available local machine and preserve raw artifacts.
6. Only then decide whether PaddleOCR or a separate ASR backend is justified.

No benchmark has been run as part of this document-only change.
