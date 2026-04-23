"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TriangleAlert } from "lucide-react";

const AUTH_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:4000";

interface NpmConfig {
  frontendHost: string;
  frontendPort: number;
  updatedAt: string | null;
}

interface FailedSync {
  domain: string;
  error: string;
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm font-medium">{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export default function AdminSystemPage() {
  const [frontendHost, setFrontendHost] = useState("");
  const [frontendPort, setFrontendPort] = useState("");
  const [portError, setPortError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastResult, setLastResult] = useState<{ synced: number; failed: FailedSync[] } | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${AUTH_URL}/api/system/npm-config`, { credentials: "include" })
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error ?? "Failed to load");
        return r.json();
      })
      .then((data: NpmConfig) => {
        setFrontendHost(data.frontendHost);
        setFrontendPort(String(data.frontendPort));
        setUpdatedAt(data.updatedAt);
      })
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load current NPM config"))
      .finally(() => setLoading(false));
  }, []);

  const validatePort = (val: string): boolean => {
    const n = Number(val);
    if (!val || !Number.isInteger(n) || n < 1 || n > 65535) {
      setPortError("Port must be a whole number between 1 and 65535");
      return false;
    }
    setPortError("");
    return true;
  };

  const saveToDb = async (): Promise<boolean> => {
    if (!frontendHost.trim()) {
      toast.error("Frontend host cannot be empty");
      return false;
    }
    if (!validatePort(frontendPort)) return false;

    const res = await fetch(`${AUTH_URL}/api/system/npm-config`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frontendHost: frontendHost.trim(), frontendPort: Number(frontendPort) }),
    });
    const data = await res.json();
    if (!res.ok) {
      toast.error(data.error ?? "Failed to save");
      return false;
    }
    setUpdatedAt(new Date().toISOString());
    return true;
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const ok = await saveToDb();
      if (ok) toast.success("Saved — new domains will use these values");
    } catch {
      toast.error("Network error — check auth service");
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setLastResult(null);
    try {
      // Always save current form values first so Apply always reflects what's on screen
      const saved = await saveToDb();
      if (!saved) { setSyncing(false); return; }

      const res = await fetch(`${AUTH_URL}/api/system/npm-config/sync`, {
        method: "POST",
        credentials: "include",
      });
      const data = await res.json();
      if (!res.ok) {
        toast.error(data.error ?? "Sync failed");
        return;
      }
      const failed: FailedSync[] = data.failed ?? [];
      setLastResult({ synced: data.synced, failed });
      toast.success(`${data.synced} proxy host${data.synced !== 1 ? "s" : ""} updated`);
      if (failed.length > 0) {
        toast.error(`${failed.length} host${failed.length !== 1 ? "s" : ""} failed to sync`);
      }
    } catch {
      toast.error("Network error — check auth service");
    } finally {
      setSyncing(false);
    }
  };

  const busy = saving || syncing;

  return (
    <div className="space-y-6 max-w-lg">
      <div>
        <h2 className="text-2xl font-semibold">System</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Configure the internal frontend target for Nginx Proxy Manager. Save stores the values to the database. Apply to All saves and immediately updates every existing proxy host.
        </p>
      </div>

      <div className="rounded-xl border border-destructive/50 bg-destructive/5 p-4 flex gap-3">
        <TriangleAlert className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-destructive">Changing these values will immediately affect all active subdomains.</p>
          <p className="text-sm text-destructive/80">
            If the new host or port is unreachable, every tenant using a custom domain will go down until corrected.
            Do not change these unless you have already verified the new target is live and accepting traffic.
          </p>
        </div>
      </div>

      <div className="rounded-xl border bg-card p-5 space-y-5">
        <div>
          <p className="text-sm font-medium">NPM Proxy Config</p>
          {updatedAt && (
            <p className="text-xs text-muted-foreground mt-0.5" suppressHydrationWarning>
              Last updated {new Date(updatedAt).toLocaleString()}
            </p>
          )}
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="space-y-4">
            <Field
              label="Frontend Host"
              hint="Internal hostname or IP that NPM proxies to (e.g. 10.69.5.100)"
            >
              <Input
                value={frontendHost}
                onChange={(e) => setFrontendHost(e.target.value)}
                placeholder="10.69.5.100"
                disabled={busy}
              />
            </Field>

            <Field
              label="Frontend Port"
              hint="Port your Next.js app listens on inside the network (e.g. 3000)"
            >
              <Input
                value={frontendPort}
                onChange={(e) => {
                  setFrontendPort(e.target.value);
                  if (portError) validatePort(e.target.value);
                }}
                placeholder="3000"
                type="number"
                min={1}
                max={65535}
                disabled={busy}
              />
              {!!portError && <p className="text-xs text-destructive mt-1">{portError}</p>}
            </Field>

            <div className="flex gap-2">
              <Button onClick={handleSave} disabled={busy} variant="outline">
                {saving ? "Saving…" : "Save"}
              </Button>
              <Button onClick={handleSync} disabled={busy}>
                {syncing ? "Applying…" : "Apply to All Proxy Hosts"}
              </Button>
            </div>
          </div>
        )}
      </div>

      {lastResult && lastResult.failed.length > 0 && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 space-y-2">
          <p className="text-sm font-medium text-destructive">
            {lastResult.failed.length} host{lastResult.failed.length !== 1 ? "s" : ""} failed to sync
          </p>
          <ul className="space-y-1">
            {lastResult.failed.map((f) => (
              <li key={f.domain} className="text-xs font-mono text-muted-foreground">
                <span className="text-foreground">{f.domain}</span> — {f.error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
