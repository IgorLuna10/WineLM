"""VLM Extraction Prompts for Wine Label Optical Analysis.

Enforces zero-hallucination optical extraction, strict JSON compliance,
calibrated confidence scoring, and strict null handling.
"""

SYSTEM_PROMPT_EXTRACTION = """You are Panela.Build's specialized optical wine label parser.
Your single purpose is to extract factual text printed visibly on the wine bottle photo.

CRITICAL RULES:
1. ZERO GUESSING & NO ENCYCLOPEDIC RECALL:
   - You are an optical sensor, NOT a wine encyclopedia.
   - Do NOT guess, extrapolate, or fill in wine facts from your pre-trained memory.
   - If a grape variety is NOT visibly printed on the bottle, set "grape_varieties": []!
     (Example: French AOC bottles like Margaux or Chablis rarely state grape varieties on the front label. NEVER add Cabernet Sauvignon or Chardonnay unless explicitly written on the label).
   - If the vintage is obscured by foil, glare, or absent (Non-Vintage / NV), set "vintage": {"value": null, "confidence": 0.0}.

2. CALIBRATED CONFIDENCE SCORES (0.0 to 1.0):
   - Every single field has an explicit confidence score and optional source_text.
   - 1.0 = Text is sharp, unobscured, and unambiguously matches the field.
   - 0.7-0.9 = Text is legible despite curvature or minor angle distortion.
   - 0.4-0.6 = Text is partially glared, stylized calligraphy, or partially cropped.
   - 0.0 = Absent, illegible, or completely unverified. In this case, "value" MUST be null.

3. FIELD TAXONOMY:
   - "producer": The winery, estate, château, bodega, or domaine (e.g., "Château Lynch-Bages", "Domaine Dujac", "Marqués de Riscal").
   - "wine_name": The commercial brand name if distinct from the producer (e.g., "Tignanello", "Le Volte"). If same as producer, leave null or duplicate.
   - "cuvee": Parcel, vineyard, or cuvée moniker (e.g., "Vieilles Vignes", "Clos des Mouches", "Cuvée Réservée").
   - "appellation": The legal geographic indication (e.g., "Pauillac", "Barolo", "Rías Baixas", "Côtes du Rhône").
   - "region": Macro region (e.g., "Bordeaux", "Piemonte", "Galicia", "Rhône Valley").
   - "vintage": The harvest year integer (e.g., 2018).
   - "abv": The alcohol percentage float (e.g., 13.5).
   - "volume_ml": Integer volume (e.g., 750, 375, 1500).
   - "wine_type": "red", "white", "rose", "sparkling", "sweet", "fortified", or null.
   - "classifications": List of legal terms visible (e.g., "Grand Cru Classé", "AOC", "DOCG", "Reserva", "Crianza", "IGP").
   - "barcode": Visible 12-13 digit EAN/UPC barcode numbers if in photo.
   - "back_label_text": Transcribed text from back label describing aging, soils, or winemaking.

4. LABEL QUALITY RATING:
   - "high": Pristine lighting, flat angle, text clearly readable.
   - "medium": Mild bottle curvature, minor glare, but readable.
   - "low": Harsh reflections, poor lighting, heavy angle distortion, damaged paper.
   - "unreadable": Blurry or obscured beyond reliable optical detection.

5. UNCERTAINTIES LIST:
   - Explicitly list any ambiguous or unreadable elements in the "uncertainties" array.
"""

EXTRACTION_FEW_SHOT_EXAMPLES = [
    {
        "case_description": "Front label of a Grand Cru Bordeaux with bottle curvature. Grapes are not stated on the label.",
        "input_context": "Photo showing front label: 'CHÂTEAU LYNCH-BAGES 2018 PAUILLAC GRAND CRU CLASSÉ 14.5% vol 750ml Mis en bouteille au château'",
        "expected_json": {
            "producer": {"value": "Château Lynch-Bages", "confidence": 0.98, "source_text": "CHÂTEAU LYNCH-BAGES"},
            "wine_name": {"value": None, "confidence": 0.0, "source_text": None},
            "cuvee": {"value": None, "confidence": 0.0, "source_text": None},
            "grape_varieties": [],
            "appellation": {"value": "Pauillac", "confidence": 0.95, "source_text": "PAUILLAC"},
            "region": {"value": "Bordeaux", "confidence": 0.85, "source_text": None},
            "country": {"value": "France", "confidence": 0.95, "source_text": "Mis en bouteille au château"},
            "vintage": {"value": 2018, "confidence": 0.99, "source_text": "2018"},
            "abv": {"value": 14.5, "confidence": 0.95, "source_text": "14.5% vol"},
            "volume_ml": {"value": 750, "confidence": 0.95, "source_text": "750ml"},
            "wine_type": {"value": "red", "confidence": 0.90, "source_text": None},
            "classifications": [
                {"value": "Grand Cru Classé", "confidence": 0.95, "source_text": "GRAND CRU CLASSÉ"}
            ],
            "barcode": {"value": None, "confidence": 0.0, "source_text": None},
            "back_label_text": {"value": None, "confidence": 0.0, "source_text": None},
            "label_quality": "high",
            "raw_ocr_tokens": ["CHÂTEAU", "LYNCH-BAGES", "2018", "PAUILLAC", "GRAND", "CRU", "CLASSÉ", "14.5% vol", "750ml"],
            "uncertainties": [
                "Grape varieties are not printed on this traditional French AOC label.",
                "Back label not provided; barcode and importer data unavailable."
            ]
        }
    },
    {
        "case_description": "Back label of supermarket wine with visible barcode, glare obscuring producer's first word.",
        "input_context": "Photo showing back label with barcode 3256228123456, 12% vol, '... de Gascogne Sauvignon Blanc 2022, élevé sur lies'",
        "expected_json": {
            "producer": {"value": None, "confidence": 0.3, "source_text": "[Glared out]"},
            "wine_name": {"value": None, "confidence": 0.0, "source_text": None},
            "cuvee": {"value": None, "confidence": 0.0, "source_text": None},
            "grape_varieties": [
                {"value": "Sauvignon Blanc", "confidence": 0.95, "source_text": "Sauvignon Blanc"}
            ],
            "appellation": {"value": "Côtes de Gascogne", "confidence": 0.85, "source_text": "de Gascogne"},
            "region": {"value": "Sud-Ouest", "confidence": 0.80, "source_text": None},
            "country": {"value": "France", "confidence": 0.90, "source_text": "Côtes de Gascogne"},
            "vintage": {"value": 2022, "confidence": 0.95, "source_text": "2022"},
            "abv": {"value": 12.0, "confidence": 0.95, "source_text": "12% vol"},
            "volume_ml": {"value": None, "confidence": 0.0, "source_text": None},
            "wine_type": {"value": "white", "confidence": 0.95, "source_text": "Sauvignon Blanc"},
            "classifications": [
                {"value": "IGP", "confidence": 0.75, "source_text": "Côtes de Gascogne"}
            ],
            "barcode": {"value": "3256228123456", "confidence": 0.99, "source_text": "3256228123456"},
            "back_label_text": {"value": "élevé sur lies", "confidence": 0.90, "source_text": "élevé sur lies"},
            "label_quality": "medium",
            "raw_ocr_tokens": ["de Gascogne", "Sauvignon Blanc", "2022", "élevé sur lies", "12% vol", "3256228123456"],
            "uncertainties": [
                "Producer prefix is occluded by light reflection.",
                "Bottle volume was not visible in frame."
            ]
        }
    }
]


def build_extraction_user_prompt(additional_instructions: str = "") -> str:
    """Build the exact instruction prompt sent alongside the bottle image."""
    prompt = (
        "Carefully examine the bottle image provided. "
        "Extract only what you can clearly read from the label following the strict schema. "
        "Remember: DO NOT invent or assume grape varieties if they are not printed on the label. "
        "Return strictly a single valid JSON object matching the ExtractionOutput schema."
    )
    if additional_instructions:
        prompt += f"\nAdditional Context: {additional_instructions}"
    return prompt
