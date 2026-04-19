"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import { Ban, CheckCircle2, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ROLES = ["STUDENT", "STAFF", "FACULTY", "SUPER_ADMIN"] as const;
const PAGE_SIZE = 20;

export default function AdminUsersPage() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const qc = useQueryClient();

  const queryKey = ["admin-users", search, offset];

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: async () => {
      const { data } = await authClient.admin.listUsers({
        query: {
          searchValue: search || undefined,
          searchField: "name",
          searchOperator: "contains",
          limit: PAGE_SIZE,
          offset,
          sortBy: "createdAt",
          sortDirection: "desc",
        },
      });
      return data;
    },
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-users"] });

  const users = data?.users ?? [];
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

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">Users</h2>
        <p className="text-sm text-muted-foreground mt-1">{total} total users</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search by name…"
          value={search}
          onChange={e => { setSearch(e.target.value); setOffset(0); }}
        />
      </div>

      <div className="rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">User</th>
              <th className="px-4 py-3 text-left font-medium">Role</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td colSpan={4} className="px-4 py-3">
                    <div className="h-4 animate-pulse rounded bg-muted w-3/4" />
                  </td>
                </tr>
              ))
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                  No users found.
                </td>
              </tr>
            ) : (
              users.map((u) => {
                const isBanned = (u as unknown as Record<string, unknown>).banned === true;
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
                    <td className="px-4 py-3 text-right">
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
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
