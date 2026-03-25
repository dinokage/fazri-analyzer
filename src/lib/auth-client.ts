import { createAuthClient } from "better-auth/react";
import { usernameClient } from "better-auth/client/plugins";
import { jwtClient } from "better-auth/client/plugins";
import { toast } from "sonner";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_SERVICE_URL,
  plugins: [usernameClient(), jwtClient()],
  fetchOptions: {
    onError: async (context) => {
      const status = context.response?.status;

      // Network error / auth service unreachable
      if (!status || status === 0 || status >= 500) {
        toast.error("Auth service is unreachable. Please try again later.", {
          id: "auth-unreachable",
        });
      }
    },
  },
});

export const { useSession, signOut, getSession } = authClient;
