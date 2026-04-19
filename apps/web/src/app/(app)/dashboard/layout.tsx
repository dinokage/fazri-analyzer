import type React from "react";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { SidebarLayout } from "@/components/sidebar-layout";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AlertNotificationListener } from "@/components/alert-notification-listener";
import { OrgProvider } from "@/lib/org-context";
import { getAuthSession } from "@/lib/auth-server";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getAuthSession(await headers());

  if (!session && process.env.NODE_ENV === "production") {
    redirect("/auth");
  }

  return (
    <OrgProvider>
      <SidebarLayout>
        <AlertNotificationListener enabled pollInterval={10000} />
        <ErrorBoundary>{children}</ErrorBoundary>
      </SidebarLayout>
    </OrgProvider>
  );
}
