"use client";

import { createContext, useContext } from "react";
import { useSession } from "@/lib/auth-client";

interface OrgContextValue {
  organizationId: string | null;
  organizationSlug: string | null;
  isLoaded: boolean;
}

const OrgCtx = createContext<OrgContextValue>({
  organizationId: null,
  organizationSlug: null,
  isLoaded: false,
});

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const { data: session, isPending } = useSession();
  const rawSession = session?.session as Record<string, unknown> | undefined;

  return (
    <OrgCtx.Provider
      value={{
        organizationId: (rawSession?.activeOrganizationId as string) ?? null,
        organizationSlug: null,
        isLoaded: !isPending,
      }}
    >
      {children}
    </OrgCtx.Provider>
  );
}

export const useOrg = () => useContext(OrgCtx);
