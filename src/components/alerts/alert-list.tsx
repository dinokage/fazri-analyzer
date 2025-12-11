'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { RefreshCw, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCard } from './alert-card';
import { AlertFilters } from './alert-filters';
import { useAlerts } from '@/hooks/useAlerts';
import type { AlertStatus, AlertSeverity } from '@/types/alert';

interface AlertListProps {
  defaultFilters?: {
    status?: AlertStatus[];
    severity?: AlertSeverity[];
  };
  showFilters?: boolean;
  compact?: boolean;
  maxItems?: number;
}

export function AlertList({
  defaultFilters,
  showFilters = true,
  compact = false,
  maxItems,
}: AlertListProps) {
  const router = useRouter();
  const [filters, setFilters] = useState<{
    status?: AlertStatus[];
    severity?: AlertSeverity[];
    search?: string;
  }>(defaultFilters || {});

  const { alerts, total, loading, error, refetch } = useAlerts({
    filters: {
      status: filters.status,
      severity: filters.severity,
    },
    pollInterval: 30000,
  });

  // Filter by search locally (backend might not support text search)
  const filteredAlerts = filters.search
    ? alerts.filter(
        (alert) =>
          alert.title.toLowerCase().includes(filters.search!.toLowerCase()) ||
          alert.description.toLowerCase().includes(filters.search!.toLowerCase())
      )
    : alerts;

  const displayAlerts = maxItems ? filteredAlerts.slice(0, maxItems) : filteredAlerts;

  const handleAlertClick = (alertId: string) => {
    router.push(`/dashboard/alerts/${alertId}`);
  };

  if (loading && alerts.length === 0) {
    return (
      <div className="space-y-4">
        {showFilters && <Skeleton className="h-10 w-full" />}
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
        <h3 className="text-lg font-medium text-white mb-2">Failed to load alerts</h3>
        <p className="text-gray-400 mb-4">{error}</p>
        <Button onClick={() => refetch()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {showFilters && (
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1">
            <AlertFilters activeFilters={filters} onFiltersChange={setFilters} />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={loading}
            className="shrink-0"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      )}

      {displayAlerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center border border-dashed border-gray-800 rounded-lg">
          <AlertTriangle className="h-12 w-12 text-gray-600 mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No alerts found</h3>
          <p className="text-gray-400">
            {filters.status || filters.severity || filters.search
              ? 'Try adjusting your filters'
              : 'No security alerts at this time'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {displayAlerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onClick={() => handleAlertClick(alert.id)}
              compact={compact}
            />
          ))}
        </div>
      )}

      {maxItems && filteredAlerts.length > maxItems && (
        <div className="text-center">
          <Button
            variant="link"
            onClick={() => router.push('/dashboard/alerts')}
            className="text-blue-400 hover:text-blue-300"
          >
            View all {total} alerts
          </Button>
        </div>
      )}
    </div>
  );
}
