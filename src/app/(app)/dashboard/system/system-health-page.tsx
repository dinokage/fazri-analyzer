'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Heart,
  Database,
  Network,
  Cpu,
  Wifi,
  Camera,
  Key,
  Radio,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ServiceHealth {
  status: 'up' | 'down' | 'degraded' | 'polling' | 'disabled';
  latency_ms?: number | null;
  details?: string | null;
  last_poll?: string | null;
  error?: string | null;
}

interface SystemHealthData {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: Record<string, ServiceHealth>;
  uptime_seconds: number;
  version: string;
  timestamp: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

const SERVICE_META: Record<string, { label: string; icon: React.ReactNode }> = {
  postgres:       { label: 'PostgreSQL',     icon: <Database className="h-5 w-5" /> },
  pgvector:       { label: 'pgvector',       icon: <Database className="h-5 w-5" /> },
  neo4j:          { label: 'Neo4j',          icon: <Network className="h-5 w-5" /> },
  redis:          { label: 'Redis',          icon: <Cpu className="h-5 w-5" /> },
  deepface_server:{ label: 'DeepFace',       icon: <Camera className="h-5 w-5" /> },
  hikvision:      { label: 'Hikvision RFID', icon: <Key className="h-5 w-5" /> },
  aruba:          { label: 'Aruba WiFi',     icon: <Wifi className="h-5 w-5" /> },
  go2rtc:         { label: 'go2rtc',         icon: <Radio className="h-5 w-5" /> },
};

function statusColor(status: ServiceHealth['status']): string {
  switch (status) {
    case 'up':       return 'text-green-400';
    case 'polling':  return 'text-blue-400';
    case 'degraded': return 'text-yellow-400';
    case 'disabled': return 'text-gray-500';
    case 'down':     return 'text-red-400';
    default:         return 'text-gray-400';
  }
}

function statusDot(status: ServiceHealth['status']): string {
  switch (status) {
    case 'up':       return 'bg-green-500';
    case 'polling':  return 'bg-blue-500 animate-pulse';
    case 'degraded': return 'bg-yellow-500';
    case 'disabled': return 'bg-gray-600';
    case 'down':     return 'bg-red-500';
    default:         return 'bg-gray-500';
  }
}

function StatusIcon({ status }: { status: ServiceHealth['status'] }) {
  const cls = `h-4 w-4 ${statusColor(status)}`;
  if (status === 'up' || status === 'polling')
    return <CheckCircle2 className={cls} />;
  if (status === 'down')
    return <XCircle className={cls} />;
  if (status === 'degraded')
    return <AlertTriangle className={cls} />;
  return <Clock className={cls} />;
}

function OverallBanner({ status }: { status: SystemHealthData['status'] }) {
  const styles: Record<string, string> = {
    healthy:   'bg-green-900/30 border-green-700 text-green-300',
    degraded:  'bg-yellow-900/30 border-yellow-700 text-yellow-300',
    unhealthy: 'bg-red-900/30 border-red-700 text-red-300',
  };
  const icons: Record<string, React.ReactNode> = {
    healthy:   <CheckCircle2 className="h-5 w-5" />,
    degraded:  <AlertTriangle className="h-5 w-5" />,
    unhealthy: <XCircle className="h-5 w-5" />,
  };
  const labels: Record<string, string> = {
    healthy:   'All systems operational',
    degraded:  'Some services are degraded',
    unhealthy: 'Critical services are down',
  };
  return (
    <div className={`flex items-center gap-3 px-5 py-3 rounded-lg border ${styles[status]}`}>
      {icons[status]}
      <span className="font-semibold text-sm">{labels[status]}</span>
    </div>
  );
}

// ─── Service Card ─────────────────────────────────────────────────────────────

function ServiceCard({ name, health }: { name: string; health: ServiceHealth }) {
  const meta = SERVICE_META[name] ?? { label: name, icon: <Database className="h-5 w-5" /> };
  const dotCls = statusDot(health.status);
  const colorCls = statusColor(health.status);

  return (
    <div className="bg-[#1c1c24] border border-gray-800 rounded-lg p-4 flex flex-col gap-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-gray-300">
          <span className={colorCls}>{meta.icon}</span>
          <span className="text-sm font-medium">{meta.label}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`h-2 w-2 rounded-full ${dotCls}`} />
          <span className={`text-xs font-medium capitalize ${colorCls}`}>
            {health.status}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="flex flex-col gap-1">
        {health.latency_ms != null && (
          <span className="text-xs text-gray-500">
            Latency: <span className="text-gray-300">{health.latency_ms} ms</span>
          </span>
        )}
        {health.last_poll && (
          <span className="text-xs text-gray-500">
            Last poll: <span className="text-gray-300">{health.last_poll}</span>
          </span>
        )}
        {health.details && (
          <span className="text-xs text-gray-400 truncate">{health.details}</span>
        )}
        {health.error && (
          <span className="text-xs text-red-400 truncate" title={health.error}>
            {health.error}
          </span>
        )}
      </div>

      {/* Status indicator bar */}
      <div className="mt-1 h-1 rounded-full bg-gray-800 overflow-hidden">
        <div
          className={`h-full rounded-full ${
            health.status === 'up' || health.status === 'polling'
              ? 'bg-green-500 w-full'
              : health.status === 'degraded'
              ? 'bg-yellow-500 w-3/4'
              : health.status === 'disabled'
              ? 'bg-gray-600 w-1/4'
              : 'bg-red-500 w-full'
          }`}
        />
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SystemHealthPage() {
  const [data, setData] = useState<SystemHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const result = await apiClient.getSystemHealth();
      setData(result as SystemHealthData);
      setLastRefresh(new Date());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load system health');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    intervalRef.current = setInterval(fetchHealth, 10000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchHealth]);

  return (
    <div className="min-h-screen bg-[#14141a] text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Heart className="h-6 w-6 text-red-400" />
            System Health
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Status of all FAZRI subsystems · auto-refreshes every 10s
          </p>
        </div>
        <div className="flex items-center gap-3">
          {data && (
            <span className="text-xs text-gray-500">
              Uptime: {formatUptime(data.uptime_seconds)} · v{data.version}
            </span>
          )}
          {lastRefresh && (
            <span className="text-xs text-gray-600">
              Last: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={fetchHealth}
            className="border-gray-700 text-gray-300 hover:bg-gray-800"
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall banner */}
      {data && (
        <div className="mb-6">
          <OverallBanner status={data.status} />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-4 mb-6 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-28 bg-gray-800 rounded-lg" />
          ))}
        </div>
      )}

      {/* Service cards grid */}
      {!loading && data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(data.services).map(([name, health]) => (
            <ServiceCard key={name} name={name} health={health} />
          ))}
        </div>
      )}

      {/* Timestamp footer */}
      {data && (
        <p className="text-xs text-gray-600 mt-6 text-right">
          Server time: {new Date(data.timestamp).toLocaleString()}
        </p>
      )}
    </div>
  );
}
