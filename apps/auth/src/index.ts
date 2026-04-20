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
