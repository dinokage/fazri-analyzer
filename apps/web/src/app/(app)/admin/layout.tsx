import type React from "react";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getAuthSession } from "@/lib/auth-server";
import { SidebarLayout } from "@/components/sidebar-layout";
import { OrgProvider } from "@/lib/org-context";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getAuthSession(await headers());

  if (!session) {
    if (process.env.NODE_ENV === "production") redirect("/auth");
  } else if (session.user.role !== "SUPER_ADMIN") {
    console.warn("[admin] access denied — role:", session.user.role);
    redirect("/dashboard");
  }

  return (
    <OrgProvider>
      <SidebarLayout>{children}</SidebarLayout>
    </OrgProvider>
  );
}
