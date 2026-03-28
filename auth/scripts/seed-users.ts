/**
 * Seed script: CSV → better-auth PostgreSQL
 * Reads student_staff_profiles.csv and bulk-inserts users + credential accounts.
 * Default password for every user is their entity_id (e.g. "E100000").
 * Safe to re-run — ON CONFLICT DO NOTHING skips already-seeded rows.
 *
 * Usage:
 *   npx tsx scripts/seed-users.ts [path/to/student_staff_profiles.csv]
 *
 * Default CSV path: ../../backend/augmented/student_staff_profiles.csv
 */

import "dotenv/config";
import fs from "fs";
import path from "path";
import readline from "readline";
import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

const BATCH_SIZE = 500;
const BCRYPT_ROUNDS = 10;

const ROLE_MAP: Record<string, string> = {
  student: "STUDENT",
  staff: "STAFF",
  faculty: "FACULTY",
};

interface CsvRow {
  entity_id: string;
  name: string;
  role: string;
  email: string;
  department: string;
  student_id: string;
  staff_id: string;
  card_id: string;
  device_hash: string;
  face_id: string;
}

async function parseCsv(filePath: string): Promise<CsvRow[]> {
  const rows: CsvRow[] = [];
  const rl = readline.createInterface({
    input: fs.createReadStream(filePath),
    crlfDelay: Infinity,
  });

  let headers: string[] = [];
  let isFirst = true;

  for await (const line of rl) {
    if (isFirst) {
      headers = line.split(",").map((h) => h.trim());
      isFirst = false;
      continue;
    }
    if (!line.trim()) continue;
    const values = line.split(",");
    const row = Object.fromEntries(
      headers.map((h, i) => [h, (values[i] ?? "").trim()])
    ) as CsvRow;
    rows.push(row);
  }

  return rows;
}

async function seed(csvPath: string) {
  console.log(`Reading CSV: ${csvPath}`);
  const rows = await parseCsv(csvPath);
  console.log(`Found ${rows.length} rows — hashing passwords and seeding...`);

  let inserted = 0;
  let skipped = 0;

  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    const batch = rows.slice(i, i + BATCH_SIZE);

    // Hash the shared default password once per batch
    const hashed = await bcrypt.hash(process.env.DEFAULT_SEED_PASSWORD ?? "change-me", BCRYPT_ROUNDS);

    // Bulk insert users — skip on conflict
    await prisma.$executeRaw`
      INSERT INTO "user" (
        "id", "entity_id", "name", "role", "email",
        "department", "student_id", "staff_id", "card_id",
        "device_hash", "face_id", "password", "username",
        "emailVerified", "createdAt", "updatedAt"
      )
      SELECT
        u."id", u."entity_id", u."name", u."role"::\"UserRole\", u."email",
        NULLIF(u."department", ''), NULLIF(u."student_id", ''), NULLIF(u."staff_id", ''),
        NULLIF(u."card_id", ''), NULLIF(u."device_hash", ''), NULLIF(u."face_id", ''),
        u."password", u."entity_id",
        false, NOW(), NOW()
      FROM json_to_recordset(${JSON.stringify(
        batch.map((row, idx) => ({
          id: crypto.randomUUID(),
          entity_id: row.entity_id,
          name: row.name,
          role: ROLE_MAP[row.role.toLowerCase()] ?? "STUDENT",
          email: row.email || `${row.entity_id}@internal.fazri`,
          department: row.department,
          student_id: row.student_id,
          staff_id: row.staff_id,
          card_id: row.card_id,
          device_hash: row.device_hash,
          face_id: row.face_id,
          password: hashed,
        }))
      )}::json) AS u(
        "id" text, "entity_id" text, "name" text, "role" text, "email" text,
        "department" text, "student_id" text, "staff_id" text, "card_id" text,
        "device_hash" text, "face_id" text, "password" text
      )
      ON CONFLICT DO NOTHING
    `;

    // Bulk insert credential accounts for the seeded users
    await prisma.$executeRaw`
      INSERT INTO "account" ("id", "accountId", "providerId", "userId", "password", "createdAt", "updatedAt")
      SELECT
        gen_random_uuid()::text,
        u."id",
        'credential',
        u."id",
        u."password",
        NOW(),
        NOW()
      FROM "user" u
      WHERE u."entity_id" = ANY(${batch.map((r) => r.entity_id)}::text[])
      ON CONFLICT ("providerId", "accountId") DO NOTHING
    `;

    inserted += batch.length;
    process.stdout.write(`\r  Processed ${inserted}/${rows.length}...`);
  }

  // Count actual rows to show skipped
  const total = await prisma.user.count();
  skipped = rows.length - (total < rows.length ? total : rows.length - skipped);

  console.log(`\n\nDone.`);
  console.log(`  Users in DB:  ${total}`);
  console.log(`  Default password = set via DEFAULT_SEED_PASSWORD env var`);
}

const csvPath =
  process.argv[2] ??
  path.resolve(__dirname, "../../backend/augmented/student_staff_profiles.csv");

if (!fs.existsSync(csvPath)) {
  console.error(`CSV not found: ${csvPath}`);
  process.exit(1);
}

seed(csvPath)
  .catch(console.error)
  .finally(() => prisma.$disconnect());
