# WineLM 🍷 — Zero-Hallucination VLM Pipeline for Wine Bottle Recognition

> **TL;DR (FR)** : Pipeline multimodal de Computer Vision & VLM (Vision-Language Model) développé avec **FastAPI**, **Gemini 1.5 Flash**, **Pydantic v2** et **SQLite FTS5 + RapidFuzz**. Il transforme les photos d'étiquettes de vin (recto/verso) en explications œnologiques factuelles (température de service, carafage, notes de dégustation sourcées et accords mets-vins chimiques/structurels). Positionné à l'opposé du marketing des notes Vivino, le système garantit **zéro hallucination** grâce à une base légale européenne (eAmbrosia) et un validateur de traçabilité des assertions.


A factual, hallucination-free backend pipeline transforming wine bottle photos into calm, educational wine explanations (serving guidelines, grape/terroir-grounded tasting notes, and structural food pairings).

Positioning: **Closer to Yuka than Vivino**. NO ratings, NO scores, NO reviews, NO social feeds.

---

## Architecture Overview

```
                        [ Single Photo or Multi-Photo (Front + Back) ]
                                          │
                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │ Stage 1: VLM Extraction (Gemini 1.5 Flash + Multi-Photo Fusion)             │
   │  - Strict JSON Optical Transcriber (Never guesses, per-field confidence)     │
   │  - Unprinted grapes = null, obscured vintage = null, barcode = EAN-13      │
   │  - Fuses front label (branding/AOC) + back label (barcode/ABV/terroir)      │
   └──────────────────────────────────────┬──────────────────────────────────────┘
                                          │  ExtractionOutput (Fused Pydantic Record)
                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │ Stage 2: Identification (Offline-First SQLite Index)                        │
   │  1. Sub-millisecond indexed barcode lookup (EAN-13) in wines.sqlite         │
   │  2. SQLite FTS5 candidate retrieval + RapidFuzz token-set re-ranking        │
   └──────────────────────────────────────┬──────────────────────────────────────┘
                                          │  MatchInfo + Reference Entity
                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │ Stage 3: Curated Knowledge Layer                                            │
   │  - Versioned in-repo database (eAmbrosia legal appellations, grape chemistry)│
   │  - Serving rules matrix (temp, glass, decanting, drink window)              │
   │  - Chemical & structural food pairing matrix (acidity, tannin, fat, salt)   │
   └──────────────────────────────────────┬──────────────────────────────────────┘
                                          │  RetrievedKnowledge
                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │ Stage 4: Generation, Capture Advice & Attributed Validation                 │
   │  - Confidence Tiers: 'identified_wine' | 'identified_style' | 'unidentified'│
   │  - Capture Advice: Analyzes if 1st photo is enough or asks for back label  │
   │  - HallucinationValidator: Verifies all claims against extraction + KB     │
   │  - Full Traceability Log (each statement mapped to its exact source)       │
   └──────────────────────────────────────┬──────────────────────────────────────┘
                                          │
                                          ▼
                               [ FinalResponse JSON ]
```

---

## Core Zero-Hallucination Principles

1. **The LLM is NEVER the source of truth for wine facts.** Facts derive strictly from optical label reading or retrieved enological knowledge.
2. **Strict Null & Confidence Calibration**: Every extracted field is a `ConfidenceField[T]` with a score from `0.0` to `1.0`. If a field is unprinted (e.g. grape varieties on classic French AOC bottles), it is set to `null` or `[]` with `0.0` confidence.
3. **Three Confidence Tiers**:
   - `identified_wine`: Exact match of producer, wine name, and vintage.
   - `identified_style`: Appellation or grape known, producer unknown. Phrased as *"Typical for this style/region"*, never attributing facts to a specific estate.
   - `unidentified`: Label illegible. Tasting notes and drinking guide are null; honest uncertainties and photo suggestions returned.
4. **Intelligent Camera Ingestion (Capture Advice)**:
   - Supports 1 photo or multi-photo uploads (front + back label).
   - If a single photo is passed, the engine evaluates whether that photo is enough. If key facts are missing (e.g. front label without vintage/barcode), `capture_advice.needs_second_photo` is flagged with instructions to snap the back label.
5. **Offline-First SQLite Database**: Barcodes and canonical wines are indexed locally in SQLite with FTS5 candidate search, eliminating reliance on unstable external APIs during scanning.
6. **Attribution & Hallucination Validator**: Inspects generated output for unauthorized claims, unverified grapes, or unwarranted estate assertions.
7. **Always Returns Uncertainties**: Explicitly declares what could not be determined from the bottle image.

---

## Quickstart

### 1. Installation
```bash
# Using uv or pip
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. Configure Gemini 1.5 Flash (Optional for live API)
```bash
# Set your Gemini API key (optional; defaults safely to mock backend when unset)
export GEMINI_API_KEY="your-google-gemini-api-key"
```

### 3. Run Single Test Image CLI
```bash
# Single image test
python cli.py --image tests/fixtures/sample_bottle.jpg

# Multi-photo test (front + back label)
python cli.py --image front.jpg --image back.jpg
```

### 4. Run Evaluation Benchmark
```bash
python cli.py --eval
# or
python eval/harness.py
```

### 5. Run Unit Tests (12 tests)
```bash
pytest tests/ -v
```

### 6. Start FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
# Test health: curl http://localhost:8000/health
# Interactive Swagger docs: http://localhost:8000/docs
```

---

## API Endpoints

### `POST /api/v1/explain`
Accepts `multipart/form-data`:
- `files`: One or multiple image files (front and/or back labels).
- `file`: Single image upload fallback.
- `additional_context`: Optional hint string (e.g. "Front label").

Returns `FinalResponse`:
- `summary`: Headline, tier (`identified_wine`, `identified_style`, `unidentified`), canonical match.
- `capture_advice`:
  - `needs_second_photo`: Boolean.
  - `suggested_label_type`: `"back_label"`, `"front_label"`, or `"clearer_shot"`.
  - `reason`: Why a second photo would improve confidence.
  - `user_prompt_message`: Calm, user-facing prompt.
- `drinking_guide`: Serving temp (°C and °F), glassware, decanting, drink window.
- `tasting_notes`: Structural indicators (1-5), primary aroma/flavor notes, fact-restricted narrative.
- `food_pairings`: Recommended dishes (pairing rules) + dishes to avoid (chemical clashes).
- `uncertainties`: Explicit list of unreadable or unconfirmed fields.
- `traceability_log`: Factual provenance audit log for every claim.
- `metrics`: Per-stage latency breakdown and estimated cost in USD.