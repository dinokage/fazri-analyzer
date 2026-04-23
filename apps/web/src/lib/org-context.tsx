"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useSession } from "@/lib/auth-client";

const ORG_COOKIE = "fazri-org-id";

function readOrgCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${ORG_COOKIE}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}

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
  const [cookieOrgId, setCookieOrgId] = useState<string | null>(null);

  useEffect(() => {
    setCookieOrgId(readOrgCookie());
  }, []);

  const sessionOrgId = (rawSession?.activeOrganizationId as string) ?? null;

  return (
    <OrgCtx.Provider
      value={{
        // Session takes priority; fall back to hostname-resolved cookie (custom/sub domains)
        organizationId: sessionOrgId ?? cookieOrgId,
        organizationSlug: null,
        isLoaded: !isPending,
      }}
    >
      {children}
    </OrgCtx.Provider>
  );
}

export const useOrg = () => useContext(OrgCtx);
