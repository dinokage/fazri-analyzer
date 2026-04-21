"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { authClient } from "@/lib/auth-client";
import { format, startOfWeek, subDays } from "date-fns";

const chartConfig = {
  users: {
    label: "Users",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig;

interface Props {
  days?: number;
}

export function UserGrowthChart({ days = 14 }: Props) {
  const [chartData, setChartData] = useState<{ date: string; users: number }[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    setChartData(null);

    authClient.admin.listUsers({
      query: { limit: 500, sortBy: "createdAt", sortDirection: "asc" },
    }).then(({ data }) => {
      if (cancelled) return;
      const users = data?.users ?? [];
      const cutoff = subDays(new Date(), days);
      const buckets = new Map<string, number>();
      let cumulative = 0;

      for (const user of users) {
        const d = new Date(user.createdAt as unknown as string);
        if (isNaN(d.getTime())) continue;
        const weekKey = format(startOfWeek(d), "MMM d");
        if (d >= cutoff) {
          buckets.set(weekKey, (buckets.get(weekKey) ?? 0) + 1);
        } else {
          cumulative++;
        }
      }

      const result: { date: string; users: number }[] = [];
      let running = cumulative;
      for (const [date, count] of buckets) {
        running += count;
        result.push({ date, users: running });
      }
      setChartData(result);
    }).catch(() => {
      if (!cancelled) setChartData([]);
    });

    return () => { cancelled = true; };
  }, [days]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">User Growth</CardTitle>
        <CardDescription>Cumulative registrations</CardDescription>
      </CardHeader>
      <CardContent>
        {chartData === null ? (
          <div className="h-[200px] animate-pulse rounded bg-muted" />
        ) : chartData.length === 0 ? (
          <div className="h-[200px] flex items-center justify-center text-sm text-muted-foreground">
            No data available
          </div>
        ) : (
          <ChartContainer config={chartConfig} className="aspect-video max-h-[200px] w-full">
            <LineChart data={chartData}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                interval="preserveStartEnd"
              />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} width={28} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line
                type="monotone"
                dataKey="users"
                stroke="var(--color-users)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
