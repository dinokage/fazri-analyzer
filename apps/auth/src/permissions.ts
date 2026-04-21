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
import {
  defaultStatements as adminDefaultStatements,
  adminAc as adminPluginDefaults,
} from "better-auth/plugins/admin/access";

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

// ── Admin plugin access control ──────────────────────────────────────────────
// Separate from the organization plugin AC above.
const adminPluginStatement = { ...adminDefaultStatements } as const;
export const adminPluginAc = createAccessControl(adminPluginStatement);

export const superAdminPluginRole = adminPluginAc.newRole({
  ...adminPluginDefaults.statements,
});
export const regularPluginRole = adminPluginAc.newRole({
  user: [],
  session: [],
});
