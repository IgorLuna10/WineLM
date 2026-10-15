"use client";

import React, { useRef, useState } from "react";
import {
  Camera,
  Upload,
  X,
  Sparkles,
  Layers,
  ArrowRight,
  FileQuestion,
  CheckCircle,
} from "lucide-react";
import { SAMPLE_PRESETS } from "../lib/api";

interface CaptureStudioProps {
  onAnalyze: (files: File[], context: string) => Promise<void>;
  onLoadPreset: (presetKey: string) => void;
  isLoading: boolean;
}

export function CaptureStudio({ onAnalyze, onLoadPreset, isLoading }: CaptureStudioProps) {
  const [frontFile, setFrontFile] = useState<File | null>(null);
  const [backFile, setBackFile] = useState<File | null>(null);
  const [frontPreview, setFrontPreview] = useState<string | null>(null);
  const [backPreview, setBackPreview] = useState<string | null>(null);
  const [contextNote, setContextNote] = useState<string>("");

  const frontInputRef = useRef<HTMLInputElement>(null);
  const backInputRef = useRef<HTMLInputElement>(null);
  const frontCameraRef = useRef<HTMLInputElement>(null);
  const backCameraRef = useRef<HTMLInputElement>(null);

  const handleFrontSelect = (file: File) => {
    setFrontFile(file);
    setFrontPreview(URL.createObjectURL(file));
  };

  const handleBackSelect = (file: File) => {
    setBackFile(file);
    setBackPreview(URL.createObjectURL(file));
  };

  const clearFront = () => {
    setFrontFile(null);
    if (frontPreview) URL.revokeObjectURL(frontPreview);
    setFrontPreview(null);
  };

  const clearBack = () => {
    setBackFile(null);
    if (backPreview) URL.revokeObjectURL(backPreview);
    setBackPreview(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const filesToSend: File[] = [];
    if (frontFile) filesToSend.push(frontFile);
    if (backFile) filesToSend.push(backFile);

    if (filesToSend.length === 0) return;
    await onAnalyze(filesToSend, contextNote);
  };

  return (
    <div className="bg-white dark:bg-stone-900 rounded-2xl border border-stone-200 dark:border-stone-800 shadow-sm p-5 sm:p-6 space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-stone-100 dark:border-stone-800 pb-4">
        <div>
          <h2 className="text-lg font-serif font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <Camera className="w-5 h-5 text-rose-800 dark:text-rose-400" />
            Wine Bottle Photo Ingestion
          </h2>
          <p className="text-xs text-stone-500 dark:text-stone-400">
            Snap or upload bottle photos. Multi-photo ingestion (front + back label) enables complete barcode & vintage verification.
          </p>
        </div>

        {/* Demo Presets dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-stone-400 hidden sm:inline">Try Demo:</span>
          <select
            aria-label="Try Demo Presets"
            className="text-xs bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-lg px-2.5 py-1.5 text-stone-700 dark:text-stone-300 font-medium focus:outline-none focus:ring-1 focus:ring-rose-500"
            onChange={(e) => {
              if (e.target.value) {
                onLoadPreset(e.target.value);
                e.target.value = "";
              }
            }}
            defaultValue=""
          >
            <option value="" disabled>
              ⚡ Select Preset...
            </option>
            {Object.entries(SAMPLE_PRESETS).map(([key, item]) => (
              <option key={key} value={key}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Dual Photo Slot Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Slot 1: Front Label */}
          <div className="flex flex-col space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-stone-700 dark:text-stone-300 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-700" />
                Photo 1: Front Label
              </span>
              <span className="text-[11px] text-stone-400">Estate, AOC, Vintage</span>
            </div>

            {frontPreview ? (
              <div className="relative aspect-[3/4] max-h-72 w-full rounded-xl overflow-hidden border border-stone-200 dark:border-stone-700 bg-stone-950 flex items-center justify-center">
                <img
                  src={frontPreview}
                  alt="Front Label Preview"
                  className="w-full h-full object-contain"
                />
                <button
                  type="button"
                  onClick={clearFront}
                  className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
                  title="Remove photo"
                >
                  <X className="w-4 h-4" />
                </button>
                <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/60 text-white text-[10px] font-medium backdrop-blur-sm">
                  Front Label Ready
                </div>
              </div>
            ) : (
              <div className="aspect-[3/4] max-h-72 w-full rounded-xl border-2 border-dashed border-stone-300 dark:border-stone-700 hover:border-rose-500 dark:hover:border-rose-400 transition-colors flex flex-col items-center justify-center p-4 text-center bg-stone-50/50 dark:bg-stone-900/50">
                <div className="w-10 h-10 rounded-full bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-400 flex items-center justify-center mb-3">
                  <Upload className="w-5 h-5" />
                </div>
                <p className="text-xs font-semibold text-stone-800 dark:text-stone-200 mb-1">
                  Front Label Photo
                </p>
                <p className="text-[11px] text-stone-400 max-w-[200px] mb-4">
                  Drag & drop image or choose camera on mobile
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => frontInputRef.current?.click()}
                    className="px-3 py-1.5 text-xs font-medium bg-white dark:bg-stone-800 border border-stone-300 dark:border-stone-600 rounded-lg shadow-sm hover:bg-stone-50 dark:hover:bg-stone-700 transition"
                  >
                    Select File
                  </button>
                  <button
                    type="button"
                    onClick={() => frontCameraRef.current?.click()}
                    className="px-3 py-1.5 text-xs font-medium bg-rose-900 text-white rounded-lg shadow-sm hover:bg-rose-800 transition flex items-center gap-1"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    Camera
                  </button>
                </div>

                <input
                  ref={frontInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFrontSelect(e.target.files[0])}
                />
                <input
                  ref={frontCameraRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFrontSelect(e.target.files[0])}
                />
              </div>
            )}
          </div>

          {/* Slot 2: Back Label (Optional or multi-photo) */}
          <div className="flex flex-col space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-stone-700 dark:text-stone-300 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-600" />
                Photo 2: Back Label <span className="text-stone-400 font-normal">(Recommended)</span>
              </span>
              <span className="text-[11px] text-stone-400">Barcode, ABV, Tech specs</span>
            </div>

            {backPreview ? (
              <div className="relative aspect-[3/4] max-h-72 w-full rounded-xl overflow-hidden border border-stone-200 dark:border-stone-700 bg-stone-950 flex items-center justify-center">
                <img
                  src={backPreview}
                  alt="Back Label Preview"
                  className="w-full h-full object-contain"
                />
                <button
                  type="button"
                  onClick={clearBack}
                  className="absolute top-2 right-2 p-1.5 rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
                  title="Remove photo"
                >
                  <X className="w-4 h-4" />
                </button>
                <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/60 text-white text-[10px] font-medium backdrop-blur-sm">
                  Back Label Ready
                </div>
              </div>
            ) : (
              <div className="aspect-[3/4] max-h-72 w-full rounded-xl border-2 border-dashed border-stone-300 dark:border-stone-700 hover:border-amber-500 dark:hover:border-amber-400 transition-colors flex flex-col items-center justify-center p-4 text-center bg-stone-50/50 dark:bg-stone-900/50">
                <div className="w-10 h-10 rounded-full bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 flex items-center justify-center mb-3">
                  <Layers className="w-5 h-5" />
                </div>
                <p className="text-xs font-semibold text-stone-800 dark:text-stone-200 mb-1">
                  Back Label Photo
                </p>
                <p className="text-[11px] text-stone-400 max-w-[200px] mb-4">
                  Captures EAN-13 barcode & enological blend facts
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => backInputRef.current?.click()}
                    className="px-3 py-1.5 text-xs font-medium bg-white dark:bg-stone-800 border border-stone-300 dark:border-stone-600 rounded-lg shadow-sm hover:bg-stone-50 dark:hover:bg-stone-700 transition"
                  >
                    Select File
                  </button>
                  <button
                    type="button"
                    onClick={() => backCameraRef.current?.click()}
                    className="px-3 py-1.5 text-xs font-medium bg-amber-800 text-white rounded-lg shadow-sm hover:bg-amber-700 transition flex items-center gap-1"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    Camera
                  </button>
                </div>

                <input
                  ref={backInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleBackSelect(e.target.files[0])}
                />
                <input
                  ref={backCameraRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleBackSelect(e.target.files[0])}
                />
              </div>
            )}
          </div>
        </div>

        {/* Optional Context Note */}
        <div>
          <label className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1">
            Optional Context Hint (e.g., &ldquo;Bordeaux cave photo with glare&rdquo;)
          </label>
          <input
            type="text"
            value={contextNote}
            onChange={(e) => setContextNote(e.target.value)}
            placeholder="Type any hints or leave blank..."
            className="w-full text-xs bg-stone-50 dark:bg-stone-800/80 border border-stone-200 dark:border-stone-700 rounded-xl px-3.5 py-2.5 text-stone-800 dark:text-stone-200 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-rose-500"
          />
        </div>

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            disabled={(!frontFile && !backFile) || isLoading}
            className={`w-full py-3.5 px-6 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2 shadow-md ${
              (!frontFile && !backFile) || isLoading
                ? "bg-stone-200 dark:bg-stone-800 text-stone-400 cursor-not-allowed shadow-none"
                : "bg-gradient-to-r from-rose-900 to-amber-900 hover:from-rose-800 hover:to-amber-800 text-white shadow-rose-900/20 active:scale-[0.99]"
            }`}
          >
            {isLoading ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin" />
                <span>Running Zero-Hallucination Pipeline...</span>
              </>
            ) : (
              <>
                <span>Analyze Wine Bottle</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
