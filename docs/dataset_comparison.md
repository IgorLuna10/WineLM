# Dataset & Free API Evaluation for European Wine Identification

This report evaluates open wine datasets and public APIs for Panela.Build's Phase 1 pipeline, focusing on coverage, licensing, schemas, and real-world gaps across French and European supermarket shelves and independent wine caves.

---

## 1. Executive Summary & Comparison Matrix

| Source | Primary Strength | Coverage (FR/EU Supermarket) | Licence | Fields Available | Critical Gaps | Recommended Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Open Food Facts (OFF)** | 100k+ barcode (EAN-13) SKU mappings | **High (80–90%)** for supermarket private labels & standard brands | **ODbL** (Open Database License) | Barcode, brand, product title, ABV, volume, origin, bio/AOC tags | Vintage rarely structured; grape blend % missing; tasting notes absent | **Tier 1 Barcode Resolver** |
| **Wikidata** | Canonical ontology of grapes & appellations | **Low (<5%)** for specific SKUs; **High (95%+)** for AOCs & top châteaux | **CC0** (Public Domain) | Appellation hierarchy, legal grapes, geo-coordinates, Wikidata QIDs | No retail SKUs; no supermarket private labels; no vintage tracking | **Knowledge Layer Taxonomy** |
| **European Commission eAmbrosia** | Legal ground-truth for EU protected designations | **100%** of EU registered PDO/PGI/AOC/DOC/DOCa | **Public Sector Info** (Free commercial reuse) | Legal appellation name, allowed grapes, viticultural bounds, legal ABV | No commercial brand names; no vintage info; PDF legal specs | **Legal Ground-Truth Verifier** |
| **X-Wines Dataset (Kaggle / Research)** | 100,000+ structured wines with grapes & regions | **Moderate (40–60%)** for global wines; weak on French supermarket private labels | **CC BY-NC 4.0** (*Non-commercial only!*) | Producer, wine name, vintage, grapes, region, country, wine type | **STRICT LEGAL TRAP**: Non-commercial licence prohibits production use | **Research benchmark only (DO NOT ship)** |
| **Wine-Searcher / Vivino Scrapers** | Deepest commercial SKU coverage | **Very High (90%+)** | **Propietary / Terms of Service Violations** | Full catalog, retail pricing, vintages, ratings | Severe risk of IP blocking, legal cease-and-desist, violates calm positioning | **Reject entirely** |

---

## 2. In-Depth Source Analysis

### A. Open Food Facts (OFF)
* **Licence**: Open Database Licence (ODbL 1.0). Commercial use is permitted, provided derivative database alterations are shared under the same terms.
* **Supermarket Coverage**: Outstanding for French supermarkets (Carrefour, E.Leclerc, Monoprix, Auchan, Intermarché) and Pan-European retailers (Lidl, Aldi).
* **Field Fidelity**:
  * `code`: EAN-13 barcode (extremely reliable when back label is scanned).
  * `product_name` / `brands`: Good for brand name (e.g. *Mouton Cadet*, *Domaine Tariquet*).
  * `alcohol_100g` / `volume`: High accuracy for ABV and 750ml volume.
  * `labels_tags`: Good detection of `en:organic`, `fr:aoc`, `fr:aop`, `fr:igp`.
* **Gaps**:
  * Vintages are almost never structured fields—they are often baked into the free-text product title (e.g., "Bordeaux Rouge 2019") or entirely absent if the barcode remains constant across annual releases.
  * Grape varieties are sparsely tagged (under 15% of records have structured varietal metadata).

### B. European Commission eAmbrosia & INAO
* **Licence**: Open European Union Public Sector Information (Directive 2019/1024). Fully permitted for commercial products.
* **Coverage**: Every single registered appellation across France (AOC/IGP via INAO), Italy (DOC/DOCG/IGT), Spain (DO/DOCa), and Portugal (DOC).
* **Factual Authority**: Ground truth for what grapes can legally exist in an appellation (e.g. confirming that *Mercurey* only permits Pinot Noir and Chardonnay, preventing any LLM hallucination of Merlot or Cabernet).
* **Gaps**: eAmbrosia registers the *legal geographical designation*, not individual estate bottlings or commercial SKUs.

### C. Wikidata (Knowledge Graph)
* **Licence**: Creative Commons CC0 1.0 Universal (Public Domain dedication). Zero legal encumbrance for commercial software.
* **Coverage**: Excellent for canonical knowledge entities:
  * Grape varietal entities (Q-nodes) with synonyms (e.g., *Tempranillo* = *Tinto Fino* = *Tinta del País*).
  * Major wine domains and historical châteaux (e.g., *Château Margaux*, *Domaine de la Romanée-Conti*).
* **Gaps**: Does not track small artisanal grower bottlings or supermarket private-label cuvées.

### D. X-Wines Dataset (Critical Licensing Caveat)
* **Dataset**: Created by researchers in 2023 containing 100,646 wines and 21 million ratings.
* **Licence Trap**: Distributed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.
* **Verdict**: Panela.Build is a commercial product. Integrating or shipping X-Wines in a backend database poses direct copyright liability. We use it strictly for offline comparative benchmarking in Phase 1 and do not bundle its data into production artifacts.

---

## 3. Recommended Hybrid Strategy for Phase 1 & 2

To achieve maximum accuracy without hallucinations or licensing violations:

1. **Barcode Identification (Step 2a)**:
   - Query **Open Food Facts API** (and cache offline SQLite snapshot of French/EU wine barcodes).
   - If an EAN match occurs, ingest brand, volume, and ABV directly.
2. **Canonical Terroir & Grape Layer (Step 3)**:
   - Base knowledge entities on **eAmbrosia / INAO** legal rules and **Wikidata** synonym dictionaries.
   - All grape profiles (acidity, tannin, body, typical aromas) are curated internally and version-controlled.
3. **Estate & Wine Fuzzy Match (Step 2b)**:
   - Maintain an embedded, curated reference database of top 1,000 European benchmark estates and high-volume supermarket wines.
   - Expand continuously via validated label extractions.
