"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Menu, Sun, Moon } from "lucide-react";
import { crawlerApi } from "@/lib/api";

export function Header() {
  const [isCrawling, setIsCrawling] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const activeTheme = document.documentElement.className === "light" ? "light" : "dark";
    setTheme(activeTheme);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    document.documentElement.className = nextTheme;
    localStorage.setItem("theme", nextTheme);
    setTheme(nextTheme);
  };

  const handleTriggerCrawl = async () => {
    setIsCrawling(true);
    try {
      // Calls the fast trigger endpoint
      await crawlerApi.trigger({ trigger_type: "fast" });
    } catch (error) {
      console.error("Failed to trigger crawl:", error);
    } finally {
      setTimeout(() => setIsCrawling(false), 3000);
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[hsl(var(--border))] bg-[hsl(var(--background))]/80 px-4 md:px-6 backdrop-blur-xl transition-colors duration-200">
      <div className="flex items-center">
        {/* Mobile Sidebar Hamburger Toggle */}
        <button
          onClick={() => window.dispatchEvent(new CustomEvent("toggle-sidebar"))}
          className="mr-3 rounded-lg p-2 text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))] hover:text-[hsl(var(--foreground))] lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        <h2 className="text-sm md:text-base font-semibold text-[hsl(var(--foreground))] truncate max-w-[200px] sm:max-w-xs md:max-w-none">
          Sân bay Long Thành — Radar Cảnh báo sớm
        </h2>
        <span className="ml-2.5 hidden sm:inline-block rounded-full bg-cyan-500/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-cyan-400 ring-1 ring-cyan-500/20">
          MVP v1.0
        </span>
      </div>

      <div className="flex items-center gap-2">
        {/* Theme Switching Button */}
        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))] hover:text-[hsl(var(--foreground))] transition-colors"
          title="Chuyển đổi giao diện"
        >
          {theme === "dark" ? (
            <Sun className="h-5 w-5 text-amber-400" />
          ) : (
            <Moon className="h-5 w-5 text-indigo-500" />
          )}
        </button>

        {/* Fast Trigger Button */}
        <button
          onClick={handleTriggerCrawl}
          disabled={isCrawling}
          className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-3 py-1.8 md:px-4 md:py-2 text-xs md:text-sm font-medium text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${isCrawling ? "animate-spin" : ""}`}
          />
          <span className="hidden xs:inline">{isCrawling ? "Đang quét..." : "Quét nhanh"}</span>
          <span className="xs:hidden">{isCrawling ? "..." : "Quét"}</span>
        </button>
      </div>
    </header>
  );
}
