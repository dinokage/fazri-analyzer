'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { apiClient } from '@/lib/api-client';
import type { Alert, AlertFilters, AlertsResponse } from '@/types/alert';

interface UseAlertsOptions {
  filters?: AlertFilters;
  pollInterval?: number; // in milliseconds, 0 to disable
  enabled?: boolean;
}

interface UseAlertsReturn {
  alerts: Alert[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  newAlerts: Alert[];
  clearNewAlerts: () => void;
}

export function useAlerts(options: UseAlertsOptions = {}): UseAlertsReturn {
  const { filters, pollInterval = 30000, enabled = true } = options;

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newAlerts, setNewAlerts] = useState<Alert[]>([]);

  const previousAlertIdsRef = useRef<Set<string>>(new Set());
  const isFirstFetchRef = useRef(true);
  const isFetchingRef = useRef(false);

  // Memoize filters to prevent infinite re-renders when filters object is recreated
  const memoizedFilters = useMemo(() => ({
    status: filters?.status,
    severity: filters?.severity,
    assigned_to: filters?.assigned_to,
    start_date: filters?.start_date,
    end_date: filters?.end_date,
    page: filters?.page,
    page_size: filters?.page_size,
  }), [
    // Stringify arrays to compare by value, not reference
    JSON.stringify(filters?.status),
    JSON.stringify(filters?.severity),
    filters?.assigned_to,
    filters?.start_date,
    filters?.end_date,
    filters?.page,
    filters?.page_size,
  ]);

  const fetchAlerts = useCallback(async () => {
    if (!enabled) return;

    // Prevent concurrent fetches
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;

    try {
      const response: AlertsResponse = await apiClient.getAlerts(memoizedFilters);

      const fetchedAlerts = response.alerts || [];
      const currentAlertIds = new Set(fetchedAlerts.map((a: Alert) => a.id));

      // Detect new alerts (only after first fetch)
      if (!isFirstFetchRef.current) {
        const newOnes = fetchedAlerts.filter(
          (alert: Alert) => !previousAlertIdsRef.current.has(alert.id)
        );
        if (newOnes.length > 0) {
          setNewAlerts(prev => [...newOnes, ...prev]);
        }
      }

      previousAlertIdsRef.current = currentAlertIds;
      isFirstFetchRef.current = false;

      setAlerts(fetchedAlerts);
      setTotal(response.total || 0);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
    } finally {
      setLoading(false);
      isFetchingRef.current = false;
    }
  }, [enabled, memoizedFilters]);

  const clearNewAlerts = useCallback(() => {
    setNewAlerts([]);
  }, []);

  // Initial fetch - only run once on mount or when filters actually change
  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Polling - separate from initial fetch to avoid double-fetching
  useEffect(() => {
    if (!enabled || pollInterval <= 0) return;

    const intervalId = setInterval(fetchAlerts, pollInterval);
    return () => clearInterval(intervalId);
  }, [enabled, pollInterval, fetchAlerts]);

  return {
    alerts,
    total,
    loading,
    error,
    refetch: fetchAlerts,
    newAlerts,
    clearNewAlerts,
  };
}

// Hook for fetching a single alert
export function useAlert(alertId: string | null) {
  const [alert, setAlert] = useState<Alert | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAlert = useCallback(async () => {
    if (!alertId) return;

    setLoading(true);
    try {
      const data = await apiClient.getAlert(alertId);
      setAlert(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alert');
    } finally {
      setLoading(false);
    }
  }, [alertId]);

  useEffect(() => {
    fetchAlert();
  }, [fetchAlert]);

  return { alert, loading, error, refetch: fetchAlert };
}

// Hook for active (unresolved) alert count
export function useActiveAlertCount(pollInterval = 30000) {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const response = await apiClient.getAlerts({
          status: ['created', 'assigned', 'acknowledged', 'investigating'],
          page_size: 1,
        });
        setCount(response.total || 0);
      } catch {
        // Silently fail for count
      } finally {
        setLoading(false);
      }
    };

    fetchCount();

    if (pollInterval > 0) {
      const intervalId = setInterval(fetchCount, pollInterval);
      return () => clearInterval(intervalId);
    }
  }, [pollInterval]);

  return { count, loading };
}
