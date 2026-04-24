import { type NextRequest, NextResponse } from "next/server";

const AUTH_SERVICE_URL =
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:4000";

const BASE_DOMAIN = process.env.NEXT_PUBLIC_BASE_DOMAIN ?? "rayzrsole.com";

/**
 * Rewrite Set-Cookie headers for cross-domain tenants.
 *
 * For *.rayzrsole.com subdomains: keep cookies unchanged (Domain=.rayzrsole.com
 * gives shared session across org subdomains).
 *
 * For custom TLD domains (e.g. test-fazri.rdpdc.in): strip the Domain attribute
 * so the browser scopes the cookie to the current host — making it first-party
 * and bypassing Safari ITP / third-party cookie restrictions.
 */
function rewriteSetCookies(setCookies: string[], requestHost: string): string[] {
  const isBaseDomain =
    requestHost === BASE_DOMAIN || requestHost.endsWith(`.${BASE_DOMAIN}`);

  if (isBaseDomain) return setCookies;

  return setCookies.map((cookie) =>
    cookie
      .replace(/;\s*Domain=[^;]+/gi, "")
      .replace(/;\s*SameSite=None/gi, "; SameSite=Lax")
  );
}

async function handler(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const search = request.nextUrl.search;
  const targetUrl = `${AUTH_SERVICE_URL}/api/auth/${path.join("/")}${search}`;

  const headers = new Headers(request.headers);
  // Tell the auth service the real public-facing host so it can derive base URL and cookies
  headers.set("x-forwarded-host", request.nextUrl.hostname);
  headers.set("x-forwarded-proto", request.nextUrl.protocol.replace(":", ""));
  headers.delete("host");

  let body: BodyInit | null = null;
  if (request.method !== "GET" && request.method !== "HEAD") {
    body = await request.blob();
  }

  const upstream = await fetch(targetUrl, {
    method: request.method,
    headers,
    body,
    redirect: "manual",
  });

  const responseHeaders = new Headers(upstream.headers);

  // Rewrite Set-Cookie for custom TLD domains
  const setCookies = upstream.headers.getSetCookie?.() ?? [];
  if (setCookies.length > 0) {
    const rewritten = rewriteSetCookies(setCookies, request.nextUrl.hostname);
    responseHeaders.delete("set-cookie");
    for (const c of rewritten) {
      responseHeaders.append("set-cookie", c);
    }
  }

  // Forward redirects (e.g. OAuth callbacks) as-is
  if (upstream.status >= 300 && upstream.status < 400) {
    return NextResponse.redirect(upstream.headers.get("location") ?? "/", {
      status: upstream.status,
      headers: responseHeaders,
    });
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const OPTIONS = handler;
