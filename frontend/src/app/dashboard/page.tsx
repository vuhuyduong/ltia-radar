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

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsRes, risksRes] = await Promise.all([
          dashboardApi.stats(),
          dashboardApi.topRisks(),
        ]);
        setStats(statsRes);
        setTopRisks((risksRes.data as Record<string, unknown>[]) || []);
      } catch (error) {
        console.error("Failed to load dashboard:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

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
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Tổng quan tình hình truyền thông Dự án Sân bay Long Thành
        </p>
      </div>

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
