import type React from "react";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getAuthSession } from "@/lib/auth-server";
import { SidebarLayout } from "@/components/sidebar-layout";
import { OrgProvider } from "@/lib/org-context";
import { AdminSubNav } from "@/components/admin/AdminSubNav";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getAuthSession(await headers());

  if (!session) redirect("/auth");
  if (session.user.role !== "SUPER_ADMIN") {
    console.warn("[admin] access denied — role:", session.user.role);
    redirect("/dashboard");
  }

  return (
    <OrgProvider>
      <SidebarLayout>
        <div className="-mx-6 -mt-6 mb-6">
          <AdminSubNav />
        </div>
        {children}
      </SidebarLayout>
    </OrgProvider>
  );
}
