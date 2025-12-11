'use client';

import { useRouter } from 'next/navigation';
import { ShieldAlert, ArrowRight, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCard } from './alert-card';
import { useAlerts } from '@/hooks/useAlerts';

interface RecentAlertsCardProps {
  maxItems?: number;
}

export function RecentAlertsCard({ maxItems = 3 }: RecentAlertsCardProps) {
  const router = useRouter();
  const { alerts, total, loading, error, refetch } = useAlerts({
    filters: {
      status: ['created', 'assigned', 'acknowledged', 'investigating'],
    },
    pollInterval: 30000,
  });

  const displayAlerts = alerts.slice(0, maxItems);

  return (
    <Card className="bg-gray-900/50 border-gray-800">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-red-500" />
          Active Security Alerts
          {total > 0 && (
            <span className="ml-2 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-xs font-medium text-white">
              {total}
            </span>
          )}
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetch()}
            disabled={loading}
            className="h-8 w-8"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/dashboard/alerts')}
            className="text-blue-400 hover:text-blue-300"
          >
            View All
            <ArrowRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && alerts.length === 0 ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-6 text-gray-400">
            <p>Failed to load alerts</p>
            <Button
              variant="link"
              onClick={() => refetch()}
              className="text-blue-400"
            >
              Retry
            </Button>
          </div>
        ) : displayAlerts.length === 0 ? (
          <div className="text-center py-6 text-gray-400">
            <ShieldAlert className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No active alerts</p>
          </div>
        ) : (
          <div className="space-y-3">
            {displayAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onClick={() => router.push(`/dashboard/alerts/${alert.id}`)}
                compact
              />
            ))}
            {total > maxItems && (
              <p className="text-center text-sm text-gray-400 pt-2">
                +{total - maxItems} more alerts
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
