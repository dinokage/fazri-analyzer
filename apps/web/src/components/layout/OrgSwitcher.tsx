"use client";

import { useRouter } from "next/navigation";
import { authClient } from "@/lib/auth-client";
import { useOrg } from "@/lib/org-context";
import { invalidateTokenCache } from "@/lib/api-client";
import { Building2, ChevronsUpDown, Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function OrgSwitcher() {
  const router = useRouter();
  const { organizationId, organizationSlug, isLoaded } = useOrg();
  const { data: orgs } = authClient.useListOrganizations();

  const currentOrg = orgs?.find((o) => o.id === organizationId);
  const hasMultipleOrgs = orgs && orgs.length > 1;

  const switchOrg = async (orgId: string) => {
    if (orgId === organizationId) return;
    await authClient.organization.setActive({ organizationId: orgId });
    invalidateTokenCache();
    router.refresh();
  };

  if (!isLoaded) {
    return <div className="h-9 w-full animate-pulse rounded-md bg-sidebar-accent/50" />;
  }

  if (!hasMultipleOrgs) {
    return (
      <div className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-sidebar-foreground">
        <Building2 className="h-4 w-4 shrink-0 text-sidebar-foreground/60" />
        <span className="truncate font-medium">
          {currentOrg?.name ?? organizationSlug ?? "No organization"}
        </span>
      </div>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
          <Building2 className="h-4 w-4 shrink-0 text-sidebar-foreground/60" />
          <span className="truncate font-medium flex-1 text-left">
            {currentOrg?.name ?? organizationSlug ?? "Select organization"}
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-sidebar-foreground/40" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {orgs.map((org) => (
          <DropdownMenuItem
            key={org.id}
            onSelect={() => switchOrg(org.id)}
            className="flex items-center gap-2"
          >
            <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="flex-1 truncate">{org.name}</span>
            {org.id === organizationId && (
              <Check className="h-3.5 w-3.5 shrink-0 text-primary" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
