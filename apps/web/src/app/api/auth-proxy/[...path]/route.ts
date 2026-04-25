import { type NextRequest, NextResponse } from "next/server";

const AUTH_SERVICE_URL =
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:4000";

/**
 * Proxy for auth-service custom management endpoints
 * (sso-providers, domain, org, etc.) that require the session cookie.
 *
 * The session cookie is first-party on the frontend domain (set via the
 * /api/auth/* proxy). Direct browser fetches to the auth-service domain
 * are cross-origin and won't include it. This proxy keeps the request
 * same-origin so the browser sends the cookie, then forwards it
 * server-side to the auth service.
 *
 * Maps:  /api/auth-proxy/<rest>  →  AUTH_SERVICE_URL/api/<rest>
 */
async function handler(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const search = request.nextUrl.search;
  const targetUrl = `${AUTH_SERVICE_URL}/${path.join("/")}${search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");

  let body: BodyInit | null = null;
  if (request.method !== "GET" && request.method !== "HEAD") {
    body = await request.blob();
  }

  const upstream = await fetch(targetUrl, {
    method: request.method,
    headers,
    body,
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: upstream.headers,
  });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const OPTIONS = handler;
