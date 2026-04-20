"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CheckCircle2 } from "lucide-react";

const ROLES = ["STUDENT", "STAFF", "FACULTY", "SUPER_ADMIN"] as const;
const ORG_ROLES = ["member", "admin", "owner"] as const;
const STEPS = ["Create Organization", "Create User", "Assign to Org", "Done"];

const STORAGE_KEY = "fazri_admin_onboarding";

interface State {
  orgName: string;
  orgSlug: string;
  orgId: string;
  userName: string;
  userEmail: string;
  userUsername: string;
  userPassword: string;
  userRole: string;
  userDepartment: string;
  orgRole: string;
  userId: string;
}

const DEFAULT_STATE: State = {
  orgName: "", orgSlug: "", orgId: "",
  userName: "", userEmail: "", userUsername: "", userPassword: "", userRole: "STAFF", userDepartment: "",
  orgRole: "owner", userId: "",
};

function saveProgress(step: number, state: State) {
  try {
    const { userPassword: _, ...rest } = state;
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ step, state: rest }));
  } catch {}
}

function clearProgress() {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
}

export function OnboardingWizard() {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [state, setState] = useState<State>(DEFAULT_STATE);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const { step: savedStep, state: savedState } = JSON.parse(raw) as {
          step: number;
          state: Partial<State>;
        };
        if (typeof savedStep === "number" && savedStep > 0 && savedStep < 4) {
          setStep(savedStep);
          setState((s) => ({ ...s, ...savedState }));
        }
      }
    } catch {}
    setMounted(true);
  }, []);

  const set = (key: keyof State, val: string) => setState((s) => ({ ...s, [key]: val }));

  const reset = () => {
    clearProgress();
    setStep(0);
    setState(DEFAULT_STATE);
  };

  const stepZero = async () => {
    // Org already created (user went Back from step 1) — just advance
    if (state.orgId) {
      setStep(1);
      return;
    }
    if (!state.orgName.trim() || !state.orgSlug.trim()) {
      toast.error("Name and slug are required.");
      return;
    }
    setLoading(true);
    const { data, error } = await authClient.organization.create({
      name: state.orgName.trim(),
      slug: state.orgSlug.trim().toLowerCase(),
    });
    setLoading(false);
    if (error) { toast.error(error.message ?? "Failed to create org."); return; }
    const next = { ...state, orgId: (data as { id: string }).id };
    setState(next);
    saveProgress(1, next);
    toast.success(`Organization "${state.orgName}" created.`);
    setStep(1);
  };

  const stepOne = async () => {
    if (!state.userName || !state.userEmail || !state.userUsername || !state.userPassword) {
      toast.error("All fields marked * are required.");
      return;
    }
    setLoading(true);
    const { data, error } = await authClient.admin.createUser({
      name: state.userName,
      email: state.userEmail,
      password: state.userPassword,
      role: state.userRole as "admin" | "user",
      data: {
        entity_id: crypto.randomUUID(),
        username: state.userUsername,
        department: state.userDepartment || undefined,
      },
    });
    setLoading(false);
    if (error) { toast.error(error.message ?? "Failed to create user."); return; }
    const next = { ...state, userId: (data as { user: { id: string } }).user.id };
    setState(next);
    saveProgress(2, next);
    toast.success(`User "${state.userName}" created.`);
    setStep(2);
  };

  const stepTwo = async () => {
    setLoading(true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error } = await (authClient.organization as any).addMember({
      userId: state.userId,
      organizationId: state.orgId,
      role: state.orgRole,
    });
    setLoading(false);
    if (error) { toast.error(error.message ?? "Failed to assign user."); return; }
    saveProgress(3, state);
    toast.success(`${state.userName} added to ${state.orgName} as ${state.orgRole}.`);
    setStep(3);
  };

  if (!mounted) {
    return <div className="rounded-xl border bg-card h-48 animate-pulse" />;
  }

  return (
    <div className="rounded-xl border bg-card">
      {/* Step indicator */}
      <div className="px-6 pt-6 pb-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {STEPS.map((label, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium border-2 transition-colors ${
                  i < step
                    ? "bg-primary border-primary text-primary-foreground"
                    : i === step
                    ? "border-primary text-primary"
                    : "border-muted-foreground/30 text-muted-foreground"
                }`}>
                  {i < step ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
                </div>
                <span className={`text-xs hidden sm:block ${i === step ? "font-medium" : "text-muted-foreground"}`}>
                  {label}
                </span>
                {i < STEPS.length - 1 && (
                  <div className={`h-px flex-1 w-6 ${i < step ? "bg-primary" : "bg-border"}`} />
                )}
              </div>
            ))}
          </div>
          {step > 0 && step < 3 && (
            <button
              onClick={reset}
              className="text-xs text-muted-foreground hover:text-destructive transition-colors ml-4 shrink-0"
            >
              Start over
            </button>
          )}
        </div>
      </div>

      <div className="p-6">
        {step === 0 && (
          <div className="space-y-4 max-w-md">
            <div>
              <h3 className="font-medium">Create Organization</h3>
              <p className="text-sm text-muted-foreground mt-1">Add a new college or institution to the platform.</p>
            </div>

            {state.orgId ? (
              <>
                <div className="rounded-xl border border-green-500/30 bg-green-500/5 p-4 space-y-1.5 text-sm">
                  <div className="flex items-center gap-2 text-green-600 dark:text-green-400 font-medium mb-2">
                    <CheckCircle2 className="h-4 w-4" />
                    Organization already created
                  </div>
                  <p><span className="text-muted-foreground">Name:</span> {state.orgName}</p>
                  <p><span className="text-muted-foreground">Slug:</span> <span className="font-mono">/{state.orgSlug}</span></p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={reset}>Use different org</Button>
                  <Button onClick={() => setStep(1)}>Next: Create User</Button>
                </div>
              </>
            ) : (
              <>
                <Field label="Organization Name *">
                  <Input value={state.orgName} onChange={(e) => {
                    set("orgName", e.target.value);
                    set("orgSlug", e.target.value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, ""));
                  }} placeholder="KIIT University" />
                </Field>
                <Field label="Slug *">
                  <Input value={state.orgSlug} onChange={(e) => set("orgSlug", e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))} placeholder="kiit-university" />
                </Field>
                <Button onClick={stepZero} disabled={loading}>{loading ? "Creating…" : "Next: Create User"}</Button>
              </>
            )}
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4 max-w-md">
            <div>
              <h3 className="font-medium">Create Admin User</h3>
              <p className="text-sm text-muted-foreground mt-1">Create the initial user who will manage <strong>{state.orgName}</strong>.</p>
            </div>
            <Field label="Full Name *">
              <Input value={state.userName} onChange={(e) => set("userName", e.target.value)} placeholder="Dr. Jane Smith" />
            </Field>
            <Field label="Email *">
              <Input type="email" value={state.userEmail} onChange={(e) => set("userEmail", e.target.value)} placeholder="jsmith@college.edu" />
            </Field>
            <Field label="Username *">
              <Input value={state.userUsername} onChange={(e) => set("userUsername", e.target.value)} placeholder="jsmith" />
            </Field>
            <Field label="Password *">
              <Input type="password" value={state.userPassword} onChange={(e) => set("userPassword", e.target.value)} placeholder="Min 8 characters" />
            </Field>
            <Field label="Platform Role">
              <Select value={state.userRole} onValueChange={(v) => set("userRole", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Department">
              <Input value={state.userDepartment} onChange={(e) => set("userDepartment", e.target.value)} placeholder="Computer Science" />
            </Field>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(0)}>Back</Button>
              <Button onClick={stepOne} disabled={loading}>{loading ? "Creating…" : "Next: Assign"}</Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4 max-w-md">
            <div>
              <h3 className="font-medium">Assign User to Organization</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Add <strong>{state.userName}</strong> to <strong>{state.orgName}</strong>.
              </p>
            </div>
            <div className="rounded-xl border bg-muted/30 p-4 space-y-2 text-sm">
              <p><span className="text-muted-foreground">Organization:</span> {state.orgName} <span className="font-mono text-xs text-muted-foreground">/{state.orgSlug}</span></p>
              <p><span className="text-muted-foreground">User:</span> {state.userName} <span className="text-muted-foreground text-xs">({state.userEmail})</span></p>
            </div>
            <Field label="Org Role">
              <Select value={state.orgRole} onValueChange={(v) => set("orgRole", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ORG_ROLES.map((r) => <SelectItem key={r} value={r} className="capitalize">{r}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button onClick={stepTwo} disabled={loading}>{loading ? "Assigning…" : "Complete Onboarding"}</Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4 max-w-md text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10 mx-auto">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
            <div>
              <h3 className="font-medium text-lg">Onboarding Complete</h3>
              <p className="text-sm text-muted-foreground mt-1">
                <strong>{state.orgName}</strong> is set up with <strong>{state.userName}</strong> as <span className="capitalize">{state.orgRole}</span>.
              </p>
            </div>
            <div className="flex gap-2 justify-center">
              <Button asChild variant="outline" size="sm">
                <Link href="/admin/orgs">View Organizations</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/admin/users">View Users</Link>
              </Button>
              <Button size="sm" onClick={reset}>Onboard Another</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}
