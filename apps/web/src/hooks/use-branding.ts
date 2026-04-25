"use client";

import { authClient } from "@/lib/auth-client";

export interface OrgBranding {
  logo: string | null;
  name: string | null;
  tagline: string | null;
  websiteUrl: string | null;
  primaryColor: string | null;
  faviconUrl: string | null;
  welcomeMessage: string | null;
  loginBgUrl: string | null;
}

const DEFAULT: OrgBranding = {
  logo: null,
  name: null,
  tagline: null,
  websiteUrl: null,
  primaryColor: null,
  faviconUrl: null,
  welcomeMessage: null,
  loginBgUrl: null,
};

function parseMeta(raw: unknown): Partial<OrgBranding> {
  if (!raw) return {};
  if (typeof raw === "object") return raw as Partial<OrgBranding>;
  try { return JSON.parse(raw as string); } catch { return {}; }
}

export function useBranding(): OrgBranding {
  const { data: org } = authClient.useActiveOrganization();
  if (!org) return DEFAULT;
  const meta = parseMeta(org.metadata);
  return {
    logo: org.logo ?? null,
    name: org.name ?? null,
    tagline: meta.tagline ?? null,
    websiteUrl: meta.websiteUrl ?? null,
    primaryColor: meta.primaryColor ?? null,
    faviconUrl: meta.faviconUrl ?? null,
    welcomeMessage: meta.welcomeMessage ?? null,
    loginBgUrl: meta.loginBgUrl ?? null,
  };
}
