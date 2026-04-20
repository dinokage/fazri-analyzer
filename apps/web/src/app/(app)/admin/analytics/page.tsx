"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertsTrendChart } from "@/components/admin/AlertsTrendChart";
import { UserGrowthChart } from "@/components/admin/UserGrowthChart";
import { OrgActivityChart } from "@/components/admin/OrgActivityChart";
import { apiClient } from "@/lib/api-client";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PolarAngleAxis, PolarGrid, Radar, RadarChart } from "recharts";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";

const serviceConfig = {
  health: {
    label: "Health",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

interface ServiceHealth {
  status: "up" | "down" | "degraded" | "polling" | "disabled";
  paused?: boolean | null;
}

function serviceScore(svc: ServiceHealth): number {
  if (svc.paused) return 0.3;
  switch (svc.status) {
    case "up":       return 1;
    case "polling":  return 0.7;
    case "degraded": return 0.4;
    case "disabled": return 0.2;
    case "down":     return 0;
    default:         return 0;
  }
}

const SERVICE_LABELS: Record<string, string> = {
  postgres: "PG", pgvector: "PGV", neo4j: "Neo4j",
  redis: "Redis", deepface_server: "DeepFace",
  hikvision: "RFID", aruba: "WiFi", go2rtc: "RTSP",
};

export default function AdminAnalyticsPage() {
  const [days, setDays] = useState("14");

  const { data: healthData } = useQuery<{
    services: Record<string, ServiceHealth>;
  }>({
    queryKey: ["admin-system-health"],
    queryFn: () => apiClient.getSystemHealth(),
    staleTime: 30_000,
  });

  const radarData = healthData
    ? Object.entries(healthData.services).map(([key, svc]) => ({
        service: SERVICE_LABELS[key] ?? key,
        health: serviceScore(svc),
      }))
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Analytics</h2>
          <p className="text-sm text-muted-foreground mt-1">Platform-wide metrics and trends.</p>
        </div>
        <Select value={days} onValueChange={setDays}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="14">Last 14 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <AlertsTrendChart days={Number(days)} />
        <UserGrowthChart days={Number(days)} />
        <OrgActivityChart />

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Service Health Radar</CardTitle>
            <CardDescription>Health score per service (1 = up, 0 = down)</CardDescription>
          </CardHeader>
          <CardContent>
            {radarData.length === 0 ? (
              <div className="h-[200px] animate-pulse rounded bg-muted" />
            ) : (
              <ChartContainer config={serviceConfig} className="mx-auto aspect-square max-h-[220px]">
                <RadarChart data={radarData}>
                  <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                  <PolarAngleAxis dataKey="service" tick={{ fontSize: 10 }} />
                  <PolarGrid strokeDasharray="3 3" />
                  <Radar
                    dataKey="health"
                    stroke="var(--color-health)"
                    fill="var(--color-health)"
                    fillOpacity={0.2}
                  />
                </RadarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
