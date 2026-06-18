"use client";

import {
  Newspaper,
  AlertTriangle,
  TrendingDown,
  ShieldAlert,
} from "lucide-react";

interface StatsCardsProps {
  stats: Record<string, unknown> | null;
}

const cards = [
  {
    key: "total_articles",
    label: "Tổng tin tức",
    icon: Newspaper,
    gradient: "from-cyan-500/20 to-blue-500/10",
    iconColor: "text-cyan-400",
    format: (v: unknown) => String(v || 0),
  },
  {
    key: "critical_count",
    label: "Mức CRITICAL",
    icon: AlertTriangle,
    gradient: "from-red-500/20 to-orange-500/10",
    iconColor: "text-red-400",
    format: (v: unknown) => String(v || 0),
  },
  {
    key: "negative_percentage",
    label: "Tỷ lệ Tiêu cực",
    icon: TrendingDown,
    gradient: "from-orange-500/20 to-amber-500/10",
    iconColor: "text-orange-400",
    format: (v: unknown) => `${v || 0}%`,
  },
  {
    key: "rumor_count",
    label: "Tin đồn phát hiện",
    icon: ShieldAlert,
    gradient: "from-purple-500/20 to-pink-500/10",
    iconColor: "text-purple-400",
    format: (v: unknown) => String(v || 0),
  },
];

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.key}
          className={`stat-card glass-card rounded-xl p-5 bg-gradient-to-br ${card.gradient}`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                {card.label}
              </p>
              <p className="mt-2 text-3xl font-bold text-white">
                {card.format(stats?.[card.key])}
              </p>
            </div>
            <div className={`rounded-lg bg-[hsl(var(--secondary))] p-3`}>
              <card.icon className={`h-5 w-5 ${card.iconColor}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
