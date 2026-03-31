'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Camera, Plus, Trash2, Wifi, WifiOff, AlertTriangle,
  Play, RefreshCw, Network, Link2, ChevronRight, ChevronLeft,
  CheckCircle2, Loader2, ServerCrash,
} from 'lucide-react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// ─── Types ───────────────────────────────────────────────────────────────────

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

interface OnvifChannel {
  id: string;
  name: string;
  rtsp_url: string;
}

type AddStep = 'source' | 'rtsp' | 'nvr' | 'confirm';

type NvrDiscoveryState = 'idle' | 'probing' | 'success' | 'failed';

// Vendor RTSP URL templates
const VENDOR_TEMPLATES: Record<string, (ip: string, user: string, pass: string, ch: number) => string> = {
  hikvision: (ip, u, p, ch) =>
    `rtsp://${encodeURIComponent(u)}:${encodeURIComponent(p)}@${ip}/Streaming/Channels/${ch}01`,
  dahua: (ip, u, p, ch) =>
    `rtsp://${encodeURIComponent(u)}:${encodeURIComponent(p)}@${ip}/cam/realmonitor?channel=${ch}&subtype=0`,
  reolink: (ip, u, p, ch) =>
    `rtsp://${encodeURIComponent(u)}:${encodeURIComponent(p)}@${ip}/h264Preview_0${String(ch).padStart(2, '0')}_main`,
  axis: (ip, u, p, _ch) =>
    `rtsp://${encodeURIComponent(u)}:${encodeURIComponent(p)}@${ip}/axis-media/media.amp?videocodec=h264`,
  generic: (ip, u, p, ch) =>
    `rtsp://${encodeURIComponent(u)}:${encodeURIComponent(p)}@${ip}:554/stream${ch}`,
};

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  active: { label: 'Active', icon: Wifi, className: 'bg-green-900/30 text-green-400 border border-green-900' },
  stopped: { label: 'Stopped', icon: WifiOff, className: 'bg-gray-800 text-gray-400 border border-gray-700' },
  error: { label: 'Error', icon: AlertTriangle, className: 'bg-red-900/30 text-red-400 border border-red-900' },
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

// ─── Toggle ───────────────────────────────────────────────────────────────────

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${value ? 'bg-blue-600' : 'bg-gray-700'}`}
    >
      <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${value ? 'translate-x-4' : 'translate-x-1'}`} />
    </button>
  );
}

// ─── Confirm form (shared between RTSP and NVR paths) ────────────────────────

interface ConfirmFormProps {
  prefillRtspUrl?: string;
  onSubmit: (data: {
    stream_id: string;
    rtsp_url: string;
    zone_id: string;
    building?: string;
    floor?: string;
    alert_on_unknown_face: boolean;
  }) => Promise<void>;
  onBack: () => void;
  submitting: boolean;
}

function ConfirmForm({ prefillRtspUrl = '', onSubmit, onBack, submitting }: ConfirmFormProps) {
  const [streamId, setStreamId] = useState('');
  const [rtspUrl, setRtspUrl] = useState(prefillRtspUrl);
  const [zoneId, setZoneId] = useState('');
  const [building, setBuilding] = useState('');
  const [floor, setFloor] = useState('');
  const [alertUnknown, setAlertUnknown] = useState(true);

  // Sync if prefill changes (e.g. user selected a different ONVIF channel)
  useEffect(() => { setRtspUrl(prefillRtspUrl); }, [prefillRtspUrl]);

  const handleSubmit = async () => {
    if (!streamId.trim() || !rtspUrl.trim() || !zoneId.trim()) {
      toast.error('Stream ID, RTSP URL, and Zone ID are required');
      return;
    }
    if (!rtspUrl.startsWith('rtsp://')) {
      toast.error('RTSP URL must start with rtsp://');
      return;
    }
    await onSubmit({
      stream_id: streamId.trim(),
      rtsp_url: rtspUrl.trim(),
      zone_id: zoneId.trim(),
      building: building.trim() || undefined,
      floor: floor.trim() || undefined,
      alert_on_unknown_face: alertUnknown,
    });
  };

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <label className="text-xs text-gray-400">Stream ID *</label>
        <Input value={streamId} onChange={(e) => setStreamId(e.target.value)}
          placeholder="e.g. cam-entrance-01"
          className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600" />
      </div>
      <div className="space-y-1">
        <label className="text-xs text-gray-400">RTSP URL *</label>
        <Input value={rtspUrl} onChange={(e) => setRtspUrl(e.target.value)}
          placeholder="rtsp://..."
          className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600 font-mono text-xs" />
      </div>
      <div className="space-y-1">
        <label className="text-xs text-gray-400">Zone ID *</label>
        <Input value={zoneId} onChange={(e) => setZoneId(e.target.value)}
          placeholder="e.g. LAB_101"
          className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs text-gray-400">Building</label>
          <Input value={building} onChange={(e) => setBuilding(e.target.value)}
            placeholder="Optional"
            className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600" />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-400">Floor</label>
          <Input value={floor} onChange={(e) => setFloor(e.target.value)}
            placeholder="Optional"
            className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600" />
        </div>
      </div>
      <div className="flex items-center justify-between pt-1">
        <div>
          <p className="text-sm text-white">Alert on unknown face</p>
          <p className="text-xs text-gray-500">Trigger an alert when an unregistered face is detected</p>
        </div>
        <Toggle value={alertUnknown} onChange={setAlertUnknown} />
      </div>
      <div className="flex gap-3 pt-2">
        <Button variant="outline" onClick={onBack} disabled={submitting} className="border-gray-700 flex-1">
          <ChevronLeft className="h-4 w-4 mr-1" /> Back
        </Button>
        <Button onClick={handleSubmit} disabled={submitting} className="bg-blue-600 hover:bg-blue-700 flex-1">
          {submitting ? 'Adding…' : 'Add Camera'}
        </Button>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

const EMPTY_NVR = { ip: '', port: '80', username: '', password: '', useHttps: false };

export default function CamerasPageContent() {
  const { data: session, isPending } = useSession();

  const [streams, setStreams] = useState<CameraStream[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [addStep, setAddStep] = useState<AddStep>('source');
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Preview modal
  const [previewStream, setPreviewStream] = useState<CameraStream | null>(null);
  const [snapshotBlobUrl, setSnapshotBlobUrl] = useState<string | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const autoRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevBlobUrlRef = useRef<string | null>(null);

  // NVR wizard state
  const [nvrForm, setNvrForm] = useState(EMPTY_NVR);
  const [nvrDiscovery, setNvrDiscovery] = useState<NvrDiscoveryState>('idle');
  const [nvrVendor, setNvrVendor] = useState('');
  const [nvrModel, setNvrModel] = useState('');
  const [nvrProtocol, setNvrProtocol] = useState('');
  const [nvrChannels, setNvrChannels] = useState<OnvifChannel[]>([]);
  const [nvrSelectedChannel, setNvrSelectedChannel] = useState('');
  const [nvrFallbackVendor, setNvrFallbackVendor] = useState('hikvision');
  const [nvrFallbackChannel, setNvrFallbackChannel] = useState('1');

  // RTSP direct state
  const [rtspUrl, setRtspUrl] = useState('');

  // ─── Data loading ───────────────────────────────────────────────────────────

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

  useEffect(() => { loadStreams(); }, [loadStreams]);

  // ─── Snapshot fetching (auth-aware) ─────────────────────────────────────────

  const fetchSnapshot = useCallback(async (stream: CameraStream) => {
    setSnapshotLoading(true);
    try {
      const blobUrl = await apiClient.getCameraSnapshot(stream.stream_id);
      // Revoke the previous object URL to avoid memory leaks
      if (prevBlobUrlRef.current) URL.revokeObjectURL(prevBlobUrlRef.current);
      prevBlobUrlRef.current = blobUrl;
      setSnapshotBlobUrl(blobUrl);
    } catch {
      setSnapshotBlobUrl(null);
    } finally {
      setSnapshotLoading(false);
    }
  }, []);

  // Fetch snapshot when preview opens, and clean up blob URL when it closes
  useEffect(() => {
    if (previewStream) {
      fetchSnapshot(previewStream);
    } else {
      if (prevBlobUrlRef.current) {
        URL.revokeObjectURL(prevBlobUrlRef.current);
        prevBlobUrlRef.current = null;
      }
      setSnapshotBlobUrl(null);
    }
  }, [previewStream, fetchSnapshot]);

  // ─── Auto-refresh snapshot ──────────────────────────────────────────────────

  useEffect(() => {
    if (autoRefresh && previewStream) {
      autoRefreshRef.current = setInterval(() => fetchSnapshot(previewStream), 5000);
    } else {
      if (autoRefreshRef.current) clearInterval(autoRefreshRef.current);
    }
    return () => { if (autoRefreshRef.current) clearInterval(autoRefreshRef.current); };
  }, [autoRefresh, previewStream, fetchSnapshot]);

  // ─── Access guard ───────────────────────────────────────────────────────────

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

  // ─── Handlers ───────────────────────────────────────────────────────────────

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

  const handleAddCamera = async (data: Parameters<ConfirmFormProps['onSubmit']>[0]) => {
    setSubmitting(true);
    try {
      await apiClient.createCameraStream(data);
      toast.success('Camera stream added');
      closeAddDialog();
      await loadStreams();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add camera');
    } finally {
      setSubmitting(false);
    }
  };

  const closeAddDialog = () => {
    setAddOpen(false);
    setAddStep('source');
    setRtspUrl('');
    setNvrForm(EMPTY_NVR);
    setNvrDiscovery('idle');
    setNvrVendor('');
    setNvrModel('');
    setNvrProtocol('');
    setNvrChannels([]);
    setNvrSelectedChannel('');
    setNvrFallbackVendor('hikvision');
    setNvrFallbackChannel('1');
  };

  const handleOnvifProbe = async () => {
    if (!nvrForm.ip.trim()) { toast.error('IP address is required'); return; }
    setNvrDiscovery('probing');
    setNvrChannels([]);
    try {
      const result = await apiClient.probeOnvif({
        ip: nvrForm.ip.trim(),
        port: parseInt(nvrForm.port) || 80,
        username: nvrForm.username,
        password: nvrForm.password,
        use_https: nvrForm.useHttps,
      });
      if (result.error) {
        setNvrDiscovery('failed');
      } else {
        setNvrVendor(result.vendor ?? '');
        setNvrModel(result.model ?? '');
        setNvrProtocol((result as Record<string, string>).protocol ?? '');
        setNvrChannels(result.channels ?? []);
        setNvrSelectedChannel(result.channels?.[0]?.id ?? '');
        setNvrDiscovery('success');
      }
    } catch {
      setNvrDiscovery('failed');
    }
  };

  // Derive RTSP URL for NVR confirm step
  const nvrConfirmRtspUrl = (() => {
    if (nvrDiscovery === 'success') {
      return nvrChannels.find((c) => c.id === nvrSelectedChannel)?.rtsp_url ?? '';
    }
    const fn = VENDOR_TEMPLATES[nvrFallbackVendor] ?? VENDOR_TEMPLATES.generic;
    return fn(nvrForm.ip, nvrForm.username, nvrForm.password, parseInt(nvrFallbackChannel) || 1);
  })();

  const formatLastEvent = (ts?: string) => {
    if (!ts) return '—';
    const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  // ─── Render ──────────────────────────────────────────────────────────────────

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
            {[1, 2, 3].map((i) => <div key={i} className="h-12 bg-gray-800 rounded animate-pulse" />)}
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
                <tr key={stream.id} className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/20 transition-colors">
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
                  <td className="px-4 py-3 text-gray-400">{formatLastEvent(stream.last_event_at)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${stream.alert_on_unknown_face ? 'text-amber-400' : 'text-gray-500'}`}>
                      {stream.alert_on_unknown_face ? 'On' : 'Off'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => { setPreviewStream(stream); setAutoRefresh(false); }}
                        className="p-1.5 rounded text-gray-500 hover:text-blue-400 hover:bg-blue-900/20 transition-colors"
                        type="button"
                        title="Preview stream"
                      >
                        <Play className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(stream)}
                        disabled={deletingId === stream.stream_id}
                        className="p-1.5 rounded text-gray-500 hover:text-red-400 hover:bg-red-900/20 transition-colors disabled:opacity-40"
                        type="button"
                        title="Delete stream"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ─── Preview Modal ─────────────────────────────────────────────────── */}
      <Dialog open={!!previewStream} onOpenChange={(open) => { if (!open) { setPreviewStream(null); setAutoRefresh(false); } }}>
        <DialogContent className="bg-gray-900 border-gray-800 sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Camera className="h-4 w-4 text-blue-400" />
              {previewStream?.stream_id}
            </DialogTitle>
            <DialogDescription className="text-gray-400 flex items-center gap-2">
              <StatusBadge status={previewStream?.status ?? 'stopped'} />
              <span className="text-xs font-mono truncate">{previewStream?.rtsp_url}</span>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            {/* Snapshot image */}
            <div className="relative bg-black rounded-lg overflow-hidden aspect-video flex items-center justify-center border border-gray-800">
              {snapshotLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/60 z-10">
                  <RefreshCw className="h-6 w-6 text-gray-400 animate-spin" />
                </div>
              )}
              {snapshotBlobUrl ? (
                <img
                  src={snapshotBlobUrl}
                  alt="Camera snapshot"
                  className="w-full h-full object-contain"
                />
              ) : !snapshotLoading ? (
                <div className="flex flex-col items-center justify-center text-gray-600">
                  <ServerCrash className="h-10 w-10 mb-2" />
                  <p className="text-sm">Could not load snapshot</p>
                  <p className="text-xs">Camera may be offline or unreachable</p>
                </div>
              ) : null}
            </div>

            {/* Controls */}
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => previewStream && fetchSnapshot(previewStream)}
                disabled={snapshotLoading}
                className="border-gray-700 gap-1.5"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${snapshotLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <button
                type="button"
                onClick={() => setAutoRefresh((v) => !v)}
                className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-md border transition-colors ${
                  autoRefresh
                    ? 'border-blue-600 text-blue-400 bg-blue-900/20'
                    : 'border-gray-700 text-gray-400 hover:border-gray-600'
                }`}
              >
                <span className={`inline-block h-2 w-2 rounded-full ${autoRefresh ? 'bg-blue-400 animate-pulse' : 'bg-gray-600'}`} />
                Auto-refresh {autoRefresh ? '(5s)' : ''}
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ─── Add Camera Wizard ─────────────────────────────────────────────── */}
      <Dialog open={addOpen} onOpenChange={(open) => { if (!open) closeAddDialog(); }}>
        <DialogContent className="bg-gray-900 border-gray-800 sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Add Camera Stream</DialogTitle>
            <DialogDescription className="text-gray-400">
              {addStep === 'source' && 'Choose how to connect your camera.'}
              {addStep === 'rtsp' && 'Enter the RTSP stream URL.'}
              {addStep === 'nvr' && 'Connect to your NVR or IP camera.'}
              {addStep === 'confirm' && 'Configure stream settings.'}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            {/* Step 1 — Source picker */}
            {addStep === 'source' && (
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setAddStep('rtsp')}
                  className="flex flex-col items-center gap-3 p-4 rounded-lg border border-gray-700 bg-[#1a1a24] hover:border-blue-600 hover:bg-[#1e1e30] transition-colors text-center"
                >
                  <Link2 className="h-7 w-7 text-blue-400" />
                  <div>
                    <p className="text-sm font-medium text-white">Direct RTSP</p>
                    <p className="text-xs text-gray-500 mt-0.5">I already have an RTSP URL</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-600" />
                </button>
                <button
                  type="button"
                  onClick={() => setAddStep('nvr')}
                  className="flex flex-col items-center gap-3 p-4 rounded-lg border border-gray-700 bg-[#1a1a24] hover:border-blue-600 hover:bg-[#1e1e30] transition-colors text-center"
                >
                  <Network className="h-7 w-7 text-purple-400" />
                  <div>
                    <p className="text-sm font-medium text-white">NVR / IP Camera</p>
                    <p className="text-xs text-gray-500 mt-0.5">Discover via ONVIF or vendor template</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-600" />
                </button>
              </div>
            )}

            {/* Step 2a — Direct RTSP */}
            {addStep === 'rtsp' && (
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs text-gray-400">RTSP URL *</label>
                  <Input
                    value={rtspUrl}
                    onChange={(e) => setRtspUrl(e.target.value)}
                    placeholder="rtsp://192.168.1.1/stream"
                    className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600 font-mono text-xs"
                    autoFocus
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <Button variant="outline" onClick={() => setAddStep('source')} className="border-gray-700 flex-1">
                    <ChevronLeft className="h-4 w-4 mr-1" /> Back
                  </Button>
                  <Button
                    onClick={() => {
                      if (!rtspUrl.trim() || !rtspUrl.startsWith('rtsp://')) {
                        toast.error('Enter a valid rtsp:// URL');
                        return;
                      }
                      setAddStep('confirm');
                    }}
                    className="bg-blue-600 hover:bg-blue-700 flex-1"
                  >
                    Next <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step 2b — NVR */}
            {addStep === 'nvr' && (
              <div className="space-y-4">
                {/* NVR connection inputs */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="col-span-2 space-y-1">
                    <label className="text-xs text-gray-400">IP Address *</label>
                    <Input
                      value={nvrForm.ip}
                      onChange={(e) => setNvrForm((f) => ({ ...f, ip: e.target.value }))}
                      placeholder="192.168.1.64"
                      className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Port</label>
                    <Input
                      value={nvrForm.port}
                      onChange={(e) => {
                        const port = e.target.value;
                        // Auto-suggest HTTPS for standard HTTPS ports
                        const autoHttps = port === '443' || port === '8443';
                        setNvrForm((f) => ({ ...f, port, useHttps: autoHttps }));
                      }}
                      placeholder="80"
                      className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-gray-800 bg-[#1a1a24] px-3 py-2">
                  <div>
                    <p className="text-sm text-white">Prefer HTTPS</p>
                    <p className="text-xs text-gray-500">Try HTTPS first — auto-retries with HTTP if it fails. Self-signed certs are accepted.</p>
                  </div>
                  <Toggle value={nvrForm.useHttps} onChange={(v) => setNvrForm((f) => ({ ...f, useHttps: v }))} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Username</label>
                    <Input
                      value={nvrForm.username}
                      onChange={(e) => setNvrForm((f) => ({ ...f, username: e.target.value }))}
                      placeholder="admin"
                      className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Password</label>
                    <Input
                      type="password"
                      value={nvrForm.password}
                      onChange={(e) => setNvrForm((f) => ({ ...f, password: e.target.value }))}
                      placeholder="••••••••"
                      className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600"
                    />
                  </div>
                </div>

                <Button
                  onClick={handleOnvifProbe}
                  disabled={nvrDiscovery === 'probing' || !nvrForm.ip.trim()}
                  className="w-full bg-purple-700 hover:bg-purple-600"
                >
                  {nvrDiscovery === 'probing' ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Discovering via ONVIF…</>
                  ) : (
                    <><Network className="h-4 w-4 mr-2" /> Discover via ONVIF</>
                  )}
                </Button>

                {/* ONVIF success */}
                {nvrDiscovery === 'success' && (
                  <div className="space-y-3 rounded-lg border border-green-900 bg-green-900/10 p-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-400 flex-shrink-0" />
                      <p className="text-sm text-green-300 font-medium">
                        Discovered: {nvrVendor} {nvrModel}
                      {nvrProtocol && (
                        <span className="ml-2 text-xs text-green-500 font-mono uppercase">{nvrProtocol}</span>
                      )}
                      </p>
                    </div>
                    {nvrChannels.length > 0 && (
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Select Channel</label>
                        <Select value={nvrSelectedChannel} onValueChange={setNvrSelectedChannel}>
                          <SelectTrigger className="bg-[#1a1a24] border-gray-700 text-white">
                            <SelectValue placeholder="Choose a channel…" />
                          </SelectTrigger>
                          <SelectContent className="bg-[#1a1a24] border-gray-700">
                            {nvrChannels.map((ch) => (
                              <SelectItem key={ch.id} value={ch.id} className="text-white">
                                {ch.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                )}

                {/* ONVIF failed → vendor template fallback */}
                {nvrDiscovery === 'failed' && (
                  <div className="space-y-3 rounded-lg border border-amber-900 bg-amber-900/10 p-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0" />
                      <p className="text-sm text-amber-300">
                        ONVIF not available — use vendor template instead
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Vendor</label>
                        <Select value={nvrFallbackVendor} onValueChange={setNvrFallbackVendor}>
                          <SelectTrigger className="bg-[#1a1a24] border-gray-700 text-white">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#1a1a24] border-gray-700">
                            <SelectItem value="hikvision" className="text-white">Hikvision</SelectItem>
                            <SelectItem value="dahua" className="text-white">Dahua</SelectItem>
                            <SelectItem value="reolink" className="text-white">Reolink</SelectItem>
                            <SelectItem value="axis" className="text-white">Axis</SelectItem>
                            <SelectItem value="generic" className="text-white">Generic</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Channel</label>
                        <Input
                          type="number"
                          min={1}
                          max={32}
                          value={nvrFallbackChannel}
                          onChange={(e) => setNvrFallbackChannel(e.target.value)}
                          className="bg-[#1a1a24] border-gray-700 text-white"
                        />
                      </div>
                    </div>
                    {nvrForm.ip && (
                      <div className="rounded bg-[#0e0e18] border border-gray-800 p-2">
                        <p className="text-xs text-gray-500 mb-1">RTSP URL preview</p>
                        <p className="text-xs font-mono text-gray-300 break-all">{nvrConfirmRtspUrl}</p>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex gap-3 pt-1">
                  <Button variant="outline" onClick={() => { setAddStep('source'); setNvrDiscovery('idle'); }} className="border-gray-700 flex-1">
                    <ChevronLeft className="h-4 w-4 mr-1" /> Back
                  </Button>
                  <Button
                    onClick={() => setAddStep('confirm')}
                    disabled={
                      nvrDiscovery === 'probing' ||
                      (nvrDiscovery !== 'success' && nvrDiscovery !== 'failed') ||
                      !nvrConfirmRtspUrl
                    }
                    className="bg-blue-600 hover:bg-blue-700 flex-1"
                  >
                    Next <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3 — Confirm */}
            {addStep === 'confirm' && (
              <ConfirmForm
                prefillRtspUrl={rtspUrl || nvrConfirmRtspUrl}
                onSubmit={handleAddCamera}
                onBack={() => setAddStep(rtspUrl ? 'rtsp' : 'nvr')}
                submitting={submitting}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
