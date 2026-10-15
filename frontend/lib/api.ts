import { FinalResponse } from "../types/wine";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function checkBackendHealth(): Promise<{ healthy: boolean; details?: any }> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
    if (res.ok) {
      const data = await res.json();
      return { healthy: true, details: data };
    }
    return { healthy: false };
  } catch (err) {
    return { healthy: false };
  }
}

export async function explainWineApi(
  files: File[],
  additionalContext: string = ""
): Promise<FinalResponse> {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append("files", file);
  });

  if (additionalContext.trim()) {
    formData.append("additional_context", additionalContext.trim());
  }

  const res = await fetch(`${API_BASE_URL}/api/v1/explain`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let errorDetail = `Server responded with ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return (await res.json()) as FinalResponse;
}

// Curated sample demonstrations matching real pipeline outputs
export const SAMPLE_PRESETS: Record<string, { label: string; description: string; data: FinalResponse }> = {
  naturalys: {
    label: "2024 Gérard Bertrand Naturalys",
    description: "Pays d'Oc IGP Pinot Noir — Live Cellar Photo (Bottle 05)",
    data: {
      summary: {
        headline: "2024 Gérard Bertrand Naturalys Pinot Noir",
        tier: "identified_wine",
        tier_explanation: "Verified specific bottling via sqlite_fts_fuzzy_match (confidence: 1.0).",
        wine_type: "red",
        vintage: 2024,
        country: "France",
        region: "Languedoc",
        appellation: "Pays d'Oc",
        grapes: ["Pinot Noir"],
        match_info: {
          matched_id: "ref_gérard_bertrand_naturalys_pays_doc_igp_2",
          canonical_producer: "Gérard Bertrand",
          canonical_wine_name: "Naturalys",
          canonical_vintage: 2024,
          match_source: "sqlite_fts_fuzzy_match",
          match_confidence: 1.0,
        },
      },
      capture_advice: {
        needs_second_photo: false,
        user_prompt_message: "First photo was sufficient for complete identification.",
      },
      drinking_guide: {
        temperature: {
          min_c: 14.0,
          max_c: 16.0,
          display_c: "14–16°C",
          display_f: "57–61°F",
        },
        glass_type: "Burgundy glass with wide bowl to concentrate delicate red fruit aromas",
        decanting: {
          recommended: false,
          duration_minutes: null,
          rationale: "Delicate light red wine; excessive decanting risks dissipating primary aromas",
        },
        drink_window: {
          status: "ready_to_drink",
          window_years: "1 to 3 years from vintage",
          rationale: "Organic cuvée crafted for immediate aromatic freshness.",
        },
      },
      tasting_notes: {
        structure: {
          acidity: 4,
          tannin: 2,
          body: 2,
          sweetness: 1,
        },
        primary_notes: [
          { descriptor: "wild strawberry", source_factor: "grape_variety" },
          { descriptor: "red cherry", source_factor: "grape_variety" },
          { descriptor: "subtle forest floor notes", source_factor: "winemaking_ageing" },
          { descriptor: "Mediterranean clay-limestone minerality", source_factor: "terroir_soil_climate" },
        ],
        narrative:
          "This 2024 Gérard Bertrand Naturalys Pinot Noir exhibits classic South of France freshness. Driven by organically farmed Pinot Noir, it reveals bright notes of wild strawberry and red cherry, underpinned by supple tannins and vibrant acidity.",
      },
      food_pairings: {
        recommended: [
          {
            dish: "Roasted duck breast with cherry reduction",
            pairing_rule: "Fruit mirroring & acidity cut",
            why_it_works: "Bright berry acidity cuts through duck fat while mirroring the fruit glaze.",
          },
          {
            dish: "Pan-seared salmon with lentils",
            pairing_rule: "Light tannin compatibility",
            why_it_works: "Supple, gentle tannins complement meaty fish without yielding a metallic finish.",
          },
        ],
        avoid: [
          {
            dish_category: "Heavy braised beef shank",
            conflict_reason: "Heavy gelatinous beef overpowers light Pinot Noir body and delicate fruit.",
          },
        ],
      },
      uncertainties: [
        "ABV percentage was not printed on front label.",
      ],
      traceability_log: [
        { claim: "Producer: Gérard Bertrand", source_tier: "extracted_label_text", evidence: "Optical label OCR reading (confidence 1.0)" },
        { claim: "Vintage: 2024", source_tier: "extracted_label_text", evidence: "Label printed vintage 2024 (confidence 1.0)" },
        { claim: "Grape: Pinot Noir", source_tier: "extracted_label_text", evidence: "Printed on front label (confidence 1.0)" },
        { claim: "Serving temp: 14–16°C", source_tier: "retrieved_knowledge_base", evidence: "Light/medium red wine serving rule" },
      ],
      metrics: {
        vlm_extraction_ms: 6230.1,
        identification_ms: 0.28,
        knowledge_retrieval_ms: 0.35,
        text_generation_ms: 0.81,
        validation_ms: 0.1,
        total_pipeline_ms: 6231.6,
        estimated_cost_usd: 0.0002,
      },
    },
  },
  lynchBages: {
    label: "2018 Château Lynch-Bages",
    description: "Pauillac AOC Grand Cru Classé — High Glare Fixture",
    data: {
      summary: {
        headline: "2018 Château Lynch-Bages Grand Cru Classé",
        tier: "identified_wine",
        tier_explanation: "Verified specific bottling via sqlite_fts_fuzzy_match (confidence: 1.0).",
        wine_type: "red",
        vintage: 2018,
        country: "France",
        region: "Bordeaux",
        appellation: "Pauillac",
        grapes: ["Cabernet Sauvignon", "Merlot", "Cabernet Franc"],
        match_info: {
          matched_id: "ref_lynch_bages_2018",
          canonical_producer: "Château Lynch-Bages",
          canonical_wine_name: "Château Lynch-Bages Grand Cru Classé",
          canonical_vintage: 2018,
          match_source: "sqlite_fts_fuzzy_match",
          match_confidence: 1.0,
        },
      },
      capture_advice: {
        needs_second_photo: false,
        user_prompt_message: "First photo was sufficient for complete identification.",
      },
      drinking_guide: {
        temperature: {
          min_c: 16.0,
          max_c: 18.0,
          display_c: "16–18°C",
          display_f: "61–64°F",
        },
        glass_type: "Bordeaux glass with tall bowl to aerate robust tannins",
        decanting: {
          recommended: true,
          duration_minutes: 45,
          rationale: "Softens youthful astringent tannins and allows concentrated cedar and cassis notes to open",
        },
        drink_window: {
          status: "ready_to_drink",
          window_years: "5 to 15 years from vintage",
          rationale: "Based on typical ageing potential for Pauillac classified growth.",
        },
      },
      tasting_notes: {
        structure: {
          acidity: 4,
          tannin: 4,
          body: 4,
          sweetness: 1,
        },
        primary_notes: [
          { descriptor: "cassis", source_factor: "grape_variety" },
          { descriptor: "blackcurrant", source_factor: "grape_variety" },
          { descriptor: "cigar box & cedar wood", source_factor: "winemaking_ageing" },
          { descriptor: "Deep gravel mounds (croupes de graves) mineral imprint", source_factor: "terroir_soil_climate" },
        ],
        narrative:
          "This 2018 Château Lynch-Bages reflects quintessential Pauillac enology. Driven by Cabernet Sauvignon, Merlot, and Cabernet Franc, it showcases powerful cassis and black fruit balanced by firm, sculpted tannins and mineral depth.",
      },
      food_pairings: {
        recommended: [
          {
            dish: "Grilled prime ribeye steak",
            pairing_rule: "Protein-tannin binding",
            why_it_works: "High protein and marbling soften muscular tannins and release black fruit flavors.",
          },
          {
            dish: "Roasted lamb shank with rosemary",
            pairing_rule: "Fat cleansing",
            why_it_works: "Rich unctuous lamb fat cuts through firm structure, while herbal notes mirror wine complexity.",
          },
        ],
        avoid: [
          {
            dish_category: "Oily fish (salmon, mackerel, sardines)",
            conflict_reason: "Tannins interact with fish oils to produce an unpleasant metallic, tinny taste.",
          },
        ],
      },
      uncertainties: [
        "Grape varieties not printed on label; derived from legal AOC regulations for Pauillac.",
      ],
      traceability_log: [
        { claim: "Producer: Château Lynch-Bages", source_tier: "extracted_label_text", evidence: "Optical OCR reading" },
        { claim: "Vintage: 2018", source_tier: "extracted_label_text", evidence: "Optical OCR reading" },
        { claim: "Grapes: Cabernet Sauvignon, Merlot, Cabernet Franc", source_tier: "retrieved_knowledge_base", evidence: "Catalog blend profile" },
      ],
      metrics: {
        vlm_extraction_ms: 7890.0,
        identification_ms: 0.31,
        knowledge_retrieval_ms: 0.22,
        text_generation_ms: 0.65,
        validation_ms: 0.1,
        total_pipeline_ms: 7891.2,
        estimated_cost_usd: 0.0002,
      },
    },
  },
  needsSecondPhoto: {
    label: "Cave Bottle (Missing Back Label)",
    description: "Single Front Photo with missing vintage/barcode triggering Capture Advice",
    data: {
      summary: {
        headline: "Dry French White (Burgundy Style)",
        tier: "identified_style",
        tier_explanation: "Regional style matched from Chablis appellation. Specific estate bottling unverified.",
        wine_type: "white",
        vintage: null,
        country: "France",
        region: "Burgundy",
        appellation: "Chablis",
        grapes: ["Chardonnay"],
        match_info: null,
      },
      capture_advice: {
        needs_second_photo: true,
        suggested_label_type: "back_label",
        reason: "Vintage year and barcode were absent on front label shot.",
        user_prompt_message: "Tip: Snapping the back label will confirm the exact vintage and estate.",
      },
      drinking_guide: {
        temperature: {
          min_c: 10.0,
          max_c: 12.0,
          display_c: "10–12°C",
          display_f: "50–54°F",
        },
        glass_type: "Standard white wine glass with tapered rim",
        decanting: {
          recommended: false,
          duration_minutes: null,
          rationale: "Crisp mineral white; decanting not required",
        },
        drink_window: {
          status: "ready_to_drink",
          window_years: "2 to 5 years",
          rationale: "Standard drinking window for Chablis village wines.",
        },
      },
      tasting_notes: {
        structure: {
          acidity: 5,
          tannin: 1,
          body: 2,
          sweetness: 1,
        },
        primary_notes: [
          { descriptor: "green apple", source_factor: "grape_variety" },
          { descriptor: "lemon zest", source_factor: "grape_variety" },
          { descriptor: "Kimmeridgian limestone flint", source_factor: "terroir_soil_climate" },
        ],
        narrative:
          "Exemplifies classic Chablis terroir. Bone dry with piercing acidity, exhibiting vibrant green apple and chalky flint stone minerality.",
      },
      food_pairings: {
        recommended: [
          {
            dish: "Fresh oysters on the half shell",
            pairing_rule: "Saline-mineral acid alignment",
            why_it_works: "High natural acidity acts like a squeeze of lemon over fresh briny oysters.",
          },
        ],
        avoid: [
          {
            dish_category: "Rich red meat steaks",
            conflict_reason: "High protein and heavy fat overpower light mineral white wine.",
          },
        ],
      },
      uncertainties: [
        "Vintage not visible on label photo.",
        "Barcode missing; please provide back label photo.",
      ],
      traceability_log: [
        { claim: "Appellation: Chablis", source_tier: "extracted_label_text", evidence: "Label OCR text" },
        { claim: "Grape: Chardonnay", source_tier: "retrieved_knowledge_base", evidence: "Chablis AOC single-varietal requirement" },
      ],
      metrics: {
        vlm_extraction_ms: 6100.0,
        identification_ms: 0.15,
        knowledge_retrieval_ms: 0.19,
        text_generation_ms: 0.52,
        validation_ms: 0.1,
        total_pipeline_ms: 6100.9,
        estimated_cost_usd: 0.0002,
      },
    },
  },
};
