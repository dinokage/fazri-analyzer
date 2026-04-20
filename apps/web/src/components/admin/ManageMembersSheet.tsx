"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, UserMinus } from "lucide-react";

const ORG_ROLES = ["member", "admin", "owner"] as const;

interface Member {
  id: string;
  userId: string;
  role: string;
  user?: { name?: string; email?: string } | null;
}

interface Org {
  id: string;
  name: string;
  slug: string;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  org: Org;
}

export function ManageMembersSheet({ open, onOpenChange, org }: Props) {
  const qc = useQueryClient();
  const [addSearch, setAddSearch] = useState("");
  const [addRole, setAddRole] = useState("member");
  const [adding, setAdding] = useState<string | null>(null);

  const { data: fullOrg, isLoading } = useQuery({
    queryKey: ["admin-org-full", org.id],
    queryFn: async () => {
      const { data } = await authClient.organization.getFullOrganization({
        query: { organizationId: org.id },
      });
      return data;
    },
    enabled: open,
    staleTime: 30_000,
  });

  const { data: searchResults } = useQuery({
    queryKey: ["admin-user-search", addSearch],
    queryFn: async () => {
      if (!addSearch.trim()) return [];
      const { data } = await authClient.admin.listUsers({
        query: { searchValue: addSearch, searchField: "email", limit: 8 },
      });
      return data?.users ?? [];
    },
    enabled: addSearch.length >= 2,
    staleTime: 10_000,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin-org-full", org.id] });
    qc.invalidateQueries({ queryKey: ["admin-org-details"] });
  };

  const updateRole = async (memberId: string, role: string) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error } = await (authClient.organization as any).updateMemberRole({
      memberId,
      organizationId: org.id,
      role,
    });
    if (error) toast.error(error.message ?? "Failed to update role.");
    else { toast.success("Role updated."); invalidate(); }
  };

  const removeMember = async (memberId: string, name: string) => {
    if (!confirm(`Remove ${name} from ${org.name}?`)) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error } = await (authClient.organization as any).removeMember({
      memberIdOrEmail: memberId,
      organizationId: org.id,
    });
    if (error) toast.error(error.message ?? "Failed to remove member.");
    else { toast.success(`${name} removed.`); invalidate(); }
  };

  const addMember = async (userId: string, userName: string) => {
    setAdding(userId);
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/api/add-org-member`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ userId, organizationId: org.id, role: addRole }),
      }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      toast.error((body as { error?: string }).error ?? "Failed to add member.");
    } else {
      toast.success(`${userName} added to ${org.name}.`);
      setAddSearch("");
      invalidate();
    }
    setAdding(null);
  };

  const members: Member[] = (fullOrg?.members as Member[] | undefined) ?? [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[480px] sm:max-w-[480px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{org.name} — Members</SheetTitle>
        </SheetHeader>

        <div className="mt-6">
          <Tabs defaultValue="members">
            <TabsList className="w-full">
              <TabsTrigger value="members" className="flex-1">
                Members {members.length > 0 && `(${members.length})`}
              </TabsTrigger>
              <TabsTrigger value="add" className="flex-1">Add Member</TabsTrigger>
            </TabsList>

            <TabsContent value="members" className="mt-4">
              {isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="h-14 animate-pulse rounded-xl bg-muted" />
                  ))}
                </div>
              ) : members.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">No members yet.</p>
              ) : (
                <div className="rounded-xl border divide-y divide-border">
                  {members.map((m) => (
                    <div key={m.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{m.user?.name ?? m.userId}</p>
                        <p className="text-xs text-muted-foreground truncate">{m.user?.email ?? ""}</p>
                      </div>
                      <Select
                        defaultValue={m.role}
                        onValueChange={(v) => updateRole(m.id, v)}
                      >
                        <SelectTrigger className="h-7 w-24 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {ORG_ROLES.map((r) => (
                            <SelectItem key={r} value={r} className="text-xs capitalize">{r}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10 shrink-0"
                        onClick={() => removeMember(m.id, m.user?.name ?? m.userId)}
                      >
                        <UserMinus className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="add" className="mt-4 space-y-4">
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-xs text-muted-foreground">Search user by email</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      className="pl-9"
                      placeholder="user@college.edu"
                      value={addSearch}
                      onChange={(e) => setAddSearch(e.target.value)}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs text-muted-foreground">Role</label>
                  <Select value={addRole} onValueChange={setAddRole}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ORG_ROLES.map((r) => (
                        <SelectItem key={r} value={r} className="capitalize">{r}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {searchResults && searchResults.length > 0 && (
                <div className="rounded-xl border divide-y divide-border">
                  {searchResults.map((u) => {
                    const alreadyMember = members.some((m) => m.userId === u.id);
                    return (
                      <div key={u.id} className="flex items-center gap-3 px-4 py-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{u.name}</p>
                          <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs shrink-0"
                          disabled={alreadyMember || adding === u.id}
                          onClick={() => addMember(u.id, u.name)}
                        >
                          {alreadyMember ? "Already added" : adding === u.id ? "Adding…" : "Add"}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}

              {addSearch.length >= 2 && !searchResults?.length && (
                <p className="text-sm text-muted-foreground text-center py-4">No users found.</p>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </SheetContent>
    </Sheet>
  );
}
