import type React from "react"
import { SidebarLayout } from "@/components/sidebar-layout"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { AlertNotificationListener } from "@/components/alert-notification-listener"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SidebarLayout>
      <AlertNotificationListener enabled pollInterval={10000} />
      <ErrorBoundary>
        {children}
      </ErrorBoundary>
    </SidebarLayout>
  )
}
