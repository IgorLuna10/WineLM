"use client";

import React, { useEffect, useState } from "react";
import { Wine, Activity, CheckCircle2, AlertCircle } from "lucide-react";
import { checkBackendHealth } from "../lib/api";

export function Header() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    checkBackendHealth().then(({ healthy }) => {
      setBackendStatus(healthy ? "online" : "offline");
    });

    const interval = setInterval(() => {
      checkBackendHealth().then(({ healthy }) => {
        setBackendStatus(healthy ? "online" : "offline");
      });
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-white/90 dark:bg-stone-900/90 backdrop-blur-md border-b border-stone-200 dark:border-stone-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-900 via-rose-800 to-amber-900 flex items-center justify-center shadow-md shadow-rose-900/20 text-white">
            <Wine className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-serif font-bold text-xl tracking-tight text-stone-900 dark:text-stone-100">
                Panela.Wine
              </span>
              <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300">
                Phase 1 Engine
              </span>
            </div>
            <p className="text-xs text-stone-500 dark:text-stone-400 hidden sm:block">
              Factual, Hallucination-Free Wine Ingestion &bull; Closer to Yuka than Vivino
            </p>
          </div>
        </div>

        {/* Backend health status badge */}
        <div className="flex items-center space-x-3 text-xs">
          <div
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full font-medium transition-colors border ${
              backendStatus === "online"
                ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
                : backendStatus === "offline"
                ? "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800"
                : "bg-stone-100 dark:bg-stone-800 text-stone-500 border-stone-200 dark:border-stone-700"
            }`}
            title={
              backendStatus === "online"
                ? "Connected to FastAPI at http://localhost:8000"
                : "FastAPI not detected on :8000 (Demo Mode Active)"
            }
          >
            {backendStatus === "online" ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Backend Online (:8000)</span>
              </>
            ) : backendStatus === "offline" ? (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Demo / Standalone Mode</span>
              </>
            ) : (
              <>
                <Activity className="w-3.5 h-3.5 animate-spin" />
                <span>Checking Engine...</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
