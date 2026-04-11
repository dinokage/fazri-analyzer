"use client";

import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  secret: string;
  active: boolean;
  created_at: string;
}

export function useWebhooks() {
  const [data, setData] = useState<Webhook[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const mutate = useCallback(async () => {
    try {
      const webhooks = await apiClient.listWebhooks();
      setData(webhooks);
    } catch {
      setData([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    mutate();
  }, [mutate]);

  return { data, isLoading, mutate };
}
