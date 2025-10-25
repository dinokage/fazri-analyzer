'use client';

import { AlertCircle, AlertTriangle, Info, ShieldAlert, Clock, MapPin, User } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { useState } from 'react';
import { Anomaly, AnomalySeverity } from '@/types/anomaly';

interface AnomalyListProps {
  anomalies: Anomaly[] | null;
  loading?: boolean;
}

export function AnomalyList({ anomalies, loading }: AnomalyListProps) {
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null);

  const getSeverityConfig = (severity: AnomalySeverity) => {
    switch (severity) {
      case 'critical':
        return {
          icon: <ShieldAlert className="h-5 w-5" />,
          color: 'text-red-500',
          bgColor: 'bg-red-950/30',
          borderColor: 'border-red-900/50',
          badgeVariant: 'destructive' as const,
        };
      case 'high':
        return {
          icon: <AlertTriangle className="h-5 w-5" />,
          color: 'text-orange-500',
          bgColor: 'bg-orange-950/30',
          borderColor: 'border-orange-900/50',
          badgeVariant: 'default' as const,
        };
      case 'medium':
        return {
          icon: <AlertCircle className="h-5 w-5" />,
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-950/30',
          borderColor: 'border-yellow-900/50',
          badgeVariant: 'secondary' as const,
        };
      case 'low':
        return {
          icon: <Info className="h-5 w-5" />,
          color: 'text-blue-500',
          bgColor: 'bg-blue-950/30',
          borderColor: 'border-blue-900/50',
          badgeVariant: 'outline' as const,
        };
      default:
        return {
          icon: <AlertCircle className="h-5 w-5" />,
          color: 'text-gray-500',
          bgColor: 'bg-gray-950/30',
          borderColor: 'border-gray-900/50',
          badgeVariant: 'outline' as const,
        };
    }
  };

  const formatAnomalyType = (type: string) => {
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const formatTimestamp = (timestamp: string, formatStr: string) => {
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }
      return format(date, formatStr);
    } catch (error) {
      console.error('Error formatting timestamp:', timestamp, error);
      return 'Invalid date';
    }
  };

  if (loading) {
    return (
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <ShieldAlert className="h-5 w-5" />
            Anomalies
          </CardTitle>
          <CardDescription>Detected security and behavioral anomalies</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-20 bg-gray-800 rounded" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!anomalies || anomalies.length === 0) {
    return (
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <ShieldAlert className="h-5 w-5" />
            Anomalies
          </CardTitle>
          <CardDescription>Detected security and behavioral anomalies</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-gray-400">
            <ShieldAlert className="h-12 w-12 mb-3 opacity-50" />
            <p className="text-sm">No anomalies detected</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Deduplicate anomalies by ID
  const uniqueAnomalies = Array.from(
    new Map(anomalies.map(anomaly => [anomaly.id, anomaly])).values()
  );

  // Group anomalies by severity
  const grouped = uniqueAnomalies.reduce((acc, anomaly) => {
    if (!acc[anomaly.severity]) {
      acc[anomaly.severity] = [];
    }
    acc[anomaly.severity].push(anomaly);
    return acc;
  }, {} as Record<AnomalySeverity, Anomaly[]>);

  const severityOrder: AnomalySeverity[] = ['critical', 'high', 'medium', 'low'];
  const sortedAnomalies = severityOrder
    .flatMap(severity => grouped[severity] || []);

  return (
    <>
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <ShieldAlert className="h-5 w-5" />
            Anomalies
            <Badge variant="secondary" className="ml-auto">
              {anomalies.length}
            </Badge>
          </CardTitle>
          <CardDescription>
            Detected security and behavioral anomalies
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-3">
              {sortedAnomalies.map((anomaly, index) => {
                const severityConfig = getSeverityConfig(anomaly.severity);

                return (
                  <div
                    key={index}
                    onClick={() => setSelectedAnomaly(anomaly)}
                    className={cn(
                      'p-4 rounded-lg border cursor-pointer transition-all hover:scale-[1.02]',
                      severityConfig.bgColor,
                      severityConfig.borderColor
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className={severityConfig.color}>
                        {severityConfig.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <h4 className="text-sm font-medium text-white truncate">
                            {formatAnomalyType(anomaly.type)}
                          </h4>
                          <Badge variant={severityConfig.badgeVariant} className="shrink-0">
                            {anomaly.severity}
                          </Badge>
                        </div>

                        <p className="text-xs text-gray-400 line-clamp-2 mb-2">
                          {anomaly.description}
                        </p>

                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {anomaly.location_name}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatTimestamp(anomaly.timestamp, 'MMM d, HH:mm')}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <Dialog open={!!selectedAnomaly} onOpenChange={() => setSelectedAnomaly(null)}>
        <DialogContent className="bg-gray-900 border-gray-800 max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              {selectedAnomaly && getSeverityConfig(selectedAnomaly.severity).icon}
              {selectedAnomaly && formatAnomalyType(selectedAnomaly.type)}
            </DialogTitle>
            <DialogDescription>
              Anomaly Details
            </DialogDescription>
          </DialogHeader>

          {selectedAnomaly && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge variant={getSeverityConfig(selectedAnomaly.severity).badgeVariant}>
                  {selectedAnomaly.severity}
                </Badge>
                <Badge variant="outline">
                  {formatAnomalyType(selectedAnomaly.type)}
                </Badge>
              </div>

              <div className="space-y-3">
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Description</h4>
                  <p className="text-sm text-white">{selectedAnomaly.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-1 flex items-center gap-1">
                      <User className="h-3 w-3" />
                      Entity
                    </h4>
                    <p className="text-sm text-white">{selectedAnomaly.entity_name}</p>
                    {selectedAnomaly.entity_role && (
                      <p className="text-xs text-gray-500">{selectedAnomaly.entity_role}</p>
                    )}
                  </div>

                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-1 flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      Location
                    </h4>
                    <p className="text-sm text-white">{selectedAnomaly.location_name}</p>
                    <p className="text-xs text-gray-500">{selectedAnomaly.location}</p>
                  </div>

                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-1 flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Timestamp
                    </h4>
                    <p className="text-sm text-white">
                      {formatTimestamp(selectedAnomaly.timestamp, 'PPpp')}
                    </p>
                  </div>
                </div>

                {selectedAnomaly.details && Object.keys(selectedAnomaly.details).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-2">Additional Details</h4>
                    <div className="bg-gray-950/50 rounded-lg p-3 space-y-1">
                      {Object.entries(selectedAnomaly.details).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-xs">
                          <span className="text-gray-500">{formatAnomalyType(key)}:</span>
                          <span className="text-white">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedAnomaly.recommended_actions && selectedAnomaly.recommended_actions.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-2">Recommended Actions</h4>
                    <ul className="space-y-1">
                      {selectedAnomaly.recommended_actions.map((action, index) => (
                        <li key={index} className="text-sm text-gray-300 flex items-start gap-2">
                          <span className="text-blue-400 mt-1">•</span>
                          <span>{action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
