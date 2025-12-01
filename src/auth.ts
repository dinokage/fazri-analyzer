import { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { Adapter } from "next-auth/adapters";
import { PrismaAdapter } from "@auth/prisma-adapter";
import { PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/prisma";
import bcrypt from "bcrypt";
import { UserRole } from "@prisma/client";

function CustomPrismaAdapter(p: PrismaClient): Adapter {
  const origin = PrismaAdapter(p);
  return {
    ...origin,
    deleteSession: async (sessionToken: string) => {
      try {
        return await p.session.delete({ where: { sessionToken } });
      } catch (e) {
        console.error("Failed to delete session", e);
        return null;
      }
    },
  } as unknown as Adapter;
}

export const OPTIONS: NextAuthOptions = {
    adapter: CustomPrismaAdapter(prisma),
    secret: process.env.NEXTAUTH_SECRET,

    providers: [
      CredentialsProvider({
        name: "Credentials",
        credentials: {
          entity_id: { label: "Entity ID", type: "text" },
          password: { label: "Password", type: "password" },
        },
        async authorize(credentials) {
          if (!credentials?.entity_id || !credentials?.password) {
            return null; 
          }

          const user = await prisma.user.findUnique({
            where: { entity_id: credentials.entity_id },
          });

          if (!user) {
            return null; // No user found
          }

          const isValidPassword = await bcrypt.compare(
            credentials.password,
            user.password
          );

          if (!isValidPassword) {
            return null; // Password does not match
          }

          return {
            id: user.id,
            entity_id: user.entity_id,
            name: user.name || user.entity_id,
            email: user.email,
            role: user.role, 
            face_id: user.face_id, 
            student_id: user.student_id,
            staff_id: user.staff_id,
            department: user.department,

          };
        },
      }),
    ],

    session: {
      strategy: "jwt",
      maxAge: 30 * 24 * 60 * 60,
    },

    callbacks: {
      async jwt({ token, user }) {
        if (user) {
          const customUser = user as typeof user & {
            entity_id?: string;
            role?: UserRole; 
          };

          token.id = customUser.id;
          token.entity_id = customUser.entity_id;
          token.name = customUser.name;
          token.email = customUser.email;
          token.role = customUser.role;
          token.face_id = customUser.face_id;
          token.student_id = customUser.student_id;
          token.staff_id = customUser.staff_id;
          token.department = customUser.department;

        }
        return token;
      },

      async session({ session, token }) {
        if (token) {
          session.user.id = token.id as string;
          session.user.entity_id = token.entity_id as string;
          session.user.name = token.name as string;
          session.user.email = token.email as string;
          session.user.role = token.role as UserRole;
          session.user.face_id = token.face_id as string;
          session.user.student_id = token.student_id as string;
          session.user.staff_id = token.staff_id as string;
          session.user.department = token.department as string;
        }
        return session;
      },
    },

    pages: {
      signIn: "/auth",
    },
  };

export const authOptions = OPTIONS;
