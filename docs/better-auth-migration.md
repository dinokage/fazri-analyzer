# better-auth Migration Plan

Migrate from next-auth v4 to better-auth as a standalone Express microservice.

## Architecture Overview

```
Browser ──── cookies ────► Auth Service (Express + better-auth :4000)
  │                               │
  │ JWT Bearer                    │ Prisma (shared DB)
  ▼                               │
FastAPI (:8000) ◄────────────────┘
  (verifies JWT locally)

Next.js (:3000) ──► Auth Service (session checks via HTTP)
```

---

## Key Decisions

1. **`username` plugin** for `entity_id` — better-auth doesn't natively support non-email logins, but the `username` plugin handles this. Login becomes `authClient.signIn.username({ username, password })`.

2. **JWT plugin** for FastAPI — auth service issues a JWT the frontend passes to FastAPI as `Bearer`. FastAPI verifies it locally with the shared `BETTER_AUTH_SECRET`. No network hop per request.

3. **Shared database** — auth microservice shares the same PostgreSQL DB. Requires a schema migration.

4. **Roles as `additionalField`** — `role: "STUDENT" | "STAFF" | "FACULTY" | "SUPER_ADMIN"` declared as a custom field. Role-checking logic in dashboard pages stays identical.

5. **Password migration** — bcrypt hashes copy from `User.password` → `account.password`. No re-hashing, no password resets.

---

## Phase 1 — Auth Microservice (`auth/`)

New directory at repo root, parallel to `backend/`.

### Directory Structure

```
auth/
  src/
    index.ts          — Express app entrypoint
    auth.ts           — better-auth config
    lib/
      prisma.ts       — Prisma client singleton
  prisma/
    schema.prisma     — better-auth schema
  scripts/
    migrate-users.ts  — one-time data migration
  package.json
  tsconfig.json
  Dockerfile
  .env.example
```

### `auth/src/auth.ts`

```typescript
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { username } from "better-auth/plugins";
import { jwt } from "better-auth/plugins";
import { prisma } from "./lib/prisma";

export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: "postgresql" }),

  plugins: [
    username(),
    jwt({
      jwt: {
        expirationTime: "30d",
        definePayload(session) {
          return {
            id: session.user.id,
            entity_id: session.user.entity_id,
            name: session.user.name,
            email: session.user.email,
            role: session.user.role,
            face_id: session.user.face_id,
            student_id: session.user.student_id,
            staff_id: session.user.staff_id,
            department: session.user.department,
          };
        },
      },
      jwks: {
        keyPairConfig: { alg: "HS256" }, // preserve HS256 to match FastAPI
      },
    }),
  ],

  user: {
    additionalFields: {
      entity_id:   { type: "string", required: true,  unique: true },
      username:    { type: "string", required: true,  unique: true },
      role:        { type: "string", required: true,  defaultValue: "STUDENT" },
      face_id:     { type: "string", required: false },
      student_id:  { type: "string", required: false },
      staff_id:    { type: "string", required: false },
      department:  { type: "string", required: false },
      card_id:     { type: "string", required: false },
      device_hash: { type: "string", required: false },
    },
  },

  session: {
    expiresIn: 30 * 24 * 60 * 60, // 30 days
    cookieCache: { enabled: true, maxAge: 5 * 60 },
  },

  trustedOrigins: [process.env.FRONTEND_URL!],
  secret: process.env.BETTER_AUTH_SECRET!,
  baseURL: process.env.AUTH_SERVICE_URL!,
});
```

### `auth/src/index.ts`

```typescript
import express from "express";
import cors from "cors";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth";

const app = express();

app.use(cors({
  origin: [process.env.FRONTEND_URL!, process.env.FASTAPI_URL!],
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization", "Cookie"],
}));

app.all("/api/auth/*", toNodeHandler(auth));
app.get("/health", (_, res) => res.json({ status: "ok" }));

app.listen(4000, () => console.log("Auth service running on port 4000"));
```

### `auth/prisma/schema.prisma`

better-auth requires lowercase table names with specific columns. The existing NextAuth tables must be renamed.

```prisma
model user {
  id            String    @id @default(cuid())
  name          String
  email         String    @unique
  emailVerified Boolean   @default(false)
  image         String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt

  // Custom fields (additionalFields in better-auth config)
  entity_id     String    @unique
  username      String    @unique
  role          String    @default("STUDENT")
  face_id       String?   @unique
  student_id    String?
  staff_id      String?
  department    String?
  card_id       String?
  device_hash   String?   @unique

  sessions      session[]
  accounts      account[]
}

model session {
  id        String   @id @default(cuid())
  expiresAt DateTime
  token     String   @unique
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  ipAddress String?
  userAgent String?
  userId    String
  user      user     @relation(fields: [userId], references: [id], onDelete: Cascade)
}

model account {
  id                    String    @id @default(cuid())
  accountId             String
  providerId            String
  userId                String
  accessToken           String?   @db.Text
  refreshToken          String?   @db.Text
  idToken               String?   @db.Text
  accessTokenExpiresAt  DateTime?
  refreshTokenExpiresAt DateTime?
  scope                 String?
  password              String?
  createdAt             DateTime  @default(now())
  updatedAt             DateTime  @updatedAt
  user                  user      @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@unique([providerId, accountId])
}

model verification {
  id         String   @id @default(cuid())
  identifier String
  value      String
  expiresAt  DateTime
  createdAt  DateTime @default(now())
  updatedAt  DateTime @updatedAt
}
```

### Data Migration Script (`auth/scripts/migrate-users.ts`)

One-time script to run after table rename migration:

1. For each existing `User` record, create an `account` record:
   - `accountId = user.id`
   - `providerId = "credential"`
   - `userId = user.id`
   - `password = user.password` (bcrypt hash copied as-is)
2. Set `user.username = user.entity_id` for every user.
3. For users with `email = NULL`, generate `<entity_id>@internal.fazri` as a placeholder.

No password re-hashing required — better-auth uses bcrypt by default and the hash format is compatible.

### `auth/Dockerfile`

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/prisma ./prisma
COPY package.json ./

EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=10s CMD wget -qO- http://localhost:4000/health || exit 1
CMD ["node", "dist/index.js"]
```

### Environment Variables

```env
BETTER_AUTH_SECRET=<32+ char random string>
DATABASE_URL=postgresql://...
AUTH_SERVICE_URL=http://localhost:4000
FRONTEND_URL=http://localhost:3000
FASTAPI_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379
```

---

## Phase 2 — FastAPI (minimal changes)

Only **one file changes**: `backend/auth/jwt.py`

```python
# Before
payload = jwt.decode(token, settings.NEXTAUTH_SECRET, algorithms=[settings.JWT_ALGORITHM])

# After
payload = jwt.decode(token, settings.BETTER_AUTH_SECRET, algorithms=[settings.JWT_ALGORITHM])
```

`backend/config.py`: rename `NEXTAUTH_SECRET` → `BETTER_AUTH_SECRET`. Use the **same secret value** to avoid invalidating existing sessions during the cutover window.

No changes to `dependencies.py`, `models.py`, or any endpoint.

---

## Phase 3 — Next.js Frontend

### Files to Delete

- `src/auth.ts`
- `src/app/api/auth/[...nextauth]/route.ts`
- `src/types/next-auth.d.ts`
- `src/components/SessionWrapper.tsx` (and remove from `src/app/layout.tsx`)

### Packages

Remove: `next-auth`, `@auth/prisma-adapter`, `bcrypt`, `@types/bcrypt`, `jose`

Add: `better-auth`

### New `src/lib/auth-client.ts`

```typescript
import { createAuthClient } from "better-auth/react";
import { usernameClient } from "better-auth/client/plugins";
import { jwtClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_SERVICE_URL!,
  plugins: [usernameClient(), jwtClient()],
});

export const { useSession, signIn, signOut, getSession } = authClient;
```

### New `src/lib/auth-server.ts`

Used in Server Components instead of `getServerSession()`:

```typescript
export const auth = {
  api: {
    async getSession({ headers }: { headers: Headers }) {
      const response = await fetch(
        `${process.env.AUTH_SERVICE_INTERNAL_URL}/api/auth/get-session`,
        {
          headers: { cookie: headers.get("cookie") || "" },
          cache: "no-store",
        }
      );
      if (!response.ok) return null;
      return response.json();
    },
  },
};
```

### `src/lib/api-client.ts`

```typescript
// Before
import { getSession } from "next-auth/react";
const session = await getSession();
const token = session?.accessToken;

// After
import { authClient } from "@/lib/auth-client";
const token = await authClient.getToken(); // JWT plugin
```

### 8 Dashboard Pages

Each page using `getServerSession(OPTIONS)`:

```typescript
// Before
import { getServerSession } from "next-auth";
import { OPTIONS } from "@/auth";
const session = await getServerSession(OPTIONS);

// After
import { auth } from "@/lib/auth-server";
import { headers } from "next/headers";
const session = await auth.api.getSession({ headers: await headers() });
```

Role-check logic (`session.user.role !== "SUPER_ADMIN"`) is unchanged.

Affected pages:
- `src/app/(app)/dashboard/page.tsx`
- `src/app/(app)/dashboard/anomalies/page.tsx`
- `src/app/(app)/dashboard/alerts/page.tsx`
- `src/app/(app)/dashboard/alerts/[alertId]/page.tsx`
- `src/app/(app)/dashboard/zones/page.tsx`
- `src/app/(app)/dashboard/chat/page.tsx`
- `src/app/(app)/dashboard/profile/page.tsx`
- `src/app/(app)/auth/page.tsx`

### Client Components

`src/components/SigninForm.tsx`, `src/components/sidebar-layout.tsx`, `src/components/user-nav.tsx`, `src/components/SentryUserContext.tsx`:

```typescript
// Before
import { useSession, signOut } from "next-auth/react";

// After
import { useSession, signOut } from "@/lib/auth-client";
```

**`useSession` shape change:**
```typescript
// Before
const { data: session, status } = useSession();
const isLoading = status === "loading";

// After
const { data: session, isPending } = useSession();
const isLoading = isPending;
```

**`signOut` change:**
```typescript
// Before
signOut({ callbackUrl: "/auth" })

// After
signOut({ redirectTo: "/auth" })
```

### `src/components/auth/SigninForm.tsx`

```typescript
// Before
await signIn('credentials', { entity_id: username, password, redirect: false });

// After
const { data, error } = await authClient.signIn.username({
  username,
  password,
  rememberMe: true,
  fetchOptions: { redirect: false },
});
if (error) { /* show error toast */ }
else router.push('/dashboard');
```

### New Environment Variables

```env
NEXT_PUBLIC_AUTH_SERVICE_URL=http://localhost:4000
AUTH_SERVICE_INTERNAL_URL=http://auth:4000
```

Remove: `NEXTAUTH_URL`, `NEXTAUTH_SECRET`

### ⚠ Watch Out: `/api/check` Route

After the `User` → `user` table rename, the Prisma client in the Next.js app (generated from the old schema) will break. Options:
- **(a) Preferred:** Move `/api/check` to the auth microservice as a public endpoint.
- **(b) Simple:** Update the Next.js `prisma/schema.prisma` to match the new lowercase table names.

---

## Phase 4 — Infrastructure

### `docker-compose-db.yml`

Add the auth service:

```yaml
auth:
  build:
    context: ./auth
    dockerfile: Dockerfile
  container_name: fazri_auth
  ports:
    - "4000:4000"
  environment:
    DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
    BETTER_AUTH_SECRET: ${BETTER_AUTH_SECRET}
    AUTH_SERVICE_URL: http://localhost:4000
    FRONTEND_URL: ${FRONTEND_URL}
    FASTAPI_URL: http://backend:8000
    REDIS_URL: redis://redis:6379
  depends_on:
    - db
    - redis
  healthcheck:
    test: ["CMD", "wget", "-qO-", "http://localhost:4000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Production Routing (Nginx)

```
/api/auth/*  →  auth service  (port 4000)
/api/v1/*    →  FastAPI        (port 8000)
/*           →  Next.js        (port 3000)
```

Set `NEXT_PUBLIC_AUTH_SERVICE_URL` to the public-facing URL for the auth service.

### Cookie Domain

If auth service and Next.js are on different subdomains in production (e.g., `auth.fazri.campus` vs `app.fazri.campus`), add to better-auth config:

```typescript
advanced: {
  cookieOptions: { domain: ".fazri.campus" }
}
```

---

## Database Migration Sequence

Run once during deployment:

1. **Backup** the existing database.
2. Apply `auth/prisma/schema.prisma` migration — renames tables, adds new columns.
3. Run `auth/scripts/migrate-users.ts` — populates `account` records and `username` field.
4. Drop the old `password` column from the `user` table.
5. Update the Next.js Prisma schema to match new table names (or remove Prisma from Next.js entirely).

---

## Execution Order

1. Build and test auth microservice in isolation against a dev DB copy
2. Run Prisma schema migration + data migration script on dev DB, verify login works
3. Update FastAPI (rename one env var) — safe to deploy before the switchover
4. Update Next.js frontend — deploy together with auth service going live
5. Cut over traffic, run DB migration on production, drop old NextAuth columns
