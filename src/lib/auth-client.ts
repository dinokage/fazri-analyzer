import { createAuthClient } from "better-auth/react";
import { usernameClient } from "better-auth/client/plugins";
import { jwtClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  // No baseURL — auth requests go to /api/auth/* (same origin)
  // and are proxied to the auth service via Next.js rewrites in next.config.ts
  plugins: [usernameClient(), jwtClient()],
});

export const { useSession, signOut, getSession } = authClient;
