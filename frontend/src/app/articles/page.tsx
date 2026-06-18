"use client";

import { useEffect, useState } from "react";
import {
  Search,
  Filter,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import { articlesApi } from "@/lib/api";

interface Article {
  _id: string;
  title: string;
  source_url: string;
  sentiment: string;
  impact_level: string;
  category: string[];
  executive_summary: string;
  is_rumor: boolean;
  processed_time: string;
}

const impactBadge: Record<string, string> = {
  CRITICAL: "badge-critical",
  HIGH: "badge-high",
  MEDIUM: "badge-medium",
  LOW: "badge-low",
};

const sentimentBadge: Record<string, string> = {
  NEGATIVE: "badge-negative",
  POSITIVE: "badge-positive",
  NEUTRAL: "badge-neutral",
};

const sentimentLabel: Record<string, string> = {
  NEGATIVE: "Tiêu cực",
  POSITIVE: "Tích cực",
  NEUTRAL: "Trung lập",
};

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sentiment, setSentiment] = useState("");
  const [impactLevel, setImpactLevel] = useState("");

  useEffect(() => {
    const fetchArticles = async () => {
      setLoading(true);
      try {
        const params: Record<string, string> = {};
        if (search) params.search = search;
        if (sentiment) params.sentiment = sentiment;
        if (impactLevel) params.impact_level = impactLevel;

        const res = await articlesApi.list(params);
        setArticles((res.data as Article[]) || []);
      } catch (error) {
        console.error("Failed to load articles:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchArticles();
  }, [sentiment, impactLevel, search]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // search state change already triggers useEffect refetch
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Tin tức đã phân tích</h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Danh sách tin tức đã qua xử lý AI — lọc, tìm kiếm và phân tích
        </p>
      </div>

      {/* Filters */}
      <div className="glass-card flex flex-wrap items-center gap-3 rounded-xl p-4">
        <form onSubmit={handleSearch} className="flex flex-1 gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm kiếm theo tiêu đề, tóm tắt..."
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] py-2 pl-10 pr-3 text-sm text-white placeholder:text-[hsl(var(--muted-foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
          >
            Tìm
          </button>
        </form>

        <select
          value={sentiment}
          onChange={(e) => setSentiment(e.target.value)}
          className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
        >
          <option value="">Tất cả sắc thái</option>
          <option value="NEGATIVE">Tiêu cực</option>
          <option value="POSITIVE">Tích cực</option>
          <option value="NEUTRAL">Trung lập</option>
        </select>

        <select
          value={impactLevel}
          onChange={(e) => setImpactLevel(e.target.value)}
          className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
        >
          <option value="">Tất cả mức độ</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>
      </div>

      {/* Articles List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
        </div>
      ) : articles.length === 0 ? (
        <div className="glass-card rounded-xl py-16 text-center">
          <Filter className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))]" />
          <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
            Không tìm thấy tin tức. Thay đổi bộ lọc hoặc chạy quét mới.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {articles.map((article) => (
            <div
              key={article._id}
              className="glass-card group rounded-xl p-5 transition-all duration-200 hover:border-cyan-500/30"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${
                        impactBadge[article.impact_level] || ""
                      }`}
                    >
                      {article.impact_level}
                    </span>
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-[10px] font-medium ${
                        sentimentBadge[article.sentiment] || ""
                      }`}
                    >
                      {sentimentLabel[article.sentiment] || article.sentiment}
                    </span>
                    {article.is_rumor && (
                      <span className="flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-400 ring-1 ring-amber-500/30">
                        <ShieldAlert className="h-3 w-3" />
                        Tin đồn
                      </span>
                    )}
                    {article.category?.map((cat) => (
                      <span
                        key={cat}
                        className="rounded-md bg-[hsl(var(--secondary))] px-2 py-0.5 text-[10px] text-[hsl(var(--muted-foreground))]"
                      >
                        {cat}
                      </span>
                    ))}
                  </div>

                  <h3 className="text-sm font-semibold text-white group-hover:text-cyan-400 transition-colors">
                    {article.title || "Không có tiêu đề"}
                  </h3>

                  <p className="text-xs leading-relaxed text-[hsl(var(--muted-foreground))]">
                    {article.executive_summary}
                  </p>

                  <div className="flex items-center gap-3 text-[10px] text-[hsl(var(--muted-foreground))]">
                    <span>
                      {article.processed_time
                        ? new Date(article.processed_time).toLocaleString("vi-VN")
                        : ""}
                    </span>
                  </div>
                </div>

                {article.source_url && (
                  <a
                    href={article.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 rounded-lg p-2 text-[hsl(var(--muted-foreground))] transition-colors hover:bg-cyan-500/10 hover:text-cyan-400"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
