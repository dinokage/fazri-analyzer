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
// import { Separator } from "@/components/ui/separator"
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

  // Directly redirect unauthenticated users to /auth
  React.useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth")
    }
  }, [status, router])


  // If not authenticated (and thus being redirected), we can render a minimal loading shell
  // to avoid showing partially loaded content before the redirect takes effect.
  // This helps prevent "flash of content" or temporary incorrect states.
  if (!isAuthenticated && !isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        Redirecting to login...
      </div>
    );
  }


  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader className="h-16 flex items-center justify-center">
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg">Fazri Analyzer</span>
          </div>
        </SidebarHeader>

        <SidebarContent>
          {
            // Only render actual content if authenticated (as unauthenticated redirects)
            isAuthenticated && (
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
                              <LayoutDashboard className="h-5 w-5" />
                              <span>Dashboard Overview</span>
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
                              <Bug className="h-5 w-5" />
                              <span>Anomalies Detection</span>
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
                              <Activity className="h-5 w-5" />
                              <span>Zones</span>
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
                          <User className="h-5 w-5" />
                          <span>My Profile</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  </SidebarMenu>
                </SidebarGroup>
              </>
            )
          }
        </SidebarContent>

        <SidebarFooter className="p-4 border-t border-border/70 flex flex-col justify-end gap-3">
          {isLoading ? (
            <div className="h-10 animate-pulse bg-muted rounded-md w-full"></div>
          ) : (
            // Only render actual content if authenticated (as unauthenticated redirects)
            isAuthenticated && (
              <div className="flex items-center justify-between w-full">
                <div className="text-sm text-sidebar-foreground flex flex-col">
                  <p className="font-semibold">{session.user?.name}</p>
                  {session.user?.email && (
                    <p className="text-xs leading-none text-sidebar-foreground/80">
                      {session.user.email}
                    </p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => signOut({ callbackUrl: "/auth" })} // Redirect to /auth after logout
                  className="text-sidebar-foreground hover:text-accent-foreground hover:bg-accent"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            )
            
          )}
          <div className="text-xs text-sidebar-foreground/70 pt-3 border-t border-border/70 -mx-4 px-4 mt-auto">
            &copy; {new Date().getFullYear()}Fazri Analyzer | IIT Bombay 
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset>
        <header className="flex flex-col h-16 border-b border-border text-foreground">
          <div className="flex h-full items-center justify-between gap-4 px-6">
            <div className="flex items-center gap-3">
              <SidebarTrigger />
              <h1 className="text-lg font-semibold text-pretty capitalize">
                {pathname === "/dashboard"
                  ? "Dashboard Overview"
                  : pathname.split("/").pop()?.replace(/-/g, " ") ||
                    "Application Overview"}
              </h1>
            </div>
            {/* UserNav should ideally handle its own loading/unauthenticated state or be hidden */}
            {isLoading ? (
                <div className="h-8 w-8 rounded-full animate-pulse bg-muted" />
            ) : isAuthenticated ? (
                <UserNav />
            ) : null}
          </div>
        </header>

        <main className="min-w-0 p-6 text-foreground">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}