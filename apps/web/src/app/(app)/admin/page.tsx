"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { authClient } from "@/lib/auth-client";
import { Building2, Users, ShieldCheck } from "lucide-react";

export default function AdminPage() {
  const { data: orgs } = authClient.useListOrganizations();

  const { data: usersData } = useQuery({
    queryKey: ["admin-users-count"],
    queryFn: async () => {
      const { data } = await authClient.admin.listUsers({ query: { limit: 1 } });
      return data;
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Admin Console</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Manage organizations, users, and platform settings.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Link
          href="/admin/orgs"
          className="rounded-xl border bg-card p-5 hover:bg-accent/50 transition-colors"
        >
          <Building2 className="h-6 w-6 text-muted-foreground mb-3" />
          <p className="text-2xl font-bold">{orgs?.length ?? "—"}</p>
          <p className="text-sm text-muted-foreground mt-0.5">Organizations</p>
        </Link>

        <Link
          href="/admin/users"
          className="rounded-xl border bg-card p-5 hover:bg-accent/50 transition-colors"
        >
          <Users className="h-6 w-6 text-muted-foreground mb-3" />
          <p className="text-2xl font-bold">{usersData?.total ?? "—"}</p>
          <p className="text-sm text-muted-foreground mt-0.5">Total Users</p>
        </Link>

        <div className="rounded-xl border bg-card p-5">
          <ShieldCheck className="h-6 w-6 text-muted-foreground mb-3" />
          <p className="text-2xl font-bold">Active</p>
          <p className="text-sm text-muted-foreground mt-0.5">Platform Status</p>
        </div>
      </div>
    </div>
  );
}
