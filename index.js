// scripts/importUsersWithRoles.js (UPDATED FOR USER MODEL & DEBUGGING)
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcrypt';
import fs from 'fs';
import csv from 'csv-parser';
import { UserRole } from '@prisma/client'; // Import UserRole enum for type safety (optional for script but good practice)

const prisma = new PrismaClient();

// <<< DOUBLE-CHECK THESE VALUES CAREFULLY >>>
const commonPassword = "Ethos@123"; // <<< THE ACTUAL PASSWORD FOR ALL USERS (EXCEPT PERHAPS ADMIN IF ADMIN HAS A DIFFERENT ONE)
const superAdminEntityId = "super_admin_ethos"; // <<< A UNIQUE IDENTIFIER FOR YOUR SUPER ADMIN. SHOULD NOT CONFLICT WITH CSV ENTITY_IDs.
const superAdminEmail = "admin@rdpdc.in";
const csvFilePath = "profile.csv";
const saltRounds = 10; // Standard number of salt rounds for bcrypt

// Renamed function to reflect User model
async function importUsersWithRoles() {
    try {
      const hashedPassword = await bcrypt.hash(commonPassword, saltRounds);
      console.log('[IMPORT DEBUG] Common password being hashed:', commonPassword); // DEBUG LOG
      console.log('[IMPORT DEBUG] Generated hash:', hashedPassword); // DEBUG LOG
      console.log('Common password hashed.');

      const usersToCreate = []; // Renamed array

      // Read and process the CSV
      console.log(`Reading CSV from ${csvFilePath}...`);
      await new Promise((resolve, reject) => {
        fs.createReadStream(csvFilePath)
          .pipe(csv())
          .on('data', (row) => {
            let roleEnum;
            const csvRole = row.role ? row.role.toLowerCase() : '';

            switch (csvRole) {
              case 'student':
                roleEnum = UserRole.STUDENT; // Use enum for assignment
                break;
              case 'staff':
                roleEnum = UserRole.STAFF; // Use enum for assignment
                break;
              case 'faculty':
                roleEnum = UserRole.FACULTY; // Use enum for assignment
                break;
              default:
                console.warn(`Warning: Unknown role "${row.role}" for entity ${row.entity_id}. Defaulting to STUDENT.`);
                roleEnum = UserRole.STUDENT; // Default using enum
                break;
            }

            usersToCreate.push({
              entity_id: row.entity_id,
              name: row.name || null,
              role: roleEnum, // Assign mapped role as enum type
              email: row.email || null,
              department: row.department || null,
              student_id: row.student_id || null,
              staff_id: row.staff_id || null,
              card_id: row.card_id || null,
              device_hash: row.device_hash || null,
              face_id: row.face_id || null,
              password: hashedPassword, // Assign common hashed password
              // Add other fields from your User model here if they come from CSV or need default
              // e.g., emailVerified: null, image: null,
            });
          })
          .on('end', () => {
            console.log(`Finished reading CSV. Found ${usersToCreate.length} users.`); // Renamed log
            resolve();
          })
          .on('error', (error) => {
            console.error("Error reading CSV:", error);
            reject(error);
          });
      });

      // Batch create or update users
      console.log('Inserting/updating users from CSV...');
      const transaction = usersToCreate.map(data =>
        prisma.user.upsert({ // <<< CHANGED from prisma.entity to prisma.user
          where: { entity_id: data.entity_id },
          update: data,
          create: data,
        })
      );
      const createdUsers = await prisma.$transaction(transaction); // Renamed variable
      console.log(`Processed ${createdUsers.length} CSV users.`);

      // Create/update the SUPER_ADMIN user
      console.log(`Checking for existing Super Admin with entity_id: ${superAdminEntityId}...`);
      // Validate that superAdminEntityId is not one of the CSV entity_ids
      if (usersToCreate.some(user => user.entity_id === superAdminEntityId)) {
        console.error(`ERROR: Super Admin entity_id "${superAdminEntityId}" conflicts with an entity_id in the CSV.`);
        console.error('Please choose a unique superAdminEntityId not present in profile.csv.');
        process.exit(1); // Exit with an error
      }

      const superAdminData = {
        entity_id: superAdminEntityId,
        password: hashedPassword, // Same common password for admin
        name: "Super Admin",
        role: UserRole.SUPER_ADMIN, // Explicitly set role using enum
        email: superAdminEmail,
        // Add other fields from your User model here if they need default for admin
        // e.g., emailVerified: null, image: null,
      };

      const superAdmin = await prisma.user.upsert({ // <<< CHANGED from prisma.entity to prisma.user
        where: { entity_id: superAdminEntityId },
        update: superAdminData,
        create: superAdminData,
      });
      console.log('Super Admin created/updated:', superAdmin);

      console.log('Database import and setup complete!');

    } catch (error) {
      console.error('Error during import and setup:', error);
    } finally {
      await prisma.$disconnect();
    }
  }

// Renamed function call
importUsersWithRoles();