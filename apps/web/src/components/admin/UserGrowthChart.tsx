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
  const { data, isLoading } = useQuery({
    queryKey: ["admin-user-growth", days],
    queryFn: async () => {
      const { data } = await authClient.admin.listUsers({
        query: {
          limit: 500,
          sortBy: "createdAt",
          sortDirection: "asc",
        },
      });
      return data ?? null;
    },
    staleTime: 120_000,
    retry: false,
  });

  const chartData = (() => {
    if (!data?.users) return [];
    const cutoff = subDays(new Date(), days);
    const buckets = new Map<string, number>();
    let cumulative = 0;

    for (const user of data.users) {
      const d = new Date(user.createdAt);
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
    return result;
  })();

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">User Growth</CardTitle>
        <CardDescription>Cumulative registrations</CardDescription>
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
