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

  if (!session) redirect("/auth");
  if (session.user.role !== "SUPER_ADMIN") redirect("/dashboard");

  return (
    <OrgProvider>
      <SidebarLayout>{children}</SidebarLayout>
    </OrgProvider>
  );
}
