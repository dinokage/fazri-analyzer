"use client"

import type * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  SidebarProvider,
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarSeparator,
  SidebarFooter,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { UserNav } from "@/components/user-nav"

export function SidebarLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isActive = (href: string) => pathname === href

  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader className="h-16 px-4 flex items-center">
          <div className="flex items-center gap-2">
            <img src="/placeholder-logo.svg" alt="Campus Monitor logo" className="size-5" />
            <span className="font-semibold">Campus Monitor</span>
          </div>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Navigation</SidebarGroupLabel>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild data-active={isActive("/dashboard")}>
                  <Link href="/dashboard">
                    <span>Overview</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild data-active={isActive("/dashboard/entities")}>
                  <Link href="/dashboard/entities">
                    <span>Entities</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroup>

          <SidebarSeparator />

          <SidebarGroup>
            <SidebarGroupLabel>Shortcuts</SidebarGroupLabel>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <Link href="/dashboard/entities">
                    <span>Recent activity</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="px-4 py-3 text-xs text-sidebar-foreground/70">
          v1.0 • All systems normal
        </SidebarFooter>
      </Sidebar>

      <SidebarInset>
        <header className="flex h-16 items-center justify-between gap-4 border-b border-border px-6 text-foreground">
          <div className="flex items-center gap-3">
            <SidebarTrigger />
            <Separator orientation="vertical" className="h-5" />
            <h1 className="text-sm font-medium text-pretty">Dashboard</h1>
          </div>
          <UserNav />
        </header>

        <main className="min-w-0 p-6 text-foreground">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  )
}
