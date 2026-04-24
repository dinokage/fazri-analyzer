import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { username, jwt, organization, admin } from "better-auth/plugins";
import { sso } from "@better-auth/sso";
import { prisma } from "@fazri/db";
import { ac, ownerRole, adminRole, memberRole, adminPluginAc, superAdminPluginRole, regularPluginRole } from "./permissions";
import bcrypt from "bcryptjs";

let _ssoProviderIds: string[] | null = null;
const trustedProviders: string[] = new Proxy([] as string[], {
  get(target, prop, receiver) {
    if (prop === "includes") {
      return (providerId: string) =>
        target.includes(providerId) || (_ssoProviderIds ?? []).includes(providerId);
    }
    return Reflect.get(target, prop, receiver);
  },
});

export function refreshSSOProviderIds() {
  prisma.ssoProvider
    .findMany({ select: { providerId: true } })
    .then((providers: { providerId: string }[]) => { _ssoProviderIds = providers.map((p) => p.providerId); })
    .catch(() => { _ssoProviderIds = []; });
}
refreshSSOProviderIds();

export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: "postgresql" }),

  emailAndPassword: {
    enabled: false,
    password: {
      hash: async (password) => bcrypt.hash(password, 10),
      verify: async ({ hash, password }) => bcrypt.compare(password, hash),
    },
  },

  databaseHooks: {
    user: {
      create: {
        before: async (user) => {
          if (!(user as Record<string, unknown>).entity_id) {
            return {
              data: {
                ...user,
                entity_id: crypto.randomUUID(),
                username: (user as Record<string, unknown>).username ?? user.email,
              },
            };
          }
        },
      },
    },
    session: {
      create: {
        before: async (session) => {
          const member = await prisma.member.findFirst({
            where: { userId: session.userId },
            orderBy: { createdAt: "asc" },
          });
          return {
            data: {
              ...session,
              activeOrganizationId: member?.organizationId ?? null,
            },
          };
        },
      },
    },
  },

  plugins: [
    username(),
    jwt({
      jwks: {
        keyPairConfig: {
          alg: "RS256",
        },
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
    admin({
      ac: adminPluginAc,
      roles: {
        SUPER_ADMIN: superAdminPluginRole,
        STUDENT: regularPluginRole,
        STAFF: regularPluginRole,
        FACULTY: regularPluginRole,
      },
      adminRoles: ["SUPER_ADMIN"],
      defaultRole: "STUDENT",
    }),
    sso({
      trustEmailVerified: true,
      provisionUser: async ({ user, provider }) => {
        try {
          const ssoProvider = await prisma.ssoProvider.findUnique({
            where: { providerId: provider.providerId },
            select: { organizationId: true },
          });
          if (!ssoProvider?.organizationId) return;

          const existing = await prisma.member.findFirst({
            where: { userId: user.id, organizationId: ssoProvider.organizationId },
          });
          if (existing) return;

          await prisma.member.create({
            data: {
              id: crypto.randomUUID(),
              userId: user.id,
              organizationId: ssoProvider.organizationId,
              role: "member",
              createdAt: new Date(),
            },
          });
        } catch (err) {
          console.error("SSO provisionUser error:", err);
        }
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
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60,
    },
  },

  account: {
    accountLinking: {
      enabled: true,
      trustedProviders,
    },
    skipStateCookieCheck: true,
  },

  trustedOrigins: (_request) => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getAllOrigins } = require("./trusted-origins-cache") as typeof import("./trusted-origins-cache");
    return getAllOrigins();
  },

  advanced: {
    crossSubDomainCookies: {
      enabled: true,
      domain: process.env.COOKIE_DOMAIN ?? ".rayzrsole.com",
    },
    defaultCookieAttributes: {
      sameSite: "none" as const,
      secure: true,
    },
  },

  secret: process.env.BETTER_AUTH_SECRET!,
  baseURL: process.env.AUTH_SERVICE_URL ?? "http://localhost:4000",
});

export type Auth = typeof auth;
