"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ServiceHealth {
  status: "up" | "down" | "degraded" | "polling" | "disabled";
  paused?: boolean | null;
}

interface SystemHealthData {
  status: "healthy" | "degraded" | "unhealthy";
  services: Record<string, ServiceHealth>;
}

const SERVICE_LABELS: Record<string, string> = {
  postgres: "PostgreSQL",
  pgvector: "pgvector",
  neo4j: "Neo4j",
  redis: "Redis",
  deepface_server: "DeepFace",
  hikvision: "Hikvision",
  aruba: "Aruba WiFi",
  go2rtc: "go2rtc",
};

function dotColor(svc: ServiceHealth): string {
  if (svc.paused) return "bg-orange-500";
  switch (svc.status) {
    case "up":       return "bg-green-500";
    case "polling":  return "bg-blue-500 animate-pulse";
    case "degraded": return "bg-yellow-500";
    case "disabled": return "bg-gray-400";
    case "down":     return "bg-red-500";
    default:         return "bg-gray-400";
  }
}

export function SystemHealthSummary() {
  const { data, isLoading } = useQuery<SystemHealthData>({
    queryKey: ["admin-system-health"],
    queryFn: () => apiClient.getSystemHealth(),
    staleTime: 30_000,
  });

  const overallColor =
    data?.status === "healthy"
      ? "text-green-500"
      : data?.status === "degraded"
      ? "text-yellow-500"
      : "text-red-500";

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          System Services
          {data && (
            <span className={`text-xs font-normal capitalize ${overallColor}`}>
              • {data.status}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex gap-2 flex-wrap">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-7 w-24 rounded-full bg-muted animate-pulse" />
            ))}
          </div>
        ) : !data ? (
          <p className="text-sm text-muted-foreground">Service unavailable</p>
        ) : (
          <div className="flex gap-2 flex-wrap">
            {Object.entries(data.services).map(([key, svc]) => (
              <div
                key={key}
                className="flex items-center gap-1.5 px-3 py-1 rounded-full border bg-muted/30 text-xs"
              >
                <span className={`h-2 w-2 rounded-full shrink-0 ${dotColor(svc)}`} />
                {SERVICE_LABELS[key] ?? key}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
