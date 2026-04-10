"use client";

import { useSession } from "@/lib/auth-client";
import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

/**
 * Client component that extracts user context from NextAuth session
 * and sets it in Sentry for all error events
 */
export function SentryUserContext() {
  const { data: session } = useSession();
  const user = session?.user as Record<string, unknown> | undefined;

  useEffect(() => {
    if (user) {
      Sentry.setUser({
        id: user.id as string,
        email: (user.email as string) || undefined,
        username: (user.entity_id as string) || undefined,
      });

      Sentry.setContext("user_details", {
        entity_id: user.entity_id,
        role: user.role,
        department: user.department,
        student_id: user.student_id,
        staff_id: user.staff_id,
        face_id: user.face_id,
      });

      Sentry.setTag("user_role", user.role as string);
    } else {
      Sentry.setUser(null);
      Sentry.setContext("user_details", null);
      Sentry.setTag("user_role", "anonymous");
    }
  }, [user]);

  // This component doesn't render anything
  return null;
}
