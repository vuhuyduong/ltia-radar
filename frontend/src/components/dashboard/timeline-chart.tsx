"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface TimelineChartProps {
  data: Array<{ date: string; sentiment: string; count: number }>;
}

export function TimelineChart({ data }: TimelineChartProps) {
  // Transform data: group by date, split by sentiment
  const dateMap = new Map<
    string,
    { date: string; positive: number; negative: number; neutral: number }
  >();

  data.forEach((item) => {
    if (!dateMap.has(item.date)) {
      dateMap.set(item.date, {
        date: item.date,
        positive: 0,
        negative: 0,
        neutral: 0,
      });
    }
    const entry = dateMap.get(item.date)!;
    const key = item.sentiment.toLowerCase() as
      | "positive"
      | "negative"
      | "neutral";
    if (key in entry) {
      entry[key] = item.count;
    }
  });

  const chartData = Array.from(dateMap.values()).sort((a, b) =>
    a.date.localeCompare(b.date)
  );

  return (
    <div className="chart-container p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
        Xu hướng theo thời gian
      </h3>
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border) / 0.3)"
            />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              tickLine={false}
              axisLine={{ stroke: "hsl(var(--border))" }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              tickLine={false}
              axisLine={{ stroke: "hsl(var(--border))" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                color: "hsl(var(--foreground))",
                fontSize: "12px",
              }}
            />
            <Legend
              formatter={(value) => {
                const labels: Record<string, string> = {
                  positive: "Tích cực",
                  negative: "Tiêu cực",
                  neutral: "Trung lập",
                };
                return (
                  <span
                    style={{ color: "hsl(var(--foreground))", opacity: 0.8, fontSize: "12px" }}
                  >
                    {labels[value] || value}
                  </span>
                );
              }}
            />
            <Line
              type="monotone"
              dataKey="positive"
              stroke="#22c55e"
              strokeWidth={2}
              dot={{ r: 3, fill: "#22c55e" }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="negative"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ r: 3, fill: "#ef4444" }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="neutral"
              stroke="#6b7280"
              strokeWidth={2}
              dot={{ r: 3, fill: "#6b7280" }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
