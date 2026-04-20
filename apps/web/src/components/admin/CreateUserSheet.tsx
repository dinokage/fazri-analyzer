"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
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
const ORG_ROLES = ["member", "admin", "owner"] as const;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function CreateUserSheet({ open, onOpenChange, onSuccess }: Props) {
  const { data: orgs } = authClient.useListOrganizations();

  const [form, setForm] = useState({
    name: "",
    email: "",
    username: "",
    password: "",
    role: "STUDENT",
    department: "",
    student_id: "",
    staff_id: "",
    card_id: "",
    orgId: "",
    orgRole: "member",
  });
  const [submitting, setSubmitting] = useState(false);

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const handleSubmit = async () => {
    if (!form.name || !form.email || !form.username || !form.password) {
      toast.error("Name, email, username, and password are required.");
      return;
    }
    setSubmitting(true);
    try {
      const { data: created, error } = await authClient.admin.createUser({
        name: form.name,
        email: form.email,
        password: form.password,
        role: form.role as "admin" | "user",
        data: {
          username: form.username,
          department: form.department || undefined,
          student_id: form.student_id || undefined,
          staff_id: form.staff_id || undefined,
          card_id: form.card_id || undefined,
        },
      });
      if (error) {
        toast.error(error.message ?? "Failed to create user.");
        return;
      }
      if (form.orgId && created?.user?.id) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { error: memberErr } = await (authClient.organization as any).addMember({
          userId: created.user.id,
          organizationId: form.orgId,
          role: form.orgRole,
        });
        if (memberErr) {
          toast.error(`User created but org assignment failed: ${memberErr.message}`);
        }
      }
      toast.success(`User "${form.name}" created.`);
      onSuccess();
      onOpenChange(false);
      setForm({
        name: "", email: "", username: "", password: "", role: "STUDENT",
        department: "", student_id: "", staff_id: "", card_id: "", orgId: "", orgRole: "member",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[440px] sm:max-w-[440px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Create User</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          <Field label="Full Name *">
            <Input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Jane Smith" />
          </Field>
          <Field label="Email *">
            <Input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="jane@college.edu" />
          </Field>
          <Field label="Username *">
            <Input value={form.username} onChange={(e) => set("username", e.target.value)} placeholder="janesmith" />
          </Field>
          <Field label="Password *">
            <Input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} placeholder="Min 8 characters" />
          </Field>

          <Field label="Platform Role">
            <Select value={form.role} onValueChange={(v) => set("role", v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>

          <Field label="Department">
            <Input value={form.department} onChange={(e) => set("department", e.target.value)} placeholder="Computer Science" />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Student ID">
              <Input value={form.student_id} onChange={(e) => set("student_id", e.target.value)} placeholder="2100XXXXX" />
            </Field>
            <Field label="Staff ID">
              <Input value={form.staff_id} onChange={(e) => set("staff_id", e.target.value)} placeholder="STF-XXX" />
            </Field>
          </div>

          <Field label="Card ID">
            <Input value={form.card_id} onChange={(e) => set("card_id", e.target.value)} placeholder="RFID card number" />
          </Field>

          {orgs && orgs.length > 0 && (
            <>
              <div className="border-t pt-4">
                <p className="text-xs text-muted-foreground mb-3 font-medium uppercase tracking-wide">Optional — Assign to Organization</p>
              </div>
              <Field label="Organization">
                <Select value={form.orgId} onValueChange={(v) => set("orgId", v)}>
                  <SelectTrigger><SelectValue placeholder="Select org (optional)" /></SelectTrigger>
                  <SelectContent>
                    {orgs.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
              {form.orgId && (
                <Field label="Org Role">
                  <Select value={form.orgRole} onValueChange={(v) => set("orgRole", v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {ORG_ROLES.map((r) => <SelectItem key={r} value={r} className="capitalize">{r}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </>
          )}

          <div className="flex gap-2 pt-2">
            <Button onClick={handleSubmit} disabled={submitting} className="flex-1">
              {submitting ? "Creating…" : "Create User"}
            </Button>
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
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
