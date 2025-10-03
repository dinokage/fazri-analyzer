import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { nextCookies } from "better-auth/next-js";
import {prisma} from "@/lib/db"

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

