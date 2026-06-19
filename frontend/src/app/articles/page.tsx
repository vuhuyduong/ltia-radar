"use client";

import { useEffect, useState } from "react";
import {
  Search,
  Filter,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import { articlesApi } from "@/lib/api";
import { formatArticleDate } from "@/lib/date";

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
  publish_time?: string;
  citations?: { title: string; source_url: string; domain: string; publish_time?: string }[];
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

const getFriendlyDomain = (url: string): string => {
  if (!url) return "Nguồn";
  try {
    const hostname = new URL(url).hostname;
    const domain = hostname.startsWith("www.") ? hostname.substring(4) : hostname;
    const domainLower = domain.toLowerCase();
    if (domainLower.includes("vnexpress")) return "VnExpress";
    if (domainLower.includes("tuoitre")) return "Tuổi Trẻ";
    if (domainLower.includes("thanhnien")) return "Thanh Niên";
    if (domainLower.includes("vietnamnet")) return "VietnamNet";
    if (domainLower.includes("dantri")) return "Dân trí";
    if (domainLower.includes("laodong")) return "Lao Động";
    if (domainLower.includes("vtv")) return "VTV";
    if (domainLower.includes("nld.com.vn")) return "Người Lao Động";
    if (domainLower.includes("baogiaothong")) return "Báo Giao thông";
    if (domainLower.includes("nhandan")) return "Báo Nhân Dân";
    if (domainLower.includes("vov.vn")) return "VOV";
    if (domainLower.includes("baodautu")) return "Báo Đầu tư";
    
    const parts = domain.split(".");
    return parts.length > 1 ? parts[0].charAt(0).toUpperCase() + parts[0].slice(1) : domain;
  } catch (e) {
    return "Nguồn";
  }
};

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sentiment, setSentiment] = useState("");
  const [impactLevel, setImpactLevel] = useState("");
  const [targetScope, setTargetScope] = useState("");

  // Pagination states
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);

  // Reset to first page when search or filters change
  useEffect(() => {
    setPage(1);
  }, [search, sentiment, impactLevel, targetScope]);

  useEffect(() => {
    const fetchArticles = async () => {
      setLoading(true);
      try {
        const params: Record<string, string> = {};
        if (search) params.search = search;
        if (sentiment) params.sentiment = sentiment;
        if (impactLevel) params.impact_level = impactLevel;
        if (targetScope) params.target_scope = targetScope;

        // Skip and limit calculations
        params.skip = String((page - 1) * pageSize);
        params.limit = String(pageSize);

        const res = await articlesApi.list(params);
        setArticles((res.data as Article[]) || []);
        setTotal(res.total || 0);
      } catch (error) {
        console.error("Failed to load articles:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchArticles();
  }, [sentiment, impactLevel, search, targetScope, page, pageSize]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">Tin tức đã phân tích</h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Danh sách tin tức đã qua xử lý AI — lọc, tìm kiếm và phân tích
        </p>
      </div>

      {/* Quick Filter Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Impact Level Card Group */}
        <div className="glass-card rounded-xl p-4 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Lọc nhanh theo mức độ ảnh hưởng
          </h3>
          <div className="flex flex-wrap gap-2">
            {[
              { value: "", label: "Tất cả", dotColor: "bg-blue-400" },
              { value: "CRITICAL", label: "Critical", dotColor: "bg-rose-500" },
              { value: "HIGH", label: "High", dotColor: "bg-orange-500" },
            ].map((card) => {
              const isActive = impactLevel === card.value;
              return (
                <button
                  key={card.value}
                  onClick={() => setImpactLevel(card.value)}
                  className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl border transition-all duration-200 ${
                    isActive
                      ? "bg-cyan-600 border-cyan-500 text-white shadow-lg shadow-cyan-500/20"
                      : "bg-[hsl(var(--card))] border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:border-cyan-500/50 hover:bg-[hsl(var(--accent))]/10"
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${card.dotColor}`} />
                  {card.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Sentiment Card Group */}
        <div className="glass-card rounded-xl p-4 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Lọc nhanh theo sắc thái
          </h3>
          <div className="flex flex-wrap gap-2">
            {[
              { value: "", label: "Tất cả", dotColor: "bg-blue-400" },
              { value: "NEGATIVE", label: "Tiêu cực", dotColor: "bg-rose-500" },
              { value: "POSITIVE", label: "Tích cực", dotColor: "bg-emerald-500" },
              { value: "NEUTRAL", label: "Trung lập", dotColor: "bg-slate-400" },
            ].map((card) => {
              const isActive = sentiment === card.value;
              return (
                <button
                  key={card.value}
                  onClick={() => setSentiment(card.value)}
                  className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl border transition-all duration-200 ${
                    isActive
                      ? "bg-cyan-600 border-cyan-500 text-white shadow-lg shadow-cyan-500/20"
                      : "bg-[hsl(var(--card))] border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:border-cyan-500/50 hover:bg-[hsl(var(--accent))]/10"
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${card.dotColor}`} />
                  {card.label}
                </button>
              );
            })}
          </div>
        </div>
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
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] py-2 pl-10 pr-3 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-505"
          >
            Tìm
          </button>
        </form>

        <select
          value={sentiment}
          onChange={(e) => setSentiment(e.target.value)}
          className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
        >
          <option value="">Tất cả sắc thái</option>
          <option value="NEGATIVE">Tiêu cực</option>
          <option value="POSITIVE">Tích cực</option>
          <option value="NEUTRAL">Trung lập</option>
        </select>

        <select
          value={impactLevel}
          onChange={(e) => setImpactLevel(e.target.value)}
          className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
        >
          <option value="">Tất cả mức độ</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>

        <select
          value={targetScope}
          onChange={(e) => setTargetScope(e.target.value)}
          className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
        >
          <option value="">Tất cả gói thầu</option>
          <option value="Toàn dự án">Toàn dự án</option>
          <option value="Gói thầu 5.10">Gói thầu 5.10</option>
          <option value="Gói thầu 4.6">Gói thầu 4.6</option>
          <option value="San nền">San nền</option>
          <option value="Giao thông">Giao thông</option>
          <option value="Nhà ga">Nhà ga</option>
          <option value="Đường cất hạ cánh">Đường cất hạ cánh</option>
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

                  <h3 className="text-sm font-semibold text-[hsl(var(--foreground))] transition-colors">
                    {(() => {
                      const firstUrl = Array.isArray(article.citations) && article.citations.length > 0 
                        ? article.citations[0].source_url 
                        : article.source_url;
                      return firstUrl ? (
                        <a
                          href={firstUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-cyan-400"
                        >
                          {article.title || "Không có tiêu đề"}
                        </a>
                      ) : (
                        article.title || "Không có tiêu đề"
                      );
                    })()}
                  </h3>

                  <p className="text-xs leading-relaxed text-[hsl(var(--muted-foreground))]">
                    {article.executive_summary}
                  </p>

                  {/* Grouped sources / Citations list */}
                  <div className="flex flex-wrap gap-1.5 items-center py-1">
                    <span className="text-[10px] text-[hsl(var(--muted-foreground))] mr-1">Nguồn tin:</span>
                    {Array.isArray(article.citations) && article.citations.length > 0 ? (
                      article.citations.map((cite, cIdx) => (
                        <a
                          key={cIdx}
                          href={cite.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 px-2 py-0.5 text-[9px] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/20 transition-all font-medium whitespace-nowrap"
                          title={cite.title}
                        >
                          {cite.domain || "Nguồn"}
                          <ExternalLink className="h-2.5 w-2.5 flex-shrink-0" />
                        </a>
                      ))
                    ) : (
                      !!article.source_url && (
                        <a
                          href={article.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 px-2 py-0.5 text-[9px] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/20 transition-all font-medium whitespace-nowrap"
                        >
                          {getFriendlyDomain(article.source_url)}
                          <ExternalLink className="h-2.5 w-2.5 flex-shrink-0" />
                        </a>
                      )
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-[10px] text-[hsl(var(--muted-foreground))]">
                    <span>
                      {formatArticleDate(article.publish_time || article.processed_time)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Pagination controls */}
          {totalPages > 1 && (
            <div className="flex flex-col sm:flex-row items-center justify-between border-t border-[hsl(var(--border))] pt-6 mt-6 gap-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Hiển thị <span className="font-semibold text-[hsl(var(--foreground))]">{Math.min((page - 1) * pageSize + 1, total)}</span> đến{" "}
                <span className="font-semibold text-[hsl(var(--foreground))]">{Math.min(page * pageSize, total)}</span> trong tổng số{" "}
                <span className="font-semibold text-[hsl(var(--foreground))]">{total}</span> tin tức
              </p>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setPage((p: number) => Math.max(p - 1, 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] text-[hsl(var(--foreground))] transition-all hover:bg-[hsl(var(--accent))]/10 disabled:opacity-50 disabled:hover:bg-[hsl(var(--card))]"
                >
                  Trước
                </button>
                
                {Array.from({ length: totalPages }, (_, i: number) => i + 1)
                  .filter((p: number) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
                  .map((p: number, idx: number, arr: number[]) => {
                    const showEllipsis = idx > 0 && p - arr[idx - 1] > 1;
                    return (
                      <div key={p} className="flex items-center gap-1.5">
                        {showEllipsis && (
                          <span className="px-2 text-xs text-[hsl(var(--muted-foreground))]">...</span>
                        )}
                        <button
                          onClick={() => setPage(p)}
                          className={`h-8 w-8 text-xs font-semibold rounded-lg border transition-all duration-200 ${
                            page === p
                              ? "bg-cyan-600 border-cyan-500 text-white shadow-md shadow-cyan-500/10"
                              : "bg-[hsl(var(--card))] border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:border-cyan-500/30 hover:bg-[hsl(var(--accent))]/10"
                          }`}
                        >
                          {p}
                        </button>
                      </div>
                    );
                  })}

                <button
                  onClick={() => setPage((p: number) => Math.min(p + 1, totalPages))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] text-[hsl(var(--foreground))] transition-all hover:bg-[hsl(var(--accent))]/10 disabled:opacity-50 disabled:hover:bg-[hsl(var(--card))]"
                >
                  Sau
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
