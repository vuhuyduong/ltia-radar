"use client";

import { useEffect, useState } from "react";
import { dashboardApi } from "@/lib/api";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { SentimentChart } from "@/components/dashboard/sentiment-chart";
import { TimelineChart } from "@/components/dashboard/timeline-chart";
import { TopRisksTable } from "@/components/dashboard/top-risks-table";

export default function DashboardPage() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [topRisks, setTopRisks] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(false);
  const [limitArticles, setLimitArticles] = useState<string>("all");
  const [lastDays, setLastDays] = useState<string>("all");
  const [targetScope, setTargetScope] = useState<string>("all");

  useEffect(() => {
    async function fetchData() {
      setStatsLoading(true);
      try {
        const params: Record<string, string> = {};
        if (limitArticles !== "all") {
          params.limit_articles = limitArticles;
        }
        if (lastDays !== "all") {
          params.last_days = lastDays;
        }
        if (targetScope !== "all") {
          params.target_scope = targetScope;
        }
        
        const [statsRes, risksRes] = await Promise.all([
          dashboardApi.stats(params),
          dashboardApi.topRisks(10, params),
        ]);
        
        setStats(statsRes);
        setTopRisks((risksRes.data as Record<string, unknown>[]) || []);
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setStatsLoading(false);
        setLoading(false);
      }
    }
    fetchData();
  }, [limitArticles, lastDays, targetScope]);

  const handleLimitArticlesChange = (val: string) => {
    setLimitArticles(val);
    if (val !== "all") {
      setLastDays("all");
    }
  };

  const handleLastDaysChange = (val: string) => {
    setLastDays(val);
    if (val !== "all") {
      setLimitArticles("all");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Đang tải dữ liệu...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">Dashboard</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Tổng quan tình hình truyền thông Dự án Sân bay Long Thành
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/* Limit Articles Dropdown */}
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold tracking-wider text-[hsl(var(--muted-foreground))] uppercase">Số tin gần nhất</span>
            <select
              value={limitArticles}
              onChange={(e) => handleLimitArticlesChange(e.target.value)}
              className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-1.5 text-xs text-[hsl(var(--foreground))] shadow-sm transition-all focus:border-[hsl(var(--primary))] focus:ring-1 focus:ring-[hsl(var(--primary))] focus:outline-none"
            >
              <option value="all">Tất cả bài viết</option>
              <option value="20">20 tin gần nhất</option>
              <option value="50">50 tin gần nhất</option>
              <option value="100">100 tin gần nhất</option>
            </select>
          </div>

          {/* Last Days Dropdown */}
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold tracking-wider text-[hsl(var(--muted-foreground))] uppercase">Khoảng thời gian</span>
            <select
              value={lastDays}
              onChange={(e) => handleLastDaysChange(e.target.value)}
              className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-1.5 text-xs text-[hsl(var(--foreground))] shadow-sm transition-all focus:border-[hsl(var(--primary))] focus:ring-1 focus:ring-[hsl(var(--primary))] focus:outline-none"
            >
              <option value="all">Tất cả thời gian</option>
              <option value="7">7 ngày gần nhất</option>
              <option value="14">14 ngày gần nhất</option>
              <option value="30">30 ngày gần nhất</option>
              <option value="90">90 ngày gần nhất</option>
            </select>
          </div>

          {/* Target Scope Dropdown */}
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold tracking-wider text-[hsl(var(--muted-foreground))] uppercase">Gói thầu</span>
            <select
              value={targetScope}
              onChange={(e) => setTargetScope(e.target.value)}
              className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-1.5 text-xs text-[hsl(var(--foreground))] shadow-sm transition-all focus:border-[hsl(var(--primary))] focus:ring-1 focus:ring-[hsl(var(--primary))] focus:outline-none"
            >
              <option value="all">Tất cả gói thầu</option>
              <option value="Toàn dự án">Toàn dự án</option>
              <option value="Gói thầu 5.10">Gói thầu 5.10</option>
              <option value="Gói thầu 4.6">Gói thầu 4.6</option>
              <option value="San nền">San nền</option>
              <option value="Giao thông">Giao thông</option>
              <option value="Nhà ga">Nhà ga</option>
              <option value="Đường cất hạ cánh">Đường cất hạ cánh</option>
            </select>
          </div>
        </div>
      </div>

      {statsLoading && (
        <div className="flex items-center justify-center py-2 text-xs text-cyan-500 animate-pulse">
          Đang cập nhật số liệu...
        </div>
      )}

      {/* Stat Cards */}
      <StatsCards stats={stats} />

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SentimentChart
          data={
            (stats?.sentiment_distribution as Array<{
              sentiment: string;
              count: number;
            }>) || []
          }
        />
        <TimelineChart
          data={
            (stats?.timeline as Array<{
              date: string;
              sentiment: string;
              count: number;
            }>) || []
          }
        />
      </div>

      {/* Top Risks Table */}
      <TopRisksTable data={topRisks} />
    </div>
  );
}
