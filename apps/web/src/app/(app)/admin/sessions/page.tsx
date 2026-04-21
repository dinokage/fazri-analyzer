"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Trash2 } from "lucide-react";
import { format } from "date-fns";

interface Session {
  id: string;
  token: string;
  createdAt: string;
  expiresAt: string;
  ipAddress?: string | null;
  userAgent?: string | null;
}

interface UserRecord {
  id: string;
  name: string;
  email: string;
}

export default function AdminSessionsPage() {
  const [search, setSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState<UserRecord | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [revokingAll, setRevokingAll] = useState(false);
  const qc = useQueryClient();

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ["admin-session-user-search", search],
    queryFn: async () => {
      if (!search.trim()) return [];
      const { data } = await authClient.admin.listUsers({
        query: { searchValue: search, searchField: "name", limit: 15 },
      });
      return (data?.users ?? []) as UserRecord[];
    },
    enabled: search.length >= 2,
    staleTime: 10_000,
  });

  const { data: sessions, isLoading: sessionsLoading } = useQuery<Session[]>({
    queryKey: ["admin-sessions", selectedUser?.id],
    queryFn: async () => {
      const { data } = await authClient.admin.listUserSessions({
        userId: selectedUser!.id,
      });
      return (data ?? []) as Session[];
    },
    enabled: !!selectedUser,
    staleTime: 30_000,
  });

  const invalidateSessions = () =>
    qc.invalidateQueries({ queryKey: ["admin-sessions", selectedUser?.id] });

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

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">Sessions</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Search for a user to view and revoke their active sessions.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Left: user search */}
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search users by name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="rounded-xl border divide-y divide-border overflow-hidden">
            {search.length < 2 ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                Type at least 2 characters to search.
              </p>
            ) : searchLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="px-4 py-3">
                  <div className="h-4 animate-pulse rounded bg-muted w-2/3" />
                </div>
              ))
            ) : !searchResults?.length ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">No users found.</p>
            ) : (
              searchResults.map((u) => (
                <button
                  key={u.id}
                  className={`w-full text-left px-4 py-3 hover:bg-muted/40 transition-colors ${
                    selectedUser?.id === u.id ? "bg-primary/5 border-l-2 border-l-primary" : ""
                  }`}
                  onClick={() => setSelectedUser(u)}
                >
                  <p className="text-sm font-medium">{u.name}</p>
                  <p className="text-xs text-muted-foreground">{u.email}</p>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right: sessions */}
        <div className="space-y-3">
          {!selectedUser ? (
            <div className="rounded-xl border p-8 text-center text-sm text-muted-foreground">
              Select a user to view their sessions.
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Sessions for {selectedUser.name}</p>
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

              <div className="rounded-xl border divide-y divide-border overflow-hidden">
                {sessionsLoading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="px-4 py-3">
                      <div className="h-4 animate-pulse rounded bg-muted w-3/4" />
                    </div>
                  ))
                ) : !sessions?.length ? (
                  <p className="px-4 py-8 text-center text-sm text-muted-foreground">No active sessions.</p>
                ) : (
                  sessions.map((s) => (
                    <div key={s.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="flex-1 min-w-0 space-y-0.5">
                        <p className="text-xs font-mono text-muted-foreground">
                          Token: …{s.token.slice(-8)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Created {format(new Date(s.createdAt), "MMM d, HH:mm")}
                          {" · "}
                          Expires {format(new Date(s.expiresAt), "MMM d, yyyy")}
                        </p>
                        {s.ipAddress && (
                          <p className="text-xs text-muted-foreground">IP: {s.ipAddress}</p>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10 shrink-0"
                        onClick={() => revokeSession(s.token)}
                        disabled={revoking === s.token}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
