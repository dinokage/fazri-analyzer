"use client";

import { useEffect } from "react";
import { useBranding } from "@/hooks/use-branding";

export function BrandingFavicon() {
  const { faviconUrl } = useBranding();

  useEffect(() => {
    if (!faviconUrl) return;
    const existing = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
    if (existing) {
      existing.href = faviconUrl;
    } else {
      const link = document.createElement("link");
      link.rel = "icon";
      link.href = faviconUrl;
      document.head.appendChild(link);
    }
  }, [faviconUrl]);

  return null;
}
