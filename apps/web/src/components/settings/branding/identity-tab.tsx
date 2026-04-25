"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, ImageIcon, ShieldAlert } from "lucide-react";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function IdentityTab() {
  const { data: session } = authClient.useSession();
  const { data: activeOrg } = authClient.useActiveOrganization();

  const [isOwner, setIsOwner] = useState(false);
  const [saving, setSaving] = useState(false);

  const [name, setName] = useState("");
  const [logo, setLogo] = useState("");
  const [tagline, setTagline] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");

  useEffect(() => {
    if (!session || !activeOrg) return;
    const members = (activeOrg as unknown as { members?: { userId: string; role: string }[] }).members ?? [];
    const me = members.find((m) => m.userId === session.user.id);
    setIsOwner(me?.role === "owner" || me?.role === "admin" || (session.user as Record<string, unknown>).role === "SUPER_ADMIN");
  }, [session, activeOrg]);

  useEffect(() => {
    if (!activeOrg) return;
    setName(activeOrg.name ?? "");
    setLogo(activeOrg.logo ?? "");
    let meta: Record<string, unknown> = {};
    try {
      const raw = activeOrg.metadata;
      meta = typeof raw === "string" ? JSON.parse(raw) : (raw as Record<string, unknown>) ?? {};
    } catch {}
    setTagline((meta.tagline as string) ?? "");
    setWebsiteUrl((meta.websiteUrl as string) ?? "");
  }, [activeOrg]);

  const handleSave = async () => {
    if (!activeOrg) return;
    setSaving(true);
    try {
      let existingMeta: Record<string, unknown> = {};
      try {
        const raw = activeOrg.metadata;
        existingMeta = typeof raw === "string" ? JSON.parse(raw) : (raw as Record<string, unknown>) ?? {};
      } catch {}

      const updatedMeta = { ...existingMeta, tagline: tagline.trim(), websiteUrl: websiteUrl.trim() };

      const { error } = await authClient.organization.update({
        data: {
          name: name.trim() || activeOrg.name,
          logo: logo.trim() || undefined,
          metadata: updatedMeta,
        },
      });

      if (error) {
        toast.error((error as Record<string, unknown>).message as string ?? "Failed to save identity settings");
      } else {
        toast.success("Identity settings saved");
      }
    } catch {
      toast.error("Failed to save identity settings");
    } finally {
      setSaving(false);
    }
  };

  if (!activeOrg) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <p className="text-sm text-muted-foreground">No active organization.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {!isOwner && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20 px-4 py-3">
          <ShieldAlert className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <p className="text-sm text-amber-700 dark:text-amber-300">
            Only org admins can edit branding. Contact your organization owner to make changes.
          </p>
        </div>
      )}

      <div className="rounded-xl border bg-card p-6 space-y-5">
        <Field
          label="Organization Logo"
          hint="Paste a publicly accessible image URL (PNG, SVG, or JPG). Shown in the sidebar and login page."
        >
          <div className="flex gap-3 items-start">
            <div className="h-16 w-16 shrink-0 rounded-lg border bg-muted flex items-center justify-center overflow-hidden">
              {logo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={logo} alt="Org logo preview" className="h-full w-full object-contain" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
              ) : (
                <ImageIcon className="h-6 w-6 text-muted-foreground" />
              )}
            </div>
            <Input
              value={logo}
              onChange={(e) => setLogo(e.target.value)}
              placeholder="https://example.com/logo.png"
              disabled={!isOwner}
              className="flex-1"
            />
          </div>
        </Field>

        <Field label="Organization Name" hint="Display name shown in the sidebar and login page.">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={activeOrg.name}
            disabled={!isOwner}
          />
        </Field>

        <Field label="Tagline" hint="A short description shown on the login page beneath your org name.">
          <Input
            value={tagline}
            onChange={(e) => setTagline(e.target.value)}
            placeholder="Securing our campus, together"
            disabled={!isOwner}
            maxLength={120}
          />
        </Field>

        <Field label="Website URL" hint="Shown as a link on the login page.">
          <Input
            value={websiteUrl}
            onChange={(e) => setWebsiteUrl(e.target.value)}
            placeholder="https://yourorg.edu"
            disabled={!isOwner}
          />
        </Field>

        {isOwner && (
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Saving…</> : "Save Identity"}
          </Button>
        )}
      </div>
    </div>
  );
}
