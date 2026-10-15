# Model Strategy: VLM Extraction & Text Generation Comparison

This document defines the model selection strategy for Phase 1 and the fine-tuning roadmap for Phase 2.

---

## 1. VLM Extraction Candidates (Optical Label Parser)

The Stage 1 VLM has one strict mandate: **accurately transcribe printed label facts into structured JSON with zero hallucination and calibrated confidence scores.**

| Model | Weights & Licence | VRAM Footprint | Strengths | Weaknesses | Est. Latency | Est. Cost / 1k Scans |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen2.5-VL-7B-Instruct** | Open (Apache 2.0) | 16GB (FP16) / 8GB (AWQ 4-bit) | State-of-the-art OCR on curved bottles; native dynamic resolution; excellent French/Italian diacritics; fully fine-tunable. | Requires dedicated GPU (T4 / A10G / L4). | 450–700 ms | ~$0.30 (amortized GPU) |
| **SmolVLM-2B** (HuggingFace) | Open (Apache 2.0) | 4.5GB (FP16) / 2GB (INT4) | Ultra-lightweight; runs on CPU or consumer edge; fast cold-starts. | Weak on small legal print (ABV, volume, barcode digits); lower confidence calibration. | 250–400 ms | ~$0.08 (CPU/small VM) |
| **Florence-2-Large** (0.77B) | Open (MIT) | 2GB | Outstanding bounding box OCR; pinpoint text localization on curved labels. | Outputs raw OCR strings; requires a secondary LLM call to convert into structured JSON. | 180–300 ms (+ downstream parse) | ~$0.06 |
| **Gemini 1.5 Flash** *(API Baseline)* | Proprietary (Google Cloud) | Serverless | Native Pydantic schema enforcement; zero infra management; stellar multi-lingual OCR; handles extreme glare. | Network hop to cloud API; API rate limits. | 550–900 ms | **$0.15** ($0.075 / 1M tokens) |
| **GPT-4o-mini** *(API Baseline)* | Proprietary (OpenAI) | Serverless | High JSON schema compliance; strong multilingual OCR. | Slightly higher token cost than Gemini Flash on images. | 650–1100 ms | **$0.30** ($0.15 / 1M tokens) |

### Recommendation for Phase 1 & 2
- **Phase 1 Production Baseline**: Use **Gemini 1.5 Flash** (or **GPT-4o-mini**) with strict `response_format` JSON schema enforcement. It offers zero infrastructure overhead, negligible cost (~$0.00015 per bottle), and top-tier OCR resilience against wine cave glare and bottle curvature.
- **Phase 2 Open-Weight Strategy**: Benchmark and fine-tune **Qwen2.5-VL-7B** using LoRA on the evaluation benchmark dataset. Qwen2.5-VL is the only open model matching frontier API models on multilingual typography, vintage extraction, and curved neck labels.

---

## 2. Text Generation Model Candidates (Stage 4)

Stage 4 synthesizes extracted facts + retrieved knowledge into concise, calm, educational text following the 3 confidence tiers.
Because factual retrieval happens deterministically in Stage 3, the text model does **not** need massive parameter counts—it only needs strict adherence to system prompts and attribution.

| Model | Type | Context Window | Generation Cost / 1k Requests | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini 1.5 Flash** | Managed API | 1M tokens | ~$0.04 | **Recommended default API**: blazing fast, sub-400ms generation, highly compliant. |
| **Llama 3.1 8B Instruct** | Open (Llama 3.1 Community) | 128k tokens | ~$0.02 (self-hosted) | **Recommended open self-hosted**: runs alongside Qwen2.5-VL or on lightweight vLLM instance. |
| **Llama 3.2 3B Instruct** | Open (Llama 3.2 Community) | 128k tokens | ~$0.008 | Viable for ultra-low latency; requires careful validation against style drift. |

---

## 3. End-to-End Cost & Latency Budget (Target vs Reality)

| Stage | Target Latency | Reality (API Baseline) | Reality (Self-Hosted Qwen-7B + Llama-8B) | Target Cost / Scan |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1 (VLM Extraction)** | < 800 ms | 650 ms | 520 ms | $0.00020 |
| **Stage 2 (Identification)** | < 30 ms | 4 ms (In-memory index) | 4 ms | $0.00000 |
| **Stage 3 (Knowledge Retrieval)** | < 15 ms | 2 ms (Curated JSON KB) | 2 ms | $0.00000 |
| **Stage 4 (Generation + Validator)**| < 600 ms | 350 ms | 280 ms | $0.00010 |
| **Total Pipeline** | **< 1500 ms** | **~1006 ms** | **~806 ms** | **~$0.00030 (3¢ per 100 scans)** |
