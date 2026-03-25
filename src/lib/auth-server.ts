/**
 * Server-side auth helper for Next.js Server Components.
 * Calls the auth microservice to verify the session cookie.
 */

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
};

export type FazriSession = {
  user: FazriUser;
  session: {
    id: string;
    token: string;
    expiresAt: string;
    userId: string;
  };
};

const AUTH_INTERNAL_URL =
  process.env.AUTH_SERVICE_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ??
  "http://localhost:4000";

export async function getAuthToken(headers: Headers): Promise<string | null> {
  try {
    const response = await fetch(
      `${AUTH_INTERNAL_URL}/api/auth/token`,
      {
        headers: {
          cookie: headers.get("cookie") ?? "",
        },
        cache: "no-store",
      }
    );
    if (!response.ok) return null;
    const data = await response.json();
    return data?.token ?? null;
  } catch {
    return null;
  }
}

export async function getAuthSession(
  headers: Headers
): Promise<FazriSession | null> {
  try {
    const response = await fetch(
      `${AUTH_INTERNAL_URL}/api/auth/get-session`,
      {
        headers: {
          cookie: headers.get("cookie") ?? "",
        },
        cache: "no-store",
      }
    );
    if (!response.ok) return null;
    const data = await response.json();
    if (!data?.user) return null;
    return data as FazriSession;
  } catch {
    return null;
  }
}
