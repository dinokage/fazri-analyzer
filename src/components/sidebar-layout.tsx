"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
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
import { UserNav } from "@/components/user-nav"
import {
  LayoutDashboard,
  Bug,
  User,
  Activity,
  Lightbulb,
  LogOut,
} from "lucide-react"

import { Button } from "@/components/ui/button"

export function SidebarLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { data: session, status } = useSession()
  const isActive = (href: string) => pathname === href

  const isSuperAdmin = session?.user?.role === "SUPER_ADMIN"
  const isAuthenticated = status === "authenticated"
  const isLoading = status === "loading"

  React.useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth")
    }
  }, [status, router])

  if (!isAuthenticated && !isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        Redirecting to auth...
      </div>
    );
  }

  return (
    <SidebarProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <Sidebar className="flex flex-col overflow-hidden">
          <SidebarHeader className="h-16 flex items-center justify-center flex-shrink-0">
            <div className="flex items-center gap-2 px-4">
              <span className="font-bold text-lg truncate">Fazri Analyzer</span>
            </div>
          </SidebarHeader>

          <SidebarContent className="flex-1 overflow-y-auto overflow-x-hidden">
            {isAuthenticated && (
              <>
                {isSuperAdmin && (
                  <>
                    <SidebarGroup>
                      <SidebarGroupLabel>Management Console</SidebarGroupLabel>
                      <SidebarMenu>
                        <SidebarMenuItem>
                          <SidebarMenuButton
                            asChild
                            data-active={isActive("/dashboard")}
                          >
                            <Link
                              href="/dashboard"
                              className="flex items-center gap-3"
                            >
                              <LayoutDashboard className="h-5 w-5 flex-shrink-0" />
                              <span className="truncate">Dashboard Overview</span>
                            </Link>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                          <SidebarMenuButton
                            asChild
                            data-active={isActive("/dashboard/anomalies")}
                          >
                            <Link
                              href="/dashboard/anomalies"
                              className="flex items-center gap-3"
                            >
                              <Bug className="h-5 w-5 flex-shrink-0" />
                              <span className="truncate">Anomalies Detection</span>
                            </Link>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                          <SidebarMenuButton
                            asChild
                            data-active={isActive("/dashboard/zones")}
                          >
                            <Link
                              href="/dashboard/zones"
                              className="flex items-center gap-3"
                            >
                              <Activity className="h-5 w-5 flex-shrink-0" />
                              <span className="truncate">Zones</span>
                            </Link>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      </SidebarMenu>
                    </SidebarGroup>

                    <SidebarSeparator />
                  </>
                )}

                <SidebarGroup>
                  <SidebarGroupLabel>Account</SidebarGroupLabel>
                  <SidebarMenu>
                    <SidebarMenuItem>
                      <SidebarMenuButton
                        asChild
                        data-active={isActive("/dashboard/profile")}
                      >
                        <Link
                          href="/dashboard/profile"
                          className="flex items-center gap-3"
                        >
                          <User className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">My Profile</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  </SidebarMenu>
                </SidebarGroup>
              </>
            )}
          </SidebarContent>

          <SidebarFooter className="p-4 border-t border-border/70 flex flex-col gap-3 flex-shrink-0 overflow-hidden">
            {isLoading ? (
              <div className="h-10 animate-pulse bg-muted rounded-md w-full"></div>
            ) : (
              isAuthenticated && (
                <div className="flex items-center justify-between gap-2 w-full min-w-0">
                  <div className="text-sm text-sidebar-foreground flex flex-col min-w-0 flex-1">
                    <p className="font-semibold truncate">{session.user?.name}</p>
                    {session.user?.email && (
                      <p className="text-xs leading-none text-sidebar-foreground/80 truncate">
                        {session.user.email}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => signOut({ callbackUrl: "/auth" })}
                    className="text-sidebar-foreground hover:text-accent-foreground hover:bg-accent flex-shrink-0"
                    title="Logout"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              )
            )}
            <div className="text-xs text-sidebar-foreground/70 pt-3 border-t border-border/70 -mx-4 px-4 truncate">
              &copy; {new Date().getFullYear()} Fazri Analyzer | IIT Bombay
            </div>
          </SidebarFooter>
        </Sidebar>

        <SidebarInset className="flex-1 flex flex-col overflow-hidden">
          <header className="flex flex-col h-16 border-b border-border text-foreground flex-shrink-0">
            <div className="flex h-full items-center justify-between gap-4 px-6">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <SidebarTrigger className="flex-shrink-0" />
                <h1 className="text-lg font-semibold text-pretty capitalize truncate">
                  {pathname === "/dashboard"
                    ? "Dashboard Overview"
                    : pathname.split("/").pop()?.replace(/-/g, " ") ||
                      "Application Overview"}
                </h1>
              </div>
              {isLoading ? (
                  <div className="h-8 w-8 rounded-full animate-pulse bg-muted flex-shrink-0" />
              ) : isAuthenticated ? (
                  <div className="flex-shrink-0"><UserNav /></div>
              ) : null}
            </div>
          </header>

          <main className="flex-1 overflow-auto p-6 text-foreground">
            {children}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  )
}