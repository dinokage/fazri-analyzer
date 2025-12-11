'use client';

import { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  Clock,
  User,
  CheckCircle2,
  ArrowUpCircle,
  Eye,
  Search,
  MessageSquare,
  UserPlus,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { AlertHistoryEntry } from '@/types/alert';
import { cn } from '@/lib/utils';

interface AlertHistoryTimelineProps {
  alertId: string;
}

const ACTION_CONFIG: Record<
  string,
  { icon: React.ReactNode; color: string; bgColor: string; label: string }
> = {
  created: {
    icon: <AlertCircle className="h-4 w-4" />,
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
    label: 'Alert Created',
  },
  assigned: {
    icon: <UserPlus className="h-4 w-4" />,
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/30',
    label: 'Assigned',
  },
  acknowledged: {
    icon: <Eye className="h-4 w-4" />,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-900/30',
    label: 'Acknowledged',
  },
  investigating: {
    icon: <Search className="h-4 w-4" />,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/30',
    label: 'Investigation Started',
  },
  resolved: {
    icon: <CheckCircle2 className="h-4 w-4" />,
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
    label: 'Resolved',
  },
  escalated: {
    icon: <ArrowUpCircle className="h-4 w-4" />,
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/30',
    label: 'Escalated',
  },
  note_added: {
    icon: <MessageSquare className="h-4 w-4" />,
    color: 'text-gray-400',
    bgColor: 'bg-gray-800',
    label: 'Note Added',
  },
};

function getActionConfig(action: string) {
  return (
    ACTION_CONFIG[action] || {
      icon: <Clock className="h-4 w-4" />,
      color: 'text-gray-400',
      bgColor: 'bg-gray-800',
      label: action,
    }
  );
}

export function AlertHistoryTimeline({ alertId }: AlertHistoryTimelineProps) {
  const [history, setHistory] = useState<AlertHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await apiClient.getAlertHistory(alertId);
        setHistory(response.history || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load history');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [alertId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-gray-400">
        <AlertCircle className="h-8 w-8 mx-auto mb-2" />
        <p>{error}</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <Clock className="h-8 w-8 mx-auto mb-2" />
        <p>No history available</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-800" />

      <div className="space-y-4">
        {history.map((entry, index) => {
          const config = getActionConfig(entry.action);
          const isFirst = index === 0;

          return (
            <div key={entry.id} className="relative pl-10">
              {/* Timeline dot */}
              <div
                className={cn(
                  'absolute left-0 w-8 h-8 rounded-full flex items-center justify-center',
                  config.bgColor,
                  config.color
                )}
              >
                {config.icon}
              </div>

              {/* Content */}
              <div
                className={cn(
                  'p-3 rounded-lg border',
                  isFirst ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-900 border-gray-800'
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={cn('font-medium text-sm', config.color)}>
                    {config.label}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                  </span>
                </div>

                {entry.actor_name && (
                  <div className="flex items-center gap-1 text-xs text-gray-400 mb-1">
                    <User className="h-3 w-3" />
                    <span>{entry.actor_name}</span>
                    <span className="text-gray-600">({entry.actor_type})</span>
                  </div>
                )}

                {entry.details && Object.keys(entry.details).length > 0 && (
                  <div className="mt-2 text-xs text-gray-400 space-y-1">
                    {Object.entries(entry.details).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-gray-500">{key}:</span>{' '}
                        <span>{String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
