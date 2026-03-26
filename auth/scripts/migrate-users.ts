/**
 * One-time migration script: NextAuth → better-auth
 * Uses raw SQL for bulk operations — migrates 7000+ users in seconds.
 */

import "dotenv/config";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  console.log("Starting bulk user migration...");

  // 1. Set username = entity_id for all users in one query
  const usernameResult = await prisma.$executeRaw`
    UPDATE "user"
    SET "username" = "entity_id"
    WHERE "username" IS NULL OR "username" = ''
  `;
  console.log(`✓ Set username for ${usernameResult} users`);

  // 2. Set placeholder email for users without one
  const emailResult = await prisma.$executeRaw`
    UPDATE "user"
    SET "email" = "entity_id" || '@internal.fazri'
    WHERE "email" IS NULL OR "email" = ''
  `;
  console.log(`✓ Set placeholder email for ${emailResult} users`);

  // 3. Bulk-insert account records for all users that have a password
  //    ON CONFLICT DO NOTHING skips already-migrated users safely
  const accountResult = await prisma.$executeRaw`
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
    WHERE u."password" IS NOT NULL
    ON CONFLICT ("providerId", "accountId") DO NOTHING
  `;
  console.log(`✓ Created ${accountResult} credential account records`);

  console.log("\nMigration complete.");
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
