import { createAuthClient } from "better-auth/react";
import { usernameClient } from "better-auth/client/plugins";
import { jwtClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_SERVICE_URL!,
  plugins: [usernameClient(), jwtClient()],
});

export const { useSession, signOut, getSession } = authClient;
