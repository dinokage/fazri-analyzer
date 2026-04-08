# FAZRI Multi-Tenant Migration — Claude Code Runbook

**Repo**: `github.com/dinokage/fazri-analyzer` branch `core-feature-speedrun`
**Date**: 2026-04-03
**Objective**: Add organization-based multi-tenancy using Better Auth organization plugin.
**Each college = one org. URL slug routing. All data org-scoped.**

---

## Rules for Execution

1. Execute phases strictly in order. Each depends on the previous.
2. Run the verification command after each step. Do not skip.
3. Commit after each phase with the exact message provided.
4. When modifying existing files, preserve all existing behavior — add org scoping on top, do not refactor.
5. When a step says "add to existing file", find the correct location and insert. Do not rewrite the file.
6. If a verification fails, debug and fix before proceeding.

---

## Phase 0: Prerequisites

### Step 0.1 — Upgrade better-auth to ^1.5.6

The project uses `^1.2.7`. The organization plugin API has changed between 1.2 and 1.5 (organizationCreation hooks deprecated, new organizationHooks API, checkSlug endpoint added).

```bash
cd auth && npm install better-auth@^1.5.6
cd .. && pnpm install better-auth@^1.5.6
```

**Verify**:
```bash
grep '"better-auth"' auth/package.json | head -1
grep '"better-auth"' package.json | head -1
# Both should show ^1.5.6 or a resolved version >=1.5.6
```

### Step 0.2 — Set up Alembic in the backend

```bash
cd backend
pip install alembic --break-system-packages
alembic init alembic
```

Edit `backend/alembic/env.py`:
- Set `target_metadata = Base.metadata` (import Base from `database.connection`)
- Set `sqlalchemy.url` from `config.settings.DATABASE_URL` (or from env)
- Add `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` at the top so backend modules are importable

Edit `backend/alembic.ini`:
- Set `script_location = alembic`

Create baseline migration:
```bash
cd backend
alembic revision --autogenerate -m "baseline"
alembic stamp head  # mark current DB state as baseline without running anything
```

**Verify**:
```bash
cd backend && alembic current
# Should show the baseline revision hash with "(head)"
```

**Commit**: `chore: upgrade better-auth to 1.5.6 and set up Alembic`

---

## Phase 1: Auth Layer Setup

### Step 1.1 — Create shared permissions file

Create `auth/src/permissions.ts`:

```typescript
/**
 * Shared permissions definitions — importable from both server AND client.
 * DO NOT import Prisma, database modules, or any server-only code here.
 */
import { createAccessControl } from "better-auth/plugins/access";
import {
  defaultStatements,
  ownerAc,
  adminAc,
  memberAc,
} from "better-auth/plugins/organization/access";

/**
 * FAZRI-specific resource permissions layered on top of Better Auth's
 * built-in org management permissions (member CRUD, invitation CRUD, org update).
 *
 * `as const` is required for TypeScript to infer literal types.
 */
export const statement = {
  ...defaultStatements,
  camera:  ["create", "read", "update", "delete"],
  alert:   ["create", "read", "update", "assign", "resolve", "escalate"],
  staff:   ["create", "read", "update", "delete"],
  face:    ["enroll", "read", "delete"],
  webhook: ["create", "read", "update", "delete"],
  report:  ["read"],
  sensor:  ["read"],
} as const;

export const ac = createAccessControl(statement);

/**
 * Roles. Each merges the built-in org management permissions for that role
 * level (ownerAc, adminAc, memberAc) with FAZRI-specific permissions.
 *
 * Without the spread of built-in permissions, org owners would get 403
 * when trying to manage members, send invitations, or update org settings.
 */
export const ownerRole = ac.newRole({
  ...ownerAc.statements,
  camera:  ["create", "read", "update", "delete"],
  alert:   ["create", "read", "update", "assign", "resolve", "escalate"],
  staff:   ["create", "read", "update", "delete"],
  face:    ["enroll", "read", "delete"],
  webhook: ["create", "read", "update", "delete"],
  report:  ["read"],
  sensor:  ["read"],
});

export const adminRole = ac.newRole({
  ...adminAc.statements,
  camera:  ["create", "read", "update", "delete"],
  alert:   ["create", "read", "update", "assign", "resolve", "escalate"],
  staff:   ["read", "update"],
  face:    ["enroll", "read"],
  webhook: ["create", "read", "update", "delete"],
  report:  ["read"],
  sensor:  ["read"],
});

export const memberRole = ac.newRole({
  ...memberAc.statements,
  camera:  ["read"],
  alert:   ["read"],
  staff:   ["read"],
  face:    ["read"],
  webhook: [],
  report:  ["read"],
  sensor:  ["read"],
});
```

**Verify**:
```bash
cd auth && npx tsx -e "import './src/permissions'; console.log('permissions OK')"
```

### Step 1.2 — Update auth.ts with organization plugin

Replace `auth/src/auth.ts` entirely:

```typescript
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { username, jwt, organization } from "better-auth/plugins";
import { prisma } from "./lib/prisma";
import { ac, ownerRole, adminRole, memberRole } from "./permissions";
import bcrypt from "bcryptjs";

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
    jwt({
      jwks: {
        keyPairConfig: { alg: "RS256" },
      },
      jwt: {
        expirationTime: "30d",
        definePayload: ({ user, session }) => ({
          // Existing fields — preserve exactly
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
          // NEW — org context from session (no DB queries here)
          organizationId:
            (session as Record<string, unknown>).activeOrganizationId ?? null,
        }),
      },
    }),
    organization({
      ac,
      roles: {
        owner: ownerRole,
        admin: adminRole,
        member: memberRole,
      },
      allowUserToCreateOrganization: async (user) => {
        return (user as Record<string, unknown>).role === "SUPER_ADMIN";
      },
      sendInvitationEmail: async (data) => {
        // TODO: Integrate with email provider (SendGrid / SMTP)
        console.log(
          `[FAZRI] Invite ${data.email} to org ${data.organization.name} as ${data.role}`
        );
      },
    }),
  ],

  user: {
    additionalFields: {
      entity_id:   { type: "string", required: true, unique: true },
      username:    { type: "string", required: true, unique: true },
      role:        { type: "string", required: true, defaultValue: "STUDENT" },
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
    cookieCache: { enabled: true, maxAge: 5 * 60 },
  },

  trustedOrigins: (process.env.TRUSTED_ORIGINS ?? "http://localhost:3000").split(
    ","
  ),

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

### Step 1.3 — Generate Prisma schema and migrate

```bash
cd auth
npx @better-auth/cli generate --output prisma
npx prisma migrate dev --name add_organizations
```

This auto-creates the `organization`, `member`, `invitation` tables and adds `activeOrganizationId` to `session`.

**Verify**:
```bash
cd auth && npx prisma db pull --print 2>/dev/null | grep -c "organization\|member\|invitation"
# Should show 3+ matches (the table definitions)
```

### Step 1.4 — Add org check endpoints to auth service

Edit `auth/src/index.ts`. Add these routes AFTER `app.use(express.json());` and BEFORE the existing `app.post("/api/check-username", ...)`:

```typescript
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
```

Then update the existing `app.post("/api/check-username", ...)` to accept optional `organizationSlug` for org-scoped validation. Replace the entire handler:

```typescript
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
```

**Verify**:
```bash
cd auth && npx tsx -e "import './src/index'; console.log('compiles')" 2>&1 | head -5
# Should not show TypeScript errors (may show "listen" log)
```

### Step 1.5 — Update frontend auth client

Replace `src/lib/auth-client.ts`:

```typescript
import { createAuthClient } from "better-auth/react";
import {
  usernameClient,
  jwtClient,
  organizationClient,
} from "better-auth/client/plugins";
import { toast } from "sonner";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_SERVICE_URL,
  plugins: [
    usernameClient(),
    jwtClient(),
    organizationClient(),
  ],
  fetchOptions: {
    onError: async (context) => {
      const status = context.response?.status;
      if (!status || status === 0 || status >= 500) {
        toast.error("Auth service is unreachable. Please try again later.", {
          id: "auth-unreachable",
        });
      }
    },
  },
});

export const { useSession, signOut, getSession } = authClient;
export const { organization } = authClient;
```

**Verify**:
```bash
pnpm exec tsc --noEmit --skipLibCheck 2>&1 | head -10
# Should not show errors related to auth-client.ts
```

**Commit**: `feat: add Better Auth organization plugin with shared permissions and org check endpoints`

---

## Phase 2: Database Migration

### Step 2.1 — Add organization_id column to ALL org-scoped SQLAlchemy models

The following tables ALL need `organization_id = Column(String, nullable=False, index=True)`:

**File: `backend/models/db/alerts.py`** — Add to these classes:
- `StaffProfile` (after `department` field)
- `Alert` (after `is_mock` field)
- `AlertAssignment` (after `unassigned_reason` or last field)
- `AlertAuditLog` (after last field)
- `NotificationQueue` (after last field)
- `NotificationLog` (after last field)

For each class, add this line in the column definitions section:
```python
organization_id = Column(String, nullable=False, index=True, default="default-org")
```

**File: `backend/models/db/camera_streams.py`** — Add to `CameraStream`:
```python
organization_id = Column(String, nullable=False, index=True, default="default-org")
```

**File: `backend/models/db/webhooks.py`** — Add to `OutgoingWebhook`:
```python
organization_id = Column(String, nullable=False, index=True, default="default-org")
```

**File: `backend/models/db/push_subscriptions.py`** — Add to `PushSubscription`:
```python
organization_id = Column(String, nullable=False, index=True, default="default-org")
```

**File: `backend/models/db/sensor_events.py`** — Add to `SensorEventRecord`:
```python
organization_id = Column(String, nullable=True, index=True)
```
Note: `nullable=True` here because the pollers will need to be updated to pass org_id. Existing events won't have it.

**File: `backend/models/db/entity_profiles.py`** — Add to `EntityProfile`:
```python
organization_id = Column(String, nullable=False, index=True, default="default-org")
```

**File: `backend/models/db/entity_identifiers.py`** — Add to `EntityIdentifier`:
```python
organization_id = Column(String, nullable=False, index=True, default="default-org")
```

Import `Column` and `String` are already present in all these files.

**Verify**:
```bash
cd backend && python -c "
from models.db.alerts import Alert, StaffProfile, AlertAssignment, AlertAuditLog, NotificationQueue, NotificationLog
from models.db.camera_streams import CameraStream
from models.db.webhooks import OutgoingWebhook
from models.db.push_subscriptions import PushSubscription
from models.db.sensor_events import SensorEventRecord
from models.db.entity_profiles import EntityProfile
from models.db.entity_identifiers import EntityIdentifier

models = [Alert, StaffProfile, AlertAssignment, AlertAuditLog, NotificationQueue,
          NotificationLog, CameraStream, OutgoingWebhook, PushSubscription,
          SensorEventRecord, EntityProfile, EntityIdentifier]

for m in models:
    cols = [c.name for c in m.__table__.columns]
    assert 'organization_id' in cols, f'{m.__name__} missing organization_id'
    print(f'PASS: {m.__name__}')
print('All models have organization_id')
"
```

### Step 2.2 — Create Alembic migration

```bash
cd backend
alembic revision --autogenerate -m "add_organization_id_to_all_tables"
```

Review the generated migration file. It should add `organization_id` columns to all 12 tables. Then edit it to add the backfill step:

After all `op.add_column(...)` calls, add:

```python
    # Backfill existing data with default-org
    tables_to_backfill = [
        "alerts", "staff_profiles", "alert_assignments", "alert_audit_logs",
        "notification_queue", "notification_logs", "camera_streams",
        "outgoing_webhooks", "push_subscriptions", "entity_profiles",
        "entity_identifiers",
    ]
    for table in tables_to_backfill:
        op.execute(
            f"UPDATE {table} SET organization_id = 'default-org' WHERE organization_id IS NULL"
        )

    # sensor_events stays nullable for now (pollers need updating)
    op.execute(
        "UPDATE sensor_events SET organization_id = 'default-org' WHERE organization_id IS NULL"
    )

    # Composite indexes for hot query paths
    op.create_index("ix_alerts_org_status", "alerts", ["organization_id", "status"])
    op.create_index("ix_alerts_org_created", "alerts", ["organization_id", "created_at"])
    op.create_index("ix_staff_org_duty", "staff_profiles", ["organization_id", "on_duty"])
    op.create_index("ix_cameras_org_status", "camera_streams", ["organization_id", "status"])
    op.create_index("ix_sensor_events_org_ts", "sensor_events", ["organization_id", "timestamp"])
    op.create_index("ix_entity_profiles_org", "entity_profiles", ["organization_id"])
    op.create_index(
        "ix_entity_idents_org_type",
        "entity_identifiers",
        ["organization_id", "identifier_type", "identifier_value"],
    )
```

Run the migration:
```bash
cd backend && alembic upgrade head
```

**Verify**:
```bash
cd backend && python -c "
from sqlalchemy import inspect
from database.connection import engine
inspector = inspect(engine)
for table in ['alerts', 'staff_profiles', 'camera_streams', 'sensor_events',
              'entity_profiles', 'entity_identifiers', 'outgoing_webhooks']:
    cols = [c['name'] for c in inspector.get_columns(table)]
    assert 'organization_id' in cols, f'{table} missing column'
    print(f'PASS: {table}')
print('All tables migrated')
"
```

**Commit**: `feat: add organization_id columns to all org-scoped tables with default-org backfill`

---

## Phase 3: Backend Enforcement

### Step 3.1 — Update AuthenticatedUser model

Edit `backend/auth/models.py`. Add `organizationId` field to `AuthenticatedUser`:

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
    sessionId: Optional[str] = None
    # Multi-tenancy
    organizationId: Optional[str] = None
```

### Step 3.2 — Update get_current_user in dependencies.py

Edit `backend/auth/dependencies.py`. In the `get_current_user` function, update the `AuthenticatedUser` construction to include the new fields:

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
    sessionId=payload.get("sessionId"),
    organizationId=payload.get("organizationId"),
)
```

### Step 3.3 — Add org dependency functions

Add these new dependency functions to `backend/auth/dependencies.py`:

```python
async def require_org_member(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require user to have an active organization set in their JWT."""
    if not current_user.organizationId:
        raise PermissionDeniedError(
            detail="No active organization. Please select a college first."
        )
    return current_user


async def require_org_admin(
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> AuthenticatedUser:
    """
    Require admin or owner role within the active org.

    Checks membership via the auth service so role changes take
    effect immediately without re-login.
    """
    import httpx as _httpx

    try:
        async with _httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/auth/organization/get-full-organization",
                params={"organizationId": current_user.organizationId},
            )
            if resp.status_code == 200:
                data = resp.json()
                members = data.get("members", [])
                user_member = next(
                    (m for m in members if m.get("userId") == current_user.id),
                    None,
                )
                if user_member and user_member.get("role") in ("owner", "admin"):
                    return current_user
    except Exception:
        pass

    raise PermissionDeniedError(detail="Admin access required for this organization.")
```

Add the `settings` import at the top of the file if not already present:
```python
from config import settings
```

**Verify**:
```bash
cd backend && python -c "
from auth.dependencies import get_current_user, require_org_member, require_org_admin, require_staff, require_admin
print('All dependencies import OK')
"
```

### Step 3.4 — Update alert_cooldown.py for org-scoped keys

Edit `backend/services/alert_cooldown.py`. Change the `cooldown_key` function:

**Current**:
```python
def cooldown_key(anomaly_type: str, source_device: str, entity_key: str) -> str:
    return f"fazri:alert_cd:{anomaly_type}:{source_device}:{entity_key}"
```

**New** — add `organization_id` parameter:
```python
def cooldown_key(anomaly_type: str, source_device: str, entity_key: str, organization_id: str = "default-org") -> str:
    return f"fazri:alert_cd:{organization_id}:{anomaly_type}:{source_device}:{entity_key}"
```

Update `set_alert_cooldown` and `delete_alert_cooldown` signatures to accept and pass through `organization_id`:

```python
def set_alert_cooldown(
    anomaly_type: str,
    source_device: str,
    entity_key: str,
    organization_id: str = "default-org",
) -> bool:
    # ... body unchanged except:
    key = cooldown_key(anomaly_type, source_device, entity_key, organization_id)
    # ...

def delete_alert_cooldown(
    anomaly_type: str,
    source_device: str,
    entity_key: str,
    organization_id: str = "default-org",
) -> None:
    # ... body unchanged except:
    key = cooldown_key(anomaly_type, source_device, entity_key, organization_id)
    # ...
```

### Step 3.5 — Update EventIngestionService to accept organization_id

Edit `backend/services/event_ingestion_service.py`.

Update the `ingest` method signature:
```python
async def ingest(self, event: SensorEvent, organization_id: str = "default-org") -> Optional[ResolvedEvent]:
```

In the `_persist` method, add `organization_id` to the record:
```python
def _persist(self, event: SensorEvent, organization_id: str = "default-org") -> None:
    metadata = dict(event.metadata) if event.metadata else {}
    record = SensorEventRecord(
        # ... existing fields ...
        organization_id=organization_id,
    )
```

Update `_create_alert` to pass `organization_id`:
```python
async def _create_alert(
    self,
    resolved: ResolvedEvent,
    anomaly: dict,
    organization_id: str = "default-org",
) -> None:
```

In the `_create_alert` body, pass `organization_id` to `set_alert_cooldown`:
```python
if not set_alert_cooldown(anomaly_type, source_device, entity_key, organization_id):
```

And add `organization_id` when creating the alert:
```python
alert_data = AlertCreate(
    # ... existing fields ...
)
# Pass organization_id to the alert service
alert_svc = _get_alert_service(self.db)
alert = alert_svc.create_alert(
    alert_data=alert_data,
    actor_type=ActorType.SYSTEM,
    organization_id=organization_id,
)
```

Update `ingest_batch`:
```python
async def ingest_batch(
    self, events: List[SensorEvent], organization_id: str = "default-org",
) -> List[Optional[ResolvedEvent]]:
    results: List[Optional[ResolvedEvent]] = []
    for event in events:
        result = await self.ingest(event, organization_id=organization_id)
        results.append(result)
    return results
```

### Step 3.6 — Update EntityResolutionService to scope by organization_id

Edit `backend/services/entity_resolution_service.py`.

Update the `resolve` method to accept and filter by `organization_id`:

```python
def resolve(
    self,
    identifier_type: str,
    identifier_value: str,
    organization_id: str = "default-org",
    db: Optional[Session] = None,
) -> Optional[EntityProfileDTO]:
```

In the query, add the organization_id filter:
```python
ident_query = db.query(EntityIdentifier).filter(
    EntityIdentifier.identifier_type == identifier_type,
    EntityIdentifier.organization_id == organization_id,
    EntityIdentifier.active == True,
)
```

Update `bulk_import_from_csv` to accept `organization_id`:
```python
def bulk_import_from_csv(
    self,
    csv_path: str,
    organization_id: str = "default-org",
    mapping: Optional[dict] = None,
    db: Optional[Session] = None,
) -> dict:
```

In the body, set `organization_id` on both the `EntityProfile` and `EntityIdentifier` records during upsert.

### Step 3.7 — Add organization_id to Hikvision and Aruba pollers

Edit `backend/config/__init__.py`. Add these settings:
```python
# Organization scoping for pollers (single-campus deployment)
HIKVISION_ORGANIZATION_ID: str = "default-org"
ARUBA_ORGANIZATION_ID: str = "default-org"
```

Edit `backend/services/hikvision_poller.py`. Pass `organization_id` to `ingest_batch`:
```python
results = await svc.ingest_batch(
    events,
    organization_id=settings.HIKVISION_ORGANIZATION_ID,
)
```

Edit `backend/services/aruba_poller.py`. Same pattern:
```python
results = await svc.ingest_batch(
    events,
    organization_id=settings.ARUBA_ORGANIZATION_ID,
)
```

### Step 3.8 — Update AlertService.create_alert to accept organization_id

Edit `backend/services/alerts/alert_service.py`.

Update `create_alert` method signature:
```python
def create_alert(
    self,
    alert_data,
    actor_type,
    actor_id=None,
    organization_id: str = "default-org",
):
```

In the body, set `organization_id` on the Alert object:
```python
alert = Alert(
    # ... existing fields ...
    organization_id=organization_id,
)
```

Update `get_alerts` to filter by `organization_id`:
```python
def get_alerts(self, organization_id: str = None, **kwargs):
    query = self.db.query(Alert)
    if organization_id:
        query = query.filter(Alert.organization_id == organization_id)
    # ... rest of existing filter logic unchanged ...
```

### Step 3.9 — Update route handlers to use require_org_member

This is the bulk of the work. For each route file, change the dependency from `require_staff()` or `get_current_user` to `require_org_member`, and pass `user.organizationId` to service methods.

**Pattern for every route handler**:

Before:
```python
current_user: AuthenticatedUser = Depends(require_staff())
```

After:
```python
current_user: AuthenticatedUser = Depends(require_org_member)
```

And update service calls to pass `organization_id=current_user.organizationId`.

Apply this pattern to ALL handlers in:
- `backend/routes/alert_routes.py`
- `backend/routes/staff_routes.py`
- `backend/routes/events_routes.py`
- `backend/routes/spatial_routes.py`
- `backend/routes/webhook_routes.py`
- `backend/routes/notification_routes.py`
- `backend/routes/deepface_routes.py`
- `backend/routes/import_routes.py`
- `backend/entity_routes.py`

**IMPORTANT**: Do not change `require_admin()` dependencies to `require_org_member`. Change them to `require_org_admin` instead for admin-only routes.

Add the new imports at the top of each route file:
```python
from auth.dependencies import require_org_member, require_org_admin
```

**Verify** (after all route changes):
```bash
cd backend && python -c "
import ast
import sys
errors = []
route_files = [
    'routes/alert_routes.py', 'routes/staff_routes.py', 'routes/events_routes.py',
    'routes/spatial_routes.py', 'routes/webhook_routes.py',
    'routes/notification_routes.py', 'routes/deepface_routes.py',
    'routes/import_routes.py', 'entity_routes.py',
]
for f in route_files:
    try:
        with open(f) as fh:
            ast.parse(fh.read())
        print(f'PASS: {f}')
    except SyntaxError as e:
        print(f'FAIL: {f} — {e}')
        errors.append(f)
if errors:
    sys.exit(1)
print('All route files parse OK')
"
```

**Commit**: `feat: enforce organization_id scoping across backend pipeline and all routes`

---

## Phase 4: Frontend Routing

### Step 4.1 — Create org context provider

Create `src/lib/org-context.tsx`:

```tsx
"use client";

import { createContext, useContext } from "react";
import { useSession } from "@/lib/auth-client";

interface OrgContextValue {
  organizationId: string | null;
  organizationSlug: string | null;
  isLoaded: boolean;
}

const OrgCtx = createContext<OrgContextValue>({
  organizationId: null,
  organizationSlug: null,
  isLoaded: false,
});

export function OrgProvider({
  children,
  orgSlug,
}: {
  children: React.ReactNode;
  orgSlug: string;
}) {
  const { data: session, isPending } = useSession();

  return (
    <OrgCtx.Provider
      value={{
        organizationId: (session?.user as any)?.organizationId ?? null,
        organizationSlug: orgSlug,
        isLoaded: !isPending,
      }}
    >
      {children}
    </OrgCtx.Provider>
  );
}

export const useOrg = () => useContext(OrgCtx);
```

### Step 4.2 — Move dashboard routes under [orgSlug]

Create the new directory structure:
```bash
mkdir -p src/app/\(app\)/\[orgSlug\]
mv src/app/\(app\)/dashboard src/app/\(app\)/\[orgSlug\]/dashboard
```

Create `src/app/(app)/[orgSlug]/dashboard/layout.tsx`:

```tsx
import type React from "react";
import { SidebarLayout } from "@/components/sidebar-layout";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AlertNotificationListener } from "@/components/alert-notification-listener";
import { OrgProvider } from "@/lib/org-context";

export default async function OrgDashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ orgSlug: string }>;
}) {
  const { orgSlug } = await params;

  return (
    <OrgProvider orgSlug={orgSlug}>
      <SidebarLayout orgSlug={orgSlug}>
        <AlertNotificationListener enabled pollInterval={10000} />
        <ErrorBoundary>{children}</ErrorBoundary>
      </SidebarLayout>
    </OrgProvider>
  );
}
```

### Step 4.3 — Update sidebar-layout.tsx for dynamic org slug

Edit `src/components/sidebar-layout.tsx`:

1. Accept `orgSlug` as a prop:
```tsx
export function SidebarLayout({
  children,
  orgSlug,
}: {
  children: React.ReactNode;
  orgSlug?: string;
})
```

2. Replace all hardcoded `/dashboard` paths with dynamic paths:
```tsx
const basePath = orgSlug ? `/${orgSlug}/dashboard` : "/dashboard";
```

3. Update every `href` and `isActive` check:
- `"/dashboard"` → `basePath`
- `"/dashboard/alerts"` → `${basePath}/alerts`
- `"/dashboard/cameras"` → `${basePath}/cameras`
- etc.

4. Update the sign-out redirect:
```tsx
router.push("/auth");
```
(This stays the same — auth page is not org-scoped)

### Step 4.4 — Update SigninForm.tsx for 3-step flow

The existing `SigninForm.tsx` has a 2-step flow (username → password) with `AnimatePresence` and `slideVariants`. Extend it to 3 steps (slug → username → password).

Key state additions:
```tsx
type Step = "slug" | "username" | "password";
const [step, setStep] = useState<Step>("slug");
const [orgSlug, setOrgSlug] = useState("");
const [orgName, setOrgName] = useState("");
```

Step 1 handler — validate org slug:
```tsx
const handleSlugContinue = async () => {
  const normalized = orgSlug.trim().toLowerCase();
  if (!normalized) return;
  setOrgSlug(normalized);
  setCheckingSlug(true);
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/api/check-org-slug`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug: normalized }),
      }
    );
    const data = await res.json();
    if (!data.exists) {
      toast.error("No college found with this identifier.");
      setCheckingSlug(false);
      return;
    }
    setOrgName(data.name);
    setDirection(1);
    setStep("username");
  } catch {
    toast.error("Auth service is unreachable.", { id: "auth-unreachable" });
  }
  setCheckingSlug(false);
};
```

Step 2 handler — pass `organizationSlug` to check-username:
```tsx
const handleUsernameContinue = async () => {
  // ... same as existing, but add organizationSlug to body:
  body: JSON.stringify({ username: normalized, organizationSlug: orgSlug }),
  // ... and on failure, use unified error message:
  toast.error(`No account found at ${orgName}.`);
};
```

Step 3 handler — sign in and set active org:
```tsx
const login = async () => {
  setSubmitted(true);
  try {
    const { error } = await authClient.signIn.username({
      username,
      password,
      rememberMe: true,
    });
    if (error) {
      // handle 429, 401 same as before
      setSubmitted(false);
      return;
    }
    // Set active org by slug so the JWT carries organizationId
    await authClient.organization.setActive({ organizationSlug: orgSlug });
    router.push(`/${orgSlug}/dashboard`);
  } catch {
    toast.error("Auth service is unreachable.", { id: "auth-unreachable" });
    setSubmitted(false);
  }
};
```

Back navigation:
```tsx
const goBack = () => {
  setDirection(-1);
  if (step === "password") {
    setStep("username");
    setPassword("");
  } else if (step === "username") {
    setStep("slug");
    setUsername("");
    setOrgName("");
  }
};
```

Update the `AnimatePresence` to render 3 panels based on `step` state ("slug", "username", "password") instead of the current `usernameChecked` boolean.

### Step 4.5 — Create org-setup page

Create `src/app/(app)/org-setup/page.tsx` — a simple page that:
1. Lists orgs the user belongs to (use `authClient.useListOrganizations()`)
2. Shows pending invitations (use `authClient.organization.listInvitations()`)
3. If SUPER_ADMIN, shows a "Create College" form

This is a P1 feature — stub it out with the list and invitation acceptance for now.

### Step 4.6 — Add post-login redirect logic

Edit the auth page (`src/app/(app)/auth/page.tsx`) to accept a `?college=` search param and pass it to SigninForm as `prefillSlug`:

```tsx
export default function AuthPage({
  searchParams,
}: {
  searchParams: Promise<{ college?: string }>;
}) {
  const params = use(searchParams);
  return (
    <Suspense>
      <SigninForm prefillSlug={params.college} />
    </Suspense>
  );
}
```

In SigninForm, if `prefillSlug` is provided, auto-validate on mount:
```tsx
useEffect(() => {
  if (prefillSlug) {
    setOrgSlug(prefillSlug);
    handleSlugContinue();
  }
}, []);
```

**Verify**:
```bash
pnpm exec tsc --noEmit --skipLibCheck 2>&1 | grep -c "error TS"
# Should be 0
```

**Commit**: `feat: add [orgSlug] routing, 3-step login flow, and OrgProvider context`

---

## Phase 5: DeepFace Namespace

### Step 5.1 — Create namespace helpers

Create `backend/services/face_namespace.py`:

```python
"""
Face embedding namespace helpers for multi-tenant DeepFace.

Face labels in DeepFace are namespaced as: {org_id}/{entity_id}
The `/` separator is used because it is illegal in both Better Auth
org IDs (CUIDs) and FAZRI entity IDs (alphanumeric + underscore).
"""

from __future__ import annotations
from typing import Tuple


def build_namespaced_face_id(org_id: str, entity_id: str) -> str:
    """Build a namespaced face label for DeepFace storage."""
    return f"{org_id}/{entity_id}"


def parse_namespaced_face_id(namespaced_id: str) -> Tuple[str, str]:
    """
    Parse a namespaced face label back to (org_id, entity_id).

    Returns ("", original_id) for legacy un-namespaced labels.
    """
    parts = namespaced_id.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", namespaced_id
```

### Step 5.2 — Update deepface_routes.py face registration

In `backend/routes/deepface_routes.py`, find the `register_face` endpoint. Update it to use namespaced IDs:

```python
from services.face_namespace import build_namespaced_face_id

# In the register_face handler, where entity_id is used as the face label:
namespaced_id = build_namespaced_face_id(user.organizationId, entity_id)
# Use namespaced_id wherever the current code uses entity_id as the DeepFace label
```

### Step 5.3 — Update deepface webhook handler

In the `deepface_webhook` handler, parse the namespaced ID:

```python
from services.face_namespace import parse_namespaced_face_id

# Where the current code does: face_id = match.img_name
face_id_raw = match.img_name
org_id, entity_id = parse_namespaced_face_id(face_id_raw)

# Use entity_id for entity resolution
# Use org_id as the organization_id for alert creation (with fallback to stream's org)
resolved_org_id = org_id or stream.organization_id if stream else "default-org"
```

### Step 5.4 — Update go2rtc stream names

In the stream registration code, namespace go2rtc stream names:

```python
go2rtc_stream_name = f"{user.organizationId}/{body.stream_id}"
```

### Step 5.5 — Write face embedding migration script

Create `backend/scripts/migrate_face_embeddings.py`:

```python
"""
One-time migration: rename face embedding labels from entity_id to org_id/entity_id.

Usage:
    python scripts/migrate_face_embeddings.py --org-id default-org --dry-run
    python scripts/migrate_face_embeddings.py --org-id default-org
"""
import argparse
import psycopg2

def migrate(org_id: str, dry_run: bool, deepface_db_url: str):
    conn = psycopg2.connect(deepface_db_url)
    cur = conn.cursor()

    # Find all face embeddings that don't already have a / prefix
    cur.execute("SELECT DISTINCT img_name FROM face_embeddings WHERE img_name NOT LIKE '%/%'")
    rows = cur.fetchall()

    print(f"Found {len(rows)} un-namespaced face labels")

    for (img_name,) in rows:
        new_name = f"{org_id}/{img_name}"
        if dry_run:
            print(f"  DRY RUN: {img_name} -> {new_name}")
        else:
            cur.execute(
                "UPDATE face_embeddings SET img_name = %s WHERE img_name = %s",
                (new_name, img_name),
            )

    if not dry_run:
        conn.commit()
        print(f"Migrated {len(rows)} labels")
    else:
        print(f"Dry run complete — {len(rows)} labels would be migrated")

    cur.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--org-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--deepface-db-url", default="postgresql://deepface:deepface@localhost:5432/deepface")
    args = parser.parse_args()
    migrate(args.org_id, args.dry_run, args.deepface_db_url)
```

**Commit**: `feat: namespace DeepFace face embeddings and go2rtc streams by organization_id`

---

## Phase 6: Seed Default Organization

### Step 6.1 — Create default-org in Better Auth

Create `backend/scripts/seed_default_org.py`:

```python
"""
Seed the default organization in Better Auth's database.

Run this ONCE after Phase 1 migrations to create the org that existing
data is backfilled to.

Usage:
    python scripts/seed_default_org.py
"""
import os
import sys
import psycopg2
from datetime import datetime, timezone

AUTH_DB_URL = os.getenv("AUTH_DATABASE_URL", "postgresql://postgres:password@localhost:5432/fazri_auth")

def seed():
    conn = psycopg2.connect(AUTH_DB_URL)
    cur = conn.cursor()

    org_id = "default-org"
    now = datetime.now(timezone.utc)

    # Check if already exists
    cur.execute("SELECT id FROM organization WHERE id = %s", (org_id,))
    if cur.fetchone():
        print(f"Organization '{org_id}' already exists — skipping")
        cur.close()
        conn.close()
        return

    cur.execute(
        """
        INSERT INTO organization (id, name, slug, "createdAt", "updatedAt")
        VALUES (%s, %s, %s, %s, %s)
        """,
        (org_id, "Default Campus", "default", now, now),
    )
    conn.commit()
    print(f"Created organization: id={org_id} slug=default name='Default Campus'")

    cur.close()
    conn.close()

if __name__ == "__main__":
    seed()
```

### Step 6.2 — Assign existing SUPER_ADMIN users to default-org

After seeding the org, assign existing admin users as owners:

```python
# Add to seed_default_org.py or run separately:
cur.execute("SELECT id FROM \"user\" WHERE role = 'SUPER_ADMIN'")
admins = cur.fetchall()
for (user_id,) in admins:
    cur.execute(
        """
        INSERT INTO member (id, "organizationId", "userId", role, "createdAt")
        VALUES (gen_random_uuid()::text, %s, %s, 'owner', %s)
        ON CONFLICT DO NOTHING
        """,
        ("default-org", user_id, now),
    )
print(f"Assigned {len(admins)} SUPER_ADMIN users as owners of default-org")
```

**Commit**: `feat: seed default organization and assign existing admin users`

---

## Final Verification

### Check 1: Auth service starts with organization plugin

```bash
cd auth && npm run dev &
sleep 3
curl -s http://localhost:4000/health | jq .
curl -s -X POST http://localhost:4000/api/check-org-slug \
  -H "Content-Type: application/json" \
  -d '{"slug": "default"}' | jq .
# Expected: { "exists": true, "name": "Default Campus" }
```

### Check 2: Backend starts with org-scoped models

```bash
cd backend && python -c "from main import app; print('FastAPI app created OK')"
```

### Check 3: Frontend compiles

```bash
pnpm build 2>&1 | tail -5
# Should complete without errors
```

### Check 4: No hardcoded /dashboard paths remain in sidebar

```bash
grep -n '"/dashboard' src/components/sidebar-layout.tsx | grep -v "basePath\|orgSlug"
# Expected: zero matches (all paths should use basePath variable)
```

---

## Files Changed Summary

| File | Change Type | Phase |
|------|-------------|-------|
| `auth/package.json` | Modified (upgrade) | 0 |
| `package.json` | Modified (upgrade) | 0 |
| `backend/alembic/` | New directory | 0 |
| `auth/src/permissions.ts` | **New file** | 1 |
| `auth/src/auth.ts` | Replaced | 1 |
| `auth/prisma/schema.prisma` | Auto-generated | 1 |
| `auth/src/index.ts` | Modified (2 endpoints) | 1 |
| `src/lib/auth-client.ts` | Modified | 1 |
| `backend/models/db/alerts.py` | Modified (org_id × 6 models) | 2 |
| `backend/models/db/camera_streams.py` | Modified | 2 |
| `backend/models/db/webhooks.py` | Modified | 2 |
| `backend/models/db/push_subscriptions.py` | Modified | 2 |
| `backend/models/db/sensor_events.py` | Modified | 2 |
| `backend/models/db/entity_profiles.py` | Modified | 2 |
| `backend/models/db/entity_identifiers.py` | Modified | 2 |
| `backend/alembic/versions/xxx_add_org_id.py` | **New file** | 2 |
| `backend/auth/models.py` | Modified | 3 |
| `backend/auth/dependencies.py` | Modified (2 new deps) | 3 |
| `backend/services/alert_cooldown.py` | Modified | 3 |
| `backend/services/event_ingestion_service.py` | Modified | 3 |
| `backend/services/entity_resolution_service.py` | Modified | 3 |
| `backend/services/hikvision_poller.py` | Modified | 3 |
| `backend/services/aruba_poller.py` | Modified | 3 |
| `backend/services/alerts/alert_service.py` | Modified | 3 |
| `backend/config/__init__.py` | Modified (2 new settings) | 3 |
| `backend/routes/alert_routes.py` | Modified (all handlers) | 3 |
| `backend/routes/staff_routes.py` | Modified (all handlers) | 3 |
| `backend/routes/events_routes.py` | Modified | 3 |
| `backend/routes/spatial_routes.py` | Modified | 3 |
| `backend/routes/webhook_routes.py` | Modified | 3 |
| `backend/routes/notification_routes.py` | Modified | 3 |
| `backend/routes/deepface_routes.py` | Modified | 3+5 |
| `backend/routes/import_routes.py` | Modified | 3 |
| `backend/entity_routes.py` | Modified | 3 |
| `src/lib/org-context.tsx` | **New file** | 4 |
| `src/app/(app)/[orgSlug]/dashboard/layout.tsx` | **New file** | 4 |
| `src/app/(app)/[orgSlug]/dashboard/*` | Moved from dashboard/ | 4 |
| `src/components/sidebar-layout.tsx` | Modified (dynamic paths) | 4 |
| `src/components/auth/SigninForm.tsx` | Modified (3-step flow) | 4 |
| `src/app/(app)/auth/page.tsx` | Modified (prefillSlug) | 4 |
| `src/app/(app)/org-setup/page.tsx` | **New file** | 4 |
| `backend/services/face_namespace.py` | **New file** | 5 |
| `backend/scripts/migrate_face_embeddings.py` | **New file** | 5 |
| `backend/scripts/seed_default_org.py` | **New file** | 6 |
