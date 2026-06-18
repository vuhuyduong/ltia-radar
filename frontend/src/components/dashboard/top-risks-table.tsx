"use client";

import { ExternalLink } from "lucide-react";

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
              <th className="px-5 py-3 font-medium">Mức độ</th>
              <th className="px-5 py-3 font-medium">Sắc thái</th>
              <th className="px-5 py-3 font-medium">Phân loại</th>
              <th className="px-5 py-3 font-medium">Tóm tắt</th>
              <th className="px-5 py-3 font-medium">Link</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[hsl(var(--border))]">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-5 py-12 text-center text-[hsl(var(--muted-foreground))]"
                >
                  Chưa có dữ liệu. Hãy thêm nguồn tin và chạy quét để bắt đầu.
                </td>
              </tr>
            ) : (
              data.map((item, idx) => (
                <tr key={(item._id as string) || idx}>
                  <td className="max-w-[200px] truncate px-5 py-3 font-medium text-white">
                    {(item.title as string) || "N/A"}
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
                  <td className="max-w-[300px] truncate px-5 py-3 text-[hsl(var(--muted-foreground))]">
                    {(item.executive_summary as string) || ""}
                  </td>
                  <td className="px-5 py-3">
                    {item.source_url && (
                      <a
                        href={item.source_url as string}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 hover:text-cyan-300"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
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
