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

AUTH_DB_URL = os.getenv(
    "AUTH_DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/fazri_auth",
)


def seed():
    conn = psycopg2.connect(AUTH_DB_URL)
    cur = conn.cursor()

    org_id = "default-org"
    now = datetime.now(timezone.utc)

    # Insert org only if it doesn't already exist
    cur.execute("SELECT id FROM organization WHERE id = %s", (org_id,))
    if not cur.fetchone():
        cur.execute(
            """
            INSERT INTO organization (id, name, slug, "createdAt")
            VALUES (%s, %s, %s, %s)
            """,
            (org_id, "Default Campus", "default", now),
        )
        conn.commit()
        print(f"Created organization: id={org_id} slug=default name='Default Campus'")
    else:
        print(f"Organization '{org_id}' already exists — skipping insert")

    # Always backfill SUPER_ADMIN users as owners (ON CONFLICT DO NOTHING keeps it idempotent)
    cur.execute("SELECT id FROM \"user\" WHERE role = 'SUPER_ADMIN'")
    admins = cur.fetchall()
    for (user_id,) in admins:
        cur.execute(
            """
            INSERT INTO member (id, "organizationId", "userId", role, "createdAt")
            VALUES (gen_random_uuid()::text, %s, %s, 'owner', %s)
            ON CONFLICT DO NOTHING
            """,
            (org_id, user_id, now),
        )
    conn.commit()
    print(f"Assigned {len(admins)} SUPER_ADMIN users as owners of {org_id}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    seed()
