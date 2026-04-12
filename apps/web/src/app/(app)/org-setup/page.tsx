"use client";

import { authClient } from "@/lib/auth-client";

export default function OrgSetupPage() {
  const { data: orgs } = authClient.useListOrganizations();

  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="w-full max-w-md space-y-6">
        <h1 className="text-2xl font-semibold">Select your college</h1>
        {orgs && orgs.length > 0 ? (
          <ul className="space-y-2">
            {orgs.map((org) => (
              <li key={org.id}>
                <a
                  href={`/${org.slug}/dashboard`}
                  className="block rounded-lg border p-4 hover:bg-muted transition-colors"
                >
                  <span className="font-medium">{org.name}</span>
                  <span className="ml-2 text-sm text-muted-foreground">/{org.slug}</span>
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground">No colleges found. Contact your administrator.</p>
        )}
      </div>
    </div>
  );
}
