"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import { Monitor, Trash2 } from "lucide-react";

interface Session {
  id: string;
  token: string;
  createdAt: string;
  expiresAt: string;
  ipAddress?: string | null;
  userAgent?: string | null;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: {
    id: string;
    name: string;
    email: string;
    role?: string | null;
    createdAt: string;
  } & Record<string, unknown>;
}

export function UserDetailSheet({ open, onOpenChange, user }: Props) {
  const router = useRouter();
  const qc = useQueryClient();
  const [revoking, setRevoking] = useState<string | null>(null);
  const [revokingAll, setRevokingAll] = useState(false);

  const { data: sessions, isLoading } = useQuery<Session[]>({
    queryKey: ["admin-sessions", user.id],
    queryFn: async () => {
      const { data } = await authClient.admin.listUserSessions({
        userId: user.id,
      });
      return (data ?? []) as Session[];
    },
    enabled: open,
    staleTime: 30_000,
  });

  const invalidateSessions = () => qc.invalidateQueries({ queryKey: ["admin-sessions", user.id] });

  const revokeSession = async (token: string) => {
    setRevoking(token);
    const { error } = await authClient.admin.revokeUserSession({ sessionToken: token });
    if (error) toast.error(error.message ?? "Failed to revoke session.");
    else { toast.success("Session revoked."); invalidateSessions(); }
    setRevoking(null);
  };

  const revokeAll = async () => {
    if (!sessions?.length) return;
    setRevokingAll(true);
    let failed = 0;
    for (const s of sessions) {
      const { error } = await authClient.admin.revokeUserSession({ sessionToken: s.token });
      if (error) failed++;
    }
    if (failed > 0) toast.error(`${failed} session(s) could not be revoked.`);
    else toast.success("All sessions revoked.");
    invalidateSessions();
    setRevokingAll(false);
  };

  const impersonate = async () => {
    const { error } = await authClient.admin.impersonateUser({ userId: user.id });
    if (error) toast.error(error.message ?? "Failed to impersonate user.");
    else {
      toast.success(`Now acting as ${user.name}`);
      router.push("/dashboard");
    }
  };

  const fields: [string, string][] = [
    ["Name", user.name],
    ["Email", user.email],
    ["Role", String(user.role ?? "—")],
    ["Joined", format(new Date(user.createdAt), "PPP")],
    ...(user.username ? [["Username", String(user.username)]] as [string, string][] : []),
    ...(user.department ? [["Department", String(user.department)]] as [string, string][] : []),
    ...(user.student_id ? [["Student ID", String(user.student_id)]] as [string, string][] : []),
    ...(user.staff_id ? [["Staff ID", String(user.staff_id)]] as [string, string][] : []),
  ];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[480px] sm:max-w-[480px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{user.name}</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Profile */}
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Profile</h3>
            <div className="rounded-xl border divide-y divide-border">
              {fields.map(([label, value]) => (
                <div key={label} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <span className="text-muted-foreground">{label}</span>
                  <span className="font-medium">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Sessions */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Active Sessions</h3>
              {sessions && sessions.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs text-destructive hover:text-destructive"
                  onClick={revokeAll}
                  disabled={revokingAll}
                >
                  {revokingAll ? "Revoking…" : "Revoke All"}
                </Button>
              )}
            </div>
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 2 }).map((_, i) => (
                  <div key={i} className="h-12 animate-pulse rounded-xl bg-muted" />
                ))}
              </div>
            ) : !sessions?.length ? (
              <p className="text-sm text-muted-foreground py-3 text-center">No active sessions.</p>
            ) : (
              <div className="rounded-xl border divide-y divide-border">
                {sessions.map((s) => (
                  <div key={s.id} className="flex items-center justify-between px-4 py-3 text-xs">
                    <div className="space-y-0.5">
                      <p className="font-mono text-muted-foreground">…{s.token.slice(-8)}</p>
                      <p className="text-muted-foreground">
                        Created {format(new Date(s.createdAt), "MMM d, HH:mm")}
                        {" · "}Expires {format(new Date(s.expiresAt), "MMM d")}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => revokeSession(s.token)}
                      disabled={revoking === s.token}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Impersonate */}
          <div className="border-t pt-4">
            <Button
              variant="outline"
              size="sm"
              className="w-full text-xs"
              onClick={impersonate}
            >
              <Monitor className="h-3.5 w-3.5 mr-1.5" />
              Impersonate User
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
