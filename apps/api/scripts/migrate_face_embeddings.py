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
    parser.add_argument(
        "--deepface-db-url",
        default="postgresql://deepface:deepface@localhost:5432/deepface",
    )
    args = parser.parse_args()
    migrate(args.org_id, args.dry_run, args.deepface_db_url)
