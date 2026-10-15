export interface TemperatureRange {
  min_c: number;
  max_c: number;
  display_c: string;
  display_f: string;
}

export interface DecantingAdvice {
  recommended: boolean;
  duration_minutes?: number | null;
  rationale: string;
}

export interface DrinkWindow {
  status: string;
  window_years?: string | null;
  rationale: string;
}

export interface DrinkingGuide {
  temperature: TemperatureRange;
  glass_type: string;
  decanting: DecantingAdvice;
  drink_window: DrinkWindow;
}

export interface StructuralProfile {
  acidity: number;
  tannin?: number | null;
  body: number;
  sweetness: number;
}

export interface FlavorDescriptor {
  descriptor: string;
  source_factor: "grape_variety" | "terroir_soil_climate" | "winemaking_ageing" | "style_typical" | string;
}

export interface TastingNotes {
  structure: StructuralProfile;
  primary_notes: FlavorDescriptor[];
  narrative: string;
}

export interface DishPairing {
  dish: string;
  pairing_rule: string;
  why_it_works: string;
}

export interface FoodClash {
  dish_category: string;
  conflict_reason: string;
}

export interface FoodPairings {
  recommended: DishPairing[];
  avoid: FoodClash[];
}

export interface MatchInfo {
  matched_id?: string | null;
  canonical_producer?: string | null;
  canonical_wine_name?: string | null;
  canonical_vintage?: number | null;
  match_source: string;
  match_confidence: number;
}

export interface WineSummary {
  headline: string;
  tier: "identified_wine" | "identified_style" | "unidentified";
  tier_explanation: string;
  wine_type?: string | null;
  vintage?: number | null;
  country?: string | null;
  region?: string | null;
  appellation?: string | null;
  grapes: string[];
  match_info?: MatchInfo | null;
}

export interface CaptureAdvice {
  needs_second_photo: boolean;
  suggested_label_type?: string | null;
  reason?: string | null;
  user_prompt_message?: string | null;
}

export interface TraceabilityEntry {
  claim: string;
  source_tier: string;
  evidence: string;
}

export interface StageMetrics {
  vlm_extraction_ms: number;
  identification_ms: number;
  knowledge_retrieval_ms: number;
  text_generation_ms: number;
  validation_ms: number;
  total_pipeline_ms: number;
  estimated_cost_usd: number;
}

export interface ExtractedConfidenceField<T = string | number> {
  value: T | null;
  confidence: number;
  source_text?: string | null;
}

export interface ExtractionData {
  producer?: ExtractedConfidenceField<string>;
  wine_name?: ExtractedConfidenceField<string>;
  cuvee?: ExtractedConfidenceField<string>;
  appellation?: ExtractedConfidenceField<string>;
  region?: ExtractedConfidenceField<string>;
  country?: ExtractedConfidenceField<string>;
  vintage?: ExtractedConfidenceField<number>;
  abv?: ExtractedConfidenceField<number>;
  volume_ml?: ExtractedConfidenceField<number>;
  wine_type?: ExtractedConfidenceField<string>;
  barcode?: ExtractedConfidenceField<string>;
  grape_varieties?: Array<ExtractedConfidenceField<string>>;
  classifications?: Array<ExtractedConfidenceField<string>>;
  label_quality?: string;
  uncertainties?: string[];
}

export interface FinalResponse {
  summary: WineSummary;
  capture_advice: CaptureAdvice;
  drinking_guide?: DrinkingGuide | null;
  tasting_notes?: TastingNotes | null;
  food_pairings?: FoodPairings | null;
  uncertainties: string[];
  traceability_log: TraceabilityEntry[];
  metrics: StageMetrics;
  extraction?: ExtractionData | null;
}
