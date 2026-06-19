"use client";

import { ExternalLink } from "lucide-react";
import { formatTableDate } from "@/lib/date";

interface TopRisksTableProps {
  data: Record<string, unknown>[];
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

export function TopRisksTable({ data }: TopRisksTableProps) {
  return (
    <div className="chart-container overflow-hidden">
      <div className="border-b border-[hsl(var(--border))] px-5 py-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
          Top 10 — Tin tức rủi ro cao nhất
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="data-table w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
              <th className="px-5 py-3 font-medium">Tiêu đề</th>
              <th className="px-5 py-3 font-medium">Ngày đăng tin</th>
              <th className="px-5 py-3 font-medium">Mức độ</th>
              <th className="px-5 py-3 font-medium">Sắc thái</th>
              <th className="px-5 py-3 font-medium">Phân loại</th>
              <th className="px-5 py-3 font-medium">Tóm tắt</th>
              <th className="px-5 py-3 font-medium">Nguồn tin</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[hsl(var(--border))]">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="px-5 py-12 text-center text-[hsl(var(--muted-foreground))]"
                >
                  Chưa có dữ liệu. Hãy thêm nguồn tin và chạy quét để bắt đầu.
                </td>
              </tr>
            ) : (
              data.map((item, idx) => (
                <tr key={(item._id as string) || idx}>
                  <td className="min-w-[180px] max-w-[300px] px-5 py-3 font-medium text-[hsl(var(--foreground))] whitespace-normal break-words">
                     {(item.title as string) || "N/A"}
                  </td>
                  <td className="px-5 py-3 text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                    {(() => {
                      const res = formatTableDate((item.publish_time || item.processed_time) as string);
                      return (
                        <div className="flex flex-col text-xs">
                          <span className="font-medium text-[hsl(var(--foreground))]">{res.line1}</span>
                          {res.line2 && <span className="text-[hsl(var(--muted-foreground))]/80">{res.line2}</span>}
                        </div>
                      );
                    })()}
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        impactBadge[item.impact_level as string] || ""
                      }`}
                    >
                      {item.impact_level as string}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        sentimentBadge[item.sentiment as string] || ""
                      }`}
                    >
                      {item.sentiment as string}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-[hsl(var(--muted-foreground))]">
                    {(Array.isArray(item.category) ? item.category : []).join(", ")}
                  </td>
                  <td className="min-w-[250px] max-w-[450px] px-5 py-3 text-[hsl(var(--muted-foreground))] whitespace-normal break-words">
                    {(item.executive_summary as string) || ""}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex flex-wrap gap-1.5 max-w-[150px]">
                      {Array.isArray(item.citations) && item.citations.length > 0 ? (
                        (item.citations as any[]).map((cite: any, cIdx: number) => (
                          <a
                            key={cIdx}
                            href={cite.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 px-2 py-0.5 text-xs text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/20 transition-all font-medium whitespace-nowrap"
                            title={cite.title}
                          >
                            {cite.domain || "Nguồn"}
                            <ExternalLink className="h-3 w-3 flex-shrink-0" />
                          </a>
                        ))
                      ) : (
                        !!item.source_url && (
                          <a
                            href={item.source_url as string}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 px-2 py-0.5 text-xs text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/20 transition-all font-medium whitespace-nowrap"
                          >
                            {getFriendlyDomain(item.source_url as string)}
                            <ExternalLink className="h-3 w-3 flex-shrink-0" />
                          </a>
                        )
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>

        </table>
      </div>
    </div>
  );
}
