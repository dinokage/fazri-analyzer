"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, ShieldAlert } from "lucide-react";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function AppearanceTab() {
  const { data: session } = authClient.useSession();
  const { data: activeOrg } = authClient.useActiveOrganization();

  const [isOwner, setIsOwner] = useState(false);
  const [saving, setSaving] = useState(false);

  const [primaryColor, setPrimaryColor] = useState("#6366f1");
  const [faviconUrl, setFaviconUrl] = useState("");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [loginBgUrl, setLoginBgUrl] = useState("");

  useEffect(() => {
    if (!session || !activeOrg) return;
    const members = (activeOrg as unknown as { members?: { userId: string; role: string }[] }).members ?? [];
    const me = members.find((m) => m.userId === session.user.id);
    setIsOwner(me?.role === "owner" || me?.role === "admin" || (session.user as Record<string, unknown>).role === "SUPER_ADMIN");
  }, [session, activeOrg]);

  useEffect(() => {
    if (!activeOrg) return;
    let meta: Record<string, unknown> = {};
    try {
      const raw = activeOrg.metadata;
      meta = typeof raw === "string" ? JSON.parse(raw) : (raw as Record<string, unknown>) ?? {};
    } catch {}
    setPrimaryColor((meta.primaryColor as string) ?? "#6366f1");
    setFaviconUrl((meta.faviconUrl as string) ?? "");
    setWelcomeMessage((meta.welcomeMessage as string) ?? "");
    setLoginBgUrl((meta.loginBgUrl as string) ?? "");
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

      const updatedMeta = {
        ...existingMeta,
        primaryColor: primaryColor.trim(),
        faviconUrl: faviconUrl.trim(),
        welcomeMessage: welcomeMessage.trim(),
        loginBgUrl: loginBgUrl.trim(),
      };

      const { error } = await authClient.organization.update({
        data: { metadata: updatedMeta },
      });

      if (error) {
        toast.error((error as Record<string, unknown>).message as string ?? "Failed to save appearance settings");
      } else {
        toast.success("Appearance settings saved");
      }
    } catch {
      toast.error("Failed to save appearance settings");
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
          label="Primary Brand Color"
          hint="Used as the accent color throughout the dashboard. Changes reflect immediately after saving."
        >
          <div className="flex gap-2 items-center">
            <input
              type="color"
              value={primaryColor}
              onChange={(e) => setPrimaryColor(e.target.value)}
              disabled={!isOwner}
              className="h-9 w-12 rounded-md border border-input cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 p-0.5 bg-transparent"
            />
            <Input
              value={primaryColor}
              onChange={(e) => setPrimaryColor(e.target.value)}
              placeholder="#6366f1"
              disabled={!isOwner}
              className="w-32 font-mono"
              maxLength={7}
            />
            <div
              className="h-9 w-9 rounded-md border shrink-0"
              style={{ backgroundColor: primaryColor }}
            />
          </div>
        </Field>

        <Field
          label="Favicon URL"
          hint="Shown on the browser tab when your org accesses the dashboard via a custom domain."
        >
          <Input
            value={faviconUrl}
            onChange={(e) => setFaviconUrl(e.target.value)}
            placeholder="https://example.com/favicon.ico"
            disabled={!isOwner}
          />
        </Field>

        <Field
          label="Login Page — Welcome Message"
          hint="Shown as a subtitle on the login page when users access via your custom domain."
        >
          <Input
            value={welcomeMessage}
            onChange={(e) => setWelcomeMessage(e.target.value)}
            placeholder="Sign in to your campus security dashboard"
            disabled={!isOwner}
            maxLength={160}
          />
        </Field>

        <Field
          label="Login Page — Background Image URL"
          hint="Replaces the default Fazri decorative panel on the login page."
        >
          <Input
            value={loginBgUrl}
            onChange={(e) => setLoginBgUrl(e.target.value)}
            placeholder="https://example.com/campus-bg.jpg"
            disabled={!isOwner}
          />
        </Field>

        {isOwner && (
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Saving…</> : "Save Appearance"}
          </Button>
        )}
      </div>
    </div>
  );
}
