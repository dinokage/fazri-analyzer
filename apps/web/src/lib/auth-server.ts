import { cache } from "react";

export type FazriUser = {
  id: string;
  name: string;
  email: string;
  image?: string | null;
  entity_id: string;
  username: string;
  role: "STUDENT" | "STAFF" | "FACULTY" | "SUPER_ADMIN";
  face_id?: string | null;
  student_id?: string | null;
  staff_id?: string | null;
  department?: string | null;
  card_id?: string | null;
  device_hash?: string | null;
  organizationId?: string | null;
  organizationSlug?: string | null;
};

export type FazriSession = {
  user: FazriUser;
  session: {
    id: string;
    token: string;
    expiresAt: string;
    userId: string;
    activeOrganizationId?: string | null;
  };
};

const AUTH_INTERNAL_URL =
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:4000";

export async function getAuthToken(headers: Headers): Promise<string | null> {
  try {
    let jwt: string | null = null;
    const res = await fetch(`${AUTH_INTERNAL_URL}/api/auth/get-session`, {
      headers: { cookie: headers.get("cookie") ?? "" },
      cache: "no-store",
    });
    if (res.ok) {
      jwt = res.headers.get("set-auth-jwt");
    }
    return jwt;
  } catch {
    return null;
  }
}

// cache() deduplicates calls within the same server render tree —
// multiple server components calling this share a single fetch.
export const getAuthSession = cache(async (incomingHeaders: Headers): Promise<FazriSession | null> => {
  try {
    const res = await fetch(`${AUTH_INTERNAL_URL}/api/auth/get-session`, {
      headers: { cookie: incomingHeaders.get("cookie") ?? "" },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (!data?.user) return null;
    return data as FazriSession;
  } catch {
    return null;
  }
});
