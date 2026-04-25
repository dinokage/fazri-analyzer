"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useSession, signOut } from "@/lib/auth-client"
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
  LogOut,
  ShieldAlert,
  Bot,
  UserCheck,
  Camera,
  Webhook,
  Radio,
  Heart,
  Settings,
  KeyRound,
  Palette,
} from "lucide-react"
import { useActiveAlertCount } from "@/hooks/useAlerts"
import { OrgSwitcher } from "@/components/layout/OrgSwitcher"
import { Button } from "@/components/ui/button"
import { useBranding } from "@/hooks/use-branding"

const BASE = "/dashboard" // coderabbitai[manual] ignore: org-slug routing is a planned Phase 1 feature, current URL structure has no [orgSlug] segment

export function SidebarLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { data: session, isPending } = useSession()
  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/")

  const user = session?.user as Record<string, unknown> | undefined
  const isSuperAdmin = user?.role === "SUPER_ADMIN"
  const isAuthenticated = !!session
  const isLoading = isPending

  React.useEffect(() => {
    if (!isPending && !session) {
      router.push('/auth')
    }
  }, [isPending, session, router])

  const { count: activeAlertCount } = useActiveAlertCount(30000)
  const branding = useBranding()

  return (
    <SidebarProvider>
      <div
        className="flex h-screen w-full overflow-hidden"
        style={branding.primaryColor ? { "--brand-primary": branding.primaryColor } as React.CSSProperties : undefined}
      >
        <Sidebar className="flex flex-col overflow-hidden">
          <SidebarHeader className="flex-shrink-0 px-3 pt-3 pb-2">
            <div className="flex items-center gap-2 px-1 mb-2">
              {branding.logo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={branding.logo}
                  alt={branding.name ?? "Org logo"}
                  className="h-7 w-7 rounded object-contain shrink-0"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              ) : null}
              <span className="font-bold text-lg truncate">{branding.name ?? "Fazri Analyzer"}</span>
            </div>
            <OrgSwitcher />
          </SidebarHeader>

          <SidebarContent className="flex-1 overflow-y-auto overflow-x-hidden">
            {isAuthenticated && (
              <>
                <SidebarGroup>
                  <SidebarGroupLabel>Management Console</SidebarGroupLabel>
                  <SidebarMenu>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(BASE)}>
                        <Link href={BASE} className="flex items-center gap-3">
                          <LayoutDashboard className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Dashboard Overview</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/anomalies`)}>
                        <Link href={`${BASE}/anomalies`} className="flex items-center gap-3">
                          <Bug className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Anomalies Detection</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/zones`)}>
                        <Link href={`${BASE}/zones`} className="flex items-center gap-3">
                          <Activity className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Zones</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/events`)}>
                        <Link href={`${BASE}/events`} className="flex items-center gap-3">
                          <Radio className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Sensor Events</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton
                        asChild
                        data-active={isActive(`${BASE}/alerts`) || pathname.startsWith(`${BASE}/alerts/`)}
                      >
                        <Link href={`${BASE}/alerts`} className="flex items-center gap-3">
                          <ShieldAlert className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Security Alerts</span>
                          {activeAlertCount > 0 && (
                            <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-xs font-medium text-white">
                              {activeAlertCount > 99 ? '99+' : activeAlertCount}
                            </span>
                          )}
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/chat`)}>
                        <Link href={`${BASE}/chat`} className="flex items-center gap-3">
                          <Bot className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">AI Assistant</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/face-enrollment`)}>
                        <Link href={`${BASE}/face-enrollment`} className="flex items-center gap-3">
                          <UserCheck className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Face Enrollment</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton
                        asChild
                        data-active={isActive(`${BASE}/cameras`) || pathname.startsWith(`${BASE}/cameras`)}
                      >
                        <Link href={`${BASE}/cameras`} className="flex items-center gap-3">
                          <Camera className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Camera Streams</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/webhooks`)}>
                        <Link href={`${BASE}/webhooks`} className="flex items-center gap-3">
                          <Webhook className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Webhooks</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/system`)}>
                        <Link href={`${BASE}/system`} className="flex items-center gap-3">
                          <Heart className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">System Health</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  </SidebarMenu>
                </SidebarGroup>

                <SidebarSeparator />

                <SidebarGroup>
                  <SidebarGroupLabel>Settings</SidebarGroupLabel>
                  <SidebarMenu>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/settings/sso`)}>
                        <Link href={`${BASE}/settings/sso`} className="flex items-center gap-3">
                          <KeyRound className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Single Sign-On</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/settings/branding`)}>
                        <Link href={`${BASE}/settings/branding`} className="flex items-center gap-3">
                          <Palette className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">Branding</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  </SidebarMenu>
                </SidebarGroup>

                <SidebarSeparator />

                <SidebarGroup>
                  <SidebarGroupLabel>Account</SidebarGroupLabel>
                  <SidebarMenu>
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild data-active={isActive(`${BASE}/profile`)}>
                        <Link href={`${BASE}/profile`} className="flex items-center gap-3">
                          <User className="h-5 w-5 flex-shrink-0" />
                          <span className="truncate">My Profile</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                    {isSuperAdmin && (
                      <SidebarMenuItem>
                        <SidebarMenuButton
                          asChild
                          data-active={pathname.startsWith('/admin')}
                        >
                          <Link href="/admin" className="flex items-center gap-3">
                            <Settings className="h-5 w-5 flex-shrink-0" />
                            <span className="truncate">Admin Console</span>
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    )}
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
                    <p className="font-semibold truncate">{String(user?.name ?? '')}</p>
                    {!!user?.email && (
                      <p className="text-xs leading-none text-sidebar-foreground/80 truncate">
                        {String(user.email)}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => signOut({ fetchOptions: { onSuccess: () => router.push("/auth") } })}
                    className="text-sidebar-foreground hover:text-accent-foreground hover:bg-accent flex-shrink-0"
                    title="Logout"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              )
            )}
            <div className="text-xs text-sidebar-foreground/70 pt-3 border-t border-border/70 -mx-4 px-4 truncate">
              &copy; {new Date().getFullYear()} Fazri Analyzer
            </div>
          </SidebarFooter>
        </Sidebar>

        <SidebarInset className="flex-1 flex flex-col overflow-hidden">
          <header className="flex flex-col h-16 border-b border-border text-foreground flex-shrink-0">
            <div className="flex h-full items-center justify-between gap-4 px-6">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <SidebarTrigger className="flex-shrink-0" />
                <h1 className="text-lg font-semibold text-pretty capitalize truncate">
                  {pathname === BASE
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
