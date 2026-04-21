"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { KeyRound, Trash2 } from "lucide-react";

type ProviderType = "oidc" | "saml";
type PageState = "loading" | "empty" | "configured" | "register";

interface SSOProviderInfo {
  id: string;
  providerId: string;
  issuer: string;
  domain: string;
  type: "oidc" | "saml";
  createdAt: string;
  updatedAt: string;
}

const AUTH_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:4000";

export default function SSOSettingsPage() {
  const { data: session } = authClient.useSession();
  const { data: activeOrg } = authClient.useActiveOrganization();

  const [isOwner, setIsOwner] = useState(false);
  const [pageState, setPageState] = useState<PageState>("loading");
  const [providers, setProviders] = useState<SSOProviderInfo[]>([]);
  const [providerType, setProviderType] = useState<ProviderType>("oidc");

  const [oidcProviderId, setOidcProviderId] = useState("");
  const [oidcIssuer, setOidcIssuer] = useState("");
  const [oidcDomain, setOidcDomain] = useState("");
  const [oidcClientId, setOidcClientId] = useState("");
  const [oidcClientSecret, setOidcClientSecret] = useState("");

  const [samlProviderId, setSamlProviderId] = useState("");
  const [samlIssuer, setSamlIssuer] = useState("");
  const [samlDomain, setSamlDomain] = useState("");
  const [samlEntryPoint, setSamlEntryPoint] = useState("");
  const [samlCert, setSamlCert] = useState("");
  const [samlIdpMetadata, setSamlIdpMetadata] = useState("");

  const [registering, setRegistering] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (!session || !activeOrg) return;
    const members = (activeOrg as unknown as { members?: { userId: string; role: string }[] }).members ?? [];
    const me = members.find((m) => m.userId === session.user.id);
    setIsOwner(me?.role === "owner" || (session.user as Record<string, unknown>).role === "SUPER_ADMIN");
  }, [session, activeOrg]);

  const fetchProviders = useCallback(async () => {
    if (!activeOrg) return;
    try {
      const res = await fetch(`${AUTH_URL}/api/sso-providers/${activeOrg.id}`, {
        credentials: "include",
      });
      if (!res.ok) { setProviders([]); setPageState("empty"); return; }
      const data: SSOProviderInfo[] = await res.json();
      setProviders(data);
      setPageState(data.length > 0 ? "configured" : "empty");
    } catch {
      setProviders([]);
      setPageState("empty");
    }
  }, [activeOrg]);

  useEffect(() => {
    if (activeOrg) fetchProviders();
  }, [fetchProviders, activeOrg]);

  const resetOidcForm = () => {
    setOidcProviderId(""); setOidcIssuer(""); setOidcDomain(""); setOidcClientId(""); setOidcClientSecret("");
  };
  const resetSamlForm = () => {
    setSamlProviderId(""); setSamlIssuer(""); setSamlDomain(""); setSamlEntryPoint(""); setSamlCert(""); setSamlIdpMetadata("");
  };

  const handleRegisterOIDC = async () => {
    if (!oidcProviderId || !oidcIssuer || !oidcDomain || !oidcClientId || !oidcClientSecret) {
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
      await fetch(`${AUTH_URL}/api/sso-providers/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ providerId: oidcProviderId, organizationId: activeOrg!.id }),
      });
    } catch {
      toast.error("Provider registered but failed to link to organization");
    }
    toast.success("OIDC provider registered successfully");
    resetOidcForm();
    setRegistering(false);
    await fetchProviders();
  };

  const handleRegisterSAML = async () => {
    if (!samlProviderId || !samlIssuer || !samlDomain || !samlEntryPoint || !samlCert || !samlIdpMetadata) {
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
      await fetch(`${AUTH_URL}/api/sso-providers/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ providerId: samlProviderId, organizationId: activeOrg!.id }),
      });
    } catch {
      toast.error("Provider registered but failed to link to organization");
    }
    toast.success("SAML provider registered successfully");
    resetSamlForm();
    setRegistering(false);
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

  if (!activeOrg) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">SSO Settings</h2>
        <div className="rounded-xl border bg-card p-6">
          <p className="text-sm text-muted-foreground">
            No active organization. Join or create an organization to configure SSO.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-2xl font-semibold">Single Sign-On</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Configure OIDC or SAML identity providers for <span className="font-medium">{activeOrg.name}</span>
        </p>
      </div>

      <div className="rounded-xl border bg-card p-6 space-y-6">
        <div className="flex items-center gap-2">
          <KeyRound className="h-4 w-4 text-muted-foreground" />
          <h3 className="font-medium text-sm">Identity Providers</h3>
        </div>

        {pageState === "loading" ? (
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
        ) : pageState === "empty" ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {isOwner
                ? "No SSO provider configured. Set up an identity provider to allow your team to sign in with their institution credentials."
                : "No SSO provider configured. Only organization owners can set up SSO."}
            </p>
            {isOwner && (
              <Button size="sm" onClick={() => setPageState("register")}>
                Set up SSO
              </Button>
            )}
          </div>
        ) : pageState === "register" ? (
          <div className="space-y-6">
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
                <motion.div key="oidc" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
                  <Field label="Provider ID">
                    <Input value={oidcProviderId} onChange={(e) => setOidcProviderId(e.target.value)} placeholder="e.g. google-workspace, azure-ad" />
                  </Field>
                  <Field label="Issuer URL" hint="Base issuer URL only — do not include /.well-known/openid-configuration">
                    <Input type="url" value={oidcIssuer} onChange={(e) => setOidcIssuer(e.target.value)} placeholder="https://accounts.google.com" />
                  </Field>
                  <Field label="Domain" hint="Email domain for users who should use this provider">
                    <Input value={oidcDomain} onChange={(e) => setOidcDomain(e.target.value)} placeholder="yourcollege.edu" />
                  </Field>
                  <Field label="Client ID">
                    <Input value={oidcClientId} onChange={(e) => setOidcClientId(e.target.value)} placeholder="Your OIDC client ID" />
                  </Field>
                  <Field label="Client Secret">
                    <Input type="password" value={oidcClientSecret} onChange={(e) => setOidcClientSecret(e.target.value)} placeholder="Your OIDC client secret" />
                  </Field>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={handleRegisterOIDC} disabled={registering}>
                      {registering ? "Registering…" : "Register OIDC Provider"}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => { resetOidcForm(); setPageState(providers.length > 0 ? "configured" : "empty"); }}>
                      Cancel
                    </Button>
                  </div>
                </motion.div>
              ) : (
                <motion.div key="saml" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
                  <Field label="Provider ID">
                    <Input value={samlProviderId} onChange={(e) => setSamlProviderId(e.target.value)} placeholder="e.g. okta-saml, azure-ad-saml" />
                  </Field>
                  <Field label="Issuer / Entity ID">
                    <Input value={samlIssuer} onChange={(e) => setSamlIssuer(e.target.value)} placeholder="https://idp.example.com" />
                  </Field>
                  <Field label="Domain" hint="Email domain for users who should use this provider">
                    <Input value={samlDomain} onChange={(e) => setSamlDomain(e.target.value)} placeholder="yourcollege.edu" />
                  </Field>
                  <Field label="SSO Entry Point URL">
                    <Input type="url" value={samlEntryPoint} onChange={(e) => setSamlEntryPoint(e.target.value)} placeholder="https://your-idp.com/saml/sso" />
                  </Field>
                  <Field label="IdP Certificate">
                    <Textarea
                      value={samlCert}
                      onChange={(e) => setSamlCert(e.target.value)}
                      rows={4}
                      className="font-mono text-xs"
                      placeholder={"-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"}
                    />
                  </Field>
                  <Field label="IdP Metadata XML">
                    <Textarea
                      value={samlIdpMetadata}
                      onChange={(e) => setSamlIdpMetadata(e.target.value)}
                      rows={6}
                      className="font-mono text-xs"
                      placeholder="Paste IdP metadata XML here"
                    />
                  </Field>
                  {samlProviderId && (
                    <div className="rounded-lg border bg-muted/50 p-4 space-y-2">
                      <p className="text-xs font-medium">SP Metadata for your IdP</p>
                      <div className="text-xs text-muted-foreground space-y-1">
                        <p><span className="font-medium">ACS URL:</span> <code className="bg-muted px-1 py-0.5 rounded">{AUTH_URL}/api/auth/sso/saml2/callback/{samlProviderId}</code></p>
                        <p><span className="font-medium">SP Metadata URL:</span> <code className="bg-muted px-1 py-0.5 rounded">{AUTH_URL}/api/auth/sso/saml2/sp/metadata?providerId={samlProviderId}</code></p>
                      </div>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button size="sm" onClick={handleRegisterSAML} disabled={registering}>
                      {registering ? "Registering…" : "Register SAML Provider"}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => { resetSamlForm(); setPageState(providers.length > 0 ? "configured" : "empty"); }}>
                      Cancel
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ) : pageState === "configured" ? (
          <div className="space-y-4">
            {providers.map((provider) => (
              <div key={provider.id} className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{provider.providerId}</span>
                    <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      {provider.type.toUpperCase()}
                    </span>
                  </div>
                  <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                    <span>Domain: {provider.domain}</span>
                    <span>Issuer: {provider.issuer}</span>
                    <span>Added: {new Date(provider.createdAt).toLocaleDateString()}</span>
                  </div>
                  {provider.type === "saml" && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      <span className="font-medium">ACS URL:</span>{" "}
                      <code className="bg-muted px-1 py-0.5 rounded">{AUTH_URL}/api/auth/sso/saml2/callback/{provider.providerId}</code>
                    </p>
                  )}
                </div>
                {isOwner && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10 shrink-0 ml-3"
                    disabled={deleting === provider.providerId}
                    onClick={() => handleDelete(provider.providerId)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            ))}
            {isOwner ? (
              <Button size="sm" variant="outline" onClick={() => setPageState("register")}>
                Add another provider
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground">Only organization owners can add or remove SSO providers.</p>
            )}
          </div>
        ) : null}
      </div>
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