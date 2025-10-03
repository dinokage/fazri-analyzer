import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { PrismaClient } from "@prisma/client";
import { nextCookies } from "better-auth/next-js";

const prisma = new PrismaClient();

export const auth = betterAuth({
  socialProviders: {
    google:{
        prompt:"select_account",
        clientId: process.env.GOOGLE_CLIENT_ID as string,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET as string
    }
  },
  database: prismaAdapter(prisma, {
    provider: "postgresql",
  }),
  plugins:[nextCookies()]
});

