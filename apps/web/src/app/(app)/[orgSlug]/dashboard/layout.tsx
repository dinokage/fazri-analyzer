import type React from "react";
import { SidebarLayout } from "@/components/sidebar-layout";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AlertNotificationListener } from "@/components/alert-notification-listener";
import { OrgProvider } from "@/lib/org-context";

export default async function OrgDashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ orgSlug: string }>;
}) {
  const { orgSlug } = await params;

  return (
    <OrgProvider orgSlug={orgSlug}>
      <SidebarLayout orgSlug={orgSlug}>
        <AlertNotificationListener enabled pollInterval={10000} />
        <ErrorBoundary>{children}</ErrorBoundary>
      </SidebarLayout>
    </OrgProvider>
  );
}
