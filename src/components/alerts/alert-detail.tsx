'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow, format } from 'date-fns';
import {
  ArrowLeft,
  Clock,
  MapPin,
  User,
  FileText,
  History,
  RefreshCw,
  ShieldAlert,
  AlertTriangle,
  AlertCircle,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAlert } from '@/hooks/useAlerts';
import { AlertActions } from './alert-actions';
import { AlertHistoryTimeline } from './alert-history-timeline';
import { SEVERITY_CONFIG, STATUS_CONFIG } from '@/types/alert';
import type { AlertSeverity } from '@/types/alert';
import { cn } from '@/lib/utils';

interface AlertDetailProps {
  alertId: string;
  staffId: string;
}

function getSeverityIcon(severity: AlertSeverity) {
  const iconClass = 'h-6 w-6';
  switch (severity) {
    case 'critical':
      return <ShieldAlert className={iconClass} />;
    case 'high':
      return <AlertTriangle className={iconClass} />;
    case 'medium':
      return <AlertCircle className={iconClass} />;
    case 'low':
    default:
      return <Info className={iconClass} />;
  }
}

export function AlertDetail({ alertId, staffId }: AlertDetailProps) {
  const router = useRouter();
  const { alert, loading, error, refetch } = useAlert(alertId);
  const [activeTab, setActiveTab] = useState('details');

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-64" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
        <h3 className="text-lg font-medium text-white mb-2">
          {error || 'Alert not found'}
        </h3>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
          <Button onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const severityConfig = SEVERITY_CONFIG[alert.severity];
  const statusConfig = STATUS_CONFIG[alert.status];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.back()}
            className="shrink-0"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>

          <div
            className={cn(
              'w-12 h-12 rounded-lg flex items-center justify-center shrink-0',
              severityConfig.bgColor,
              severityConfig.color
            )}
          >
            {getSeverityIcon(alert.severity)}
          </div>

          <div>
            <h1 className="text-xl font-semibold text-white">{alert.title}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={severityConfig.badgeVariant}>
                {alert.severity}
              </Badge>
              <Badge
                variant="outline"
                className={cn(statusConfig.color, statusConfig.bgColor)}
              >
                {statusConfig.label}
              </Badge>
              {alert.is_mock && (
                <Badge variant="secondary" className="text-purple-400">
                  Demo
                </Badge>
              )}
            </div>
          </div>
        </div>

        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Actions */}
      <div
        className={cn(
          'p-4 rounded-lg border',
          severityConfig.bgColor,
          severityConfig.borderColor
        )}
      >
        <h3 className="text-sm font-medium text-gray-300 mb-3">Actions</h3>
        <AlertActions
          alert={alert}
          staffId={staffId}
          onActionComplete={refetch}
        />
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-gray-800/50">
          <TabsTrigger value="details" className="gap-2">
            <FileText className="h-4 w-4" />
            Details
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-2">
            <History className="h-4 w-4" />
            History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="mt-4 space-y-4">
          {/* Description */}
          <div className="p-4 rounded-lg border border-gray-800 bg-gray-900">
            <h3 className="text-sm font-medium text-gray-300 mb-2">
              Description
            </h3>
            <p className="text-white">{alert.description}</p>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Location */}
            <div className="p-4 rounded-lg border border-gray-800 bg-gray-900">
              <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Location
              </h3>
              <div className="space-y-2 text-sm">
                {alert.location?.building && (
                  <div>
                    <span className="text-gray-400">Building:</span>{' '}
                    <span className="text-white">{alert.location.building}</span>
                  </div>
                )}
                {alert.location?.floor && (
                  <div>
                    <span className="text-gray-400">Floor:</span>{' '}
                    <span className="text-white">{alert.location.floor}</span>
                  </div>
                )}
                <div>
                  <span className="text-gray-400">Zone ID:</span>{' '}
                  <span className="text-white font-mono text-xs">
                    {alert.location?.zone_id || 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* Assignment */}
            <div className="p-4 rounded-lg border border-gray-800 bg-gray-900">
              <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <User className="h-4 w-4" />
                Assignment
              </h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-gray-400">Assigned to:</span>{' '}
                  <span className="text-white">
                    {alert.assigned_staff_name || 'Unassigned'}
                  </span>
                </div>
                {alert.assigned_at && (
                  <div>
                    <span className="text-gray-400">Assigned:</span>{' '}
                    <span className="text-white">
                      {formatDistanceToNow(new Date(alert.assigned_at), {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                )}
                {alert.acknowledged_at && (
                  <div>
                    <span className="text-gray-400">Acknowledged:</span>{' '}
                    <span className="text-white">
                      {formatDistanceToNow(new Date(alert.acknowledged_at), {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Timestamps */}
            <div className="p-4 rounded-lg border border-gray-800 bg-gray-900">
              <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Timestamps
              </h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-gray-400">Created:</span>{' '}
                  <span className="text-white">
                    {format(new Date(alert.created_at), 'PPpp')}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Last updated:</span>{' '}
                  <span className="text-white">
                    {formatDistanceToNow(new Date(alert.updated_at), {
                      addSuffix: true,
                    })}
                  </span>
                </div>
                {alert.resolved_at && (
                  <div>
                    <span className="text-gray-400">Resolved:</span>{' '}
                    <span className="text-white">
                      {format(new Date(alert.resolved_at), 'PPpp')}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Resolution (if resolved) */}
            {alert.status === 'resolved' && (
              <div className="p-4 rounded-lg border border-green-900/50 bg-green-950/30">
                <h3 className="text-sm font-medium text-green-400 mb-3">
                  Resolution
                </h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-400">Type:</span>{' '}
                    <span className="text-white capitalize">
                      {alert.resolution_type?.replace('_', ' ')}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">Resolved by:</span>{' '}
                    <span className="text-white">{alert.resolver_name}</span>
                  </div>
                  {alert.resolution_notes && (
                    <div>
                      <span className="text-gray-400">Notes:</span>{' '}
                      <span className="text-white">{alert.resolution_notes}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Additional Info */}
          <div className="p-4 rounded-lg border border-gray-800 bg-gray-900">
            <h3 className="text-sm font-medium text-gray-300 mb-3">
              Additional Information
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-400 block">Anomaly Type</span>
                <span className="text-white">{alert.anomaly_type}</span>
              </div>
              <div>
                <span className="text-gray-400 block">Escalation Count</span>
                <span className="text-white">{alert.escalation_count}</span>
              </div>
              <div>
                <span className="text-gray-400 block">Affected Entities</span>
                <span className="text-white">
                  {alert.affected_entities?.length || 0}
                </span>
              </div>
              <div>
                <span className="text-gray-400 block">Data Sources</span>
                <span className="text-white">
                  {alert.data_sources?.join(', ') || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <div className="p-4 rounded-lg border border-gray-800 bg-gray-900">
            <AlertHistoryTimeline alertId={alertId} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
