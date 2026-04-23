"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Globe, Plus, Trash2, CheckCircle2, Clock, Copy, RefreshCw, ArrowRight,
  Loader2, XCircle, ShieldAlert,
} from "lucide-react";

const AUTH_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:4000";
const SERVER_IP = process.env.NEXT_PUBLIC_FAZRI_SERVER_IP ?? "";

type PageState = "loading" | "list" | "add" | "txt-verification" | "cname-instructions";
type SslStatus = "provisioning" | "active" | "failed" | null;
type DnsCheckStatus = "idle" | "checking" | "ok" | "not-propagated" | "wrong-ip" | "cloudflare-proxy" | "config-error";

interface DomainRecord {
  id: string;
  domain: string;
  ownershipVerified: boolean;
  ownershipVerifiedAt: string | null;
  verified: boolean;
  verifiedAt: string | null;
  verificationToken: string;
  createdAt: string;
  sslStatus: SslStatus;
  sslProvisioningStartedAt: string | null;
  sslError: string | null;
  npmProxyHostId: number | null;
}

interface PendingDomain {
  domain: string;
  txtName: string;
  txtValue: string;
}

interface DnsCheckResult {
  status: DnsCheckStatus;
  resolvedIps: string[];
  expectedIp: string;
  warning?: string;
}

function getEffectiveSslStatus(d: DomainRecord): SslStatus {
  if (!d.verified) return null;
  return d.sslStatus ?? "active"; // null = legacy record before SSL tracking
}

function copyText(text: string, label: string) {
  navigator.clipboard.writeText(text).then(() => toast.success(`${label} copied`));
}

function DnsRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg bg-muted/60 px-3 py-2">
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="font-mono text-xs break-all">{value}</p>
      </div>
      <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={() => copyText(value, label)}>
        <Copy className="h-3 w-3" />
      </Button>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function DnsStatusBanner({ check }: { check: DnsCheckResult | null }) {
  if (!check || check.status === "idle") return null;

  if (check.status === "checking") {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking DNS…
      </div>
    );
  }
  if (check.status === "ok") {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-green-50 dark:bg-green-900/20 px-3 py-2 text-xs text-green-700 dark:text-green-400">
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
        DNS verified — A record resolves to {check.expectedIp}
      </div>
    );
  }
  if (check.status === "not-propagated") {
    return (
      <div className="flex items-start gap-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
        <Clock className="h-3.5 w-3.5 shrink-0 mt-0.5" />
        <span>A record not found yet. DNS propagation can take minutes to 48 hours — checking automatically.</span>
      </div>
    );
  }
  if (check.status === "wrong-ip") {
    return (
      <div className="flex items-start gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 px-3 py-2 text-xs text-red-700 dark:text-red-400">
        <XCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
        <span>
          Resolves to <code className="font-mono">{check.resolvedIps.join(", ")}</code> — expected <code className="font-mono">{check.expectedIp}</code>. Check your DNS panel.
        </span>
      </div>
    );
  }
  if (check.status === "cloudflare-proxy") {
    return (
      <div className="flex items-start gap-2 rounded-lg bg-orange-50 dark:bg-orange-900/20 px-3 py-2 text-xs text-orange-700 dark:text-orange-400">
        <ShieldAlert className="h-3.5 w-3.5 shrink-0 mt-0.5" />
        <span>{check.warning ?? "Domain is behind Cloudflare proxy. Disable the orange cloud for this record."}</span>
      </div>
    );
  }
  if (check.status === "config-error") {
    return (
      <p className="text-xs text-muted-foreground">
        <span className="font-medium">Auth service misconfigured</span> — <code className="font-mono">FAZRI_SERVER_IP</code> is not set. Add your server&apos;s public IP to the auth service env and restart it.
      </p>
    );
  }
  return null;
}

function DomainStatusBadge({ domain }: { domain: DomainRecord }) {
  const sslStatus = getEffectiveSslStatus(domain);

  if (domain.verified) {
    if (sslStatus === "provisioning") {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 shrink-0">
          <Loader2 className="h-3 w-3 animate-spin" /> Provisioning SSL…
        </span>
      );
    }
    if (sslStatus === "failed") {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400 shrink-0">
          <XCircle className="h-3 w-3" /> SSL Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400 shrink-0">
        <CheckCircle2 className="h-3 w-3" /> Active
      </span>
    );
  }
  if (domain.ownershipVerified) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 shrink-0">
        <ArrowRight className="h-3 w-3" /> Pending DNS
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 shrink-0">
      <Clock className="h-3 w-3" /> Pending ownership
    </span>
  );
}

export default function CustomDomainPage() {
  const { data: session } = authClient.useSession();
  const { data: activeOrg } = authClient.useActiveOrganization();

  const [isOwner, setIsOwner] = useState(false);
  const [pageState, setPageState] = useState<PageState>("loading");
  const [domains, setDomains] = useState<DomainRecord[]>([]);
  const [newDomain, setNewDomain] = useState("");
  const [registering, setRegistering] = useState(false);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [pendingDomain, setPendingDomain] = useState<PendingDomain | null>(null);
  const [cnameDomain, setCnameDomain] = useState<string | null>(null);

  // DNS check state for the cname-instructions wizard step
  const [dnsCheck, setDnsCheck] = useState<DnsCheckResult | null>(null);
  const dnsCheckRef = useRef<DnsCheckResult | null>(null);
  const dnsCheckIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Per-domain DNS check results for the inline list view step 2
  const [dnsByDomain, setDnsByDomain] = useState<Map<string, DnsCheckResult>>(new Map());

  // Provisioning poller
  const provisionPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!session || !activeOrg) return;
    const members = (activeOrg as unknown as { members?: { userId: string; role: string }[] }).members ?? [];
    const me = members.find((m) => m.userId === session.user.id);
    setIsOwner(me?.role === "owner" || me?.role === "admin" || (session.user as Record<string, unknown>).role === "SUPER_ADMIN");
  }, [session, activeOrg]);

  const fetchDomains = useCallback(async () => {
    if (!activeOrg) return;
    try {
      const res = await fetch(`${AUTH_URL}/api/domain/${activeOrg.id}`, { credentials: "include" });
      if (!res.ok) { setDomains([]); setPageState("list"); return; }
      const data: DomainRecord[] = await res.json();
      setDomains(data);
      setPageState("list");
    } catch {
      setDomains([]);
      setPageState("list");
    }
  }, [activeOrg]);

  useEffect(() => {
    if (activeOrg) fetchDomains();
  }, [fetchDomains, activeOrg]);

  // Poll while any domain is provisioning SSL
  useEffect(() => {
    const hasProvisioning = domains.some((d) => d.sslStatus === "provisioning");
    if (hasProvisioning) {
      if (!provisionPollRef.current) {
        provisionPollRef.current = setInterval(fetchDomains, 10_000);
      }
    } else {
      if (provisionPollRef.current) {
        clearInterval(provisionPollRef.current);
        provisionPollRef.current = null;
      }
    }
    return () => {
      if (provisionPollRef.current) {
        clearInterval(provisionPollRef.current);
        provisionPollRef.current = null;
      }
    };
  }, [domains, fetchDomains]);

  const checkDns = useCallback(async (domain: string, target: "wizard" | string) => {
    const setResult = (r: DnsCheckResult) => {
      if (target === "wizard") {
        setDnsCheck(r);
      } else {
        setDnsByDomain((prev) => new Map(prev).set(target, r));
      }
    };

    setResult({ status: "checking", resolvedIps: [], expectedIp: SERVER_IP });

    try {
      const res = await fetch(`${AUTH_URL}/api/domain/check-dns?domain=${encodeURIComponent(domain)}`, {
        credentials: "include",
      });
      if (res.status === 429) {
        // silently ignore rate limit — previous result stays
        return;
      }
      const body: DnsCheckResult = await res.json();
      setResult(body);
    } catch {
      setResult({ status: "not-propagated", resolvedIps: [], expectedIp: SERVER_IP });
    }
  }, []);

  // Keep ref in sync so the interval callback always reads the latest dnsCheck status
  useEffect(() => {
    dnsCheckRef.current = dnsCheck;
  }, [dnsCheck]);

  // DNS poll for the wizard cname-instructions state
  useEffect(() => {
    if (pageState === "cname-instructions" && cnameDomain) {
      checkDns(cnameDomain, "wizard");
      dnsCheckIntervalRef.current = setInterval(() => {
        if (dnsCheckRef.current?.status !== "ok") checkDns(cnameDomain, "wizard");
      }, 15_000);
    } else {
      if (dnsCheckIntervalRef.current) {
        clearInterval(dnsCheckIntervalRef.current);
        dnsCheckIntervalRef.current = null;
      }
      setDnsCheck(null);
    }
    return () => {
      if (dnsCheckIntervalRef.current) {
        clearInterval(dnsCheckIntervalRef.current);
        dnsCheckIntervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageState, cnameDomain]);

  const handleRegister = async () => {
    const domain = newDomain.trim().toLowerCase();
    if (!domain) { toast.error("Enter a domain name"); return; }
    setRegistering(true);
    try {
      const res = await fetch(`${AUTH_URL}/api/domain/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ organizationId: activeOrg!.id, domain }),
      });
      const body = await res.json();
      if (!res.ok) { toast.error(body.error ?? "Failed to register domain"); return; }
      setPendingDomain({ domain: body.domain, txtName: body.txtRecord.name, txtValue: body.txtRecord.value });
      setNewDomain("");
      await fetchDomains();
      setPageState("txt-verification");
    } catch {
      toast.error("Failed to register domain");
    } finally {
      setRegistering(false);
    }
  };

  const handleVerifyOwnership = async (domain: string) => {
    setVerifying(domain);
    try {
      const res = await fetch(`${AUTH_URL}/api/domain/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ domain }),
      });
      const body = await res.json();
      if (!res.ok) {
        toast.error(body.error ?? "TXT record not found — check your DNS panel and try again");
      } else {
        toast.success("Ownership verified! Now point your domain to Fazri.");
        setCnameDomain(domain);
        await fetchDomains();
        setPageState("cname-instructions");
      }
    } catch {
      toast.error("Verification request failed");
    } finally {
      setVerifying(null);
    }
  };

  const handleActivate = async (domain: string) => {
    setActivating(domain);
    try {
      const res = await fetch(`${AUTH_URL}/api/domain/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ domain }),
      });
      const body = await res.json();
      if (!res.ok) {
        toast.error(body.error ?? "Activation failed — ensure the A record is set");
      } else {
        toast.success("Domain activated! SSL certificate is being provisioned.");
        setCnameDomain(null);
        await fetchDomains();
        setPageState("list");
      }
    } catch {
      toast.error("Activation request failed");
    } finally {
      setActivating(null);
    }
  };

  const handleRetrySSL = async (id: string, domain: string) => {
    setActivating(domain);
    try {
      const res = await fetch(`${AUTH_URL}/api/domain/${id}/retry-ssl`, {
        method: "POST",
        credentials: "include",
      });
      const body = await res.json();
      if (!res.ok) {
        if (res.status === 429 && body.rateLimited) {
          toast.error("Let's Encrypt rate limit reached. Wait a few days before retrying.");
        } else {
          toast.error(body.error ?? "Failed to retry SSL provisioning");
        }
      } else {
        toast.success("SSL retry started. This may take a few minutes.");
        await fetchDomains();
      }
    } catch {
      toast.error("Request failed");
    } finally {
      setActivating(null);
    }
  };

  const handleSyncNpm = async (id: string, domain: string) => {
    setSyncing(id);
    try {
      const res = await fetch(`${AUTH_URL}/api/domain/${id}/sync-npm`, {
        method: "POST",
        credentials: "include",
      });
      const body = await res.json();
      if (!res.ok) {
        toast.error(body.error ?? "Failed to sync NPM settings");
      } else {
        toast.success(`NPM settings synced for ${domain}`);
      }
    } catch {
      toast.error("Sync request failed");
    } finally {
      setSyncing(null);
    }
  };

  const handleDelete = async (id: string, domain: string) => {
    setDeleting(id);
    try {
      const res = await fetch(`${AUTH_URL}/api/domain/${id}`, { method: "DELETE", credentials: "include" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        toast.error((body as { error?: string }).error ?? "Failed to remove domain");
      } else {
        toast.success(`${domain} removed`);
        await fetchDomains();
      }
    } catch {
      toast.error("Failed to remove domain");
    } finally {
      setDeleting(null);
    }
  };

  if (!activeOrg) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Custom Domain</h2>
        <div className="rounded-xl border bg-card p-6">
          <p className="text-sm text-muted-foreground">No active organization. Join or create one to configure a custom domain.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-2xl font-semibold">Custom Domain</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Map a university-branded URL to <span className="font-medium">{activeOrg.name}</span>
        </p>
      </div>

      <div className="rounded-xl border bg-card p-6 space-y-6">

        {/* Org context row */}
        <div className="flex items-center gap-3 rounded-lg bg-muted/50 border px-3 py-2.5">
          <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">Configuring for organization</p>
            <p className="text-sm font-medium truncate">{activeOrg.name}</p>
          </div>
          <code className="ml-auto text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded shrink-0">
            {activeOrg.slug}
          </code>
        </div>

        <div className="flex items-center justify-between">
          <h3 className="font-medium text-sm">Domains</h3>
          {isOwner && pageState === "list" && (
            <Button size="sm" variant="outline" onClick={() => setPageState("add")}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />Add domain
            </Button>
          )}
        </div>

        <AnimatePresence mode="wait">

          {pageState === "loading" && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-2">
              {Array.from({ length: 2 }).map((_, i) => <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />)}
            </motion.div>
          )}

          {pageState === "add" && (
            <motion.div key="add" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
              <Field label="Domain" hint="Full subdomain you control, e.g. fazri.iitg.ac.in">
                <Input
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  placeholder="fazri.youruniversity.edu"
                  onKeyDown={(e) => e.key === "Enter" && handleRegister()}
                  autoFocus
                />
              </Field>
              <div className="flex gap-2">
                <Button size="sm" onClick={handleRegister} disabled={registering}>
                  {registering ? "Registering…" : "Register Domain"}
                </Button>
                <Button size="sm" variant="outline" onClick={() => { setNewDomain(""); setPageState("list"); }}>Cancel</Button>
              </div>
            </motion.div>
          )}

          {/* Step 1 — prove domain ownership via TXT record */}
          {pageState === "txt-verification" && pendingDomain && (
            <motion.div key="txt" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-5">
              <div className="rounded-lg border bg-muted/50 p-4 space-y-1">
                <p className="text-sm font-medium">Step 1 of 2 — Verify domain ownership</p>
                <p className="text-xs text-muted-foreground">
                  Add this TXT record to your DNS panel to prove you own{" "}
                  <code className="bg-muted px-1 py-0.5 rounded">{pendingDomain.domain}</code>.
                  Once the record propagates, click Verify.
                </p>
              </div>
              <div className="space-y-1.5">
                <DnsRow label="Type" value="TXT" />
                <DnsRow label="Name" value={pendingDomain.txtName} />
                <DnsRow label="Value" value={pendingDomain.txtValue} />
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleVerifyOwnership(pendingDomain.domain)} disabled={verifying === pendingDomain.domain}>
                  <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${verifying === pendingDomain.domain ? "animate-spin" : ""}`} />
                  {verifying === pendingDomain.domain ? "Checking…" : "Verify Ownership"}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setPageState("list")}>Do this later</Button>
              </div>
            </motion.div>
          )}

          {/* Step 2 — point domain via A record then activate */}
          {pageState === "cname-instructions" && cnameDomain && (
            <motion.div key="cname" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-5">
              <div className="rounded-lg border bg-muted/50 p-4 space-y-1">
                <p className="text-sm font-medium">Step 2 of 2 — Point your domain to Fazri</p>
                <p className="text-xs text-muted-foreground">
                  Add this A record so{" "}
                  <code className="bg-muted px-1 py-0.5 rounded">{cnameDomain}</code> resolves to your Fazri instance,
                  then click Activate to provision the SSL certificate.
                </p>
              </div>
              <div className="space-y-1.5">
                <DnsRow label="Type" value="A" />
                <DnsRow label="Name" value={cnameDomain} />
                <DnsRow label="Value" value={SERVER_IP} />
              </div>
              <DnsStatusBanner check={dnsCheck} />
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleActivate(cnameDomain)} disabled={activating === cnameDomain || dnsCheck?.status !== "ok"}>
                  <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${activating === cnameDomain ? "animate-spin" : ""}`} />
                  {activating === cnameDomain ? "Activating…" : "Activate Domain"}
                </Button>
                <Button
                  size="sm" variant="outline"
                  disabled={dnsCheck?.status === "checking"}
                  onClick={() => checkDns(cnameDomain, "wizard")}
                >
                  {dnsCheck?.status === "checking"
                    ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    : <RefreshCw className="h-3.5 w-3.5" />}
                </Button>
                <Button size="sm" variant="outline" onClick={() => { setPageState("list"); setCnameDomain(null); }}>Do this later</Button>
              </div>
            </motion.div>
          )}

          {pageState === "list" && (
            <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
              {domains.length === 0 ? (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    {isOwner
                      ? "No custom domains configured. Add one so your university can access Fazri from their own URL."
                      : "No custom domains configured. Only organization owners can add custom domains."}
                  </p>
                  {isOwner && <Button size="sm" onClick={() => setPageState("add")}>Add domain</Button>}
                </div>
              ) : (
                <>
                  {domains.map((d) => {
                    const sslStatus = getEffectiveSslStatus(d);
                    const inlineDnsCheck = dnsByDomain.get(d.id) ?? null;
                    return (
                      <div key={d.id} className="rounded-lg border p-4 space-y-3">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-sm font-medium truncate">{d.domain}</span>
                            <DomainStatusBadge domain={d} />
                          </div>
                          {isOwner && (
                            <div className="flex items-center gap-1 shrink-0">
                              {d.verified && sslStatus === "active" && (
                                <Button
                                  variant="ghost" size="icon"
                                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                                  disabled={syncing === d.id}
                                  title="Sync NPM settings (SSL, HSTS, HTTP/2)"
                                  onClick={() => handleSyncNpm(d.id, d.domain)}
                                >
                                  <RefreshCw className={`h-3.5 w-3.5 ${syncing === d.id ? "animate-spin" : ""}`} />
                                </Button>
                              )}
                              <Button
                                variant="ghost" size="icon"
                                className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                disabled={deleting === d.id}
                                onClick={() => handleDelete(d.id, d.domain)}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          )}
                        </div>

                        <p className="text-xs text-muted-foreground">
                          Added {new Date(d.createdAt).toLocaleDateString()}
                          {d.verifiedAt && ` · Active since ${new Date(d.verifiedAt).toLocaleDateString()}`}
                        </p>

                        {/* Step 1 inline: ownership not verified yet */}
                        {!d.ownershipVerified && isOwner && (
                          <div className="space-y-3 pt-2 border-t">
                            <p className="text-xs font-medium text-muted-foreground">Add this TXT record to verify ownership</p>
                            <div className="space-y-1.5">
                              <DnsRow label="Name" value={`_fazri-verify.${d.domain}`} />
                              <DnsRow label="Value" value={`fazri-verify=${d.verificationToken}`} />
                            </div>
                            <Button size="sm" variant="outline" onClick={() => handleVerifyOwnership(d.domain)} disabled={verifying === d.domain}>
                              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${verifying === d.domain ? "animate-spin" : ""}`} />
                              {verifying === d.domain ? "Checking…" : "Verify Ownership"}
                            </Button>
                          </div>
                        )}

                        {/* Step 2 inline: ownership verified, A record not set yet */}
                        {d.ownershipVerified && !d.verified && isOwner && (
                          <div className="space-y-3 pt-2 border-t">
                            <p className="text-xs font-medium text-muted-foreground">Add this A record to point your domain</p>
                            <div className="space-y-1.5">
                              <DnsRow label="Name" value={d.domain.split(".")[0]} />
                              <DnsRow label="Value" value={SERVER_IP} />
                            </div>
                            <DnsStatusBanner check={inlineDnsCheck} />
                            <div className="flex gap-2">
                              <Button
                                size="sm" variant="outline"
                                onClick={() => handleActivate(d.domain)}
                                disabled={activating === d.domain || inlineDnsCheck?.status !== "ok"}
                              >
                                <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${activating === d.domain ? "animate-spin" : ""}`} />
                                {activating === d.domain ? "Activating…" : "Activate Domain"}
                              </Button>
                              <Button
                                size="sm" variant="outline"
                                disabled={inlineDnsCheck?.status === "checking"}
                                onClick={() => checkDns(d.domain, d.id)}
                              >
                                {inlineDnsCheck?.status === "checking"
                                  ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  : <RefreshCw className="h-3.5 w-3.5" />}
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* SSL failed: show error and retry */}
                        {d.verified && sslStatus === "failed" && isOwner && (
                          <div className="space-y-2 pt-2 border-t">
                            {d.sslError && (
                              <p className="text-xs text-muted-foreground line-clamp-2">{d.sslError}</p>
                            )}
                            {d.sslError && /too many certificates|rateLimited/i.test(d.sslError) ? (
                              <p className="text-xs text-amber-600 dark:text-amber-400">
                                Let&apos;s Encrypt rate limited (5 certs/week). Wait a few days before retrying.
                              </p>
                            ) : (
                              <Button
                                size="sm" variant="outline"
                                onClick={() => handleRetrySSL(d.id, d.domain)}
                                disabled={activating === d.domain}
                              >
                                <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${activating === d.domain ? "animate-spin" : ""}`} />
                                {activating === d.domain ? "Retrying…" : "Retry SSL"}
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {isOwner && (
                    <Button size="sm" variant="outline" onClick={() => setPageState("add")}>
                      <Plus className="h-3.5 w-3.5 mr-1.5" />Add another domain
                    </Button>
                  )}
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
