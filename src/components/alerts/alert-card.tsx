'use client';

import { ShieldAlert, AlertTriangle, AlertCircle, Info, Clock, MapPin, User } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import type { Alert, AlertSeverity, AlertStatus } from '@/types/alert';
import { SEVERITY_CONFIG, STATUS_CONFIG } from '@/types/alert';

interface AlertCardProps {
  alert: Alert;
  onClick?: () => void;
  compact?: boolean;
}

function getSeverityIcon(severity: AlertSeverity) {
  const iconClass = "h-5 w-5";
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

function formatTimestamp(timestamp: string) {
  try {
    return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
  } catch {
    return 'Unknown';
  }
}

export function AlertCard({ alert, onClick, compact = false }: AlertCardProps) {
  const severityConfig = SEVERITY_CONFIG[alert.severity];
  const statusConfig = STATUS_CONFIG[alert.status as AlertStatus];

  if (compact) {
    return (
      <div
        onClick={onClick}
        className={cn(
          'p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.01]',
          severityConfig.bgColor,
          severityConfig.borderColor
        )}
      >
        <div className="flex items-center gap-3">
          <div className={severityConfig.color}>
            {getSeverityIcon(alert.severity)}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-white truncate">
              {alert.title}
            </h4>
            <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
              <Clock className="h-3 w-3" />
              {formatTimestamp(alert.created_at)}
            </div>
          </div>
          <Badge variant={severityConfig.badgeVariant} className="shrink-0">
            {alert.severity}
          </Badge>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={cn(
        'p-4 rounded-lg border cursor-pointer transition-all hover:scale-[1.01]',
        severityConfig.bgColor,
        severityConfig.borderColor
      )}
    >
      <div className="flex items-start gap-3">
        <div className={severityConfig.color}>
          {getSeverityIcon(alert.severity)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h4 className="text-sm font-medium text-white">
              {alert.title}
            </h4>
            <div className="flex items-center gap-2 shrink-0">
              <Badge variant={severityConfig.badgeVariant}>
                {alert.severity}
              </Badge>
              <Badge
                variant="outline"
                className={cn(statusConfig.color, statusConfig.bgColor)}
              >
                {statusConfig.label}
              </Badge>
            </div>
          </div>

          <p className="text-xs text-gray-400 line-clamp-2 mb-3">
            {alert.description}
          </p>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
            {alert.location?.building && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {alert.location.building}
                {alert.location.floor && `, Floor ${alert.location.floor}`}
              </span>
            )}
            {alert.assigned_staff_name && (
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {alert.assigned_staff_name}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatTimestamp(alert.created_at)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
