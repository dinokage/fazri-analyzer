"use client";

import { useState, useRef } from "react";
import { authClient } from "@/lib/auth-client";
import { toast } from "sonner";
import { OnboardingWizard } from "@/components/admin/OnboardingWizard";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Upload } from "lucide-react";

interface CsvRow {
  name: string;
  email: string;
  username: string;
  password: string;
  role: string;
  department: string;
}

export default function AdminOnboardingPage() {
  const [showBulk, setShowBulk] = useState(false);
  const [csvRows, setCsvRows] = useState<CsvRow[]>([]);
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  const parseCsv = (text: string): CsvRow[] => {
    const lines = text.trim().split("\n").filter(Boolean);
    if (lines.length < 2) return [];
    const headers = lines[0].split(",").map((h) => h.trim().replace(/^"(.+)"$/, "$1").toLowerCase());
    return lines.slice(1).map((line) => {
      const values = line.split(",").map((v) => v.trim().replace(/^"(.+)"$/, "$1"));
      const row: Record<string, string> = {};
      headers.forEach((h, i) => { row[h] = values[i] ?? ""; });
      return {
        name: row.name ?? "",
        email: row.email ?? "",
        username: row.username ?? "",
        password: row.password ?? "",
        role: row.role ?? "STUDENT",
        department: row.department ?? "",
      };
    }).filter((r) => r.name && r.email && r.username && r.password);
  };

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const rows = parseCsv(text);
      if (rows.length === 0) {
        toast.error("No valid rows found. Expected columns: name, email, username, password, role, department");
        return;
      }
      setCsvRows(rows);
      toast.success(`Parsed ${rows.length} users from CSV.`);
    };
    reader.readAsText(file);
  };

  const importUsers = async () => {
    if (!csvRows.length) return;
    setImporting(true);
    setImportProgress(0);
    let success = 0;
    let failed = 0;

    for (let i = 0; i < csvRows.length; i++) {
      const row = csvRows[i];
      const { error } = await authClient.admin.createUser({
        name: row.name,
        email: row.email,
        password: row.password,
        role: row.role as "admin" | "user",
        data: {
          username: row.username,
          department: row.department || undefined,
        },
      });
      if (error) failed++;
      else success++;
      setImportProgress(Math.round(((i + 1) / csvRows.length) * 100));
    }

    toast.success(`Import done: ${success} created, ${failed} failed.`);
    setCsvRows([]);
    setImporting(false);
    setImportProgress(0);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Onboarding</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Add a new college to the platform or bulk-import users.
        </p>
      </div>

      <OnboardingWizard />

      {/* Bulk import */}
      <div className="rounded-xl border bg-card">
        <button
          className="w-full flex items-center justify-between px-5 py-4 text-sm font-medium hover:bg-muted/30 transition-colors rounded-xl"
          onClick={() => setShowBulk((v) => !v)}
        >
          <span>Bulk User Import (CSV)</span>
          {showBulk ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {showBulk && (
          <div className="px-5 pb-5 space-y-4 border-t">
            <p className="text-xs text-muted-foreground mt-4">
              Expected CSV columns: <code className="bg-muted px-1 rounded">name, email, username, password, role, department</code>
            </p>

            <div className="flex items-center gap-3">
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                onChange={handleFile}
                className="hidden"
                id="csv-upload"
              />
              <label htmlFor="csv-upload">
                <Button variant="outline" size="sm" asChild>
                  <span className="cursor-pointer">
                    <Upload className="h-4 w-4 mr-1.5" />
                    Choose CSV File
                  </span>
                </Button>
              </label>
              {csvRows.length > 0 && (
                <span className="text-sm text-muted-foreground">{csvRows.length} users ready to import</span>
              )}
            </div>

            {csvRows.length > 0 && (
              <>
                <div className="rounded-xl border overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50 text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium">Name</th>
                        <th className="px-3 py-2 text-left font-medium">Email</th>
                        <th className="px-3 py-2 text-left font-medium">Username</th>
                        <th className="px-3 py-2 text-left font-medium">Role</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {csvRows.slice(0, 10).map((r, i) => (
                        <tr key={i}>
                          <td className="px-3 py-2">{r.name}</td>
                          <td className="px-3 py-2 text-muted-foreground">{r.email}</td>
                          <td className="px-3 py-2 font-mono">{r.username}</td>
                          <td className="px-3 py-2">{r.role}</td>
                        </tr>
                      ))}
                      {csvRows.length > 10 && (
                        <tr>
                          <td colSpan={4} className="px-3 py-2 text-center text-muted-foreground">
                            … and {csvRows.length - 10} more
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {importing && (
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Importing users…</span>
                      <span>{importProgress}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${importProgress}%` }}
                      />
                    </div>
                  </div>
                )}

                <Button
                  onClick={importUsers}
                  disabled={importing}
                  size="sm"
                >
                  {importing ? `Importing… (${importProgress}%)` : `Import ${csvRows.length} Users`}
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
