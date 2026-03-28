import "dotenv/config";
import express from "express";
import cors from "cors";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth";
import { prisma } from "./lib/prisma";

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

app.post("/api/check-username", async (req, res) => {
  const { username } = req.body;
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


app.listen(PORT, () => {
  console.log(`Auth service running on port ${PORT}`);
});
