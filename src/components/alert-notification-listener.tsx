'use client';

import { useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { ShieldAlert, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { useAlerts } from '@/hooks/useAlerts';
import type { Alert, AlertSeverity } from '@/types/alert';

const STORAGE_KEY = 'fazri_notified_alerts';

// Get notified alert IDs from localStorage
function getNotifiedAlertIds(): Set<string> {
  if (typeof window === 'undefined') return new Set();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Clean up old entries (older than 24 hours)
      const now = Date.now();
      const filtered = Object.entries(parsed)
        .filter(([, timestamp]) => now - (timestamp as number) < 24 * 60 * 60 * 1000)
        .map(([id]) => id);
      return new Set(filtered);
    }
  } catch {
    // Ignore parsing errors
  }
  return new Set();
}

// Save notified alert ID to localStorage
function saveNotifiedAlertId(alertId: string) {
  if (typeof window === 'undefined') return;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const existing = stored ? JSON.parse(stored) : {};
    existing[alertId] = Date.now();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));
  } catch {
    // Ignore storage errors
  }
}

// Get icon component based on severity
function getSeverityIcon(severity: AlertSeverity) {
  switch (severity) {
    case 'critical':
      return <ShieldAlert className="h-5 w-5 text-red-500" />;
    case 'high':
      return <AlertTriangle className="h-5 w-5 text-orange-500" />;
    case 'medium':
      return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    case 'low':
    default:
      return <Info className="h-5 w-5 text-blue-500" />;
  }
}

// Get toast type based on severity
function getToastType(severity: AlertSeverity): 'error' | 'warning' | 'info' {
  switch (severity) {
    case 'critical':
    case 'high':
      return 'error';
    case 'medium':
      return 'warning';
    case 'low':
    default:
      return 'info';
  }
}

interface AlertNotificationListenerProps {
  enabled?: boolean;
  pollInterval?: number;
}

export function AlertNotificationListener({
  enabled = true,
  pollInterval = 30000,
}: AlertNotificationListenerProps) {
  const router = useRouter();
  const notifiedIdsRef = useRef<Set<string>>(new Set());
  const isInitializedRef = useRef(false);

  // Only fetch active alerts (not resolved)
  const { newAlerts, clearNewAlerts } = useAlerts({
    filters: {
      status: ['created', 'assigned', 'acknowledged', 'investigating'],
    },
    pollInterval,
    enabled,
  });

  // Initialize notified IDs from localStorage
  useEffect(() => {
    if (!isInitializedRef.current) {
      notifiedIdsRef.current = getNotifiedAlertIds();
      isInitializedRef.current = true;
    }
  }, []);

  const showAlertToast = useCallback(
    (alert: Alert) => {
      const toastType = getToastType(alert.severity);
      const icon = getSeverityIcon(alert.severity);

      const toastFn = toastType === 'error' ? toast.error : toastType === 'warning' ? toast.warning : toast.info;

      toastFn(alert.title, {
        description: alert.description.length > 100
          ? alert.description.substring(0, 100) + '...'
          : alert.description,
        icon,
        duration: alert.severity === 'critical' ? 10000 : 5000,
        action: {
          label: 'View',
          onClick: () => router.push(`/dashboard/alerts/${alert.id}`),
        },
      });

      // Mark as notified
      notifiedIdsRef.current.add(alert.id);
      saveNotifiedAlertId(alert.id);
    },
    [router]
  );

  // Show toasts for new alerts
  useEffect(() => {
    if (!enabled || newAlerts.length === 0) return;

    // Filter out already notified alerts
    const unnotifiedAlerts = newAlerts.filter(
      (alert) => !notifiedIdsRef.current.has(alert.id)
    );

    // Show toast for each new alert (limit to 5 to avoid flooding)
    const alertsToShow = unnotifiedAlerts.slice(0, 5);
    alertsToShow.forEach((alert) => {
      showAlertToast(alert);
    });

    // If there are more alerts, show a summary toast
    if (unnotifiedAlerts.length > 5) {
      toast.info(`+${unnotifiedAlerts.length - 5} more alerts`, {
        description: 'Check the alerts dashboard for all new alerts',
        action: {
          label: 'View All',
          onClick: () => router.push('/dashboard/alerts'),
        },
      });
    }

    // Clear the new alerts from the hook
    clearNewAlerts();
  }, [enabled, newAlerts, clearNewAlerts, showAlertToast, router]);

  // This component doesn't render anything
  return null;
}
