'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Activity,
  Camera,
  Key,
  RefreshCw,
  Wifi,
  CheckCircle2,
  XCircle,
  Filter,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// ─── Types ────────────────────────────────────────────────────────────────────

interface SensorEvent {
  event_id: string;
  sensor_type: 'RFID' | 'WIFI' | 'CAMERA' | 'BIOMETRIC' | 'MANUAL';
  event_type: string;
  timestamp: string;
  zone_id: string;
  resolved_entity_id: string | null;
  entity_name: string | null;
  confidence: number;
  source_device_id: string | null;
  building: string | null;
  floor: string | null;
}

interface EventsResponse {
  items: SensorEvent[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function relativeTime(isoStr: string): string {
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return new Date(isoStr).toLocaleDateString();
}

const SENSOR_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  RFID: {
    icon: <Key className="h-4 w-4" />,
    color: 'text-blue-400',
    label: 'RFID',
  },
  WIFI: {
    icon: <Wifi className="h-4 w-4" />,
    color: 'text-green-400',
    label: 'WiFi',
  },
  CAMERA: {
    icon: <Camera className="h-4 w-4" />,
    color: 'text-purple-400',
    label: 'Camera',
  },
};

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 rounded-full bg-gray-700">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{pct}%</span>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function EventsPage() {
  const router = useRouter();
  const [events, setEvents] = useState<SensorEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [sensorTypes, setSensorTypes] = useState<string[]>(['RFID', 'WIFI', 'CAMERA']);
  const [filterZone, setFilterZone] = useState<string>('all');
  const [filterResolved, setFilterResolved] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<string>('1h');

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const sinceFromRange = useCallback((range: string): string => {
    const now = new Date();
    if (range === '15m') now.setMinutes(now.getMinutes() - 15);
    else if (range === '1h') now.setHours(now.getHours() - 1);
    else if (range === '24h') now.setHours(now.getHours() - 24);
    return now.toISOString();
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const params: Record<string, unknown> = {
        limit: 100,
        sensor_type: sensorTypes.join(','),
        since: sinceFromRange(timeRange),
      };
      if (filterZone !== 'all') params.zone_id = filterZone;
      if (filterResolved !== 'all') params.resolved = filterResolved === 'resolved';

      const data: EventsResponse = await apiClient.getSensorEvents(params as Parameters<typeof apiClient.getSensorEvents>[0]);
      setEvents(data.items);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load events');
    } finally {
      setLoading(false);
    }
  }, [sensorTypes, filterZone, filterResolved, timeRange, sinceFromRange]);

  // Initial load + auto-refresh every 5 seconds
  useEffect(() => {
    fetchEvents();
    intervalRef.current = setInterval(fetchEvents, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchEvents]);

  // ── Unique zones from current events (for filter dropdown) ────────────────
  const zones = [...new Set(events.map((e) => e.zone_id))].sort();

  return (
    <div className="min-h-screen bg-[#14141a] text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="h-6 w-6 text-blue-400" />
            Sensor Event Feed
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Real-time events from RFID, WiFi, and Camera sensors
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">{total} events</span>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchEvents}
            className="border-gray-700 text-gray-300 hover:bg-gray-800"
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-5 p-3 bg-[#1c1c24] rounded-lg border border-gray-800">
        <Filter className="h-4 w-4 text-gray-500" />

        {/* Sensor type toggles */}
        <div className="flex gap-2">
          {(['RFID', 'WIFI', 'CAMERA'] as const).map((type) => {
            const meta = SENSOR_META[type];
            const active = sensorTypes.includes(type);
            return (
              <button
                key={type}
                onClick={() =>
                  setSensorTypes((prev) =>
                    active ? prev.filter((t) => t !== type) : [...prev, type]
                  )
                }
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  active
                    ? `bg-gray-800 border-gray-600 ${meta.color}`
                    : 'border-gray-700 text-gray-600 bg-transparent'
                }`}
              >
                {meta.icon}
                {meta.label}
              </button>
            );
          })}
        </div>

        {/* Zone filter */}
        <Select value={filterZone} onValueChange={setFilterZone}>
          <SelectTrigger className="w-[160px] bg-[#14141a] border-gray-700 text-sm h-8">
            <SelectValue placeholder="All zones" />
          </SelectTrigger>
          <SelectContent className="bg-[#1c1c24] border-gray-700 text-white">
            <SelectItem value="all">All zones</SelectItem>
            {zones.map((z) => (
              <SelectItem key={z} value={z}>
                {z}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Resolution filter */}
        <Select value={filterResolved} onValueChange={setFilterResolved}>
          <SelectTrigger className="w-[160px] bg-[#14141a] border-gray-700 text-sm h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-[#1c1c24] border-gray-700 text-white">
            <SelectItem value="all">All events</SelectItem>
            <SelectItem value="resolved">Resolved only</SelectItem>
            <SelectItem value="unresolved">Unresolved only</SelectItem>
          </SelectContent>
        </Select>

        {/* Time range */}
        <Select value={timeRange} onValueChange={setTimeRange}>
          <SelectTrigger className="w-[130px] bg-[#14141a] border-gray-700 text-sm h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-[#1c1c24] border-gray-700 text-white">
            <SelectItem value="15m">Last 15 min</SelectItem>
            <SelectItem value="1h">Last hour</SelectItem>
            <SelectItem value="24h">Last 24h</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-4 mb-4 text-red-300 text-sm">
          {error}
        </div>
      )}

      <div className="bg-[#1c1c24] rounded-lg border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wide">
                <th className="text-left px-4 py-3 font-medium">Time</th>
                <th className="text-left px-4 py-3 font-medium">Source</th>
                <th className="text-left px-4 py-3 font-medium">Entity</th>
                <th className="text-left px-4 py-3 font-medium">Zone</th>
                <th className="text-left px-4 py-3 font-medium">Event</th>
                <th className="text-left px-4 py-3 font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500">
                    Loading events…
                  </td>
                </tr>
              )}
              {!loading && events.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500">
                    No events found for the selected filters
                  </td>
                </tr>
              )}
              {events.map((ev) => {
                const meta = SENSOR_META[ev.sensor_type] ?? SENSOR_META.RFID;
                return (
                  <tr
                    key={ev.event_id}
                    className="border-b border-gray-800/60 hover:bg-gray-800/30 transition-colors"
                  >
                    {/* Time */}
                    <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                      {relativeTime(ev.timestamp)}
                    </td>

                    {/* Source */}
                    <td className="px-4 py-3">
                      <span className={`flex items-center gap-1.5 ${meta.color}`}>
                        {meta.icon}
                        <span className="text-xs font-medium">{meta.label}</span>
                      </span>
                    </td>

                    {/* Entity */}
                    <td className="px-4 py-3">
                      {ev.resolved_entity_id ? (
                        <button
                          onClick={() =>
                            router.push(`/dashboard/entity/${ev.resolved_entity_id}`)
                          }
                          className="text-blue-400 hover:text-blue-300 hover:underline font-medium"
                        >
                          {ev.entity_name ?? ev.resolved_entity_id}
                        </button>
                      ) : (
                        <span className="text-amber-500 text-xs flex items-center gap-1">
                          <XCircle className="h-3.5 w-3.5" />
                          Unresolved
                        </span>
                      )}
                    </td>

                    {/* Zone */}
                    <td className="px-4 py-3 text-gray-300">
                      <span className="bg-gray-800 px-2 py-0.5 rounded text-xs font-mono">
                        {ev.zone_id}
                      </span>
                    </td>

                    {/* Event type */}
                    <td className="px-4 py-3 text-gray-400 text-xs">
                      {ev.event_type.replace(/_/g, ' ')}
                    </td>

                    {/* Confidence */}
                    <td className="px-4 py-3">
                      <ConfidenceBar value={ev.confidence} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
