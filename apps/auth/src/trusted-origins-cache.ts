import Redis from "ioredis";
import { prisma } from "@fazri/db";

const REDIS_KEY = "fazri:trusted_origins";
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

let _redis: Redis | null = null;
let _localSet = new Set<string>();

function getRedis(): Redis | null {
  if (_redis) return _redis;
  const host = process.env.REDIS_HOST;
  if (!host) return null;
  const port = parseInt(process.env.REDIS_PORT ?? "6379", 10);
  _redis = new Redis({ host, port, lazyConnect: true });
  _redis.on("connect", () => console.log(`[trusted-origins] Connected to Redis at ${host}:${port}`));
  _redis.on("error", (err) => console.error("[trusted-origins] Redis error:", err.message));
  _redis.on("close", () => console.warn("[trusted-origins] Redis connection closed"));
  return _redis;
}

function toOrigin(domain: string): string {
  return `https://${domain}`;
}

async function loadFromDb(): Promise<string[]> {
  const rows = await prisma.organizationDomain.findMany({
    where: { verified: true },
    select: { domain: true },
  });
  return rows.map((r) => toOrigin(r.domain));
}

async function syncToRedis(origins: string[]): Promise<void> {
  const r = getRedis();
  if (!r) return;
  const pipeline = r.pipeline();
  pipeline.del(REDIS_KEY);
  if (origins.length > 0) pipeline.sadd(REDIS_KEY, ...origins);
  await pipeline.exec();
  console.log(`[trusted-origins] Synced ${origins.length} origin(s) to Redis`);
}

async function refreshLocalFromRedis(): Promise<void> {
  const r = getRedis();
  if (!r) return;
  const members = await r.smembers(REDIS_KEY);
  if (members.length > 0) {
    _localSet = new Set(members);
    console.log(`[trusted-origins] Refreshed local cache from Redis — ${members.length} origin(s)`);
  }
}

export async function initTrustedOrigins(): Promise<void> {
  const redisAvailable = !!process.env.REDIS_HOST;
  if (!redisAvailable) {
    console.warn("[trusted-origins] REDIS_HOST not set — using in-memory cache only (no cross-instance sync)");
  }

  const dbOrigins = await loadFromDb();
  console.log(`[trusted-origins] Loaded ${dbOrigins.length} verified custom domain(s) from DB:`, dbOrigins);

  // Seed Redis from DB (overwrites any stale Redis state from previous deployments)
  await syncToRedis(dbOrigins);
  _localSet = new Set(dbOrigins);

  // Periodic refresh from Redis keeps all instances in sync
  setInterval(() => refreshLocalFromRedis().catch(console.error), REFRESH_INTERVAL_MS).unref();
  console.log(`[trusted-origins] Initialized — ${_localSet.size} custom domain(s) trusted, refresh every ${REFRESH_INTERVAL_MS / 1000}s`);
}

export async function addOrigin(domain: string): Promise<void> {
  const origin = toOrigin(domain);
  _localSet.add(origin);
  console.log(`[trusted-origins] Added origin: ${origin} (cache size: ${_localSet.size})`);
  const r = getRedis();
  if (r) {
    await r.sadd(REDIS_KEY, origin).catch((err) =>
      console.error(`[trusted-origins] Redis SADD failed for ${origin}:`, err.message)
    );
  }
}

export async function removeOrigin(domain: string): Promise<void> {
  const origin = toOrigin(domain);
  _localSet.delete(origin);
  console.log(`[trusted-origins] Removed origin: ${origin} (cache size: ${_localSet.size})`);
  const r = getRedis();
  if (r) {
    await r.srem(REDIS_KEY, origin).catch((err) =>
      console.error(`[trusted-origins] Redis SREM failed for ${origin}:`, err.message)
    );
  }
}

// Returns bare hostnames (no scheme) for use in Better Auth allowedHosts
export function getVerifiedCustomDomainHosts(): string[] {
  return Array.from(_localSet).map((origin) => {
    try { return new URL(origin).hostname; } catch { return ""; }
  }).filter(Boolean);
}

export function getAllOrigins(): string[] {
  const staticOrigins = (process.env.TRUSTED_ORIGINS ?? "http://localhost:3000")
    .split(",")
    .map((o) => o.trim())
    .filter(Boolean);
  const baseDomain = process.env.FAZRI_BASE_DOMAIN ?? "rayzrsole.com";
  return [
    ...staticOrigins,
    `https://${baseDomain}`,
    `https://*.${baseDomain}`,
    ..._localSet,
  ];
}

export function isOriginAllowed(requestOrigin: string | undefined): boolean {
  if (!requestOrigin) return true;

  const staticOrigins = (process.env.TRUSTED_ORIGINS ?? "http://localhost:3000")
    .split(",")
    .map((o) => o.trim())
    .filter(Boolean);
  if (staticOrigins.includes(requestOrigin)) return true;

  // Trust any subdomain of the base domain (covers all org-slug subdomains)
  const baseDomain = process.env.FAZRI_BASE_DOMAIN ?? "rayzrsole.com";
  try {
    const url = new URL(requestOrigin);
    if (
      url.protocol === "https:" &&
      (url.hostname === baseDomain || url.hostname.endsWith(`.${baseDomain}`))
    ) {
      return true;
    }
  } catch {}

  return _localSet.has(requestOrigin);
}
