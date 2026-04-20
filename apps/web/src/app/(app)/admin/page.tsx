"use client";

import { useQuery } from "@tanstack/react-query";
import { authClient } from "@/lib/auth-client";
import { apiClient } from "@/lib/api-client";
import { Building2, Users, ShieldAlert, Cpu, AlertTriangle } from "lucide-react";
import { MetricCard } from "@/components/admin/MetricCard";
import { AlertsTrendChart } from "@/components/admin/AlertsTrendChart";
import { UserGrowthChart } from "@/components/admin/UserGrowthChart";
import { SystemHealthSummary } from "@/components/admin/SystemHealthSummary";
import { formatDistanceToNow } from "date-fns";

export default function AdminPage() {
  const { data: orgs } = authClient.useListOrganizations();

  const { data: usersData } = useQuery({
    queryKey: ["admin-users-count"],
    queryFn: async () => {
      const { data } = await authClient.admin.listUsers({ query: { limit: 1 } });
      return data;
    },
  });

  const { data: recentUsers } = useQuery({
    queryKey: ["admin-recent-users"],
    queryFn: async () => {
      const { data } = await authClient.admin.listUsers({
        query: { limit: 5, sortBy: "createdAt", sortDirection: "desc" },
      });
      return data?.users ?? [];
    },
    staleTime: 60_000,
  });

  const { data: alertsData } = useQuery({
    queryKey: ["admin-active-alerts"],
    queryFn: () => apiClient.getAlerts({ status: ["created", "assigned"], page_size: 1 }),
    staleTime: 30_000,
  });

  const { data: healthData } = useQuery<{ status: "healthy" | "degraded" | "unhealthy" }>({
    queryKey: ["admin-system-health"],
    queryFn: () => apiClient.getSystemHealth(),
    staleTime: 30_000,
  });

  const { data: anomalyData } = useQuery({
    queryKey: ["admin-anomaly-summary"],
    queryFn: () => apiClient.getAnomalySummary(),
    staleTime: 60_000,
  });

  const healthBadge =
    healthData?.status === "healthy"
      ? "Healthy"
      : healthData?.status === "degraded"
      ? "Degraded"
      : healthData
      ? "Unhealthy"
      : undefined;

  const healthBadgeColor =
    healthData?.status === "healthy"
      ? "bg-green-500/10 text-green-600 dark:text-green-400"
      : healthData?.status === "degraded"
      ? "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
      : "bg-red-500/10 text-red-600 dark:text-red-400";

  const recentOrgs = orgs?.slice(-3).reverse() ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Global Admin Console</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Platform-wide overview — organizations, users, and system health.
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <MetricCard
          icon={Users}
          label="Total Users"
          value={usersData?.total}
          href="/admin/users"
        />
        <MetricCard
          icon={Building2}
          label="Organizations"
          value={orgs?.length}
          href="/admin/orgs"
        />
        <MetricCard
          icon={ShieldAlert}
          label="Active Alerts"
          value={alertsData?.total ?? "—"}
          href="/dashboard/alerts"
        />
        <MetricCard
          icon={AlertTriangle}
          label="Anomalies"
          value={anomalyData?.total ?? "—"}
        />
        <MetricCard
          icon={Cpu}
          label="System Status"
          value={healthBadge ?? "—"}
          badge={healthBadge}
          badgeColor={healthBadgeColor}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <AlertsTrendChart />
        </div>
        <div className="lg:col-span-2">
          <UserGrowthChart />
        </div>
      </div>

      {/* System health */}
      <SystemHealthSummary />

      {/* Recent activity */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border bg-card p-5 space-y-3">
          <h3 className="text-sm font-medium">Recent Registrations</h3>
          {!recentUsers ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-8 animate-pulse rounded bg-muted" />
              ))}
            </div>
          ) : recentUsers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No users yet.</p>
          ) : (
            <ul className="space-y-2">
              {recentUsers.map((u) => (
                <li key={u.id} className="flex items-center justify-between text-sm">
                  <span className="font-medium truncate max-w-[180px]">{u.name}</span>
                  <span className="text-xs text-muted-foreground shrink-0 ml-2">
                    {formatDistanceToNow(new Date(u.createdAt), { addSuffix: true })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border bg-card p-5 space-y-3">
          <h3 className="text-sm font-medium">Recent Organizations</h3>
          {recentOrgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No organizations yet.</p>
          ) : (
            <ul className="space-y-2">
              {recentOrgs.map((org) => (
                <li key={org.id} className="flex items-center justify-between text-sm">
                  <span className="font-medium">{org.name}</span>
                  <span className="text-xs text-muted-foreground font-mono">/{org.slug}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
