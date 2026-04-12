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

export function OrgProvider({
  children,
  orgSlug,
}: {
  children: React.ReactNode;
  orgSlug: string;
}) {
  const { data: session, isPending } = useSession();

  return (
    <OrgCtx.Provider
      value={{
        organizationId: (session?.user as any)?.organizationId ?? null,
        organizationSlug: orgSlug,
        isLoaded: !isPending,
      }}
    >
      {children}
    </OrgCtx.Provider>
  );
}

export const useOrg = () => useContext(OrgCtx);
