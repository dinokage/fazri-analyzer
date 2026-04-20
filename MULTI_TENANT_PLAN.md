# Multi-Tenant Architecture Plan: College Organizations with Better Auth

> **Scope:** Add multi-tenancy to fazri-analyzer so each college gets an isolated workspace
> identified by a URL slug (e.g. `/iit-bombay/dashboard/cameras`).
> **Auth:** Better Auth `organization` plugin — single source of truth for tenancy.
>
> **Updated:** 2026-04-11 — paths updated for monorepo structure (PR #20: `apps/auth/` → `apps/auth/`, `apps/api/` → `apps/api/`, `src/` → `apps/web/src/`, Prisma → `packages/db/`). Original: full rewrite after commit `ae83a72` (sensor ingestion pipeline)
> added new tables and exposed several gaps in the original plan.

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Architecture Overview](#2-architecture-overview)
3. [Key Design Decisions](#3-key-design-decisions)
4. [Phase 1: Auth Layer — Better Auth Organization Plugin](#4-phase-1-auth-layer)
5. [Phase 2: Database Schema — organization_id Columns](#5-phase-2-database-schema)
6. [Phase 3: Backend Enforcement](#6-phase-3-backend-enforcement)
7. [Phase 4: Frontend Routing — [orgSlug] Layout](#7-phase-4-frontend-routing)
8. [Phase 5: Sensor Pipeline Org-Scoping](#8-phase-5-sensor-pipeline)
9. [Phase 6: DeepFace Org-Namespacing](#9-phase-6-deepface)
10. [Migration Strategy](#10-migration-strategy)
11. [Environment Variables](#11-environment-variables)
12. [Testing Checklist](#12-testing-checklist)
13. [Quick Reference: Files to Change](#13-quick-reference)

---

## 1. Current State Assessment

Corrections from the original plan — do not re-introduce these mistakes during implementation.

| Topic | Original Plan Assumed | Actual Current State |
|---|---|---|
| better-auth version | "upgrade to 1.5.6" | `package.json` says `^1.2.7` but lockfile resolves to `1.5.6` — just pin to `^1.5.6` in package.json, no reinstall needed |
| Migration tooling | Alembic (`alembic revision --autogenerate`) | Plain Python SQL scripts in `apps/api/migrations/` — NOT Alembic. Follow `create_sensor_events.py` pattern |
| `sensor_events` table | Not mentioned | Added in `ae83a72` — needs `organization_id` stamped at ingest time |
| `entity_profiles` table | Not mentioned | Added in `ae83a72` — needs `organization_id` |
| `entity_identifiers` table | Not mentioned | Added in `ae83a72` — needs `organization_id` AND unique constraint change from `(type, value)` → `(org, type, value)` |
| `org_role` in JWT | Listed as future work | Must be **explicitly** queried in `definePayload` — Better Auth does NOT auto-include the member's role in JWT |
| `additionalFields` on organization | Treated as separate DB columns | Stored in `metadata` JSON column by Better Auth — must parse JSON in `check-org-slug` endpoint |
| JWT refresh after `setActive` | Not addressed | Frontend MUST call `authClient.token()` after `organization.setActive()` to force JWT re-issue before redirect |
| `api-client.ts` 401 redirect | Hardcoded `router.push("/auth")` | Should include `?college=${orgSlug}` from URL to pre-fill slug step |
| Sensor pipeline multi-tenancy | Not addressed | One org per backend instance via `HIKVISION_ORG_ID` / `ARUBA_ORG_ID` env vars |

---

## 2. Architecture Overview

### Current State (Single-Tenant)
```
user ──▶ auth service ──▶ JWT (role, entity_id) ──▶ backend (no org scoping)
                                                       │
                                            all cameras, alerts, staff,
                                            sensor_events, entity_profiles
                                            are globally shared
```

### Target State (Multi-Tenant)
```
user ──▶ slug entry ──▶ username entry ──▶ password ──▶ auth service
              │                                              │
         check-org-slug                              JWT (role, entity_id,
         API endpoint                                organizationId,
                                                     organizationSlug,
                                                     orgRole)
                                                          │
                                               /[orgSlug]/dashboard/...
                                                          │
                                            backend: ALL queries filtered
                                            by organization_id from JWT
                                                          │
                                            deepface: face DB namespaced
                                            per org ({org_id}__{entity_id})
```

### Tenancy Model
- Each **college** = one **Organization** in Better Auth
- Organization has a unique **slug** (e.g. `iit-bombay`, `bits-pilani`)
- Users belong to one or more orgs with a role: `owner | admin | member`
- `owner` = College system admin (full control)
- `admin` = Lab supervisor / security supervisor (manage staff, cameras, webhooks)
- `member` = Staff / faculty / student (read-only access to cameras/alerts)
- Backend enforces org isolation at every query level
- DeepFace face embeddings are namespaced by `org_id`
- Sensor data (RFID, WiFi) is stamped with `org_id` at ingest time

---

## 3. Key Design Decisions

### Decision 1: `setActiveOrganization` vs. URL-Inferred Org

**Use `setActiveOrganization`** (Better Auth's built-in mechanism).

Rationale: Better Auth writes `activeOrganizationId` into the `session` row. The `definePayload` function reads it back and includes `organizationId`, `organizationSlug`, and `orgRole` in the JWT. The backend reads org context entirely from the JWT — zero URL-parsing needed. The `[orgSlug]` URL segment is purely a Next.js routing concern for UX.

After step 3 of login: call `authClient.organization.setActive({ organizationId })` → then `authClient.token()` (force JWT refresh) → redirect to `/<orgSlug>/dashboard`. The `[orgSlug]` layout guard verifies the JWT slug matches the URL slug; if not, it corrects or redirects.

### Decision 2: Sensor Pipeline Org Assignment

**One org per backend instance**, configured via environment variables.

Rationale: Each physical campus has one Hikvision NVR and one Aruba controller. A multi-campus deployment runs separate backend instances, each configured for its own org. This avoids per-org credential management in a single process. Add `HIKVISION_ORG_ID` and `ARUBA_ORG_ID` to `apps/api/.env`. The pollers stamp every `SensorEventRecord` with that org ID at ingest time.

Startup guard: if `HIKVISION_ENABLED=True` but `HIKVISION_ORG_ID` is empty, log an error and refuse to start. Same for Aruba.

### Decision 3: `entity_identifiers` Unique Constraint

**Must change** from `UNIQUE(identifier_type, identifier_value)` to `UNIQUE(organization_id, identifier_type, identifier_value)`.

Rationale: The current global constraint prevents two different colleges from having students with the same card number or MAC address. This will fail in any real multi-college deployment. This constraint change is the most architecturally critical database migration.

---

## 4. Phase 1: Auth Layer

### 4.1 Pin better-auth Version

In `apps/auth/package.json`, change:
```json
"better-auth": "^1.2.7"
```
to:
```json
"better-auth": "^1.5.6"
```

Run `pnpm install` in the `apps/auth/` workspace. No new packages needed — the organization plugin ships inside `better-auth`.

### 4.2 Generate Prisma Schema Additions

After updating `apps/auth/src/auth.ts` (step 4.3 below), run:
```bash
cd apps/auth
npx @better-auth/cli generate
```

This reads `apps/auth/src/auth.ts` and outputs the Prisma additions. Apply them to `packages/db/prisma/schema.prisma`. The CLI will add:

```prisma
model session {
  id                   String   @id(map: "Session_pkey") @default(cuid())
  token                String   @unique(map: "Session_sessionToken_key")
  userId               String
  expiresAt            DateTime
  createdAt            DateTime @default(now())
  updatedAt            DateTime @default(now()) @updatedAt
  ipAddress            String?
  userAgent            String?
  activeOrganizationId String?  // ← NEW
  user                 user     @relation(fields: [userId], references: [id], onDelete: Cascade, map: "Session_userId_fkey")
}

model organization {
  id          String   @id @default(cuid())
  name        String
  slug        String   @unique
  logo        String?
  metadata    String?  // additionalFields (collegeCode, city, state, isActive) stored here as JSON
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  members     member[]
  invitations invitation[]
}

model member {
  id             String       @id @default(cuid())
  organizationId String
  userId         String
  role           String       // "owner" | "admin" | "member"
  createdAt      DateTime     @default(now())
  organization   organization @relation(fields: [organizationId], references: [id], onDelete: Cascade)
  user           user         @relation(fields: [userId], references: [id], onDelete: Cascade)
}

model invitation {
  id             String       @id @default(cuid())
  organizationId String
  email          String
  role           String?
  status         String
  expiresAt      DateTime
  inviterId      String
  organization   organization @relation(fields: [organizationId], references: [id], onDelete: Cascade)
  inviter        user         @relation("invitations", fields: [inviterId], references: [id], onDelete: Cascade)
}
```

Then push to DB (run from repo root — Prisma lives in `packages/db`):
```bash
pnpm --filter=@fazri/db db:push
# or in production:
pnpm --filter=@fazri/db db:migrate
```

The `user` model also needs the `member[]` and `invitation[]` relations added:
```prisma
model user {
  // ... existing fields ...
  members     member[]
  invitations invitation[] @relation("invitations")
}
```

### 4.3 `apps/auth/src/auth.ts` — Full Updated File

```typescript
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { username, jwt, organization } from "better-auth/plugins";
import { createAccessControl } from "better-auth/plugins/access";
import { prisma } from "@fazri/db";
import bcrypt from "bcryptjs";

// Fine-grained permissions for college roles
const statements = {
  camera:  ["create", "read", "update", "delete"],
  alert:   ["create", "read", "update", "assign", "resolve", "escalate"],
  staff:   ["create", "read", "update", "delete"],
  face:    ["enroll", "read", "delete"],
  webhook: ["create", "read", "update", "delete"],
  report:  ["read"],
  sensor:  ["read"],
} as const;

const ac = createAccessControl(statements);

const ownerRole = ac.newRole({
  camera:  ["create", "read", "update", "delete"],
  alert:   ["create", "read", "update", "assign", "resolve", "escalate"],
  staff:   ["create", "read", "update", "delete"],
  face:    ["enroll", "read", "delete"],
  webhook: ["create", "read", "update", "delete"],
  report:  ["read"],
  sensor:  ["read"],
});

const adminRole = ac.newRole({
  camera:  ["create", "read", "update", "delete"],
  alert:   ["create", "read", "update", "assign", "resolve", "escalate"],
  staff:   ["read", "update"],
  face:    ["enroll", "read"],
  webhook: ["create", "read", "update", "delete"],
  report:  ["read"],
  sensor:  ["read"],
});

const memberRole = ac.newRole({
  camera:  ["read"],
  alert:   ["read"],
  staff:   ["read"],
  face:    ["read"],
  webhook: [],
  report:  ["read"],
  sensor:  ["read"],
});

export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: "postgresql" }),

  emailAndPassword: {
    enabled: false,
    password: {
      hash: async (password) => bcrypt.hash(password, 10),
      verify: async ({ hash, password }) => bcrypt.compare(password, hash),
    },
  },

  plugins: [
    username(),
    organization({
      ac,
      roles: { owner: ownerRole, admin: adminRole, member: memberRole },
      allowUserToCreateOrganization: false, // only SUPER_ADMINs provision orgs
      schema: {
        organization: {
          additionalFields: {
            collegeCode: { type: "string", required: false },
            city:        { type: "string", required: false },
            state:       { type: "string", required: false },
            country:     { type: "string", required: false },
            timezone:    { type: "string", required: false },
            isActive:    { type: "boolean", required: false, defaultValue: true },
          },
        },
      },
    }),
    jwt({
      jwks: {
        keyPairConfig: { alg: "RS256" },
      },
      jwt: {
        expirationTime: "30d",
        // definePayload MUST be async to query the session for activeOrganizationId
        definePayload: async ({ user, session }) => {
          // Read activeOrganizationId from the session row
          const activeSession = await prisma.session.findUnique({
            where: { id: session.id },
            select: { activeOrganizationId: true },
          });

          let organizationId: string | null = null;
          let organizationSlug: string | null = null;
          let organizationName: string | null = null;
          let orgRole: string | null = null;

          if (activeSession?.activeOrganizationId) {
            const org = await prisma.organization.findUnique({
              where: { id: activeSession.activeOrganizationId },
              select: { id: true, slug: true, name: true },
            });
            if (org) {
              organizationId = org.id;
              organizationSlug = org.slug;
              organizationName = org.name;
            }
            // org_role is NOT auto-included by Better Auth — query the member table
            const member = await prisma.member.findFirst({
              where: {
                organizationId: activeSession.activeOrganizationId,
                userId: user.id,
              },
              select: { role: true },
            });
            orgRole = member?.role ?? null;
          }

          return {
            id: user.id,
            entity_id: (user as Record<string, unknown>).entity_id,
            name: user.name,
            email: user.email,
            role: (user as Record<string, unknown>).role,
            face_id: (user as Record<string, unknown>).face_id,
            student_id: (user as Record<string, unknown>).student_id,
            staff_id: (user as Record<string, unknown>).staff_id,
            department: (user as Record<string, unknown>).department,
            sessionId: session.id,
            // Org fields
            organizationId,
            organizationSlug,
            organizationName,
            orgRole,
          };
        },
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
    expiresIn: 30 * 24 * 60 * 60,
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60,
    },
  },

  trustedOrigins: (process.env.TRUSTED_ORIGINS ?? "http://localhost:3000").split(","),

  advanced: {
    defaultCookieAttributes: {
      sameSite: "none" as const,
      secure: true,
    },
  },

  secret: process.env.BETTER_AUTH_SECRET!,
  baseURL: process.env.AUTH_SERVICE_URL ?? "http://localhost:4000",
});

export type Auth = typeof auth;
```

### 4.4 `apps/auth/src/index.ts` — New and Updated Endpoints

Add `POST /api/check-org-slug` and update `POST /api/check-username`:

```typescript
// POST /api/check-org-slug
// Body: { slug: string }
// Returns: { exists: boolean, name: string | null, id: string | null }
app.post("/api/check-org-slug", async (req, res) => {
  const { slug } = req.body as { slug?: string };
  if (!slug?.trim()) {
    res.status(400).json({ error: "slug required" });
    return;
  }
  const normalized = slug.trim().toLowerCase();
  try {
    const org = await prisma.organization.findUnique({
      where: { slug: normalized },
      select: { id: true, name: true, metadata: true },
    });
    if (!org) {
      res.json({ exists: false, name: null, id: null });
      return;
    }
    // additionalFields (isActive) are stored as JSON in the metadata column
    let isActive = true;
    if (org.metadata) {
      try {
        const meta = JSON.parse(org.metadata as string);
        if (meta.isActive === false) isActive = false;
      } catch {
        // malformed metadata — treat as active
      }
    }
    if (!isActive) {
      res.json({ exists: false, name: null, id: null });
      return;
    }
    res.json({ exists: true, name: org.name, id: org.id });
  } catch (err) {
    console.error("check-org-slug db error:", err);
    res.status(500).json({ exists: false, name: null, id: null });
  }
});

// POST /api/check-username  (updated — now accepts optional organizationId)
// Body: { username: string, organizationId?: string }
// Returns: { exists: boolean, notInOrg?: boolean }
app.post("/api/check-username", async (req, res) => {
  const { username, organizationId } = req.body as {
    username?: string;
    organizationId?: string;
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
    if (organizationId) {
      const membership = await prisma.member.findFirst({
        where: { userId: user.id, organizationId },
      });
      if (!membership) {
        res.json({ exists: false, notInOrg: true });
        return;
      }
    }
    res.json({ exists: true });
  } catch (err) {
    console.error("check-username db error:", err);
    res.status(500).json({ exists: false });
  }
});
```

---

## 5. Phase 2: Database Schema

### 5.1 Tables Requiring `organization_id`

| Table | File | Notes |
|-------|------|-------|
| `sensor_events` | `apps/api/models/db/sensor_events.py` | Stamped at ingest via `HIKVISION_ORG_ID`/`ARUBA_ORG_ID` |
| `entity_profiles` | `apps/api/models/db/entity_profiles.py` | Each person belongs to one org |
| `entity_identifiers` | `apps/api/models/db/entity_identifiers.py` | + unique constraint change (critical) |
| `alerts` | `apps/api/models/db/alerts.py` | Core scoping |
| `staff_profiles` | `apps/api/models/db/alerts.py` | Org-specific staff |
| `camera_streams` | `apps/api/models/db/camera_streams.py` | Org-specific cameras |
| `outgoing_webhooks` | `apps/api/models/db/webhooks.py` | Org-specific webhooks |
| `push_subscriptions` | `apps/api/models/db/push_subscriptions.py` | Org-specific push |
| `notification_queue` | `apps/api/models/db/alerts.py` | Org-specific notifications |

Tables intentionally org-agnostic (platform-level):
- `demo_scenarios` / `demo_timeline_events` — platform-level content

### 5.2 Migration Script

Create `apps/api/migrations/add_organization_id.py` following the plain-SQL pattern in `apps/api/migrations/create_sensor_events.py`:

```python
from sqlalchemy import text
from database.connection import engine


def upgrade(default_org_id: str) -> None:
    """
    Add organization_id to all org-scoped tables.

    Args:
        default_org_id: The Better Auth organization.id for the initial college.
                        Get this from the organization table after creating the first
                        org via Better Auth admin API.
    """
    tables = [
        "sensor_events",
        "entity_profiles",
        "entity_identifiers",
        "alerts",
        "staff_profiles",
        "camera_streams",
        "outgoing_webhooks",
        "push_subscriptions",
        "notification_queue",
    ]

    with engine.begin() as conn:
        # 1. Add nullable organization_id columns
        for table in tables:
            conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS organization_id VARCHAR"
            ))

        # 2. Backfill all existing rows with the default org
        for table in tables:
            conn.execute(text(
                f"UPDATE {table} SET organization_id = :org_id WHERE organization_id IS NULL"
            ), {"org_id": default_org_id})

        # 3. Make NOT NULL
        for table in tables:
            conn.execute(text(
                f"ALTER TABLE {table} ALTER COLUMN organization_id SET NOT NULL"
            ))

        # 4. Fix entity_identifiers unique constraint (CRITICAL)
        conn.execute(text(
            "ALTER TABLE entity_identifiers "
            "DROP CONSTRAINT IF EXISTS uq_entity_identifiers_type_value"
        ))
        conn.execute(text("""
            ALTER TABLE entity_identifiers
            ADD CONSTRAINT uq_entity_identifiers_org_type_value
            UNIQUE (organization_id, identifier_type, identifier_value)
        """))

        # 5. Performance indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sensor_events_org ON sensor_events (organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sensor_events_org_ts ON sensor_events (organization_id, timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_entity_profiles_org ON entity_profiles (organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_entity_identifiers_org ON entity_identifiers (organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_org_status ON alerts (organization_id, status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_org_created ON alerts (organization_id, created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_staff_org ON staff_profiles (organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cameras_org ON camera_streams (organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_webhooks_org ON outgoing_webhooks (organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_push_subs_org ON push_subscriptions (organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notif_queue_org ON notification_queue (organization_id)"))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python add_organization_id.py <default_org_id>")
        sys.exit(1)
    upgrade(sys.argv[1])
    print("Migration complete.")
```

### 5.3 SQLAlchemy Model Updates

Add to every model in the tables list above:
```python
organization_id = Column(String, nullable=False, index=True)
```

For `entity_identifiers`, change `__table_args__`:
```python
__table_args__ = (
    UniqueConstraint(
        "organization_id",
        "identifier_type",
        "identifier_value",
        name="uq_entity_identifiers_org_type_value",
    ),
)
```

---

## 6. Phase 3: Backend Enforcement

### 6.1 `apps/api/auth/models.py`

Add org fields to `AuthenticatedUser`:

```python
class AuthenticatedUser(BaseModel):
    """Authenticated user model from JWT claims"""
    id: str
    entity_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    role: UserRole
    face_id: Optional[str] = None
    student_id: Optional[str] = None
    staff_id: Optional[str] = None
    department: Optional[str] = None
    # Org fields (populated after setActiveOrganization)
    organization_id: Optional[str] = None
    organization_slug: Optional[str] = None
    organization_name: Optional[str] = None
    org_role: Optional[str] = None  # "owner" | "admin" | "member"
```

### 6.2 `apps/api/auth/dependencies.py`

Update `get_current_user` to extract org claims:

```python
user = AuthenticatedUser(
    id=payload.get("id"),
    entity_id=payload.get("entity_id"),
    name=payload.get("name"),
    email=payload.get("email"),
    role=UserRole(payload.get("role")),
    face_id=payload.get("face_id"),
    student_id=payload.get("student_id"),
    staff_id=payload.get("staff_id"),
    department=payload.get("department"),
    organization_id=payload.get("organizationId"),
    organization_slug=payload.get("organizationSlug"),
    organization_name=payload.get("organizationName"),
    org_role=payload.get("orgRole"),
)
```

Add new dependency functions:

```python
def require_org_member() -> Callable:
    """Require an active organization in the JWT. Use on all org-scoped routes."""
    async def _check(
        current_user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if not current_user.organization_id:
            raise PermissionDeniedError(
                detail="No active organization. Complete the login flow with organization selection."
            )
        return current_user
    return _check


def require_org_admin() -> Callable:
    """Require owner or admin role within the active org."""
    async def _check(
        current_user: AuthenticatedUser = Depends(require_org_member())
    ) -> AuthenticatedUser:
        if current_user.org_role not in ("owner", "admin"):
            raise PermissionDeniedError(detail="Organization admin access required.")
        return current_user
    return _check


def require_org_owner() -> Callable:
    """Require owner role within the active org."""
    async def _check(
        current_user: AuthenticatedUser = Depends(require_org_member())
    ) -> AuthenticatedUser:
        if current_user.org_role != "owner":
            raise PermissionDeniedError(detail="Organization owner access required.")
        return current_user
    return _check
```

### 6.3 Route-Level Changes

For every route that queries org-scoped data, replace:
```python
current_user: AuthenticatedUser = Depends(get_current_user)
```
with:
```python
current_user: AuthenticatedUser = Depends(require_org_member())
```

And pass `organization_id=current_user.organization_id` to every service call.

Routes to update:
- `apps/api/routes/alert_routes.py`
- `apps/api/routes/staff_routes.py`
- `apps/api/routes/deepface_routes.py`
- `apps/api/routes/webhook_routes.py`
- `apps/api/routes/notification_routes.py`
- `apps/api/routes/events_routes.py`
- `apps/api/routes/spatial_routes.py`
- `apps/api/routes/anomaly_routes.py`
- Any entity or graph routes

### 6.4 Service-Level Changes

Every service method that touches an org-scoped table gains an `organization_id: str` parameter, and all ORM queries gain a `.filter(Model.organization_id == organization_id)` clause.

For example, in alert queries:
```python
# Before
query = db.query(Alert).filter(Alert.status == status)

# After
query = db.query(Alert).filter(
    Alert.organization_id == organization_id,
    Alert.status == status
)
```

### 6.5 `apps/api/config/__init__.py`

Add to `Settings`:
```python
HIKVISION_ORG_ID: str = ""   # Better Auth organization.id for this Hikvision instance
ARUBA_ORG_ID: str = ""       # Better Auth organization.id for this Aruba instance
```

---

## 7. Phase 4: Frontend Routing

### 7.1 Directory Restructure

```
Before:                                    After:
apps/web/src/app/(app)/                    apps/web/src/app/(app)/
├── auth/page.tsx                     ├── auth/page.tsx        (3-step form)
└── dashboard/                        ├── org-setup/page.tsx   (NEW)
    ├── layout.tsx                    └── [orgSlug]/
    ├── page.tsx                          └── dashboard/
    ├── [id]/page.tsx                         ├── layout.tsx   (NEW org-guard)
    ├── alerts/                               ├── page.tsx
    ├── anomalies/                            ├── [id]/
    ├── cameras/                              ├── alerts/
    ├── chat/                                 ├── anomalies/
    ├── events/                               ├── cameras/
    ├── face-enrollment/                      ├── chat/
    ├── insights/                             ├── events/
    ├── profile/                              ├── face-enrollment/
    ├── system/                               ├── insights/
    ├── webcam/                               ├── profile/
    ├── webhooks/                             ├── system/
    └── zones/                                ├── webcam/
                                              ├── webhooks/
                                              └── zones/
```

### 7.2 `apps/web/src/lib/auth-client.ts` — Add Organization Plugin

```typescript
import { createAuthClient } from "better-auth/react";
import { usernameClient, jwtClient, organizationClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_SERVICE_URL,
  plugins: [
    usernameClient(),
    jwtClient(),
    organizationClient(),
  ],
  fetchOptions: {
    onError: (ctx) => {
      if (ctx.error.status === 503 || ctx.error.status === 0) {
        // existing toast error for service down
      }
    },
  },
});

export const { useSession, signOut, getSession } = authClient;
```

### 7.3 `apps/web/src/lib/auth-server.ts` — Add Org Fields to `FazriUser`

```typescript
export type FazriUser = {
  id: string;
  name: string;
  email: string;
  image: string | null;
  entity_id: string;
  username: string;
  role: "STUDENT" | "STAFF" | "FACULTY" | "SUPER_ADMIN";
  face_id: string | null;
  student_id: string | null;
  staff_id: string | null;
  department: string | null;
  card_id: string | null;
  device_hash: string | null;
  // Org fields
  organizationId: string | null;
  organizationSlug: string | null;
  organizationName: string | null;
  orgRole: "owner" | "admin" | "member" | null;
};
```

### 7.4 `apps/web/src/app/(app)/[orgSlug]/dashboard/layout.tsx` — Org Guard

```typescript
import { redirect } from "next/navigation";
import { headers } from "next/headers";
import { getAuthSession } from "@/lib/auth-server";
import { SidebarLayout } from "@/components/SidebarLayout";
import { AlertNotificationListener } from "@/components/AlertNotificationListener";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default async function OrgDashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { orgSlug: string };
}) {
  const session = await getAuthSession(await headers());

  if (!session) {
    redirect(`/auth?college=${params.orgSlug}`);
  }

  if (!session.user.organizationId) {
    redirect("/org-setup");
  }

  // If JWT slug doesn't match URL slug, user navigated directly
  // to a different org's URL — redirect them to their actual org
  if (session.user.organizationSlug !== params.orgSlug) {
    redirect(`/${session.user.organizationSlug}/dashboard`);
  }

  return (
    <ErrorBoundary>
      <AlertNotificationListener pollIntervalMs={10000} />
      <SidebarLayout orgSlug={params.orgSlug} orgName={session.user.organizationName}>
        {children}
      </SidebarLayout>
    </ErrorBoundary>
  );
}
```

### 7.5 `apps/web/src/components/auth/SigninForm.tsx` — 3-Step State Machine

Replace the 2-step `usernameChecked` boolean with a 3-step state machine:

```typescript
type Step = "slug" | "username" | "password";

// State
const [step, setStep] = useState<Step>("slug");
const [orgSlug, setOrgSlug]       = useState(prefillSlug ?? "");
const [orgName, setOrgName]       = useState<string | null>(null);
const [orgId, setOrgId]           = useState<string | null>(null);
const [username, setUsername]     = useState("");
const [password, setPassword]     = useState("");
const [isLoading, setIsLoading]   = useState(false);
const [direction, setDirection]   = useState<"forward" | "back">("forward");
```

**Step 1 — Slug handler:**
```typescript
async function handleSlugContinue() {
  setIsLoading(true);
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/api/check-org-slug`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug: orgSlug.trim().toLowerCase() }),
    }
  );
  const data = await res.json();
  setIsLoading(false);
  if (!data.exists) {
    toast.error("College not found. Check the slug and try again.");
    return;
  }
  setOrgName(data.name);
  setOrgId(data.id);
  setDirection("forward");
  setStep("username");
}
```

**Step 2 — Username handler:**
```typescript
async function handleUsernameContinue() {
  setIsLoading(true);
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/api/check-username`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username.trim(), organizationId: orgId }),
    }
  );
  const data = await res.json();
  setIsLoading(false);
  if (!data.exists) {
    if (data.notInOrg) {
      toast.error("This username is not registered with this college.");
    } else {
      toast.error("Username not found.");
    }
    return;
  }
  setDirection("forward");
  setStep("password");
}
```

**Step 3 — Password / sign-in handler:**
```typescript
async function handleSignIn() {
  setIsLoading(true);
  const result = await authClient.signIn.username({
    username: username.trim(),
    password,
    rememberMe: true,
  });
  if (result.error) {
    setIsLoading(false);
    if (result.error.status === 429) toast.error("Too many attempts. Wait a moment.");
    else if (result.error.status === 401) toast.error("Incorrect password.");
    else toast.error("Sign-in failed. Try again.");
    return;
  }
  // Set active org so JWT carries organizationId on next token call
  await authClient.organization.setActive({ organizationId: orgId! });
  // Force JWT re-issue — REQUIRED before redirect or JWT won't have org fields
  await authClient.token();
  router.push(`/${orgSlug}/dashboard`);
}
```

**Back navigation:**
```typescript
function goBack() {
  setDirection("back");
  if (step === "password") setStep("username");
  else if (step === "username") { setStep("slug"); setOrgName(null); setOrgId(null); }
}
```

**Pre-fill support:** `apps/web/src/app/(app)/auth/page.tsx` reads `searchParams.college` and passes it as `prefillSlug` prop to `SigninForm`. On mount, if `prefillSlug` is set, auto-submit step 1.

### 7.6 `apps/web/src/lib/api-client.ts` — Fix 401 Redirect

The current handler does `router.push("/auth")`. Change to:
```typescript
// Extract orgSlug from current URL for pre-fill
const pathParts = window.location.pathname.split("/");
const orgSlug = pathParts[1] ?? "";
const redirectUrl = orgSlug ? `/auth?college=${orgSlug}` : "/auth";
router.push(redirectUrl);
```

### 7.7 `apps/web/src/app/(app)/org-setup/page.tsx` — No Org Membership Page

Simple page shown when a user signs in but has no org membership. Shows "Contact your college administrator to be added to your organization."

---

## 8. Phase 5: Sensor Pipeline

### 8.1 Environment Variables

Add to `apps/api/.env`:
```env
HIKVISION_ORG_ID=<org_id_from_better_auth_organization_table>
ARUBA_ORG_ID=<org_id_from_better_auth_organization_table>
```

### 8.2 `apps/api/services/event_ingestion_service.py`

`EventIngestionService` constructor takes `organization_id: str`:

```python
class EventIngestionService:
    def __init__(self, db: Session, organization_id: str, ...):
        self.organization_id = organization_id
        ...

    async def ingest(self, event: SensorEvent) -> ResolvedEvent:
        # Resolve entity with org scope
        resolved = await self.entity_resolution_service.resolve(
            identifier_type=event.identifier_type,
            identifier_value=event.raw_identifier,
            organization_id=self.organization_id,
        )
        # Stamp org on record
        record = SensorEventRecord(
            organization_id=self.organization_id,
            ...
        )
        ...
```

Factory function:
```python
def get_event_ingestion_service(
    db: Session,
    organization_id: str,
) -> EventIngestionService:
    resolution_svc = get_entity_resolution_service(db, organization_id)
    return EventIngestionService(db, organization_id, resolution_svc)
```

### 8.3 `apps/api/services/entity_resolution_service.py`

Scope all queries to org:

```python
async def resolve(
    self,
    identifier_type: str,
    identifier_value: str,
    organization_id: str,
) -> Optional[str]:
    # All queries filter by organization_id
    identifier = (
        db.query(EntityIdentifier)
        .filter(
            EntityIdentifier.organization_id == organization_id,
            EntityIdentifier.identifier_type == identifier_type,
            EntityIdentifier.identifier_value == identifier_value,
        )
        .first()
    )
    ...
```

### 8.4 Pollers

In `apps/api/services/hikvision_poller.py` and `apps/api/services/aruba_poller.py`:

```python
from config import settings

# Startup guard
if not settings.HIKVISION_ORG_ID:
    raise RuntimeError("HIKVISION_ORG_ID must be set when HIKVISION_ENABLED=True")

svc = get_event_ingestion_service(db, organization_id=settings.HIKVISION_ORG_ID)
```

---

## 9. Phase 6: DeepFace

### 9.1 Namespace Helpers

Add to `apps/api/services/deepface_client.py` (or a new `apps/api/services/namespace.py`):

```python
_SEPARATOR = "__"

def build_namespaced_id(org_id: str, entity_id: str) -> str:
    """Face label format: {org_id}__{entity_id}"""
    return f"{org_id}{_SEPARATOR}{entity_id}"

def parse_namespaced_id(label: str) -> tuple[str | None, str]:
    """Parse {org_id}__{entity_id}. Returns (org_id, entity_id) or (None, label) for legacy."""
    parts = label.split(_SEPARATOR, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, label
```

### 9.2 Face Registration Route

`POST /api/v1/deepface/entities/{entity_id}/register` — requires `require_org_member()`:

```python
label = build_namespaced_id(current_user.organization_id, entity_id)
# Send label to DeepFace server for face embedding registration
```

### 9.3 DeepFace Webhook Handler

When DeepFace POSTs a match event with `img_name`:

```python
org_id, entity_id = parse_namespaced_id(img_name)
if org_id is None:
    # Legacy un-namespaced label — fall back to stream's org
    org_id = stream.organization_id
# Use org_id to scope the alert
```

### 9.4 go2rtc Stream Namespacing

Stream names in go2rtc: `{org_id}__{stream_id}` via `build_namespaced_id(org_id, stream_id)`.

### 9.5 Redis Key Namespacing

```python
# Alert cooldown
f"alert_cooldown:{organization_id}:{stream_id}:{entity_id}"

# Unknown face tracking
f"unknown_face:{organization_id}:{tracker_id}"
```

### 9.6 One-Time Face Migration

Create `apps/api/scripts/migrate_face_namespaces.py`:
- List all registered faces from DeepFace server
- For each label without `__`, prefix with the default org ID
- Re-register embedding with namespaced label
- Delete old un-namespaced label

Run once manually during Phase 6 deployment.

---

## 10. Migration Strategy

Execute in this order — each phase must pass smoke tests before moving to the next.

| Order | Phase | Prerequisite |
|-------|-------|-------------|
| 1 | Auth: Prisma schema + org plugin | — |
| 2 | Auth: `check-org-slug`, updated `check-username` | Phase 1 complete |
| 3 | Backend: DB migration (add `organization_id` columns) | First org created in Better Auth |
| 4 | Backend: SQLAlchemy model updates | Phase 3 complete |
| 5 | Backend: `AuthenticatedUser` + `require_org_member()` | Phase 1 complete |
| 6 | Backend: Route + service enforcement | Phase 4, 5 complete |
| 7 | Backend: Sensor pipeline org-scoping | `HIKVISION_ORG_ID`/`ARUBA_ORG_ID` set |
| 8 | Frontend: `auth-client.ts` + `auth-server.ts` types | Phase 1 complete |
| 9 | Frontend: `SigninForm.tsx` 3-step flow | Phase 2 complete |
| 10 | Frontend: Move routes to `[orgSlug]/dashboard` | Phase 8, 9 complete |
| 11 | DeepFace: Namespace helpers + registration | Phase 6 complete |
| 12 | DeepFace: One-time face migration script | Phase 11 complete |

---

## 11. Environment Variables

New variables only (do not repeat existing env vars here):

**`apps/auth/.env`**
```env
# No new variables needed — organization plugin uses existing BETTER_AUTH_SECRET + DATABASE_URL
```

**`apps/api/.env`**
```env
# Organization ID for each sensor connector instance
# Get these IDs from the organization table after creating orgs via Better Auth
HIKVISION_ORG_ID=
ARUBA_ORG_ID=
```

**`frontend/.env.local`**
```env
# No new variables needed — NEXT_PUBLIC_AUTH_SERVICE_URL already exists
```

---

## 12. Testing Checklist

### Auth Service
- [ ] `POST /api/check-org-slug` with valid slug → `{ exists: true, name, id }`
- [ ] `POST /api/check-org-slug` with unknown slug → `{ exists: false, name: null, id: null }`
- [ ] `POST /api/check-org-slug` with inactive org → `{ exists: false }`
- [ ] `POST /api/check-username` with `organizationId` for member → `{ exists: true }`
- [ ] `POST /api/check-username` with `organizationId` for non-member → `{ exists: false, notInOrg: true }`
- [ ] JWT after login with active org → contains `organizationId`, `organizationSlug`, `orgRole`
- [ ] JWT before `setActiveOrganization` → `organizationId` is null

### Frontend
- [ ] 3-step login: slug → username → password → lands at `/<orgSlug>/dashboard`
- [ ] `?college=iit-bombay` pre-fills slug field
- [ ] Back button: password → username → slug (state preserved)
- [ ] Wrong slug → error toast, stays on step 1
- [ ] Username not in org → "not registered with this college" error
- [ ] Direct navigation to `/<wrong-slug>/dashboard` → redirected to correct org slug
- [ ] No org membership → redirected to `/org-setup`

### Backend
- [ ] Request with JWT containing `organizationId` → passes `require_org_member()`
- [ ] Request with JWT without `organizationId` → 403 from `require_org_member()`
- [ ] Alert query returns only alerts for JWT's org
- [ ] Sensor event query returns only events for JWT's org
- [ ] Entity query scoped to org

### Sensor Pipeline
- [ ] Hikvision poller fails to start if `HIKVISION_ORG_ID` is empty
- [ ] Ingested sensor events have correct `organization_id`
- [ ] Entity resolution scoped to org — same card ID resolves to different entities in different orgs

### DeepFace
- [ ] Face registration sends `{org_id}__{entity_id}` label to DeepFace
- [ ] Webhook handler parses namespaced label correctly
- [ ] Alert triggered by DeepFace event has correct `organization_id`

---

## 13. Quick Reference

### Files to Create (NEW)
| File | Purpose |
|------|---------|
| `apps/api/migrations/add_organization_id.py` | Plain SQL migration for org_id columns |
| `apps/api/scripts/migrate_face_namespaces.py` | One-time DeepFace label migration |
| `apps/web/src/app/(app)/[orgSlug]/dashboard/layout.tsx` | Org-guard server component |
| `apps/web/src/app/(app)/org-setup/page.tsx` | No-org-membership page |
| `apps/web/src/lib/org-context.tsx` | OrgProvider React context (optional) |

### Files to Modify
| File | Changes |
|------|---------|
| `apps/auth/package.json` | Pin `better-auth` to `^1.5.6` |
| `packages/db/prisma/schema.prisma` | Add org tables + `activeOrganizationId` on session (via CLI) |
| `apps/auth/src/auth.ts` | Add `organization()` plugin, async `definePayload` |
| `apps/auth/src/index.ts` | Add `check-org-slug` endpoint, update `check-username` |
| `apps/api/auth/models.py` | Add org fields to `AuthenticatedUser` |
| `apps/api/auth/dependencies.py` | Add `require_org_member()`, `require_org_admin()` |
| `apps/api/config/__init__.py` | Add `HIKVISION_ORG_ID`, `ARUBA_ORG_ID` settings |
| `apps/api/models/db/sensor_events.py` | Add `organization_id` column |
| `apps/api/models/db/entity_profiles.py` | Add `organization_id` column |
| `apps/api/models/db/entity_identifiers.py` | Add `organization_id`, fix unique constraint |
| `apps/api/models/db/alerts.py` | Add `organization_id` to alerts, staff_profiles, notification_queue |
| `apps/api/models/db/camera_streams.py` | Add `organization_id` |
| `apps/api/models/db/webhooks.py` | Add `organization_id` |
| `apps/api/models/db/push_subscriptions.py` | Add `organization_id` |
| `apps/api/services/event_ingestion_service.py` | Accept + stamp `organization_id` |
| `apps/api/services/entity_resolution_service.py` | Scope queries to `organization_id` |
| `apps/api/services/hikvision_poller.py` | Pass `HIKVISION_ORG_ID` to ingestion service |
| `apps/api/services/aruba_poller.py` | Pass `ARUBA_ORG_ID` to ingestion service |
| `apps/api/services/deepface_client.py` | Add namespace helpers |
| `apps/api/routes/alert_routes.py` | `require_org_member()`, pass org_id to service |
| `apps/api/routes/staff_routes.py` | `require_org_member()`, pass org_id to service |
| `apps/api/routes/deepface_routes.py` | `require_org_member()`, namespaced face labels |
| `apps/api/routes/events_routes.py` | `require_org_member()`, pass org_id to service |
| `apps/api/routes/spatial_routes.py` | `require_org_member()`, pass org_id to service |
| `apps/api/routes/webhook_routes.py` | `require_org_member()`, pass org_id to service |
| `apps/api/routes/notification_routes.py` | `require_org_member()`, pass org_id to service |
| `apps/api/routes/anomaly_routes.py` | `require_org_member()`, pass org_id to service |
| `apps/web/src/lib/auth-client.ts` | Add `organizationClient()` plugin |
| `apps/web/src/lib/auth-server.ts` | Add org fields to `FazriUser` type |
| `apps/web/src/lib/api-client.ts` | Fix 401 redirect to include `?college=<slug>` |
| `apps/web/src/components/auth/SigninForm.tsx` | 3-step state machine |
| `apps/web/src/app/(app)/auth/page.tsx` | Pass `prefillSlug` from `?college=` param |
| `apps/web/src/app/(app)/dashboard/layout.tsx` | Delete — replaced by `[orgSlug]/dashboard/layout.tsx` |

### Files to Move (directory rename)
```
apps/web/src/app/(app)/dashboard/  →  apps/web/src/app/(app)/[orgSlug]/dashboard/
```
All page files inside `dashboard/` move as-is. Only `layout.tsx` changes content.
