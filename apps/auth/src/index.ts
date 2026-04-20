import "./instrument";
import * as Sentry from "@sentry/node";
import express from "express";
import cors from "cors";
import { toNodeHandler } from "better-auth/node";
import { auth, refreshSSOProviderIds } from "./auth";
import { prisma } from "@fazri/db";

const app = express();
const PORT = parseInt(process.env.PORT ?? "4000", 10);

const allowedOrigins = (process.env.TRUSTED_ORIGINS ?? "http://localhost:3000").split(",");

app.use(
  cors({
    origin: allowedOrigins,
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

app.listen(PORT, () => {
  console.log(`Auth service running on port ${PORT}`);
});
