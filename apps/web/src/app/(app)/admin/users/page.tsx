"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import { Ban, CheckCircle2, Search, Plus, Download, ChevronLeft, ChevronRight, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CreateUserSheet } from "@/components/admin/CreateUserSheet";
import { UserDetailSheet } from "@/components/admin/UserDetailSheet";
import { formatDistanceToNow } from "date-fns";

const ROLES = ["STUDENT", "STAFF", "FACULTY", "SUPER_ADMIN"] as const;
const PAGE_SIZE = 20;

type UserRecord = {
  id: string;
  name: string;
  email: string;
  role?: string | null;
  createdAt: string;
} & Record<string, unknown>;

export default function AdminUsersPage() {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [offset, setOffset] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailUser, setDetailUser] = useState<UserRecord | null>(null);
  const qc = useQueryClient();

  const queryKey = ["admin-users", search, roleFilter, statusFilter, offset];

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: async () => {
      const query: Record<string, unknown> = {
        searchValue: search || undefined,
        searchField: "name",
        searchOperator: "contains",
        limit: PAGE_SIZE,
        offset,
        sortBy: "createdAt",
        sortDirection: "desc",
      };
      if (roleFilter !== "ALL") {
        query.filterField = "role";
        query.filterValue = roleFilter;
      }
      if (statusFilter === "BANNED") {
        query.filterField = "banned";
        query.filterValue = "true";
      } else if (statusFilter === "ACTIVE") {
        query.filterField = "banned";
        query.filterValue = "false";
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data } = await authClient.admin.listUsers({ query: query as any });
      return data;
    },
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-users"] });

  const users = (data?.users ?? []) as unknown as UserRecord[];
  const total = data?.total ?? 0;

  const banUser = async (userId: string, name: string) => {
    const { error } = await authClient.admin.banUser({ userId });
    if (error) toast.error(error.message ?? "Failed to ban user.");
    else { toast.success(`${name} banned.`); invalidate(); }
  };

  const unbanUser = async (userId: string, name: string) => {
    const { error } = await authClient.admin.unbanUser({ userId });
    if (error) toast.error(error.message ?? "Failed to unban user.");
    else { toast.success(`${name} unbanned.`); invalidate(); }
  };

  const setRole = async (userId: string, role: string) => {
    const { error } = await authClient.admin.setRole({
      userId,
      role: role as "admin" | "user",
    });
    if (error) toast.error(error.message ?? "Failed to update role.");
    else { toast.success("Role updated."); invalidate(); }
  };

  const exportCsv = async () => {
    toast.info("Exporting users…");
    const { data: all } = await authClient.admin.listUsers({
      query: { limit: 500, sortBy: "createdAt", sortDirection: "desc" },
    });
    if (!all?.users?.length) { toast.error("No users to export."); return; }
    const rows = [
      ["ID", "Name", "Email", "Role", "Created At", "Banned"],
      ...all.users.map((u) => [
        u.id,
        u.name,
        u.email,
        u.role ?? "",
        String(u.createdAt),
        String((u as unknown as Record<string, unknown>).banned === true),
      ]),
    ];
    const csv = rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `fazri-users-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    toast.success("CSV downloaded.");
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Users</h2>
          <p className="text-sm text-muted-foreground mt-1">{total} total users</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={exportCsv}>
            <Download className="h-4 w-4 mr-1.5" />
            Export CSV
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-1.5" />
            Add User
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[180px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search by name…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
          />
        </div>
        <Select value={roleFilter} onValueChange={(v) => { setRoleFilter(v); setOffset(0); }}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All roles</SelectItem>
            {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setOffset(0); }}>
          <SelectTrigger className="w-28">
            <SelectValue placeholder="All" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All</SelectItem>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="BANNED">Banned</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">User</th>
              <th className="px-4 py-3 text-left font-medium">Role</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-left font-medium hidden md:table-cell">Joined</th>
              <th className="px-4 py-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td colSpan={5} className="px-4 py-3">
                    <div className="h-4 animate-pulse rounded bg-muted w-3/4" />
                  </td>
                </tr>
              ))
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  No users found.
                </td>
              </tr>
            ) : (
              users.map((u) => {
                const isBanned = u.banned === true;
                return (
                  <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium">{u.name}</p>
                      <p className="text-xs text-muted-foreground">{u.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <Select
                        defaultValue={u.role ?? "STUDENT"}
                        onValueChange={(val) => setRole(u.id, val)}
                      >
                        <SelectTrigger className="h-7 w-36 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {ROLES.map((r) => (
                            <SelectItem key={r} value={r} className="text-xs">{r}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center text-xs px-2 py-0.5 rounded-full font-medium ${
                        isBanned
                          ? "bg-destructive/10 text-destructive"
                          : "bg-green-500/10 text-green-600 dark:text-green-400"
                      }`}>
                        {isBanned ? "Banned" : "Active"}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(u.createdAt as string), { addSuffix: true })}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => setDetailUser(u)}
                          title="View details"
                        >
                          <User className="h-3.5 w-3.5" />
                        </Button>
                        {isBanned ? (
                          <Button
                            variant="outline" size="sm" className="h-7 text-xs"
                            onClick={() => unbanUser(u.id, u.name)}
                          >
                            <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                            Unban
                          </Button>
                        ) : (
                          <Button
                            variant="outline" size="sm"
                            className="h-7 text-xs text-destructive hover:text-destructive hover:border-destructive/50"
                            onClick={() => banUser(u.id, u.name)}
                          >
                            <Ban className="h-3.5 w-3.5 mr-1" />
                            Ban
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}>
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <CreateUserSheet
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSuccess={() => {
          qc.invalidateQueries({ queryKey: ["admin-users"] });
          qc.invalidateQueries({ queryKey: ["admin-users-count"] });
        }}
      />

      {detailUser && (
        <UserDetailSheet
          open={!!detailUser}
          onOpenChange={(open) => { if (!open) setDetailUser(null); }}
          user={detailUser}
        />
      )}
    </div>
  );
}
