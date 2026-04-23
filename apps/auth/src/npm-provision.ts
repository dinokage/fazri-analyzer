import { NpmClient, NpmApiError } from "@fazri/npm-sdk";

const FRONTEND_HOST = process.env.FRONTEND_HOST ?? "frontend";
const FRONTEND_PORT = parseInt(process.env.FRONTEND_PORT ?? "3000", 10);

function createNpmClient(): NpmClient {
  const baseUrl = process.env.NPM_API_URL;
  if (!baseUrl) throw new Error("NPM_API_URL is not set");

  const token = process.env.NPM_API_TOKEN;
  if (token) return new NpmClient({ baseUrl, token });

  const email = process.env.NPM_EMAIL;
  const password = process.env.NPM_PASSWORD;
  if (email && password) return new NpmClient({ baseUrl, email, password });

  throw new Error("NPM auth not configured: set NPM_API_TOKEN or NPM_EMAIL + NPM_PASSWORD");
}

function describeTestHttpResult(result: string | undefined): string {
  if (!result) return "unknown error";
  if (result.startsWith("other:")) return "NPM internal error — domain may be behind a proxy or NPM cannot reach it";
  if (result === "404") return "domain reached the server but returned 404 — likely behind Cloudflare proxy or another reverse proxy intercepting the request";
  if (result === "no-host") return "domain does not resolve to this server — check your A record";
  if (result === "failed") return "HTTP-01 challenge check failed — ensure port 80 is open and not blocked by firewall";
  if (result === "wrong-data") return "HTTP-01 challenge returned unexpected data";
  return result;
}

const PROXY_HOST_DEFAULTS = {
  forward_scheme: "http" as const,
  forward_host: FRONTEND_HOST,
  forward_port: FRONTEND_PORT,
  ssl_forced: true,
  http2_support: true,
  hsts_enabled: true,
  hsts_subdomains: true,
  trust_forwarded_proto: true,
  caching_enabled: true,
  block_exploits: true,
  allow_websocket_upgrade: true,
  enabled: true,
};

export async function provisionCustomDomain(domain: string, orgName: string): Promise<{ hostId: number }> {
  if (!process.env.NPM_API_URL) {
    console.warn(`[npm-provision] NPM_API_URL not set — skipping provisioning for ${domain}`);
    return { hostId: 0 };
  }

  const client = createNpmClient();

  // Pre-flight: verify the A record is pointing here before requesting the LE cert
  const test = await client.certificates.testHttp([domain]);
  if (test[domain] !== "ok") {
    throw new Error(`[npm-provision] HTTP-01 pre-flight failed for ${domain}: ${describeTestHttpResult(test[domain])}`);
  }

  const host = await client.proxyHosts.create({
    domain_names: [domain],
    ...PROXY_HOST_DEFAULTS,
    certificate_id: "new",
    meta: { orgName },
  });

  console.log(`[npm-provision] ${domain} (${orgName}) → proxy host id=${host.id}, cert id=${host.certificate_id}`);
  return { hostId: host.id };
}

export async function reprovisionCustomDomain(
  domain: string,
  orgName: string,
  existingHostId: number | null,
): Promise<{ hostId: number }> {
  if (!process.env.NPM_API_URL) {
    console.warn(`[npm-provision] NPM_API_URL not set — skipping re-provisioning for ${domain}`);
    return { hostId: 0 };
  }

  const client = createNpmClient();

  // Pre-flight check
  const test = await client.certificates.testHttp([domain]);
  if (test[domain] !== "ok") {
    throw new Error(`[npm-provision] HTTP-01 pre-flight failed for ${domain}: ${describeTestHttpResult(test[domain])}`);
  }

  // If we have an existing host ID, try to update it to re-trigger LE cert
  if (existingHostId) {
    try {
      await client.proxyHosts.get(existingHostId);
      const updated = await client.proxyHosts.update(existingHostId, {
        ...PROXY_HOST_DEFAULTS,
        certificate_id: "new",
        meta: { orgName },
      });
      console.log(`[npm-provision] re-provisioned ${domain} via update (host id=${updated.id})`);
      return { hostId: updated.id };
    } catch (err) {
      if (err instanceof NpmApiError && err.statusCode === 404) {
        console.warn(`[npm-provision] host id=${existingHostId} not found in NPM — will create new`);
      } else {
        throw err;
      }
    }
  }

  // Create new proxy host
  const host = await client.proxyHosts.create({
    domain_names: [domain],
    ...PROXY_HOST_DEFAULTS,
    certificate_id: "new",
    meta: { orgName },
  });

  console.log(`[npm-provision] ${domain} (${orgName}) → new proxy host id=${host.id}`);
  return { hostId: host.id };
}

export async function deprovisionCustomDomain(domain: string, hostId?: number | null): Promise<void> {
  if (!process.env.NPM_API_URL) return;

  const client = createNpmClient();

  // Prefer deleting by known ID — avoids scanning all hosts and mis-targeting a freshly re-registered domain
  if (hostId) {
    try {
      await client.proxyHosts.delete(hostId);
      console.log(`[npm-provision] deleted proxy host id=${hostId} for ${domain}`);
      return;
    } catch (err) {
      if (err instanceof NpmApiError && err.statusCode === 404) {
        console.warn(`[npm-provision] proxy host id=${hostId} already gone for ${domain}`);
        return;
      }
      throw err;
    }
  }

  // Fallback: scan by domain name (used when hostId was never stored)
  const hosts = await client.proxyHosts.list();
  const existing = hosts.find((h) => h.domain_names.includes(domain));
  if (!existing) {
    console.warn(`[npm-provision] no proxy host found for ${domain} — skipping deprovision`);
    return;
  }
  await client.proxyHosts.delete(existing.id);
  console.log(`[npm-provision] deleted proxy host id=${existing.id} for ${domain}`);
}

const NPM_SETTINGS = {
  ssl_forced: true,
  http2_support: true,
  hsts_enabled: true,
  hsts_subdomains: true,
  trust_forwarded_proto: true,
  caching_enabled: true,
  block_exploits: true,
  allow_websocket_upgrade: true,
} as const;

export async function syncNpmSettings(domain: string): Promise<{ id: number }> {
  const client = createNpmClient();
  const hosts = await client.proxyHosts.list();
  const existing = hosts.find((h) => h.domain_names.includes(domain));
  if (!existing) throw new Error(`[npm-provision] No proxy host found for ${domain}`);
  await client.proxyHosts.update(existing.id, NPM_SETTINGS);
  console.log(`[npm-provision] synced settings for ${domain} (host id=${existing.id})`);
  return { id: existing.id };
}

export { NpmApiError };
