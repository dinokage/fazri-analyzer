"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Overview", href: "/admin" },
  { label: "Users", href: "/admin/users" },
  { label: "Organizations", href: "/admin/orgs" },
  { label: "Analytics", href: "/admin/analytics" },
  { label: "Sessions", href: "/admin/sessions" },
  { label: "Onboarding", href: "/admin/onboarding" },
];

export function AdminSubNav() {
  const pathname = usePathname();

  return (
    <div className="border-b bg-background/95 backdrop-blur sticky top-0 z-10">
      <div className="flex gap-1 px-4 py-1 overflow-x-auto">
        {NAV_ITEMS.map(({ label, href }) => {
          const isActive =
            href === "/admin" ? pathname === "/admin" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "px-3 py-2 text-sm rounded-md whitespace-nowrap transition-colors",
                isActive
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
