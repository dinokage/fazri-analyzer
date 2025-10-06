import { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import { Adapter } from "next-auth/adapters";
import { PrismaAdapter } from "@auth/prisma-adapter";
import { PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/prisma";

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
      GoogleProvider({
        clientId: process.env.AUTH_GOOGLE_ID as string,
        clientSecret: process.env.AUTH_GOOGLE_SECRET as string,
        allowDangerousEmailAccountLinking: true,
        httpOptions: {
          timeout: 60000, // e.g. 30s
        },
      }),
    ],
  
    session: {
      strategy: "jwt",
      maxAge: 30 * 24 * 60 * 60, // 30 days
    },
  
    callbacks: {
      async jwt({ token, user }) {
        // user is only passed the first time JWT is created
        if (user) {
          token.id = user.id;
          token.email = user.email;
          token.name = user.name;
          token.image = user.image;
        }
        return token;
      },
  
      async session({ session, token }) {
        // Fetch the latest user data from the database using Prisma
        const user = await prisma.user.findUnique({
          where: { id: token.id },
        });
        // put token values into session.user
        if (user) {
          session.user.id = token.id as string;
          session.user.email = token.email as string;
          session.user.name = token.name as string;
          session.user.image = token.image as string;
        }
        return session;
      },
    },
  };

export const authOptions = OPTIONS;