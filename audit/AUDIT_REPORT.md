# Phase 1 Audit Report: Panela.Build Wine App

## Section A: Build and tests
- **Git status & log**: UNVERIFIED (Sandboxed shell permissions prevent git cwd discovery: `fatal: unable to get current working directory: Operation not permitted`).
- **Tests**: PASS (`PYTHONPATH=. .venv/bin/pytest tests/ -q` -> 14 passed in 0.29s).

## Section B: Eval integrity
- **Backend used**: MOCK (`Backend: MOCK (SIMULATED EXTRACTION)` from `cli.py --eval`).
- **Benchmark cases**: 5 total, 5 synthetic (`split: synthetic`), 0 real.
- **Annotations**: `annotations/draft.csv` exists with 49 rows.
  - `needs_review=TRUE`: 49 (100% unreviewed, machine-drafted / pending review).
  - `needs_review=FALSE`: 0.
- **Dev/test split**: Defined in `annotations/draft.csv` (30 dev, 19 test), but active benchmark suite only has `synthetic: 5`.
- **Metrics reported (MOCK - SIMULATED)**:
  - Identification Top-1 Acc: 100.0% (n=5/5) [SIMULATED]
  - Tier Assignment Acc: 100.0% (n=5/5) [SIMULATED]
  - Confident-But-Wrong Rate: 0.0% (n=0/5) [SIMULATED]
  - Unsupported Claim Rate: 0.0% (n=0/10 claims) [SIMULATED]
  - Field Extraction Accuracy: producer 100% (n=5/5), wine_name 100% (n=5/5), appellation 100% (n=5/5), vintage 100% (n=5/5), abv 100% (n=5/5), barcode 100% (n=5/5) [SIMULATED].
- **Status**: SIMULATED / NOT PASS (eval is executed on simulated mock backend with 0 real human-reviewed ground truth cases).

## Section C: Non-negotiables
- **Nulls and confidence on every extracted field**: PASS (`app/schemas/extraction.py:32-52`, `ConfidenceField[T]` wraps value with `default=None`, `confidence: float`, and `ge=0.0, le=1.0`).
- **Tier and uncertainties in final response**: PASS (`app/schemas/response.py:16-19`, `ConfidenceTier` enum: `identified_wine`, `identified_style`, `unidentified`; `app/schemas/response.py:160-163`, `uncertainties: List[str]`).
- **Generation grounded only in extraction + match + knowledge**: PASS (`app/pipeline/generation.py:95-130`, `RuleBasedGenerator` uses purely extracted fields and retrieved knowledge nodes, with zero free-recall factual claims about the wine).
- **Validator wired into generation stage**: PASS (`app/pipeline/generation.py:356-408`, `self.validator.validate(...)` called, sanitizes narrative violations, re-validates, and applies conservative fallback).
- **No ratings, scores or reviews in output**: PASS (`grep -E -i "rating|score|review|stars|points" app/ -rn` shows only internal string similarity scores and explicit `"ratings_enabled": False` in `app/api/routes.py:36`).

## Section D: Orchestrator check
- **Variable definition**: PASS (`app/pipeline/orchestrator.py:38-43`, `contexts: Optional[List[str]] = None` properly defined and passed to `self.stage_1.run_multiple(images, contexts)` on line 56).
- **Latency measurement**: PARTIAL (`total_elapsed_ms`, `s1_ms`, `s2_ms`, `s3_ms`, `s4_ms` are timed with `time.perf_counter()`, but `validation_ms` on line 88 is hardcoded to `0.1`).
- **Sync vs async execution**: PARTIAL (Stage 1 is async `await`, but Stage 2 `SqliteWineDatabase`, Stage 3 JSON retrieval, and Stage 4 generation are synchronous methods running on the main event loop; acceptable for offline SQLite/memory, but not running in worker thread/executor).

## Section E: Knowledge base provenance
- **Files present**: `appellations.json`, `grapes.json`, `pairing_matrix.json`, `serving_rules.json`.
- **Schema versioning**: `"version": "1.0.0"` is present across all knowledge base files.
- **Provenance metadata**: PARTIAL (`docs/dataset_comparison.md:12-14,33-36` documents legal source references to INAO / eAmbrosia and Wikidata, but raw JSON files themselves lack explicit `source_url`, `last_reviewed_at`, or sommelier review-signature fields).

---

## Final Audit Synthesis

### 1. VERDICT: NOT COMPLETE

### 2. Scorecard
- **A. Build & tests**: PARTIAL (14 pytest pass in 0.29s; git status/log blocked by sandbox cwd permissions).
- **B. Eval integrity**: SIMULATED / NOT PASS (Ran on MOCK backend; 0 real human-reviewed ground truth cases; 49 real bottle rows in `annotations/draft.csv` pending review).
- **C. Non-negotiables**: PASS (Strict nulls/confidence, 3 tiers, uncertainties list, grounded generation, active validator, zero ratings/scores/reviews).
- **D. Orchestrator check**: PARTIAL (Variables clean & defined; latency timed except hardcoded `validation_ms=0.1`; stages 2-4 synchronous).
- **E. Knowledge base provenance**: PARTIAL (Versioned 1.0.0, external legal sources cited in docs, but no per-entry review/provenance metadata in JSON).

### 3. Metrics vs Exit Thresholds
- **Annotated Real Cases**: 0 / 50 required [FAIL] (Active suite has 5 synthetic; 49 unreviewed real draft rows).
- **Backend Evaluation**: SIMULATED / MOCK [FAIL] (Live Gemini API unexecuted due to unset `GEMINI_API_KEY`).
- **Extraction Accuracy**: SIMULATED (100% on mock; unmeasured on real photos).
- **Top-1 Identification**: SIMULATED (100% on mock n=5/5; unmeasured on real photos).
- **Confident-But-Wrong Rate**: 0.0% (n=0/5) [SIMULATED].
- **Unsupported Claim Rate**: 0.0% (n=0/10 claims) [SIMULATED] (Threshold requires n >= 50 claims).
- **Two VLMs Compared on Eval Set**: PARTIAL (Architectural comparison table in `docs/model_strategy.md`; no empirical head-to-head benchmark runs recorded).

### 4. Top 3 Blockers (Ranked by Hallucination Risk)
1. **Zero Human-Reviewed Ground Truth**: 49 bottle cases in `annotations/draft.csv` have `needs_review=TRUE`. Without verified ground truth, pipeline hallucination cannot be empirically measured or prevented.
2. **Unexecuted Live VLM Benchmark**: Stage 1 VLM extraction has only run on deterministic simulated mocks; real OCR error rates on glare/curved cave bottles are unmeasured.
3. **Hardcoded Validation Metric**: `validation_ms` hardcoded to 0.1ms masks actual runtime performance overhead in production.

### 5. Next 3 Actions
1. **Annotate & Promote Ground Truth (M)**: Inspect label photos and verify fields in `annotations/draft.csv`, setting `needs_review=FALSE`, then run `.venv/bin/python scripts/csv_to_benchmark.py`.
2. **Run Live Eval on Dev Split (M)**: Export `GEMINI_API_KEY` and run `PYTHONPATH=. .venv/bin/python cli.py --eval --backend gemini --split dev`.
3. **Fix Validation Latency Timing (S)**: Instrument actual `time.perf_counter()` around `self.stage_4.validator.validate()`.

### 6. Unverified Items & Commands to Run
- **Live VLM Eval**:
  ```bash
  export GEMINI_API_KEY="your-api-key"
  PYTHONPATH=. .venv/bin/python cli.py --eval --backend gemini --split dev
  ```
- **Git Status & History** (outside restricted sandbox):
  ```bash
  git status --short
  git log --oneline -n 10
  ```
