import { NextRequest, NextResponse } from "next/server";

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:4000";
const ORG_COOKIE = "fazri-org-id";
const CACHE_TTL_MS = 5 * 60 * 1000;
const MAX_CACHE_ENTRIES = 500;

interface OrgResolution {
  organizationId: string;
  slug: string;
}

// In-memory cache for hostname → org. Persists for the edge worker lifetime (~minutes).
const hostnameCache = new Map<string, { data: OrgResolution; expiresAt: number }>();

async function resolveOrgFromHostname(hostname: string): Promise<OrgResolution | null> {
  const cached = hostnameCache.get(hostname);
  if (cached && cached.expiresAt > Date.now()) return cached.data;

  try {
    const res = await fetch(
      `${AUTH_SERVICE_URL}/api/org/resolve?hostname=${encodeURIComponent(hostname)}`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    const data = (await res.json()) as OrgResolution;

    // Evict oldest entry when at cap to keep the map bounded
    if (hostnameCache.size >= MAX_CACHE_ENTRIES) {
      const oldestKey = hostnameCache.keys().next().value;
      if (oldestKey) hostnameCache.delete(oldestKey);
    }
    hostnameCache.set(hostname, { data, expiresAt: Date.now() + CACHE_TTL_MS });
    return data;
  } catch {
    return null;
  }
}

export async function proxy(request: NextRequest) {
  const rawHostname =
    request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? "";

  // Strip port (e.g., localhost:3000 → localhost)
  const hostname = rawHostname.split(":")[0];

  const org = await resolveOrgFromHostname(hostname);

  const requestHeaders = new Headers(request.headers);
  if (org) {
    requestHeaders.set("x-org-id", org.organizationId);
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });

  if (org) {
    response.cookies.set(ORG_COOKIE, org.organizationId, {
      path: "/",
      sameSite: "lax",
      maxAge: 300, // 5 minutes — matches CACHE_TTL_MS
    });
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico|api/auth).*)"],
};
