import { createAuthClient } from "better-auth/react";
import {
  usernameClient,
  jwtClient,
  organizationClient,
  adminClient,
} from "better-auth/client/plugins";
import { ssoClient } from "@better-auth/sso/client";
import { toast } from "sonner";

export const authClient = createAuthClient({
  // Browser: route through the Next.js proxy (/api/auth/*) so cookies are
  // first-party on any tenant domain. Server-side: hit the auth service directly.
  baseURL: typeof window !== "undefined" ? window.location.origin : process.env.NEXT_PUBLIC_AUTH_SERVICE_URL,
  plugins: [
    usernameClient(),
    jwtClient(),
    organizationClient(),
    adminClient(),
    ssoClient(),
  ],
  fetchOptions: {
    onError: async (context) => {
      const status = context.response?.status;
      if (!status || status === 0 || status >= 500) {
        toast.error("Auth service is unreachable. Please try again later.", {
          id: "auth-unreachable",
        });
      }
    },
  },
});

export const { useSession, signOut, getSession } = authClient;
export const { organization } = authClient;

export const signInWithSSO = (params: { email?: string; domain?: string; providerId?: string }) =>
  authClient.signIn.sso({
    ...params,
    callbackURL: `${typeof window !== "undefined" ? window.location.origin : ""}/dashboard`,
    errorCallbackURL: `${typeof window !== "undefined" ? window.location.origin : ""}/signin`,
  });
