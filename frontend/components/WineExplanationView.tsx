"use client";

import React, { useState } from "react";
import {
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  Camera,
  Thermometer,
  Wine,
  Clock,
  Sparkles,
  Utensils,
  Ban,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  MapPin,
  Calendar,
  Percent,
} from "lucide-react";
import { FinalResponse } from "../types/wine";

interface WineExplanationViewProps {
  response: FinalResponse;
}

export function WineExplanationView({ response }: WineExplanationViewProps) {
  const [showTraceability, setShowTraceability] = useState<boolean>(false);
  const [showExtractionDetails, setShowExtractionDetails] = useState<boolean>(false);

  const { summary, capture_advice, drinking_guide, tasting_notes, food_pairings, uncertainties, traceability_log, metrics } = response;

  const isIdentifiedWine = summary.tier === "identified_wine";
  const isIdentifiedStyle = summary.tier === "identified_style";
  const isUnidentified = summary.tier === "unidentified";

  return (
    <div className="space-y-6">
      {/* 1. HEADLINE & CONFIDENCE TIER HERO CARD */}
      <div
        className={`rounded-2xl p-6 border transition-all shadow-sm ${
          isIdentifiedWine
            ? "bg-gradient-to-br from-emerald-50/80 via-white to-stone-50 dark:from-emerald-950/30 dark:via-stone-900 dark:to-stone-900 border-emerald-300 dark:border-emerald-800"
            : isIdentifiedStyle
            ? "bg-gradient-to-br from-amber-50/80 via-white to-stone-50 dark:from-amber-950/30 dark:via-stone-900 dark:to-stone-900 border-amber-300 dark:border-amber-800"
            : "bg-gradient-to-br from-stone-100 via-white to-stone-50 dark:from-stone-900 dark:via-stone-900 dark:to-stone-900 border-stone-300 dark:border-stone-700"
        }`}
      >
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2 flex-1">
            {/* Confidence Badge */}
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                  isIdentifiedWine
                    ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-700"
                    : isIdentifiedStyle
                    ? "bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700"
                    : "bg-stone-200 dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-300 dark:border-stone-700"
                }`}
              >
                {isIdentifiedWine && <CheckCircle className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />}
                {isIdentifiedStyle && <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />}
                {isUnidentified && <HelpCircle className="w-3.5 h-3.5 text-stone-500" />}
                {summary.tier.replace("_", " ")}
              </span>

              {summary.match_info && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-mono bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-300 border border-stone-200 dark:border-stone-700">
                  <Cpu className="w-3 h-3 text-rose-700 dark:text-rose-400" />
                  {summary.match_info.match_source}: {Math.round(summary.match_info.match_confidence * 100)}%
                </span>
              )}
            </div>

            {/* Headline */}
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900 dark:text-stone-100 tracking-tight">
              {summary.headline}
            </h1>

            {/* Metadata Pills */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-stone-600 dark:text-stone-400 pt-1">
              {summary.vintage && (
                <span className="flex items-center gap-1 font-medium text-stone-800 dark:text-stone-200">
                  <Calendar className="w-3.5 h-3.5 text-rose-700" />
                  Vintage: {summary.vintage}
                </span>
              )}
              {summary.appellation && (
                <span className="flex items-center gap-1 font-medium text-stone-800 dark:text-stone-200">
                  <MapPin className="w-3.5 h-3.5 text-rose-700" />
                  {summary.appellation}
                  {summary.country ? ` (${summary.country})` : ""}
                </span>
              )}
              {summary.grapes && summary.grapes.length > 0 && (
                <span className="flex items-center gap-1 font-medium text-stone-800 dark:text-stone-200">
                  🍇 {summary.grapes.join(", ")}
                </span>
              )}
            </div>

            <p className="text-xs text-stone-500 dark:text-stone-400 italic pt-1">
              {summary.tier_explanation}
            </p>
          </div>
        </div>
      </div>

      {/* 2. CAPTURE ADVICE BANNER (Prominent when second photo is needed) */}
      {capture_advice.needs_second_photo && (
        <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700 rounded-2xl p-4 sm:p-5 flex items-start gap-3.5 shadow-sm">
          <div className="p-2 rounded-xl bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-300 shrink-0">
            <Camera className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-amber-900 dark:text-amber-200">
                Camera Advice from Enologist Engine
              </h3>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-amber-200 dark:bg-amber-800 text-amber-900 dark:text-amber-100">
                Follow-up Suggested
              </span>
            </div>
            <p className="text-xs text-amber-800 dark:text-amber-300 font-medium">
              {capture_advice.user_prompt_message}
            </p>
            {capture_advice.reason && (
              <p className="text-[11px] text-amber-700/80 dark:text-amber-400/80">
                Reason: {capture_advice.reason}
              </p>
            )}
          </div>
        </div>
      )}

      {/* 3. CORE ENOLOGICAL CARDS (DRINKING GUIDE & TASTING NOTES) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* DRINKING GUIDE CARD */}
        {drinking_guide && (
          <div className="bg-white dark:bg-stone-900 rounded-2xl border border-stone-200 dark:border-stone-800 p-5 sm:p-6 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-stone-100 dark:border-stone-800 pb-3">
              <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                <Thermometer className="w-5 h-5 text-rose-800 dark:text-rose-400" />
                Drinking &amp; Serving Guide
              </h3>
              <span className="text-[11px] text-stone-400 uppercase font-mono">Enological Protocol</span>
            </div>

            {/* Serving Temperature Gauge */}
            <div className="bg-stone-50 dark:bg-stone-800/60 rounded-xl p-4 border border-stone-100 dark:border-stone-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-medium">
                <span className="text-stone-600 dark:text-stone-400">Recommended Temperature</span>
                <span className="font-bold text-rose-900 dark:text-rose-300 text-sm">
                  {drinking_guide.temperature.display_c} / {drinking_guide.temperature.display_f}
                </span>
              </div>
              <div className="w-full bg-stone-200 dark:bg-stone-700 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-cyan-500 via-amber-500 to-rose-600 h-full rounded-full"
                  style={{
                    width: `${Math.min(100, Math.max(10, ((drinking_guide.temperature.max_c - 4) / 18) * 100))}%`,
                  }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-stone-400">
                <span>Cold (6°C)</span>
                <span>Cellar (14°C)</span>
                <span>Room (20°C)</span>
              </div>
            </div>

            {/* Glassware & Decanting */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="bg-stone-50 dark:bg-stone-800/40 rounded-xl p-3 border border-stone-100 dark:border-stone-800 space-y-1">
                <div className="font-semibold text-stone-800 dark:text-stone-200 flex items-center gap-1.5">
                  <Wine className="w-4 h-4 text-rose-700" />
                  Glassware
                </div>
                <p className="text-stone-600 dark:text-stone-400 text-[11px]">
                  {drinking_guide.glass_type}
                </p>
              </div>

              <div className="bg-stone-50 dark:bg-stone-800/40 rounded-xl p-3 border border-stone-100 dark:border-stone-800 space-y-1">
                <div className="font-semibold text-stone-800 dark:text-stone-200 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-amber-700" />
                  Decanting
                </div>
                <p className="text-stone-600 dark:text-stone-400 text-[11px]">
                  {drinking_guide.decanting.recommended
                    ? `Decant for ${drinking_guide.decanting.duration_minutes} min: ${drinking_guide.decanting.rationale}`
                    : `Not required: ${drinking_guide.decanting.rationale}`}
                </p>
              </div>
            </div>

            {/* Drink Window */}
            {drinking_guide.drink_window && (
              <div className="bg-stone-50 dark:bg-stone-800/40 rounded-xl p-3 border border-stone-100 dark:border-stone-800 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-stone-800 dark:text-stone-200">
                    Ageing Potential &amp; Window
                  </span>
                  {drinking_guide.drink_window.window_years && (
                    <span className="font-mono text-[11px] bg-stone-200 dark:bg-stone-700 px-2 py-0.5 rounded text-stone-700 dark:text-stone-300">
                      {drinking_guide.drink_window.window_years}
                    </span>
                  )}
                </div>
                <p className="text-stone-500 dark:text-stone-400 text-[11px]">
                  {drinking_guide.drink_window.rationale}
                </p>
              </div>
            )}
          </div>
        )}

        {/* TASTING NOTES CARD */}
        {tasting_notes && (
          <div className="bg-white dark:bg-stone-900 rounded-2xl border border-stone-200 dark:border-stone-800 p-5 sm:p-6 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-stone-100 dark:border-stone-800 pb-3">
              <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-rose-800 dark:text-rose-400" />
                Grounded Tasting Notes
              </h3>
              <span className="text-[11px] text-stone-400 uppercase font-mono">Sensory Profile</span>
            </div>

            {/* Structural Profile 1-5 Gauges */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { label: "Acidity", val: tasting_notes.structure.acidity, color: "from-amber-400 to-amber-600" },
                { label: "Tannin", val: tasting_notes.structure.tannin ?? 1, color: "from-rose-700 to-rose-900" },
                { label: "Body", val: tasting_notes.structure.body, color: "from-purple-600 to-indigo-900" },
                { label: "Sweetness", val: tasting_notes.structure.sweetness, color: "from-pink-400 to-rose-500" },
              ].map((item) => (
                <div
                  key={item.label}
                  className="bg-stone-50 dark:bg-stone-800/60 rounded-xl p-2.5 border border-stone-100 dark:border-stone-800 text-center space-y-1.5"
                >
                  <span className="text-[11px] text-stone-500 dark:text-stone-400 font-medium block">
                    {item.label}
                  </span>
                  <div className="flex justify-center gap-1">
                    {[1, 2, 3, 4, 5].map((lvl) => (
                      <span
                        key={lvl}
                        className={`w-2.5 h-4 rounded-sm transition-all ${
                          lvl <= item.val
                            ? "bg-rose-800 dark:bg-rose-500"
                            : "bg-stone-200 dark:bg-stone-700"
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-[10px] font-mono text-stone-400">{item.val}/5</span>
                </div>
              ))}
            </div>

            {/* Primary Aromas / Flavors */}
            {tasting_notes.primary_notes && tasting_notes.primary_notes.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-semibold text-stone-700 dark:text-stone-300 block">
                  Primary Notes &amp; Provenance Factors:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {tasting_notes.primary_notes.map((note, idx) => (
                    <span
                      key={idx}
                      className={`text-xs px-2.5 py-1 rounded-full font-medium border ${
                        note.source_factor === "grape_variety"
                          ? "bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border-rose-200 dark:border-rose-800"
                          : note.source_factor === "terroir_soil_climate"
                          ? "bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800"
                          : "bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 border-stone-200 dark:border-stone-700"
                      }`}
                      title={`Derived from: ${note.source_factor}`}
                    >
                      {note.source_factor === "grape_variety" && "🍇 "}
                      {note.source_factor === "terroir_soil_climate" && "⛰️ "}
                      {note.source_factor === "winemaking_ageing" && "🪵 "}
                      {note.descriptor}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Fact-Restricted Narrative */}
            <div className="bg-stone-50/80 dark:bg-stone-800/40 rounded-xl p-3.5 border border-stone-100 dark:border-stone-800 text-xs text-stone-700 dark:text-stone-300 leading-relaxed italic">
              &ldquo;{tasting_notes.narrative}&rdquo;
            </div>
          </div>
        )}
      </div>

      {/* 4. FOOD PAIRINGS CARD */}
      {food_pairings && (
        <div className="bg-white dark:bg-stone-900 rounded-2xl border border-stone-200 dark:border-stone-800 p-5 sm:p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-stone-100 dark:border-stone-800 pb-3">
            <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
              <Utensils className="w-5 h-5 text-rose-800 dark:text-rose-400" />
              Biochemical Food Pairings &amp; Clashes
            </h3>
            <span className="text-[11px] text-stone-400 uppercase font-mono">Sensory Chemistry</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Recommended Pairings */}
            <div className="space-y-3">
              <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-400 flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                Recommended Dishes
              </span>
              <div className="space-y-2">
                {food_pairings.recommended.map((pair, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 space-y-1 text-xs"
                  >
                    <div className="font-semibold text-stone-900 dark:text-stone-100">
                      {pair.dish}
                    </div>
                    <div className="text-[11px] text-emerald-700 dark:text-emerald-300 font-mono">
                      Rule: {pair.pairing_rule}
                    </div>
                    <p className="text-[11px] text-stone-600 dark:text-stone-400">
                      {pair.why_it_works}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Clashes to Avoid */}
            <div className="space-y-3">
              <span className="text-xs font-semibold text-rose-800 dark:text-rose-400 flex items-center gap-1.5">
                <Ban className="w-4 h-4 text-rose-600" />
                Chemical Clashes to Avoid
              </span>
              <div className="space-y-2">
                {food_pairings.avoid.map((clash, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/40 space-y-1 text-xs"
                  >
                    <div className="font-semibold text-stone-900 dark:text-stone-100">
                      {clash.dish_category}
                    </div>
                    <p className="text-[11px] text-stone-600 dark:text-stone-400">
                      Conflict: {clash.conflict_reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. UNCERTAINTIES & HONEST SAFETY LOG */}
      {uncertainties && uncertainties.length > 0 && (
        <div className="bg-stone-50 dark:bg-stone-800/40 border border-stone-200 dark:border-stone-700 rounded-2xl p-4 sm:p-5 space-y-2 text-xs">
          <div className="flex items-center gap-2 font-bold text-stone-800 dark:text-stone-200">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            Explicit Uncertainties &amp; Unconfirmed Facts
          </div>
          <ul className="list-disc list-inside space-y-1 text-stone-600 dark:text-stone-400 text-[11px]">
            {uncertainties.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 6. COLLAPSIBLE FACTUAL TRACEABILITY DRAWER */}
      <div className="bg-white dark:bg-stone-900 rounded-2xl border border-stone-200 dark:border-stone-800 p-4 sm:p-5 shadow-sm space-y-3">
        <button
          type="button"
          onClick={() => setShowTraceability(!showTraceability)}
          className="w-full flex items-center justify-between text-xs font-semibold text-stone-800 dark:text-stone-200 hover:text-rose-800 dark:hover:text-rose-400 transition"
        >
          <span className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            Zero-Hallucination Traceability Audit Log ({traceability_log.length} claims verified)
          </span>
          {showTraceability ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showTraceability && (
          <div className="pt-2 overflow-x-auto">
            <table className="w-full text-left text-[11px] text-stone-600 dark:text-stone-400 border-collapse">
              <thead>
                <tr className="border-b border-stone-200 dark:border-stone-700 text-stone-800 dark:text-stone-200 font-semibold">
                  <th className="py-2 pr-3">Claim</th>
                  <th className="py-2 pr-3">Source Tier</th>
                  <th className="py-2">Factual Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100 dark:divide-stone-800 font-mono text-[10px]">
                {traceability_log.map((entry, idx) => (
                  <tr key={idx}>
                    <td className="py-2 pr-3 font-semibold text-stone-800 dark:text-stone-200">{entry.claim}</td>
                    <td className="py-2 pr-3 text-rose-800 dark:text-rose-400">{entry.source_tier}</td>
                    <td className="py-2 text-stone-500">{entry.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 7. PIPELINE LATENCY & TOKEN METRICS BAR */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] text-stone-500 dark:text-stone-400 px-2 py-1 font-mono">
        <div className="flex items-center gap-4">
          <span>VLM: {metrics.vlm_extraction_ms.toFixed(0)}ms</span>
          <span>SQLite: {metrics.identification_ms.toFixed(1)}ms</span>
          <span>Knowledge: {metrics.knowledge_retrieval_ms.toFixed(1)}ms</span>
          <span>Total: {metrics.total_pipeline_ms.toFixed(0)}ms</span>
        </div>
        <div>
          <span>Est. Cost: ${metrics.estimated_cost_usd.toFixed(4)} USD</span>
        </div>
      </div>
    </div>
  );
}
