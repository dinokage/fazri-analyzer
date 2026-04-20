"use client";

import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { authClient } from "@/lib/auth-client";

const chartConfig = {
  members: {
    label: "Members",
    color: "var(--chart-3)",
  },
} satisfies ChartConfig;

export function OrgActivityChart() {
  const { data: orgs } = authClient.useListOrganizations();

  const { data: orgDetails, isLoading } = useQuery({
    queryKey: ["admin-org-details", orgs?.map((o) => o.id)],
    queryFn: async () => {
      if (!orgs?.length) return [];
      const results = await Promise.all(
        orgs.slice(0, 10).map(async (org) => {
          const { data } = await authClient.organization.getFullOrganization({
            query: { organizationId: org.id },
          });
          return {
            slug: org.slug,
            members: data?.members?.length ?? 0,
          };
        })
      );
      return results;
    },
    enabled: !!orgs?.length,
    staleTime: 120_000,
  });

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Org Members</CardTitle>
        <CardDescription>Members per organization</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading || !orgDetails ? (
          <div className="h-[200px] animate-pulse rounded bg-muted" />
        ) : (
          <ChartContainer config={chartConfig} className="aspect-video max-h-[200px] w-full">
            <BarChart data={orgDetails}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="slug"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
              />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} width={24} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="members" fill="var(--color-members)" radius={4} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
