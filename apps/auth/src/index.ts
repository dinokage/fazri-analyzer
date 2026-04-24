import "./instrument";
import * as Sentry from "@sentry/node";
import express from "express";
import cors from "cors";
import { promises as dns, setServers as dnsSetServers } from "dns";
import net from "net";
import { toNodeHandler } from "better-auth/node";
import { auth, refreshSSOProviderIds } from "./auth";
import { prisma } from "@fazri/db";
import { initTrustedOrigins, addOrigin, removeOrigin, isOriginAllowed } from "./trusted-origins-cache";
import { provisionCustomDomain, reprovisionCustomDomain, deprovisionCustomDomain, syncNpmSettings, createNpmClient, type NpmProvisionConfig } from "./npm-provision";

// Process-global DNS override — affects all dns.resolve* calls but NOT dns.lookup / libuv getaddrinfo.
// Forces Cloudflare resolvers to avoid split-horizon or ISP caching issues.
dnsSetServers(["1.1.1.1", "1.0.0.1"]);

async function getSystemSetting(key: string, fallback: string): Promise<string> {
  const row = await prisma.systemSetting.findUnique({ where: { key } });
  return row?.value ?? process.env[key] ?? fallback;
}

async function getNpmProvisionConfig(): Promise<NpmProvisionConfig> {
  const [frontendHost, frontendPortStr] = await Promise.all([
    getSystemSetting("FRONTEND_HOST", process.env.FRONTEND_HOST ?? "frontend"),
    getSystemSetting("FRONTEND_PORT", process.env.FRONTEND_PORT ?? "3000"),
  ]);
  return { frontendHost, frontendPort: parseInt(frontendPortStr, 10) };
}

// Cloudflare published IPv4 CIDRs — used to detect domains behind CF proxy
const CLOUDFLARE_CIDRS = [
  "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
  "104.16.0.0/13", "104.24.0.0/14", "108.162.192.0/18",
  "131.0.72.0/22", "141.101.64.0/18", "162.158.0.0/15",
  "172.64.0.0/13", "173.245.48.0/20", "188.114.96.0/20",
  "190.93.240.0/20", "197.234.240.0/22", "198.41.128.0/17",
];

function ipInCidr(ip: string, cidr: string): boolean {
  const [range, bits] = cidr.split("/");
  const mask = ~(2 ** (32 - parseInt(bits, 10)) - 1) >>> 0;
  const ipInt = ip.split(".").reduce((acc, oct) => (acc << 8) + parseInt(oct, 10), 0) >>> 0;
  const rangeInt = range.split(".").reduce((acc, oct) => (acc << 8) + parseInt(oct, 10), 0) >>> 0;
  return (ipInt & mask) === (rangeInt & mask);
}

function isCloudflareIp(ip: string): boolean {
  if (!net.isIPv4(ip)) return false;
  return CLOUDFLARE_CIDRS.some((cidr) => ipInCidr(ip, cidr));
}

const app = express();
const PORT = parseInt(process.env.PORT ?? "4000", 10);

app.use(
  cors({
    origin: (requestOrigin, callback) => {
      const allowed = isOriginAllowed(requestOrigin);
      callback(allowed ? null : new Error("CORS: origin not allowed"), allowed);
    },
    credentials: true,
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization", "Cookie"],
  })
);

// Mount better-auth — must come before express.json() for the auth routes
app.all("/api/auth/*", toNodeHandler(auth));

app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.post("/api/add-org-member", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session || (session.user as Record<string, unknown>).role !== "SUPER_ADMIN") {
      res.status(403).json({ error: "Forbidden" });
      return;
    }
    const { userId, organizationId, role } = req.body as {
      userId: string;
      organizationId: string;
      role: string;
    };
    if (!userId || !organizationId || !role) {
      res.status(400).json({ error: "Missing required fields" });
      return;
    }
    const existing = await prisma.member.findFirst({ where: { userId, organizationId } });
    if (existing) {
      res.status(400).json({ error: "User is already a member of this organization" });
      return;
    }
    const member = await prisma.member.create({
      data: { id: crypto.randomUUID(), userId, organizationId, role, createdAt: new Date() },
    });
    res.json({ member });
  } catch (err) {
    console.error("add-org-member error:", err);
    res.status(500).json({ error: "Failed to add member" });
  }
});

app.get("/api/sso-providers/:organizationId", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const { organizationId } = req.params;
    const isSuperAdmin = (session.user as Record<string, unknown>).role === "SUPER_ADMIN";
    const isOwner = isSuperAdmin || !!(await prisma.member.findFirst({
      where: { userId: session.user.id, organizationId, role: "owner" },
    }));
    if (!isOwner) { res.status(403).json({ error: "Forbidden" }); return; }

    const providers = await prisma.ssoProvider.findMany({
      where: { organizationId },
      select: { id: true, providerId: true, issuer: true, domain: true, oidcConfig: true, samlConfig: true },
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result = providers.map((p: any) => ({
      id: p.id,
      providerId: p.providerId,
      issuer: p.issuer,
      domain: p.domain,
      type: p.samlConfig ? "saml" : "oidc",
      createdAt: p.createdAt,
      updatedAt: p.updatedAt,
    }));
    res.json(result);
  } catch (err) {
    console.error("sso-providers GET error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.post("/api/sso-providers/link", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const { providerId, organizationId } = req.body as { providerId: string; organizationId: string };
    if (!providerId || !organizationId) { res.status(400).json({ error: "providerId and organizationId required" }); return; }

    const isSuperAdmin = (session.user as Record<string, unknown>).role === "SUPER_ADMIN";
    const isOwner = isSuperAdmin || !!(await prisma.member.findFirst({
      where: { userId: session.user.id, organizationId, role: "owner" },
    }));
    if (!isOwner) { res.status(403).json({ error: "Forbidden" }); return; }

    const provider = await prisma.ssoProvider.findUnique({ where: { providerId } });
    if (!provider) { res.status(404).json({ error: "Provider not found" }); return; }

    await prisma.ssoProvider.update({ where: { providerId }, data: { organizationId } });
    refreshSSOProviderIds();
    res.json({ success: true });
  } catch (err) {
    console.error("sso-providers link error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.delete("/api/sso-providers/:providerId", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const { providerId } = req.params;
    const provider = await prisma.ssoProvider.findUnique({ where: { providerId } });
    if (!provider) { res.status(404).json({ error: "Provider not found" }); return; }

    const isSuperAdmin = (session.user as Record<string, unknown>).role === "SUPER_ADMIN";
    if (provider.organizationId) {
      const isOwner = isSuperAdmin || !!(await prisma.member.findFirst({
        where: { userId: session.user.id, organizationId: provider.organizationId, role: "owner" },
      }));
      if (!isOwner) { res.status(403).json({ error: "Forbidden" }); return; }
    } else if (!isSuperAdmin && provider.userId !== session.user.id) {
      res.status(403).json({ error: "Forbidden" }); return;
    }

    await prisma.ssoProvider.delete({ where: { providerId } });
    refreshSSOProviderIds();
    res.json({ success: true });
  } catch (err) {
    console.error("sso-providers DELETE error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// ─── Org resolution (used by Next.js middleware — no auth required) ──────────

app.get("/api/org/resolve", async (req, res) => {
  const raw = req.query.hostname;
  const hostname = (Array.isArray(raw) ? raw[0] : raw) ?? "";
  if (!hostname || typeof hostname !== "string") {
    res.status(400).json({ error: "hostname required" });
    return;
  }

  try {
    const baseDomain = process.env.FAZRI_BASE_DOMAIN ?? "rayzrsole.com";

    if (hostname.endsWith(`.${baseDomain}`)) {
      const slug = hostname.slice(0, -(`.${baseDomain}`.length));
      if (!slug || slug.includes(".")) {
        res.status(404).json({ error: "Not found" });
        return;
      }
      const org = await prisma.organization.findUnique({ where: { slug } });
      if (!org) { res.status(404).json({ error: "Organization not found" }); return; }
      res.json({ organizationId: org.id, slug: org.slug });
      return;
    }

    const orgDomain = await prisma.organizationDomain.findUnique({
      where: { domain: hostname, verified: true },
      include: { organization: true },
    });
    if (!orgDomain) { res.status(404).json({ error: "Domain not registered" }); return; }
    res.json({
      organizationId: orgDomain.organizationId,
      slug: orgDomain.organization.slug,
    });
  } catch (err) {
    console.error("org-resolve error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// ─── Custom domain management ─────────────────────────────────────────────────

async function assertOrgAccess(session: NonNullable<Awaited<ReturnType<typeof auth.api.getSession>>>, organizationId: string): Promise<boolean> {
  if ((session.user as Record<string, unknown>).role === "SUPER_ADMIN") return true;
  const membership = await prisma.member.findFirst({
    where: { userId: session.user.id, organizationId, role: { in: ["owner", "admin"] } },
  });
  return !!membership;
}

app.post("/api/domain/register", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const { organizationId, domain } = req.body as { organizationId: string; domain: string };
    if (!organizationId || !domain) {
      res.status(400).json({ error: "organizationId and domain required" });
      return;
    }

    const hasAccess = await assertOrgAccess(session, organizationId);
    if (!hasAccess) { res.status(403).json({ error: "Forbidden" }); return; }

    const existing = await prisma.organizationDomain.findUnique({ where: { domain } });
    if (existing) {
      res.status(409).json({ error: "Domain already registered" });
      return;
    }

    const record = await prisma.organizationDomain.create({
      data: { organizationId, domain },
    });

    res.json({
      id: record.id,
      domain: record.domain,
      verificationToken: record.verificationToken,
      ownershipVerified: record.ownershipVerified,
      verified: record.verified,
      // Only TXT record shown at registration — CNAME is shown after ownership is verified
      txtRecord: {
        name: `_fazri-verify.${domain}`,
        value: `fazri-verify=${record.verificationToken}`,
      },
    });
  } catch (err) {
    console.error("domain-register error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// Step 1 — verify domain ownership via TXT record
app.post("/api/domain/verify", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const { domain } = req.body as { domain: string };
    if (!domain) { res.status(400).json({ error: "domain required" }); return; }

    const record = await prisma.organizationDomain.findUnique({ where: { domain } });
    if (!record) { res.status(404).json({ error: "Domain not registered" }); return; }

    const hasAccess = await assertOrgAccess(session, record.organizationId);
    if (!hasAccess) { res.status(403).json({ error: "Forbidden" }); return; }

    if (record.ownershipVerified) {
      const cnameTarget = `app.${process.env.FAZRI_BASE_DOMAIN ?? "rayzrsole.com"}`;
      res.json({ ownershipVerified: true, message: "Ownership already verified", cnameRecord: { name: domain.split(".")[0], value: cnameTarget } });
      return;
    }

    const txtName = `_fazri-verify.${domain}`;
    const expectedValue = `fazri-verify=${record.verificationToken}`;
    let passed = false;

    try {
      const records = await dns.resolveTxt(txtName);
      passed = records.some((r) => r.join("") === expectedValue);
    } catch {
      // DNS lookup failed
    }

    if (!passed) {
      res.status(422).json({
        ownershipVerified: false,
        error: "TXT record not found or incorrect",
        expected: { name: txtName, value: expectedValue },
      });
      return;
    }

    await prisma.organizationDomain.update({
      where: { domain },
      data: { ownershipVerified: true, ownershipVerifiedAt: new Date() },
    });

    const cnameTarget = `app.${process.env.FAZRI_BASE_DOMAIN ?? "rayzrsole.com"}`;
    res.json({
      ownershipVerified: true,
      message: "Ownership verified — now point your domain",
      cnameRecord: {
        name: domain.split(".")[0],
        value: cnameTarget,
      },
    });
  } catch (err) {
    console.error("domain-verify error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// DNS check — verifies A record resolves to this server (polled by frontend before Activate)
const dnsCheckLastCalled = new Map<string, number>();
const DNS_CHECK_COOLDOWN_MS = 10_000;

app.get("/api/domain/check-dns", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const domain = req.query.domain as string;
    if (!domain) { res.status(400).json({ error: "domain query param required" }); return; }

    const record = await prisma.organizationDomain.findUnique({ where: { domain } });
    if (!record) { res.status(404).json({ error: "Domain not registered" }); return; }

    const hasAccess = await assertOrgAccess(session, record.organizationId);
    if (!hasAccess) { res.status(403).json({ error: "Forbidden" }); return; }

    const last = dnsCheckLastCalled.get(domain) ?? 0;
    if (Date.now() - last < DNS_CHECK_COOLDOWN_MS) {
      res.status(429).json({ error: "Checked too recently — wait a moment" });
      return;
    }
    dnsCheckLastCalled.set(domain, Date.now());

    const serverIp = process.env.FAZRI_SERVER_IP ?? "";
    if (!serverIp) {
      res.json({ status: "config-error", resolvedIps: [], expectedIp: "" });
      return;
    }

    let resolvedIps: string[] = [];
    try {
      resolvedIps = await dns.resolve4(domain);
    } catch {
      res.json({ status: "not-propagated", resolvedIps: [], expectedIp: serverIp });
      return;
    }

    if (resolvedIps.some(isCloudflareIp)) {
      res.json({
        status: "cloudflare-proxy",
        resolvedIps,
        expectedIp: serverIp,
        warning: "Domain is behind Cloudflare proxy. Disable the orange cloud for this record — HTTP-01 certificate challenge requires direct reachability.",
      });
      return;
    }

    if (resolvedIps.includes(serverIp)) {
      res.json({ status: "ok", resolvedIps, expectedIp: serverIp });
    } else {
      res.json({ status: "wrong-ip", resolvedIps, expectedIp: serverIp });
    }
  } catch (err) {
    console.error("domain-check-dns error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// Step 2 — activate: check CNAME reachability + provision SSL via NPM
app.post("/api/domain/activate", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const { domain } = req.body as { domain: string };
    if (!domain) { res.status(400).json({ error: "domain required" }); return; }

    const record = await prisma.organizationDomain.findUnique({
      where: { domain },
      include: { organization: true },
    });
    if (!record) { res.status(404).json({ error: "Domain not registered" }); return; }

    const hasAccess = await assertOrgAccess(session, record.organizationId);
    if (!hasAccess) { res.status(403).json({ error: "Forbidden" }); return; }

    if (!record.ownershipVerified) {
      res.status(422).json({ error: "Complete ownership verification before activating" });
      return;
    }

    if (record.verified) {
      res.json({ verified: true, message: "Domain already active" });
      return;
    }

    // DNS pre-check — hard gate, not optional
    const serverIp = process.env.FAZRI_SERVER_IP ?? "";
    if (!serverIp && process.env.NPM_API_URL) {
      res.status(500).json({
        error: "FAZRI_SERVER_IP is not set on the auth service. Add your server's public IP to the auth env and restart.",
      });
      return;
    }
    if (serverIp) {
      let addrs: string[];
      try {
        addrs = await dns.resolve4(domain);
      } catch {
        res.status(422).json({ error: "A record not found — add the DNS record and wait for propagation before activating" });
        return;
      }
      if (addrs.some(isCloudflareIp)) {
        res.status(422).json({
          error: "Domain is behind Cloudflare proxy (orange cloud). Disable proxy mode for this A record — Let's Encrypt HTTP-01 requires direct reachability.",
        });
        return;
      }
      if (!addrs.includes(serverIp)) {
        res.status(422).json({
          error: `A record not pointing to this server — resolved ${addrs.join(", ")}, expected ${serverIp}`,
        });
        return;
      }
    }

    // Atomic update — only proceeds if still not verified (guards concurrent requests)
    const { count } = await prisma.organizationDomain.updateMany({
      where: { domain, verified: false },
      data: { verified: true, verifiedAt: new Date(), sslStatus: "provisioning", sslProvisioningStartedAt: new Date() },
    });
    if (count === 0) {
      res.json({ verified: true, message: "Domain already active" });
      return;
    }

    // Immediately allow CORS from this domain (Redis + local Set)
    void addOrigin(domain);

    // Tracked async — updates sslStatus in DB on both success and failure
    void (async () => {
      try {
        const npmCfg = await getNpmProvisionConfig();
        const { hostId } = await provisionCustomDomain(domain, record.organization.name, npmCfg);
        await prisma.organizationDomain.update({
          where: { domain },
          data: { sslStatus: "active", npmProxyHostId: hostId, sslError: null },
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error("[domain-activate] SSL provisioning failed for domain:", domain, msg);
        await prisma.organizationDomain.update({
          where: { domain },
          data: { sslStatus: "failed", sslError: msg },
        }).catch(console.error);
      }
    })();

    res.json({ verified: true, message: "Domain activated — SSL certificate provisioning started" });
  } catch (err) {
    console.error("domain-activate error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.get("/api/domain/:organizationId", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const { organizationId } = req.params;
    const hasAccess = await assertOrgAccess(session, organizationId);
    if (!hasAccess) { res.status(403).json({ error: "Forbidden" }); return; }

    const domains = await prisma.organizationDomain.findMany({
      where: { organizationId },
      orderBy: { createdAt: "desc" },
      select: {
        id: true, domain: true, ownershipVerified: true, ownershipVerifiedAt: true,
        verified: true, verifiedAt: true, verificationToken: true, createdAt: true,
        sslStatus: true, sslProvisioningStartedAt: true, sslError: true, npmProxyHostId: true,
      },
    });

    // Heal stale provisioning: if stuck >20 min, mark as failed
    const staleThreshold = new Date(Date.now() - 20 * 60 * 1000);
    const stale = domains.filter(
      (d) => d.sslStatus === "provisioning" && d.sslProvisioningStartedAt && d.sslProvisioningStartedAt < staleThreshold
    );
    if (stale.length > 0) {
      await Promise.all(
        stale.map((d) =>
          prisma.organizationDomain.update({
            where: { id: d.id },
            data: { sslStatus: "failed", sslError: "Provisioning timed out (service may have restarted)" },
          })
        )
      );
      for (const d of stale) {
        d.sslStatus = "failed";
        d.sslError = "Provisioning timed out (service may have restarted)";
      }
    }

    res.json(domains);
  } catch (err) {
    console.error("domain-list error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.post("/api/domain/:id/retry-ssl", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const record = await prisma.organizationDomain.findUnique({
      where: { id: req.params.id },
      include: { organization: true },
    });
    if (!record) { res.status(404).json({ error: "Not found" }); return; }
    if (!record.verified || record.sslStatus !== "failed") {
      res.status(422).json({ error: "Domain must be active with a failed SSL status to retry" });
      return;
    }

    const hasAccess = await assertOrgAccess(session, record.organizationId);
    if (!hasAccess) { res.status(403).json({ error: "Forbidden" }); return; }

    if (record.sslError && /too many certificates|rateLimited/i.test(record.sslError)) {
      res.status(429).json({ rateLimited: true, error: "Let's Encrypt rate limited (5 certs/domain/week). Wait before retrying." });
      return;
    }

    await prisma.organizationDomain.update({
      where: { id: record.id },
      data: { sslStatus: "provisioning", sslProvisioningStartedAt: new Date(), sslError: null },
    });

    res.status(202).json({ message: "SSL retry started" });

    // Tracked async provisioning
    void (async () => {
      try {
        const npmCfg = await getNpmProvisionConfig();
        const { hostId } = await reprovisionCustomDomain(record.domain, record.organization.name, record.npmProxyHostId, npmCfg);
        await prisma.organizationDomain.update({
          where: { id: record.id },
          data: { sslStatus: "active", npmProxyHostId: hostId, sslError: null },
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[retry-ssl] Re-provisioning failed for ${record.domain}:`, msg);
        await prisma.organizationDomain.update({
          where: { id: record.id },
          data: { sslStatus: "failed", sslError: msg },
        }).catch(console.error);
      }
    })();
  } catch (err) {
    console.error("domain-retry-ssl error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

const syncNpmLastCalled = new Map<string, number>();
const SYNC_NPM_COOLDOWN_MS = 60_000;

app.post("/api/domain/:id/sync-npm", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const record = await prisma.organizationDomain.findUnique({ where: { id: req.params.id } });
    if (!record) { res.status(404).json({ error: "Not found" }); return; }
    if (!record.verified) { res.status(422).json({ error: "Domain is not active yet" }); return; }

    const hasAccess = await assertOrgAccess(session, record.organizationId);
    if (!hasAccess) { res.status(403).json({ error: "Forbidden" }); return; }

    const lastCalled = syncNpmLastCalled.get(record.id) ?? 0;
    const secondsLeft = Math.ceil((SYNC_NPM_COOLDOWN_MS - (Date.now() - lastCalled)) / 1000);
    if (secondsLeft > 0) {
      res.status(429).json({ error: "Already synced recently - try again shortly" });
      return;
    }
    syncNpmLastCalled.set(record.id, Date.now());

    const result = await syncNpmSettings(record.domain, record.npmProxyHostId);
    res.json({ success: true, hostId: result.id });
  } catch (err) {
    console.error("domain-sync-npm error:", err);
    const msg = err instanceof Error ? err.message : "Internal server error";
    res.status(500).json({ error: msg });
  }
});

app.delete("/api/domain/:id", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session) { res.status(401).json({ error: "Unauthorized" }); return; }

    const record = await prisma.organizationDomain.findUnique({ where: { id: req.params.id } });
    if (!record) { res.status(404).json({ error: "Not found" }); return; }

    const hasAccess = await assertOrgAccess(session, record.organizationId);
    if (!hasAccess) { res.status(403).json({ error: "Forbidden" }); return; }

    const domainName = record.domain;
    const proxyHostId = record.npmProxyHostId;
    await prisma.organizationDomain.delete({ where: { id: req.params.id } });
    void removeOrigin(domainName);
    res.json({ success: true });

    // Clean up NPM proxy host by ID after responding — targeted delete avoids racing a re-register
    if (proxyHostId) {
      deprovisionCustomDomain(domainName, proxyHostId).catch((err) =>
        console.error(`[domain-delete] NPM cleanup failed for ${domainName}:`, err)
      );
    }
  } catch (err) {
    console.error("domain-delete error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// ─── System settings (SUPER_ADMIN only) ──────────────────────────────────────

app.get("/api/system/npm-config", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session || (session.user as Record<string, unknown>).role !== "SUPER_ADMIN") {
      res.status(403).json({ error: "Forbidden" });
      return;
    }

    const [hostRow, portRow] = await Promise.all([
      prisma.systemSetting.findUnique({ where: { key: "FRONTEND_HOST" } }),
      prisma.systemSetting.findUnique({ where: { key: "FRONTEND_PORT" } }),
    ]);

    res.json({
      frontendHost: hostRow?.value ?? process.env.FRONTEND_HOST ?? "frontend",
      frontendPort: parseInt(portRow?.value ?? process.env.FRONTEND_PORT ?? "3000", 10),
      updatedAt: hostRow?.updatedAt ?? portRow?.updatedAt ?? null,
    });
  } catch (err) {
    console.error("system/npm-config GET error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.put("/api/system/npm-config", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session || (session.user as Record<string, unknown>).role !== "SUPER_ADMIN") {
      res.status(403).json({ error: "Forbidden" });
      return;
    }

    const { frontendHost, frontendPort } = req.body as { frontendHost: string; frontendPort: number };
    if (!frontendHost || typeof frontendHost !== "string" || !frontendHost.trim()) {
      res.status(400).json({ error: "frontendHost must be a non-empty string" });
      return;
    }
    const port = Number(frontendPort);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      res.status(400).json({ error: "frontendPort must be an integer between 1 and 65535" });
      return;
    }

    await Promise.all([
      prisma.systemSetting.upsert({
        where: { key: "FRONTEND_HOST" },
        create: { key: "FRONTEND_HOST", value: frontendHost.trim() },
        update: { value: frontendHost.trim() },
      }),
      prisma.systemSetting.upsert({
        where: { key: "FRONTEND_PORT" },
        create: { key: "FRONTEND_PORT", value: String(port) },
        update: { value: String(port) },
      }),
    ]);

    res.json({ frontendHost: frontendHost.trim(), frontendPort: port });
  } catch (err) {
    console.error("system/npm-config PUT error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.post("/api/system/npm-config/sync", async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: new Headers({ cookie: req.headers.cookie ?? "" }),
    });
    if (!session || (session.user as Record<string, unknown>).role !== "SUPER_ADMIN") {
      res.status(403).json({ error: "Forbidden" });
      return;
    }

    if (!process.env.NPM_API_URL) {
      res.status(422).json({ error: "NPM_API_URL is not configured — cannot sync proxy hosts" });
      return;
    }

    const cfg = await getNpmProvisionConfig();
    const [verifiedDomains, allNpmHosts] = await Promise.all([
      prisma.organizationDomain.findMany({
        where: { verified: true },
        select: { id: true, domain: true, npmProxyHostId: true },
      }),
      createNpmClient().proxyHosts.list(),
    ]);

    // Build a domain→npmHostId lookup from the live NPM list
    const npmHostByDomain = new Map<string, number>();
    for (const h of allNpmHosts) {
      for (const d of h.domain_names) {
        npmHostByDomain.set(d, h.id);
      }
    }

    const synced: string[] = [];
    const failed: { domain: string; error: string }[] = [];
    const client = createNpmClient();

    await Promise.allSettled(
      verifiedDomains.map(async (d) => {
        // Prefer stored ID; fall back to live domain-name lookup for pre-existing hosts
        const npmHostId = d.npmProxyHostId ?? npmHostByDomain.get(d.domain) ?? null;
        if (!npmHostId) {
          failed.push({ domain: d.domain, error: "No NPM proxy host found for this domain" });
          return;
        }
        try {
          await client.proxyHosts.update(npmHostId, {
            forward_host: cfg.frontendHost,
            forward_port: cfg.frontendPort,
          });
          synced.push(d.domain);
          // Backfill the ID if it was missing
          if (!d.npmProxyHostId) {
            await prisma.organizationDomain.update({
              where: { id: d.id },
              data: { npmProxyHostId: npmHostId },
            }).catch(() => { /* non-critical */ });
          }
        } catch (err) {
          failed.push({ domain: d.domain, error: err instanceof Error ? err.message : String(err) });
        }
      })
    );

    console.log(`[system/npm-config/sync] ${cfg.frontendHost}:${cfg.frontendPort} — synced ${synced.length}, failed ${failed.length}`);
    res.json({ synced: synced.length, failed });
  } catch (err) {
    console.error("system/npm-config/sync error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

app.post("/api/check-username", async (req, res) => {
  const { username } = req.body as { username: string };
  if (!username || typeof username !== "string") {
    res.status(400).json({ exists: false });
    return;
  }
  try {
    const user = await prisma.user.findFirst({
      where: { username: { equals: username.trim(), mode: "insensitive" } },
      select: { id: true },
    });
    res.json({ exists: !!user });
  } catch (err) {
    console.error("check-username db error:", err);
    res.status(500).json({ exists: false });
  }
});


Sentry.setupExpressErrorHandler(app);

initTrustedOrigins()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Auth service running on port ${PORT}`);
      if (!process.env.NPM_API_URL) {
        console.warn("[startup] NPM_API_URL not set — SSL auto-provisioning disabled. Domains will be marked active without certificate setup.");
      }
      if (process.env.NPM_API_URL && !process.env.FAZRI_SERVER_IP) {
        console.warn("[startup] NPM_API_URL is set but FAZRI_SERVER_IP is missing — DNS verification will be skipped and domain activation will be blocked. Set FAZRI_SERVER_IP to your server's public IP.");
      }
    });
  })
  .catch((err) => {
    console.error("[startup] Failed to initialize trusted origins cache:", err);
    app.listen(PORT, () => {
      console.log(`Auth service running on port ${PORT} (trusted origins degraded — static TRUSTED_ORIGINS env only)`);
    });
  });
