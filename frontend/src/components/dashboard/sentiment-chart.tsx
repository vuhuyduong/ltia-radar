"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

interface SentimentChartProps {
  data: Array<{ sentiment: string; count: number }>;
}

const COLORS: Record<string, string> = {
  POSITIVE: "#22c55e",
  NEGATIVE: "#ef4444",
  NEUTRAL: "#6b7280",
};

const LABELS: Record<string, string> = {
  POSITIVE: "Tích cực",
  NEGATIVE: "Tiêu cực",
  NEUTRAL: "Trung lập",
};

export function SentimentChart({ data }: SentimentChartProps) {
  const chartData = data.map((item) => ({
    name: LABELS[item.sentiment] || item.sentiment,
    value: item.count,
    color: COLORS[item.sentiment] || "#6b7280",
  }));

  // Show placeholder if no data
  if (chartData.length === 0) {
    chartData.push(
      { name: "Tích cực", value: 0, color: COLORS.POSITIVE },
      { name: "Tiêu cực", value: 0, color: COLORS.NEGATIVE },
      { name: "Trung lập", value: 1, color: COLORS.NEUTRAL }
    );
  }

  return (
    <div className="chart-container p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
        Phân bố Sắc thái
      </h3>
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={3}
              dataKey="value"
              stroke="none"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(222 47% 11%)",
                border: "1px solid hsl(217 33% 25%)",
                borderRadius: "8px",
                color: "white",
                fontSize: "12px",
              }}
            />
            <Legend
              formatter={(value) => (
                <span style={{ color: "hsl(210 40% 80%)", fontSize: "12px" }}>
                  {value}
                </span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
