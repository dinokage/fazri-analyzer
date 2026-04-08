'use client';

import { useEffect, useState, useCallback } from 'react';
import { Key, Wifi, Camera, AlertTriangle, ChevronRight, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';

// ─── Types ────────────────────────────────────────────────────────────────────

interface TimelineEvent {
  event_id: string;
  sensor_type: 'RFID' | 'WIFI' | 'CAMERA' | string;
  event_type: string;
  timestamp: string;
  zone_id: string;
  building: string | null;
  floor: string | null;
  confidence: number;
  source_device_id: string | null;
}

interface AlertWindow {
  alert_id: string;
  anomaly_type: string | null;
  timestamp: string | null;
}

interface EntityTimeline {
  entity_id: string;
  since: string;
  total: number;
  events: TimelineEvent[];
  alerts: AlertWindow[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SENSOR_STYLE: Record<string, { icon: React.ReactNode; color: string; dot: string }> = {
  RFID: {
    icon: <Key className="h-3.5 w-3.5" />,
    color: 'text-blue-400',
    dot: 'bg-blue-500',
  },
  WIFI: {
    icon: <Wifi className="h-3.5 w-3.5" />,
    color: 'text-green-400',
    dot: 'bg-green-500',
  },
  CAMERA: {
    icon: <Camera className="h-3.5 w-3.5" />,
    color: 'text-purple-400',
    dot: 'bg-purple-500',
  },
};

function fallbackStyle(type: string) {
  return SENSOR_STYLE[type] ?? {
    icon: <Key className="h-3.5 w-3.5" />,
    color: 'text-gray-400',
    dot: 'bg-gray-500',
  };
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
}

/**
 * Returns true when an alert timestamp is within 2 minutes of the given event timestamp.
 * Used to highlight events that likely triggered an alert.
 */
function isNearAlert(eventTs: string, alerts: AlertWindow[]): AlertWindow | null {
  const evMs = new Date(eventTs).getTime();
  for (const a of alerts) {
    if (!a.timestamp) continue;
    const alertMs = new Date(a.timestamp).getTime();
    if (Math.abs(alertMs - evMs) <= 2 * 60 * 1000) return a;
  }
  return null;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function MovementTimeline({ entityId }: { entityId: string }) {
  const [data, setData] = useState<EntityTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'1d' | '7d' | '30d'>('7d');

  const sinceForRange = (range: '1d' | '7d' | '30d') => {
    const d = new Date();
    if (range === '1d') d.setDate(d.getDate() - 1);
    else if (range === '7d') d.setDate(d.getDate() - 7);
    else d.setDate(d.getDate() - 30);
    return d.toISOString();
  };

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.getEntitySensorTimeline(entityId, {
        since: sinceForRange(timeRange),
        limit: 200,
      });
      setData(result as EntityTimeline);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load timeline');
    } finally {
      setLoading(false);
    }
  }, [entityId, timeRange]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const events = data?.events ?? [];
  const alerts = data?.alerts ?? [];

  // Group events by calendar date for section headers
  const groupedByDate: { date: string; events: TimelineEvent[] }[] = [];
  let currentDate = '';
  for (const ev of events) {
    const d = formatDate(ev.timestamp);
    if (d !== currentDate) {
      groupedByDate.push({ date: d, events: [] });
      currentDate = d;
    }
    groupedByDate[groupedByDate.length - 1].events.push(ev);
  }

  return (
    <div className="bg-[#1c1c24] rounded-lg border border-gray-800 p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Movement Timeline</h3>
        <div className="flex items-center gap-2">
          {/* Time range selector */}
          <div className="flex rounded-md overflow-hidden border border-gray-700">
            {(['1d', '7d', '30d'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-2.5 py-1 text-xs transition-colors ${
                  timeRange === r
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetch}
            className="h-7 w-7 p-0 text-gray-400 hover:text-gray-200"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Sensor legend */}
      <div className="flex gap-4 mb-4 text-xs text-gray-500">
        {Object.entries(SENSOR_STYLE).map(([type, s]) => (
          <span key={type} className={`flex items-center gap-1 ${s.color}`}>
            {s.icon}
            {type}
          </span>
        ))}
        <span className="flex items-center gap-1 text-red-400">
          <AlertTriangle className="h-3.5 w-3.5" />
          Anomaly
        </span>
      </div>

      {/* Body */}
      {loading && (
        <div className="space-y-3 animate-pulse">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 bg-gray-800 rounded" />
          ))}
        </div>
      )}

      {!loading && error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}

      {!loading && !error && events.length === 0 && (
        <p className="text-gray-500 text-sm text-center py-8">
          No sensor events found for this entity in the selected period.
        </p>
      )}

      {!loading && !error && events.length > 0 && (
        <div className="relative">
          {/* Vertical timeline rail */}
          <div className="absolute left-[7px] top-2 bottom-2 w-px bg-gray-700" />

          <div className="space-y-0.5">
            {groupedByDate.map(({ date, events: dayEvents }) => (
              <div key={date}>
                {/* Date separator */}
                <div className="flex items-center gap-2 py-2 pl-6">
                  <span className="text-xs text-gray-500 font-medium">{date}</span>
                  <div className="flex-1 h-px bg-gray-800" />
                </div>

                {dayEvents.map((ev, idx) => {
                  const prevZone = idx > 0 ? dayEvents[idx - 1].zone_id : null;
                  const zoneChanged = prevZone !== null && prevZone !== ev.zone_id;
                  const style = fallbackStyle(ev.sensor_type);
                  const nearAlert = isNearAlert(ev.timestamp, alerts);

                  return (
                    <div
                      key={ev.event_id}
                      className={`relative flex items-start gap-3 pl-2 pr-2 py-1.5 rounded-md transition-colors ${
                        nearAlert
                          ? 'bg-red-900/20 border border-red-800/40'
                          : 'hover:bg-gray-800/30'
                      }`}
                    >
                      {/* Timeline dot */}
                      <div
                        className={`relative z-10 mt-1 h-3.5 w-3.5 rounded-full border-2 border-[#1c1c24] flex-shrink-0 ${style.dot}`}
                      />

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          {/* Zone transition arrow */}
                          {zoneChanged && (
                            <span className="flex items-center gap-1 text-xs text-gray-500">
                              <span className="font-mono text-gray-600">{prevZone}</span>
                              <ChevronRight className="h-3 w-3 text-gray-600" />
                            </span>
                          )}

                          {/* Sensor badge */}
                          <span className={`flex items-center gap-1 text-xs font-medium ${style.color}`}>
                            {style.icon}
                            {ev.sensor_type}
                          </span>

                          {/* Zone pill */}
                          <span className="bg-gray-800 px-1.5 py-0.5 rounded text-xs font-mono text-gray-300">
                            {ev.zone_id}
                          </span>

                          {/* Event type */}
                          <span className="text-xs text-gray-400">
                            {ev.event_type.replace(/_/g, ' ')}
                          </span>

                          {/* Anomaly badge */}
                          {nearAlert && (
                            <span className="flex items-center gap-1 text-xs text-red-400 ml-auto">
                              <AlertTriangle className="h-3 w-3" />
                              {nearAlert.anomaly_type ?? 'anomaly'}
                            </span>
                          )}
                        </div>

                        {/* Confidence + timestamp */}
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-gray-600">{formatTime(ev.timestamp)}</span>
                          <span className="text-xs text-gray-600">
                            {Math.round(ev.confidence * 100)}% conf
                          </span>
                          {ev.building && (
                            <span className="text-xs text-gray-600 truncate">
                              {ev.building}{ev.floor ? ` · F${ev.floor}` : ''}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Summary footer */}
          <div className="mt-3 pt-3 border-t border-gray-800 flex items-center gap-4 text-xs text-gray-500">
            <span>{events.length} events</span>
            {alerts.length > 0 && (
              <span className="text-red-400">{alerts.length} anomaly alert{alerts.length !== 1 ? 's' : ''}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
