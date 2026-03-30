'use client';

import { useCallback, useEffect, useState } from 'react';
import { Camera, Plus, Trash2, Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

import { useSession } from '@/lib/auth-client';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface CameraStream {
  id: string;
  stream_id: string;
  rtsp_url: string;
  zone_id: string;
  building?: string;
  floor?: string;
  alert_on_unknown_face: boolean;
  status: 'active' | 'stopped' | 'error';
  last_event_at?: string;
  error_message?: string;
}

const STATUS_CONFIG = {
  active: {
    label: 'Active',
    icon: Wifi,
    className: 'bg-green-900/30 text-green-400 border border-green-900',
  },
  stopped: {
    label: 'Stopped',
    icon: WifiOff,
    className: 'bg-gray-800 text-gray-400 border border-gray-700',
  },
  error: {
    label: 'Error',
    icon: AlertTriangle,
    className: 'bg-red-900/30 text-red-400 border border-red-900',
  },
};

function StatusBadge({ status }: { status: CameraStream['status'] }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.stopped;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.className}`}>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  );
}

const EMPTY_FORM = {
  stream_id: '',
  rtsp_url: '',
  zone_id: '',
  building: '',
  floor: '',
  alert_on_unknown_face: true,
};

export default function CamerasPageContent() {
  const { data: session, isPending } = useSession();

  const [streams, setStreams] = useState<CameraStream[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadStreams = useCallback(async () => {
    try {
      const data = await apiClient.getCameraStreams();
      setStreams(data.streams ?? data ?? []);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load streams');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStreams();
  }, [loadStreams]);

  if (isPending) return null;

  const role = (session?.user as Record<string, unknown>)?.role;
  if (role !== 'SUPER_ADMIN') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Access Denied</h2>
          <p className="text-gray-400">You do not have permission to view this page.</p>
        </div>
      </div>
    );
  }

  const handleFormChange = (field: keyof typeof EMPTY_FORM, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleAdd = async () => {
    if (!form.stream_id.trim() || !form.rtsp_url.trim() || !form.zone_id.trim()) {
      toast.error('Stream ID, RTSP URL, and Zone ID are required');
      return;
    }
    if (!form.rtsp_url.startsWith('rtsp://')) {
      toast.error('RTSP URL must start with rtsp://');
      return;
    }
    setSubmitting(true);
    try {
      await apiClient.createCameraStream({
        stream_id: form.stream_id.trim(),
        rtsp_url: form.rtsp_url.trim(),
        zone_id: form.zone_id.trim(),
        building: form.building.trim() || undefined,
        floor: form.floor.trim() || undefined,
        alert_on_unknown_face: form.alert_on_unknown_face,
      });
      toast.success('Camera stream added');
      setAddOpen(false);
      setForm(EMPTY_FORM);
      await loadStreams();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add camera');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (stream: CameraStream) => {
    if (!window.confirm(`Delete stream "${stream.stream_id}"? This cannot be undone.`)) return;
    setDeletingId(stream.stream_id);
    try {
      await apiClient.deleteCameraStream(stream.stream_id);
      toast.success(`Stream "${stream.stream_id}" deleted`);
      await loadStreams();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete stream');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDialogClose = (open: boolean) => {
    if (!open) setForm(EMPTY_FORM);
    setAddOpen(open);
  };

  const formatLastEvent = (ts?: string) => {
    if (!ts) return '—';
    const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Camera className="h-6 w-6 text-blue-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Camera Streams</h1>
            <p className="text-sm text-gray-400">Manage RTSP streams monitored by DeepFace</p>
          </div>
        </div>
        <Button onClick={() => setAddOpen(true)} className="bg-blue-600 hover:bg-blue-700">
          <Plus className="h-4 w-4 mr-1" />
          Add Camera
        </Button>
      </div>

      {/* Table */}
      <div className="bg-[#14141a] rounded-lg border border-gray-800 overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-gray-800 rounded animate-pulse" />
            ))}
          </div>
        ) : streams.length === 0 ? (
          <div className="p-12 text-center">
            <Camera className="h-10 w-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400 font-medium">No camera streams configured</p>
            <p className="text-sm text-gray-600 mt-1">Add an RTSP stream to start monitoring</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase tracking-wide">
                <th className="px-4 py-3 text-left">Stream ID</th>
                <th className="px-4 py-3 text-left">Zone</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Last Event</th>
                <th className="px-4 py-3 text-left">Unknown Alert</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {streams.map((stream) => (
                <tr
                  key={stream.id}
                  className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/20 transition-colors"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-white">{stream.stream_id}</p>
                    <p className="text-xs text-gray-500 truncate max-w-[220px]">{stream.rtsp_url}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    <p>{stream.zone_id}</p>
                    {(stream.building || stream.floor) && (
                      <p className="text-xs text-gray-500">
                        {[stream.building, stream.floor].filter(Boolean).join(', Floor ')}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={stream.status} />
                    {stream.status === 'error' && stream.error_message && (
                      <p className="text-xs text-red-400 mt-1 max-w-[180px] truncate">{stream.error_message}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {formatLastEvent(stream.last_event_at)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-medium ${
                        stream.alert_on_unknown_face ? 'text-amber-400' : 'text-gray-500'
                      }`}
                    >
                      {stream.alert_on_unknown_face ? 'On' : 'Off'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(stream)}
                      disabled={deletingId === stream.stream_id}
                      className="p-1.5 rounded text-gray-500 hover:text-red-400 hover:bg-red-900/20 transition-colors disabled:opacity-40"
                      type="button"
                      title="Delete stream"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Camera dialog */}
      <Dialog open={addOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="bg-gray-900 border-gray-800 sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Add Camera Stream</DialogTitle>
            <DialogDescription className="text-gray-400">
              Configure an RTSP stream for DeepFace to monitor.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 space-y-3">
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Stream ID *</label>
              <Input
                value={form.stream_id}
                onChange={(e) => handleFormChange('stream_id', e.target.value)}
                placeholder="e.g. cam-entrance-01"
                className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-400">RTSP URL *</label>
              <Input
                value={form.rtsp_url}
                onChange={(e) => handleFormChange('rtsp_url', e.target.value)}
                placeholder="rtsp://192.168.1.1/stream"
                className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-400">Zone ID *</label>
              <Input
                value={form.zone_id}
                onChange={(e) => handleFormChange('zone_id', e.target.value)}
                placeholder="e.g. LAB_101"
                className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-400">Building</label>
                <Input
                  value={form.building}
                  onChange={(e) => handleFormChange('building', e.target.value)}
                  placeholder="Optional"
                  className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400">Floor</label>
                <Input
                  value={form.floor}
                  onChange={(e) => handleFormChange('floor', e.target.value)}
                  placeholder="Optional"
                  className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
                />
              </div>
            </div>
            <div className="flex items-center justify-between pt-1">
              <div>
                <p className="text-sm text-white">Alert on unknown face</p>
                <p className="text-xs text-gray-500">Trigger an alert when an unregistered face is detected</p>
              </div>
              <button
                type="button"
                onClick={() => handleFormChange('alert_on_unknown_face', !form.alert_on_unknown_face)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  form.alert_on_unknown_face ? 'bg-blue-600' : 'bg-gray-700'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                    form.alert_on_unknown_face ? 'translate-x-4' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => handleDialogClose(false)}
              disabled={submitting}
              className="border-gray-700"
            >
              Cancel
            </Button>
            <Button
              onClick={handleAdd}
              disabled={submitting}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {submitting ? 'Adding…' : 'Add Camera'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
