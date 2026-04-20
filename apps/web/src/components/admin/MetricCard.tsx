import Link from "next/link";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number | undefined;
  href?: string;
  badge?: string;
  badgeColor?: string;
}

export function MetricCard({ icon: Icon, label, value, href, badge, badgeColor }: MetricCardProps) {
  const content = (
    <div className="rounded-xl border bg-card p-5 space-y-3 hover:bg-accent/30 transition-colors">
      <div className="flex items-center justify-between">
        <Icon className="h-5 w-5 text-muted-foreground" />
        {badge && (
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badgeColor ?? "bg-green-500/10 text-green-600 dark:text-green-400"}`}>
            {badge}
          </span>
        )}
      </div>
      <div>
        <p className="text-2xl font-bold">{value ?? "—"}</p>
        <p className="text-sm text-muted-foreground mt-0.5">{label}</p>
      </div>
    </div>
  );

  return href ? <Link href={href}>{content}</Link> : content;
}
