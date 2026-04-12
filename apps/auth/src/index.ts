import "./instrument";
import * as Sentry from "@sentry/node";
import express from "express";
import cors from "cors";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth";
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

// ── Org slug validation (unauthenticated — used by login step 1) ──────────
app.post("/api/check-org-slug", async (req, res) => {
  const { slug } = req.body as { slug: string };
  if (!slug?.trim()) {
    res.status(400).json({ error: "slug required" });
    return;
  }

  try {
    const org = await prisma.organization.findUnique({
      where: { slug: slug.trim().toLowerCase() },
      select: { name: true },
    });

    if (!org) {
      res.json({ exists: false, name: null });
      return;
    }

    // SECURITY: Do NOT return the internal org `id` to unauthenticated callers
    res.json({ exists: true, name: org.name });
  } catch (err) {
    console.error("check-org-slug db error:", err);
    res.status(500).json({ error: "internal error" });
  }
});

app.post("/api/check-username", async (req, res) => {
  const { username, organizationSlug } = req.body as {
    username: string;
    organizationSlug?: string;
  };
  if (!username || typeof username !== "string") {
    res.status(400).json({ exists: false });
    return;
  }
  try {
    const user = await prisma.user.findFirst({
      where: { username: { equals: username.trim(), mode: "insensitive" } },
      select: { id: true },
    });

    if (!user) {
      res.json({ exists: false });
      return;
    }

    // If org context provided, verify user is a member of that org
    if (organizationSlug) {
      const org = await prisma.organization.findUnique({
        where: { slug: organizationSlug.trim().toLowerCase() },
        select: { id: true },
      });
      if (org) {
        const membership = await prisma.member.findFirst({
          where: { userId: user.id, organizationId: org.id },
        });
        if (!membership) {
          // SECURITY: Return same error as "user not found" to prevent enumeration
          res.json({ exists: false });
          return;
        }
      }
    }

    res.json({ exists: true });
  } catch (err) {
    console.error("check-username db error:", err);
    res.status(500).json({ exists: false });
  }
});


Sentry.setupExpressErrorHandler(app);

app.listen(PORT, () => {
  console.log(`Auth service running on port ${PORT}`);
});
