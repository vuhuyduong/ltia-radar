"use client";

import { useState } from "react";
import { RefreshCw, Radar } from "lucide-react";
import { crawlerApi } from "@/lib/api";

export function Header() {
  const [isCrawling, setIsCrawling] = useState(false);

  const handleTriggerCrawl = async () => {
    setIsCrawling(true);
    try {
      await crawlerApi.trigger();
    } catch (error) {
      console.error("Failed to trigger crawl:", error);
    } finally {
      setTimeout(() => setIsCrawling(false), 3000);
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[hsl(var(--border))] bg-[hsl(var(--background))]/80 px-6 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold text-white">
          Sân bay Long Thành — Radar Cảnh báo sớm
        </h2>
        <span className="rounded-full bg-cyan-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-cyan-400 ring-1 ring-cyan-500/20">
          MVP v1.0
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleTriggerCrawl}
          disabled={isCrawling}
          className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${isCrawling ? "animate-spin" : ""}`}
          />
          {isCrawling ? "Đang quét..." : "Quét ngay"}
        </button>
      </div>
    </header>
  );
}
