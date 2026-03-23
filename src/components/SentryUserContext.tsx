"use client";

import { useSession } from "next-auth/react";
import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

/**
 * Client component that extracts user context from NextAuth session
 * and sets it in Sentry for all error events
 */
export function SentryUserContext() {
  const { data: session } = useSession();

  useEffect(() => {
    if (session?.user) {
      // Set user identification in Sentry
      Sentry.setUser({
        id: session.user.id,
        email: session.user.email || undefined,
        username: session.user.entity_id || undefined,
      });

      // Add additional user context
      Sentry.setContext("user_details", {
        entity_id: session.user.entity_id,
        role: session.user.role,
        department: session.user.department,
        student_id: session.user.student_id,
        staff_id: session.user.staff_id,
        face_id: session.user.face_id,
      });

      // Add user role as a tag for filtering in Sentry
      Sentry.setTag("user_role", session.user.role);
    } else {
      // Clear user context when logged out
      Sentry.setUser(null);
      Sentry.setContext("user_details", null);
      Sentry.setTag("user_role", "anonymous");
    }
  }, [session]);

  // This component doesn't render anything
  return null;
}
