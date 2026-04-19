"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import { Building2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AdminOrgsPage() {
  const { data: orgs, refetch } = authClient.useListOrganizations();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const createOrg = async () => {
    if (!name.trim() || !slug.trim()) return;
    setSubmitting(true);
    try {
      const { error } = await authClient.organization.create({
        name: name.trim(),
        slug: slug.trim().toLowerCase(),
      });
      if (error) {
        toast.error(error.message ?? "Failed to create organization.");
      } else {
        toast.success(`Organization "${name}" created.`);
        setName("");
        setSlug("");
        setCreating(false);
        refetch();
      }
    } catch {
      toast.error("Unexpected error. Please try again.");
    }
    setSubmitting(false);
  };

  const deleteOrg = async (orgId: string, orgName: string) => {
    if (!confirm(`Delete "${orgName}"? This cannot be undone.`)) return;
    try {
      const { error } = await authClient.organization.delete({ organizationId: orgId });
      if (error) {
        toast.error(error.message ?? "Failed to delete organization.");
      } else {
        toast.success(`"${orgName}" deleted.`);
        refetch();
      }
    } catch {
      toast.error("Unexpected error. Please try again.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Organizations</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {orgs?.length ?? 0} organization{orgs?.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Button onClick={() => setCreating(!creating)} size="sm">
          <Plus className="h-4 w-4 mr-1.5" />
          New Organization
        </Button>
      </div>

      {creating && (
        <div className="rounded-xl border bg-card p-5 space-y-4">
          <h3 className="font-medium text-sm">Create Organization</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">Name</label>
              <Input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="KIIT University"
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">Slug (URL identifier)</label>
              <Input
                value={slug}
                onChange={e => setSlug(e.target.value.toLowerCase().replace(/\s+/g, '-'))}
                placeholder="kiit-university"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={createOrg} disabled={submitting || !name.trim() || !slug.trim()} size="sm">
              {submitting ? "Creating…" : "Create"}
            </Button>
            <Button variant="outline" onClick={() => setCreating(false)} size="sm">Cancel</Button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {!orgs ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 rounded-xl border animate-pulse bg-muted" />
          ))
        ) : orgs.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            No organizations yet. Create one above.
          </p>
        ) : (
          orgs.map((org) => (
            <div
              key={org.id}
              className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3"
            >
              <Building2 className="h-5 w-5 shrink-0 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{org.name}</p>
                <p className="text-xs text-muted-foreground truncate">/{org.slug}</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={() => deleteOrg(org.id, org.name)}
                title="Delete organization"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
