"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { authClient } from "@/lib/auth-client";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Trash2 } from "lucide-react";

type ProviderType = "oidc" | "saml";
type PageState = "loading" | "empty" | "configured" | "register" | "error";

interface SSOProviderInfo {
  id: string;
  providerId: string;
  issuer: string;
  domain: string;
  type: "oidc" | "saml";
  createdAt: string;
  updatedAt: string;
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

const AUTH_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:4000";

export function OrgSSOSheet({ open, onOpenChange, org }: Props) {
  const [pageState, setPageState] = useState<PageState>("loading");
  const [providers, setProviders] = useState<SSOProviderInfo[]>([]);
  const [providerType, setProviderType] = useState<ProviderType>("oidc");

  const [oidcSuffix, setOidcSuffix] = useState("");
  const [oidcIssuer, setOidcIssuer] = useState("");
  const [oidcDomain, setOidcDomain] = useState("");
  const [oidcClientId, setOidcClientId] = useState("");
  const [oidcClientSecret, setOidcClientSecret] = useState("");

  const [samlSuffix, setSamlSuffix] = useState("");
  const [samlIssuer, setSamlIssuer] = useState("");
  const [samlDomain, setSamlDomain] = useState("");
  const [samlEntryPoint, setSamlEntryPoint] = useState("");
  const [samlCert, setSamlCert] = useState("");
  const [samlIdpMetadata, setSamlIdpMetadata] = useState("");

  // Provider IDs — org slug prefix guarantees global uniqueness, user picks the suffix
  const oidcProviderId = oidcSuffix ? `${org.slug}-${oidcSuffix}` : "";
  const samlProviderId = samlSuffix ? `${org.slug}-${samlSuffix}` : "";

  const [registering, setRegistering] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const resetOidc = useCallback(() => { setOidcSuffix(""); setOidcIssuer(""); setOidcDomain(""); setOidcClientId(""); setOidcClientSecret(""); }, []);
  const resetSaml = useCallback(() => { setSamlSuffix(""); setSamlIssuer(""); setSamlDomain(""); setSamlEntryPoint(""); setSamlCert(""); setSamlIdpMetadata(""); }, []);

  const fetchProviders = useCallback(async () => {
    setPageState("loading");
    try {
      const res = await fetch(`${AUTH_URL}/api/sso-providers/${org.id}`, {
        credentials: "include",
      });
      if (!res.ok) {
        const msg = await res.text().catch(() => "");
        toast.error(`Failed to load SSO providers [${org.id}] — HTTP ${res.status}${msg ? `: ${msg}` : ""} (${AUTH_URL})`);
        setProviders([]);
        setPageState("error");
        return;
      }
      const data: SSOProviderInfo[] = await res.json();
      setProviders(data);
      setPageState(data.length > 0 ? "configured" : "empty");
    } catch {
      toast.error("Network error loading SSO providers — check auth service connectivity");
      setProviders([]);
      setPageState("error");
    }
  }, [org.id]);

  useEffect(() => {
    setProviderType("oidc");
    resetOidc();
    resetSaml();
  }, [org.id, open, resetOidc, resetSaml]);

  useEffect(() => {
    if (open) fetchProviders();
  }, [open, fetchProviders]);

  const handleRegisterOIDC = async () => {
    if (!oidcSuffix || !oidcIssuer || !oidcDomain || !oidcClientId || !oidcClientSecret) {
      toast.error("Please fill in all fields"); return;
    }
    setRegistering(true);
    const issuer = oidcIssuer.replace(/\/\.well-known\/openid-configuration\/?$/, "");
    const { error } = await authClient.sso.register({
      providerId: oidcProviderId,
      issuer,
      domain: oidcDomain,
      oidcConfig: { clientId: oidcClientId, clientSecret: oidcClientSecret },
    });
    if (error) {
      toast.error((error as Record<string, unknown>).message as string ?? "Failed to register OIDC provider");
      setRegistering(false); return;
    }
    try {
      const res = await fetch(`${AUTH_URL}/api/sso-providers/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ providerId: oidcProviderId, organizationId: org.id }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        await fetch(`${AUTH_URL}/api/sso-providers/${oidcProviderId}`, { method: "DELETE", credentials: "include" }).catch(() => {});
        toast.error((body as { error?: string }).error ?? "Failed to link provider to organization");
        setRegistering(false); return;
      }
    } catch {
      await fetch(`${AUTH_URL}/api/sso-providers/${oidcProviderId}`, { method: "DELETE", credentials: "include" }).catch(() => {});
      toast.error("Provider registered but failed to link to organization");
      setRegistering(false); return;
    }
    toast.success("OIDC provider registered successfully");
    resetOidc(); setRegistering(false);
    await fetchProviders();
  };

  const handleRegisterSAML = async () => {
    if (!samlSuffix || !samlIssuer || !samlDomain || !samlEntryPoint || !samlCert || !samlIdpMetadata) {
      toast.error("Please fill in all fields"); return;
    }
    setRegistering(true);
    const acsUrl = `${AUTH_URL}/api/auth/sso/saml2/callback/${samlProviderId}`;
    const spEntityId = `${AUTH_URL}/api/auth/sso/saml2/sp/metadata`;
    const { error } = await authClient.sso.register({
      providerId: samlProviderId,
      issuer: samlIssuer,
      domain: samlDomain,
      samlConfig: {
        entryPoint: samlEntryPoint,
        cert: samlCert,
        callbackUrl: acsUrl,
        idpMetadata: { metadata: samlIdpMetadata },
        spMetadata: { entityID: spEntityId },
      },
    });
    if (error) {
      toast.error((error as Record<string, unknown>).message as string ?? "Failed to register SAML provider");
      setRegistering(false); return;
    }
    try {
      const res = await fetch(`${AUTH_URL}/api/sso-providers/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ providerId: samlProviderId, organizationId: org.id }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        await fetch(`${AUTH_URL}/api/sso-providers/${samlProviderId}`, { method: "DELETE", credentials: "include" }).catch(() => {});
        toast.error((body as { error?: string }).error ?? "Failed to link provider to organization");
        setRegistering(false); return;
      }
    } catch {
      await fetch(`${AUTH_URL}/api/sso-providers/${samlProviderId}`, { method: "DELETE", credentials: "include" }).catch(() => {});
      toast.error("Provider registered but failed to link to organization");
      setRegistering(false); return;
    }
    toast.success("SAML provider registered successfully");
    resetSaml(); setRegistering(false);
    await fetchProviders();
  };

  const handleDelete = async (providerId: string) => {
    setDeleting(providerId);
    try {
      const res = await fetch(`${AUTH_URL}/api/sso-providers/${providerId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        toast.error((body as { error?: string }).error ?? "Failed to delete SSO provider");
      } else {
        toast.success("SSO provider deleted");
        await fetchProviders();
      }
    } catch {
      toast.error("Failed to delete SSO provider");
    }
    setDeleting(null);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[680px] sm:max-w-[680px] overflow-y-auto px-6">
        <SheetHeader className="pb-4 border-b">
          <SheetTitle className="text-lg">{org.name} — SSO Settings</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {pageState === "loading" ? (
            <div className="space-y-2">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-muted" />
              ))}
            </div>
          ) : pageState === "error" ? (
            <div className="space-y-3">
              <p className="text-sm text-destructive">Failed to load SSO providers. Check the toast for details.</p>
              <Button size="sm" variant="outline" onClick={fetchProviders}>Retry</Button>
            </div>
          ) : pageState === "empty" ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">No SSO provider configured for this organization.</p>
              <Button size="sm" onClick={() => setPageState("register")}>Set up SSO</Button>
            </div>
          ) : pageState === "register" ? (
            <div className="space-y-5">
              <div className="flex gap-1 rounded-lg bg-muted p-1">
                {(["oidc", "saml"] as ProviderType[]).map((type) => (
                  <button
                    key={type}
                    onClick={() => setProviderType(type)}
                    className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
                      providerType === type
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {type.toUpperCase()}
                  </button>
                ))}
              </div>

              <AnimatePresence mode="wait">
                {providerType === "oidc" ? (
                  <motion.div key="oidc" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-5">
                    <SSOField label="Provider ID" hint={`Will be registered as: ${org.slug}-${oidcSuffix || "<name>"}`}>
                      <div className="flex items-center">
                        <span className="flex h-10 shrink-0 items-center rounded-l-md border border-r-0 bg-muted px-3 text-sm text-muted-foreground select-none whitespace-nowrap">{org.slug}-</span>
                        <Input value={oidcSuffix} onChange={(e) => setOidcSuffix(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))} placeholder="gsuite" className="rounded-l-none flex-1" />
                      </div>
                    </SSOField>
                    <SSOField label="Issuer URL" hint="Do not include /.well-known/openid-configuration">
                      <Input type="url" value={oidcIssuer} onChange={(e) => setOidcIssuer(e.target.value)} placeholder="https://accounts.google.com" />
                    </SSOField>
                    <SSOField label="Domain" hint="Email domain (e.g. college.edu)"><Input value={oidcDomain} onChange={(e) => setOidcDomain(e.target.value)} placeholder="college.edu" /></SSOField>
                    <SSOField label="Client ID"><Input value={oidcClientId} onChange={(e) => setOidcClientId(e.target.value)} /></SSOField>
                    <SSOField label="Client Secret"><Input type="password" value={oidcClientSecret} onChange={(e) => setOidcClientSecret(e.target.value)} /></SSOField>
                    <div className="flex gap-2 pt-2">
                      <Button size="sm" onClick={handleRegisterOIDC} disabled={registering}>{registering ? "Registering…" : "Register OIDC"}</Button>
                      <Button size="sm" variant="outline" onClick={() => { resetOidc(); setPageState(providers.length > 0 ? "configured" : "empty"); }}>Cancel</Button>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div key="saml" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-5">
                    <SSOField label="Provider ID" hint={`Will be registered as: ${org.slug}-${samlSuffix || "<name>"}`}>
                      <div className="flex items-center">
                        <span className="flex h-10 shrink-0 items-center rounded-l-md border border-r-0 bg-muted px-3 text-sm text-muted-foreground select-none whitespace-nowrap">{org.slug}-</span>
                        <Input value={samlSuffix} onChange={(e) => setSamlSuffix(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))} placeholder="gsuite" className="rounded-l-none flex-1" />
                      </div>
                    </SSOField>
                    {samlSuffix && (
                      <div className="rounded-lg border bg-muted/50 p-3 text-xs text-muted-foreground space-y-1">
                        <p className="font-medium text-foreground mb-1">Copy these into your Identity Provider:</p>
                        <p><span className="font-medium">ACS URL:</span> <code className="bg-muted px-1 rounded break-all">{AUTH_URL}/api/auth/sso/saml2/callback/{samlProviderId}</code></p>
                        <p><span className="font-medium">Entity ID:</span> <code className="bg-muted px-1 rounded break-all">{AUTH_URL}/api/auth/sso/saml2/sp/metadata</code></p>
                      </div>
                    )}
                    <SSOField label="Issuer / Entity ID"><Input value={samlIssuer} onChange={(e) => setSamlIssuer(e.target.value)} placeholder="https://idp.example.com" /></SSOField>
                    <SSOField label="Domain"><Input value={samlDomain} onChange={(e) => setSamlDomain(e.target.value)} placeholder="college.edu" /></SSOField>
                    <SSOField label="SSO Entry Point URL"><Input type="url" value={samlEntryPoint} onChange={(e) => setSamlEntryPoint(e.target.value)} /></SSOField>
                    <SSOField label="IdP Certificate">
                      <Textarea value={samlCert} onChange={(e) => setSamlCert(e.target.value)} rows={3} className="font-mono text-xs" placeholder={"-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"} />
                    </SSOField>
                    <SSOField label="IdP Metadata XML">
                      <Textarea value={samlIdpMetadata} onChange={(e) => setSamlIdpMetadata(e.target.value)} rows={5} className="font-mono text-xs" placeholder="Paste IdP metadata XML here" />
                    </SSOField>
                    <div className="flex gap-2 pt-2">
                      <Button size="sm" onClick={handleRegisterSAML} disabled={registering}>{registering ? "Registering…" : "Register SAML"}</Button>
                      <Button size="sm" variant="outline" onClick={() => { resetSaml(); setPageState(providers.length > 0 ? "configured" : "empty"); }}>Cancel</Button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : providers.map((provider) => (
            <div key={provider.id} className="flex items-start justify-between rounded-lg border p-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{provider.providerId}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">{provider.type.toUpperCase()}</span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground space-y-0.5">
                  <p>Domain: {provider.domain}</p>
                  <p>Issuer: {provider.issuer}</p>
                  <p>Added: {new Date(provider.createdAt).toLocaleDateString()}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10 shrink-0"
                disabled={deleting === provider.providerId}
                onClick={() => handleDelete(provider.providerId)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}

          {pageState === "configured" && (
            <Button size="sm" variant="outline" onClick={() => setPageState("register")}>Add another provider</Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function SSOField({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
