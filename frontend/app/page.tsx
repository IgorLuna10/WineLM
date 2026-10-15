"use client";

import React, { useState } from "react";
import { Header } from "../components/Header";
import { CaptureStudio } from "../components/CaptureStudio";
import { WineExplanationView } from "../components/WineExplanationView";
import { explainWineApi, SAMPLE_PRESETS } from "../lib/api";
import { FinalResponse } from "../types/wine";
import { Wine, AlertCircle, Info, Sparkles } from "lucide-react";

export default function Home() {
  const [result, setResult] = useState<FinalResponse | null>(SAMPLE_PRESETS.naturalys.data);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleAnalyze = async (files: File[], context: string) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await explainWineApi(files, context);
      setResult(response);
    } catch (err: any) {
      console.warn("API Error, falling back to simulated analysis:", err);
      setErrorMessage(
        `Backend API note: ${err.message || "Failed to connect to http://localhost:8000"}. Loaded sample result for demonstration.`
      );
      // Fallback to demo preset if API isn't booted
      setResult(SAMPLE_PRESETS.naturalys.data);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadPreset = (presetKey: string) => {
    if (SAMPLE_PRESETS[presetKey]) {
      setResult(SAMPLE_PRESETS[presetKey].data);
      setErrorMessage(null);
    }
  };

  return (
    <div className="min-h-screen bg-stone-100/60 dark:bg-stone-950 text-stone-900 dark:text-stone-100 flex flex-col font-sans transition-colors selection:bg-rose-900 selection:text-white">
      {/* Top Navbar */}
      <Header />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
        {/* Error notification banner if API connection fails */}
        {errorMessage && (
          <div className="bg-amber-50 dark:bg-amber-950/50 border border-amber-300 dark:border-amber-800 rounded-xl p-3.5 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2.5 shadow-sm">
            <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-semibold">Notice: </span>
              <span>{errorMessage}</span>
            </div>
          </div>
        )}

        {/* Responsive Dual Column on Desktop, Stack on Mobile */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left / Ingestion Column (5 cols on Desktop) */}
          <div className="lg:col-span-5 space-y-6 sticky top-20">
            <CaptureStudio
              onAnalyze={handleAnalyze}
              onLoadPreset={handleLoadPreset}
              isLoading={isLoading}
            />

            {/* Quick Helper Tips */}
            <div className="bg-white/60 dark:bg-stone-900/60 rounded-xl p-4 border border-stone-200/80 dark:border-stone-800 text-xs text-stone-500 dark:text-stone-400 space-y-2">
              <div className="flex items-center gap-1.5 font-semibold text-stone-700 dark:text-stone-300">
                <Info className="w-3.5 h-3.5 text-rose-700" />
                Zero-Hallucination Guardrails
              </div>
              <p className="text-[11px] leading-relaxed">
                Facts derive strictly from optical label reading and the eAmbrosia EU legal appellations index. Unprinted grapes or obscured vintages are explicitly marked null, never guessed.
              </p>
            </div>
          </div>

          {/* Right / Enological Report Column (7 cols on Desktop) */}
          <div className="lg:col-span-7 space-y-6">
            {isLoading ? (
              <div className="bg-white dark:bg-stone-900 rounded-2xl border border-stone-200 dark:border-stone-800 p-12 text-center shadow-sm space-y-4">
                <div className="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-400 flex items-center justify-center mx-auto animate-pulse">
                  <Sparkles className="w-6 h-6 animate-spin" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-100">
                    Inspecting Wine Label Facts...
                  </h3>
                  <p className="text-xs text-stone-500 dark:text-stone-400 max-w-sm mx-auto">
                    Running Stage 1 VLM extraction, Stage 2 offline SQLite barcode &amp; FTS5 search, and enological pairing verification.
                  </p>
                </div>
              </div>
            ) : result ? (
              <WineExplanationView response={result} />
            ) : (
              <div className="bg-white dark:bg-stone-900 rounded-2xl border border-stone-200 dark:border-stone-800 p-12 text-center shadow-sm space-y-3">
                <div className="w-12 h-12 rounded-full bg-stone-100 dark:bg-stone-800 text-stone-400 flex items-center justify-center mx-auto">
                  <Wine className="w-6 h-6" />
                </div>
                <p className="text-xs text-stone-500">
                  Select a demo preset or upload wine bottle photos on the left to see the explanation.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
