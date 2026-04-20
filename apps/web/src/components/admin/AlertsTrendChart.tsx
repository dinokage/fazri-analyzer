"use client";

import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";
import { format, subDays, startOfDay } from "date-fns";

const chartConfig = {
  alerts: {
    label: "Alerts",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

interface Props {
  days?: number;
}

export function AlertsTrendChart({ days = 14 }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-alerts-trend", days],
    queryFn: () =>
      apiClient.getAlerts({
        page_size: 200,
        start_date: subDays(new Date(), days).toISOString(),
      }),
    staleTime: 60_000,
  });

  const chartData = (() => {
    const buckets: Record<string, number> = {};
    for (let i = days - 1; i >= 0; i--) {
      buckets[format(subDays(new Date(), i), "MMM d")] = 0;
    }
    if (data?.alerts) {
      for (const alert of data.alerts) {
        const key = format(startOfDay(new Date(alert.created_at)), "MMM d");
        if (key in buckets) buckets[key]++;
      }
    }
    return Object.entries(buckets).map(([date, alerts]) => ({ date, alerts }));
  })();

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Alert Volume</CardTitle>
        <CardDescription>Last {days} days</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-[200px] animate-pulse rounded bg-muted" />
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
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} width={24} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line
                type="monotone"
                dataKey="alerts"
                stroke="var(--color-alerts)"
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
