"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Palette } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { IdentityTab } from "@/components/settings/branding/identity-tab";
import { AppearanceTab } from "@/components/settings/branding/appearance-tab";
import { CustomDomainTab } from "@/components/settings/branding/custom-domain-tab";

const TABS = ["identity", "appearance", "custom-domain"] as const;
type TabValue = (typeof TABS)[number];

function BrandingPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const rawTab = searchParams.get("tab");
  const activeTab: TabValue = TABS.includes(rawTab as TabValue) ? (rawTab as TabValue) : "identity";

  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", value);
    router.replace(`?${params.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
          <Palette className="h-4.5 w-4.5 text-muted-foreground" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold">Branding</h1>
          <p className="text-sm text-muted-foreground">
            Customize how your organization appears across the dashboard and login page.
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="identity">Identity</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
          <TabsTrigger value="custom-domain">Custom Domain</TabsTrigger>
        </TabsList>

        <TabsContent value="identity" className="mt-6">
          <IdentityTab />
        </TabsContent>

        <TabsContent value="appearance" className="mt-6">
          <AppearanceTab />
        </TabsContent>

        <TabsContent value="custom-domain" className="mt-6">
          <CustomDomainTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function BrandingPage() {
  return (
    <Suspense>
      <BrandingPageInner />
    </Suspense>
  );
}
