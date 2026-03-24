import type React from "react"
import { SidebarLayout } from "@/components/sidebar-layout"
import { ErrorBoundary } from "@/components/ErrorBoundary"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SidebarLayout>
      <ErrorBoundary>
        {children}
      </ErrorBoundary>
    </SidebarLayout>
  )
}
