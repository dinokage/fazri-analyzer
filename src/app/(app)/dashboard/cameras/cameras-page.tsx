'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Camera, Plus, Trash2, Wifi, WifiOff, AlertTriangle,
  Play, RefreshCw, Network, Link2, ChevronRight, ChevronLeft,
  CheckCircle2, Loader2, ServerCrash, Search, Check, X,
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

interface ChannelOverride {
  stream_id?: string;
  rtsp_url?: string;
  zone_id?: string;
  building?: string;
  floor?: string;
  alert_on_unknown_face?: boolean;
}

interface CameraDefaults {
  zone_id: string;
  building: string;
  floor: string;
  alert_on_unknown_face: boolean;
}

interface SubmitResult {
  stream_id: string;
  status: 'pending' | 'sending' | 'success' | 'failed';
  error?: string;
}

type WizardStep = 'source' | 'rtsp' | 'rtsp_confirm' | 'nvr_auth' | 'nvr_fallback' | 'channel_select' | 'review' | 'submitting';

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

const VENDOR_URL_PATTERNS: Record<string, string> = {
  hikvision: 'rtsp://{user}:{pass}@{ip}/Streaming/Channels/{ch}01',
  dahua: 'rtsp://{user}:{pass}@{ip}/cam/realmonitor?channel={ch}&subtype=0',
  reolink: 'rtsp://{user}:{pass}@{ip}/h264Preview_0{ch}_main',
  axis: 'rtsp://{user}:{pass}@{ip}/axis-media/media.amp?videocodec=h264',
  generic: 'rtsp://{user}:{pass}@{ip}:554/stream{ch}',
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

// ─── Step indicator ───────────────────────────────────────────────────────────

function StepIndicator({ steps, current }: { steps: { key: string; label: string }[]; current: string }) {
  const currentIdx = steps.findIndex((s) => s.key === current);
  return (
    <div className="flex items-center gap-2 mb-4">
      {steps.map((step, i) => (
        <div key={step.key} className="flex items-center gap-2">
          {i > 0 && <div className={`h-px w-4 ${i <= currentIdx ? 'bg-blue-600' : 'bg-gray-700'}`} />}
          <div className="flex items-center gap-1.5">
            <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
              i < currentIdx ? 'bg-blue-600 text-white' :
              i === currentIdx ? 'bg-blue-600 text-white' :
              'bg-gray-800 text-gray-500 border border-gray-700'
            }`}>
              {i < currentIdx ? <Check className="h-3 w-3" /> : i + 1}
            </div>
            <span className={`text-xs ${i <= currentIdx ? 'text-gray-300' : 'text-gray-600'}`}>{step.label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Single RTSP confirm form ────────────────────────────────────────────────

interface SingleConfirmFormProps {
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

function SingleConfirmForm({ prefillRtspUrl = '', onSubmit, onBack, submitting }: SingleConfirmFormProps) {
  const [streamId, setStreamId] = useState('');
  const [rtspUrl, setRtspUrl] = useState(prefillRtspUrl);
  const [zoneId, setZoneId] = useState('');
  const [building, setBuilding] = useState('');
  const [floor, setFloor] = useState('');
  const [alertUnknown, setAlertUnknown] = useState(true);

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
const EMPTY_DEFAULTS: CameraDefaults = { zone_id: '', building: '', floor: '', alert_on_unknown_face: true };

export default function CamerasPageContent() {
  const { data: session, isPending } = useSession();

  const [streams, setStreams] = useState<CameraStream[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [addStep, setAddStep] = useState<WizardStep>('source');
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Preview modal
  const [previewStream, setPreviewStream] = useState<CameraStream | null>(null);
  const [snapshotBlobUrl, setSnapshotBlobUrl] = useState<string | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const autoRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevBlobUrlRef = useRef<string | null>(null);

  // Face detection overlays
  type Detection = {
    img_name: string;
    entity_name: string | null;
    confidence: number;
    distance: number;
    facial_area: { x: number; y: number; w: number; h: number } | null;
    is_unknown: boolean;
  };
  const [detections, setDetections] = useState<Detection[]>([]);
  const imgRef = useRef<HTMLImageElement>(null);
  const [imgDimensions, setImgDimensions] = useState<{ naturalWidth: number; naturalHeight: number } | null>(null);

  // NVR wizard state
  const [nvrForm, setNvrForm] = useState(EMPTY_NVR);
  const [nvrDiscovery, setNvrDiscovery] = useState<NvrDiscoveryState>('idle');
  const [nvrVendor, setNvrVendor] = useState('');
  const [nvrModel, setNvrModel] = useState('');
  const [nvrProtocol, setNvrProtocol] = useState('');
  const [nvrChannels, setNvrChannels] = useState<OnvifChannel[]>([]);

  // Multi-channel selection state
  const [selectedChannels, setSelectedChannels] = useState<Set<string>>(new Set());
  const [channelOverrides, setChannelOverrides] = useState<Map<string, ChannelOverride>>(new Map());
  const [defaults, setDefaults] = useState<CameraDefaults>(EMPTY_DEFAULTS);
  const [focusedChannel, setFocusedChannel] = useState<string | null>(null);
  const [channelSearch, setChannelSearch] = useState('');

  // Vendor fallback state
  const [fallbackVendor, setFallbackVendor] = useState('hikvision');
  const [fallbackChannelCount, setFallbackChannelCount] = useState('4');

  // RTSP direct state
  const [rtspUrl, setRtspUrl] = useState('');

  // Submit progress
  const [submitResults, setSubmitResults] = useState<SubmitResult[]>([]);

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
      const [blobUrl, detectionsResp] = await Promise.all([
        apiClient.getCameraSnapshot(stream.stream_id),
        apiClient.getStreamDetections(stream.stream_id).catch(() => ({ detections: [], cached: false })),
      ]);
      if (prevBlobUrlRef.current) URL.revokeObjectURL(prevBlobUrlRef.current);
      prevBlobUrlRef.current = blobUrl;
      setSnapshotBlobUrl(blobUrl);
      setDetections(detectionsResp.detections);
    } catch {
      setSnapshotBlobUrl(null);
      setDetections([]);
    } finally {
      setSnapshotLoading(false);
    }
  }, []);

  useEffect(() => {
    if (previewStream) {
      fetchSnapshot(previewStream);
    } else {
      if (prevBlobUrlRef.current) {
        URL.revokeObjectURL(prevBlobUrlRef.current);
        prevBlobUrlRef.current = null;
      }
      setSnapshotBlobUrl(null);
      setDetections([]);
      setImgDimensions(null);
    }
  }, [previewStream, fetchSnapshot]);

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

  // ─── Helpers ────────────────────────────────────────────────────────────────

  const autoStreamId = (vendor: string, channelId: string) => {
    const sanitized = vendor.toLowerCase().replace(/[^a-z0-9]/g, '');
    const ipFallback = nvrForm.ip ? nvrForm.ip.replace(/[^a-z0-9]/g, '-') : 'unknown';
    const v = sanitized || `nvr-${ipFallback}`;
    return `${v}-ch${channelId}`;
  };

  const getChannelStreamId = (ch: OnvifChannel) =>
    channelOverrides.get(ch.id)?.stream_id ?? autoStreamId(nvrVendor, ch.id);

  const getChannelRtspUrl = (ch: OnvifChannel) =>
    channelOverrides.get(ch.id)?.rtsp_url ?? ch.rtsp_url;

  const getMergedConfig = (ch: OnvifChannel) => ({
    stream_id: getChannelStreamId(ch),
    rtsp_url: getChannelRtspUrl(ch),
    zone_id: channelOverrides.get(ch.id)?.zone_id ?? defaults.zone_id,
    building: channelOverrides.get(ch.id)?.building ?? defaults.building,
    floor: channelOverrides.get(ch.id)?.floor ?? defaults.floor,
    alert_on_unknown_face: channelOverrides.get(ch.id)?.alert_on_unknown_face ?? defaults.alert_on_unknown_face,
  });

  const formatLastEvent = (ts?: string) => {
    if (!ts) return '—';
    const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

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

  const handleAddSingleCamera = async (data: Parameters<SingleConfirmFormProps['onSubmit']>[0]) => {
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
    setSelectedChannels(new Set());
    setChannelOverrides(new Map());
    setDefaults({ ...EMPTY_DEFAULTS });
    setFocusedChannel(null);
    setChannelSearch('');
    setImgDimensions(null);
    setFallbackVendor('hikvision');
    setFallbackChannelCount('4');
    setSubmitResults([]);
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
      if (result.error || !result.channels?.length) {
        setNvrVendor(result.vendor ?? '');
        setNvrModel(result.model ?? '');
        setNvrDiscovery('failed');
      } else {
        setNvrVendor(result.vendor ?? '');
        setNvrModel(result.model ?? '');
        setNvrProtocol((result as Record<string, string>).protocol ?? '');
        setNvrChannels(result.channels);
        // Auto-select all channels
        setSelectedChannels(new Set(result.channels.map((c) => c.id)));
        setNvrDiscovery('success');
        setAddStep('channel_select');
      }
    } catch {
      setNvrDiscovery('failed');
    }
  };

  const handleGenerateFallbackChannels = () => {
    const count = Math.min(Math.max(parseInt(fallbackChannelCount) || 1, 1), 64);
    const fn = VENDOR_TEMPLATES[fallbackVendor] ?? VENDOR_TEMPLATES.generic;
    const channels: OnvifChannel[] = [];
    for (let i = 1; i <= count; i++) {
      channels.push({
        id: String(i),
        name: `Channel ${i}`,
        rtsp_url: fn(nvrForm.ip, nvrForm.username, nvrForm.password, i),
      });
    }
    setNvrChannels(channels);
    setSelectedChannels(new Set(channels.map((c) => c.id)));
    setAddStep('channel_select');
  };

  const handleBatchSubmit = async () => {
    const selected = nvrChannels.filter((ch) => selectedChannels.has(ch.id));
    const results: SubmitResult[] = selected.map((ch) => ({
      stream_id: getChannelStreamId(ch),
      status: 'pending' as const,
    }));
    setSubmitResults(results);
    setAddStep('submitting');

    for (let i = 0; i < selected.length; i++) {
      const ch = selected[i];
      const config = getMergedConfig(ch);
      setSubmitResults((prev) =>
        prev.map((r, j) => j === i ? { ...r, status: 'sending' } : r)
      );
      try {
        await apiClient.createCameraStream({
          stream_id: config.stream_id,
          rtsp_url: config.rtsp_url,
          zone_id: config.zone_id,
          building: config.building || undefined,
          floor: config.floor || undefined,
          alert_on_unknown_face: config.alert_on_unknown_face,
        });
        setSubmitResults((prev) =>
          prev.map((r, j) => j === i ? { ...r, status: 'success' } : r)
        );
      } catch (err) {
        setSubmitResults((prev) =>
          prev.map((r, j) => j === i ? { ...r, status: 'failed', error: err instanceof Error ? err.message : 'Failed' } : r)
        );
      }
    }
    await loadStreams();
  };

  const handleRetryFailed = async () => {
    const failedStreamIds = submitResults.filter((r) => r.status === 'failed').map((r) => r.stream_id);

    for (const failedId of failedStreamIds) {
      const ch = nvrChannels.find((c) => selectedChannels.has(c.id) && getChannelStreamId(c) === failedId);
      if (!ch) continue;
      const resultIdx = submitResults.findIndex((r) => r.stream_id === failedId);
      const config = getMergedConfig(ch);
      setSubmitResults((prev) =>
        prev.map((r, j) => j === resultIdx ? { ...r, status: 'sending', error: undefined } : r)
      );
      try {
        await apiClient.createCameraStream({
          stream_id: config.stream_id,
          rtsp_url: config.rtsp_url,
          zone_id: config.zone_id,
          building: config.building || undefined,
          floor: config.floor || undefined,
          alert_on_unknown_face: config.alert_on_unknown_face,
        });
        setSubmitResults((prev) =>
          prev.map((r, j) => j === resultIdx ? { ...r, status: 'success' } : r)
        );
      } catch (err) {
        setSubmitResults((prev) =>
          prev.map((r, j) => j === resultIdx ? { ...r, status: 'failed', error: err instanceof Error ? err.message : 'Failed' } : r)
        );
      }
    }
    await loadStreams();
  };

  // ─── Derived ────────────────────────────────────────────────────────────────

  const filteredChannels = nvrChannels.filter((ch) =>
    !channelSearch || ch.name.toLowerCase().includes(channelSearch.toLowerCase()) || ch.id.includes(channelSearch)
  );

  const overrideCount = Array.from(selectedChannels).filter((id) => channelOverrides.has(id)).length;
  const selectedCount = selectedChannels.size;

  const isNvrPath = addStep === 'nvr_auth' || addStep === 'nvr_fallback' || addStep === 'channel_select' || addStep === 'review' || addStep === 'submitting';
  const nvrSteps = [
    { key: 'nvr_auth', label: 'Connect' },
    { key: 'channel_select', label: 'Select' },
    { key: 'review', label: 'Review' },
  ];
  const nvrCurrentStep = addStep === 'nvr_fallback' ? 'nvr_auth' : addStep === 'submitting' ? 'review' : addStep;

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
            <div className="relative bg-black rounded-lg overflow-hidden aspect-video flex items-center justify-center border border-gray-800">
              {snapshotLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/60 z-10">
                  <RefreshCw className="h-6 w-6 text-gray-400 animate-spin" />
                </div>
              )}
              {snapshotBlobUrl ? (
                <div className="relative w-full h-full">
                  <img
                    ref={imgRef}
                    src={snapshotBlobUrl}
                    alt="Camera snapshot"
                    className="w-full h-full object-contain"
                    onLoad={() => {
                      if (imgRef.current) {
                        setImgDimensions({
                          naturalWidth: imgRef.current.naturalWidth,
                          naturalHeight: imgRef.current.naturalHeight,
                        });
                      }
                    }}
                  />
                  {imgDimensions && detections.map((det, i) => {
                    if (!det.facial_area) return null;
                    const { x, y, w, h } = det.facial_area;
                    const left = (x / imgDimensions.naturalWidth) * 100;
                    const top = (y / imgDimensions.naturalHeight) * 100;
                    const width = (w / imgDimensions.naturalWidth) * 100;
                    const height = (h / imgDimensions.naturalHeight) * 100;
                    return (
                      <div
                        key={i}
                        className="absolute border-2 pointer-events-none"
                        style={{
                          left: `${left}%`, top: `${top}%`,
                          width: `${width}%`, height: `${height}%`,
                          borderColor: det.is_unknown ? '#ef4444' : '#22c55e',
                        }}
                      >
                        <span
                          className="absolute -top-5 left-0 text-[10px] leading-tight px-1 py-0.5 rounded whitespace-nowrap"
                          style={{ backgroundColor: det.is_unknown ? '#ef4444' : '#22c55e', color: 'white' }}
                        >
                          {det.is_unknown ? 'Unknown' : (det.entity_name || det.img_name)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : !snapshotLoading ? (
                <div className="flex flex-col items-center justify-center text-gray-600">
                  <ServerCrash className="h-10 w-10 mb-2" />
                  <p className="text-sm">Could not load snapshot</p>
                  <p className="text-xs">Camera may be offline or unreachable</p>
                </div>
              ) : null}
            </div>

            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" onClick={() => previewStream && fetchSnapshot(previewStream)}
                disabled={snapshotLoading} className="border-gray-700 gap-1.5">
                <RefreshCw className={`h-3.5 w-3.5 ${snapshotLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <button type="button" onClick={() => setAutoRefresh((v) => !v)}
                className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-md border transition-colors ${
                  autoRefresh ? 'border-blue-600 text-blue-400 bg-blue-900/20' : 'border-gray-700 text-gray-400 hover:border-gray-600'
                }`}>
                <span className={`inline-block h-2 w-2 rounded-full ${autoRefresh ? 'bg-blue-400 animate-pulse' : 'bg-gray-600'}`} />
                Auto-refresh {autoRefresh ? '(5s)' : ''}
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ─── Add Camera Wizard ─────────────────────────────────────────────── */}
      <Dialog open={addOpen} onOpenChange={(open) => { if (!open && addStep !== 'submitting') closeAddDialog(); }}>
        <DialogContent className={`bg-gray-900 border-gray-800 max-h-[90vh] flex flex-col ${
          addStep === 'channel_select' || addStep === 'review' || addStep === 'submitting' ? 'sm:max-w-4xl' : 'sm:max-w-md'
        }`}>
          <DialogHeader>
            <DialogTitle className="text-white">
              {isNvrPath ? 'Add Cameras from NVR' : 'Add Camera Stream'}
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              {addStep === 'source' && 'Choose how to connect your camera.'}
              {addStep === 'rtsp' && 'Enter the RTSP stream URL.'}
              {addStep === 'rtsp_confirm' && 'Configure stream settings.'}
              {addStep === 'nvr_auth' && 'Connect to your NVR or IP camera.'}
              {addStep === 'nvr_fallback' && 'Configure channels manually.'}
              {addStep === 'channel_select' && `${nvrVendor} ${nvrModel} · ${nvrChannels.length} channel${nvrChannels.length !== 1 ? 's' : ''} available`.trim()}
              {addStep === 'review' && `Review ${selectedCount} camera${selectedCount !== 1 ? 's' : ''} before adding.`}
              {addStep === 'submitting' && 'Adding cameras...'}
            </DialogDescription>
          </DialogHeader>

          {isNvrPath && addStep !== 'submitting' && (
            <StepIndicator steps={nvrSteps} current={nvrCurrentStep} />
          )}

          <div className="py-2 overflow-y-auto flex-1 min-h-0">
            {/* Step: Source picker */}
            {addStep === 'source' && (
              <div className="grid grid-cols-2 gap-3">
                <button type="button" onClick={() => setAddStep('rtsp')}
                  className="flex flex-col items-center gap-3 p-4 rounded-lg border border-gray-700 bg-[#1a1a24] hover:border-blue-600 hover:bg-[#1e1e30] transition-colors text-center">
                  <Link2 className="h-7 w-7 text-blue-400" />
                  <div>
                    <p className="text-sm font-medium text-white">Direct RTSP</p>
                    <p className="text-xs text-gray-500 mt-0.5">I already have an RTSP URL</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-600" />
                </button>
                <button type="button" onClick={() => setAddStep('nvr_auth')}
                  className="flex flex-col items-center gap-3 p-4 rounded-lg border border-gray-700 bg-[#1a1a24] hover:border-blue-600 hover:bg-[#1e1e30] transition-colors text-center">
                  <Network className="h-7 w-7 text-purple-400" />
                  <div>
                    <p className="text-sm font-medium text-white">NVR / IP Camera</p>
                    <p className="text-xs text-gray-500 mt-0.5">Discover channels via ONVIF</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-600" />
                </button>
              </div>
            )}

            {/* Step: Direct RTSP */}
            {addStep === 'rtsp' && (
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs text-gray-400">RTSP URL *</label>
                  <Input value={rtspUrl} onChange={(e) => setRtspUrl(e.target.value)}
                    placeholder="rtsp://192.168.1.1/stream" autoFocus
                    className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600 font-mono text-xs" />
                </div>
                <div className="flex gap-3 pt-2">
                  <Button variant="outline" onClick={() => setAddStep('source')} className="border-gray-700 flex-1">
                    <ChevronLeft className="h-4 w-4 mr-1" /> Back
                  </Button>
                  <Button onClick={() => {
                    if (!rtspUrl.trim() || !rtspUrl.startsWith('rtsp://')) { toast.error('Enter a valid rtsp:// URL'); return; }
                    setAddStep('rtsp_confirm');
                  }} className="bg-blue-600 hover:bg-blue-700 flex-1">
                    Next <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step: RTSP Confirm */}
            {addStep === 'rtsp_confirm' && (
              <SingleConfirmForm prefillRtspUrl={rtspUrl} onSubmit={handleAddSingleCamera}
                onBack={() => setAddStep('rtsp')} submitting={submitting} />
            )}

            {/* Step: NVR Auth */}
            {addStep === 'nvr_auth' && (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-2">
                  <div className="col-span-2 space-y-1">
                    <label className="text-xs text-gray-400">IP Address *</label>
                    <Input value={nvrForm.ip} onChange={(e) => setNvrForm((f) => ({ ...f, ip: e.target.value }))}
                      placeholder="192.168.1.64" className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600" />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Port</label>
                    <Input value={nvrForm.port} onChange={(e) => {
                      const port = e.target.value;
                      setNvrForm((f) => ({ ...f, port, useHttps: port === '443' || port === '8443' }));
                    }} placeholder="80" className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600" />
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-gray-800 bg-[#1a1a24] px-3 py-2">
                  <div>
                    <p className="text-sm text-white">Prefer HTTPS</p>
                    <p className="text-xs text-gray-500">Try HTTPS first — auto-retries with HTTP if it fails.</p>
                  </div>
                  <Toggle value={nvrForm.useHttps} onChange={(v) => setNvrForm((f) => ({ ...f, useHttps: v }))} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Username</label>
                    <Input value={nvrForm.username} onChange={(e) => setNvrForm((f) => ({ ...f, username: e.target.value }))}
                      placeholder="admin" className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600" />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Password</label>
                    <Input type="password" value={nvrForm.password} onChange={(e) => setNvrForm((f) => ({ ...f, password: e.target.value }))}
                      placeholder="••••••••" className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-600" />
                  </div>
                </div>
                <Button onClick={handleOnvifProbe} disabled={nvrDiscovery === 'probing' || !nvrForm.ip.trim()}
                  className="w-full bg-purple-700 hover:bg-purple-600">
                  {nvrDiscovery === 'probing' ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Discovering via ONVIF…</>
                  ) : (
                    <><Network className="h-4 w-4 mr-2" /> Discover via ONVIF</>
                  )}
                </Button>

                {nvrDiscovery === 'failed' && (
                  <div className="rounded-lg border border-amber-900 bg-amber-900/10 p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0" />
                      <p className="text-sm text-amber-300">
                        ONVIF not available{nvrVendor ? ` — detected ${nvrVendor} ${nvrModel}` : ''}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => setAddStep('nvr_fallback')}
                      className="border-amber-800 text-amber-400 hover:bg-amber-900/20 w-full">
                      Configure channels manually
                    </Button>
                  </div>
                )}

                <div className="flex gap-3 pt-1">
                  <Button variant="outline" onClick={() => { setAddStep('source'); setNvrDiscovery('idle'); }} className="border-gray-700 flex-1">
                    <ChevronLeft className="h-4 w-4 mr-1" /> Back
                  </Button>
                </div>
              </div>
            )}

            {/* Step: Vendor Fallback */}
            {addStep === 'nvr_fallback' && (
              <div className="space-y-4">
                <div className="rounded-lg border border-amber-900 bg-amber-900/10 p-3">
                  <p className="text-sm text-amber-300 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                    Manually specify channels and RTSP URL pattern
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Vendor</label>
                    <Select value={fallbackVendor} onValueChange={(v) => setFallbackVendor(v)}>
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
                    <label className="text-xs text-gray-400">Number of Channels</label>
                    <Input type="number" min={1} max={64} value={fallbackChannelCount}
                      onChange={(e) => setFallbackChannelCount(e.target.value)}
                      className="bg-[#1a1a24] border-gray-700 text-white" />
                  </div>
                </div>
                <div className="rounded bg-[#0e0e18] border border-gray-800 p-2">
                  <p className="text-xs text-gray-500 mb-1">RTSP URL pattern</p>
                  <p className="text-xs font-mono text-gray-300 break-all">
                    {VENDOR_URL_PATTERNS[fallbackVendor] ?? VENDOR_URL_PATTERNS.generic}
                  </p>
                </div>
                <div className="flex gap-3 pt-1">
                  <Button variant="outline" onClick={() => setAddStep('nvr_auth')} className="border-gray-700 flex-1">
                    <ChevronLeft className="h-4 w-4 mr-1" /> Back
                  </Button>
                  <Button onClick={handleGenerateFallbackChannels} className="bg-blue-600 hover:bg-blue-700 flex-1">
                    Generate {fallbackChannelCount} Channel{parseInt(fallbackChannelCount) !== 1 ? 's' : ''} <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step: Channel Select (two-panel) */}
            {addStep === 'channel_select' && (
              <div className="space-y-4">
                <div className="flex gap-4" style={{ maxHeight: 'calc(70vh - 200px)', minHeight: 280 }}>
                  {/* Left panel — Channel checklist */}
                  <div className="w-[280px] flex-shrink-0 flex flex-col border border-gray-800 rounded-lg bg-[#0e0e18]">
                    <div className="p-2 border-b border-gray-800">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-gray-400 font-medium">Channels ({nvrChannels.length})</span>
                        <div className="flex gap-1">
                          <button type="button" onClick={() => setSelectedChannels(new Set(nvrChannels.map((c) => c.id)))}
                            className="text-[10px] text-blue-400 hover:text-blue-300 px-1">Select All</button>
                          <button type="button" onClick={() => setSelectedChannels(new Set())}
                            className="text-[10px] text-gray-500 hover:text-gray-400 px-1">Clear</button>
                        </div>
                      </div>
                      {nvrChannels.length > 12 && (
                        <div className="relative">
                          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-500" />
                          <Input value={channelSearch} onChange={(e) => setChannelSearch(e.target.value)}
                            placeholder="Filter channels…" className="h-7 pl-7 text-xs bg-[#14141a] border-gray-700 text-white" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 overflow-y-auto p-1 space-y-0.5">
                      {filteredChannels.map((ch) => {
                        const isSelected = selectedChannels.has(ch.id);
                        const hasOverride = channelOverrides.has(ch.id);
                        const isFocused = focusedChannel === ch.id;
                        return (
                          <button type="button" key={ch.id}
                            className={`flex items-start gap-2 p-2 rounded cursor-pointer transition-colors w-full text-left ${
                              isFocused ? 'bg-blue-900/30 border border-blue-800' :
                              isSelected ? 'bg-gray-800/40 hover:bg-gray-800/60' :
                              'hover:bg-gray-800/30'
                            } ${!isFocused ? 'border border-transparent' : ''}`}
                            onClick={() => setFocusedChannel(isFocused ? null : ch.id)}
                          >
                            <button type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedChannels((prev) => {
                                  const next = new Set(prev);
                                  if (next.has(ch.id)) next.delete(ch.id);
                                  else next.add(ch.id);
                                  return next;
                                });
                              }}
                              className={`mt-0.5 h-4 w-4 rounded border flex-shrink-0 flex items-center justify-center transition-colors ${
                                isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-600 hover:border-gray-400'
                              }`}
                            >
                              {isSelected && <Check className="h-3 w-3 text-white" />}
                            </button>
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-1">
                                <p className="text-xs text-white truncate">{ch.name}</p>
                                {hasOverride && <span className="h-1.5 w-1.5 rounded-full bg-amber-400 flex-shrink-0" />}
                              </div>
                              <p className="text-[10px] text-gray-500 truncate">{getChannelStreamId(ch)}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Right panel — Defaults + per-channel detail */}
                  <div className="flex-1 flex flex-col gap-3 min-w-0 overflow-y-auto">
                    {/* Defaults section */}
                    <div className="rounded-lg border border-gray-800 bg-[#0e0e18] p-3 space-y-2">
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Defaults (apply to all)</p>
                      <div className="space-y-1">
                        <label className="text-[10px] text-gray-500">Zone ID *</label>
                        <Input value={defaults.zone_id} onChange={(e) => setDefaults((d) => ({ ...d, zone_id: e.target.value }))}
                          placeholder="e.g. LAB_101" className="h-8 text-xs bg-[#14141a] border-gray-700 text-white placeholder:text-gray-600" />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                          <label className="text-[10px] text-gray-500">Building</label>
                          <Input value={defaults.building} onChange={(e) => setDefaults((d) => ({ ...d, building: e.target.value }))}
                            placeholder="Optional" className="h-8 text-xs bg-[#14141a] border-gray-700 text-white placeholder:text-gray-600" />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] text-gray-500">Floor</label>
                          <Input value={defaults.floor} onChange={(e) => setDefaults((d) => ({ ...d, floor: e.target.value }))}
                            placeholder="Optional" className="h-8 text-xs bg-[#14141a] border-gray-700 text-white placeholder:text-gray-600" />
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-400">Alert on unknown face</span>
                        <Toggle value={defaults.alert_on_unknown_face} onChange={(v) => setDefaults((d) => ({ ...d, alert_on_unknown_face: v }))} />
                      </div>
                    </div>

                    {/* Per-channel detail */}
                    {focusedChannel && (() => {
                      const ch = nvrChannels.find((c) => c.id === focusedChannel);
                      if (!ch) return null;
                      const override = channelOverrides.get(ch.id) ?? {};
                      const hasOverride = channelOverrides.has(ch.id);

                      const updateOverride = (patch: Partial<ChannelOverride>) => {
                        setChannelOverrides((prev) => {
                          const next = new Map(prev);
                          next.set(ch.id, { ...next.get(ch.id), ...patch });
                          return next;
                        });
                      };

                      const clearOverride = () => {
                        setChannelOverrides((prev) => {
                          const next = new Map(prev);
                          next.delete(ch.id);
                          return next;
                        });
                      };

                      return (
                        <div className="rounded-lg border border-blue-900/50 bg-blue-900/10 p-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <p className="text-xs font-medium text-blue-300">{ch.name}</p>
                            {hasOverride && (
                              <button type="button" onClick={clearOverride}
                                className="text-[10px] text-amber-400 hover:text-amber-300">Reset to defaults</button>
                            )}
                          </div>
                          <div className="space-y-1">
                            <label className="text-[10px] text-gray-500">Stream ID</label>
                            <Input value={override.stream_id ?? autoStreamId(nvrVendor, ch.id)}
                              onChange={(e) => updateOverride({ stream_id: e.target.value })}
                              className="h-8 text-xs bg-[#14141a] border-gray-700 text-white" />
                          </div>
                          <div className="space-y-1">
                            <label className="text-[10px] text-gray-500">RTSP URL</label>
                            <Input value={override.rtsp_url ?? ch.rtsp_url}
                              onChange={(e) => updateOverride({ rtsp_url: e.target.value })}
                              className="h-8 text-xs bg-[#14141a] border-gray-700 text-white font-mono" />
                          </div>
                          <div className="space-y-1">
                            <label className="text-[10px] text-gray-500">Zone ID (leave blank to use default)</label>
                            <Input value={override.zone_id ?? ''}
                              onChange={(e) => updateOverride({ zone_id: e.target.value || undefined })}
                              placeholder={defaults.zone_id || 'Using default'}
                              className="h-8 text-xs bg-[#14141a] border-gray-700 text-white placeholder:text-gray-600" />
                          </div>
                        </div>
                      );
                    })()}

                    {!focusedChannel && (
                      <div className="flex-1 flex items-center justify-center text-gray-600">
                        <p className="text-xs">Click a channel to configure it individually</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Status bar + actions */}
                <div className="flex items-center justify-between pt-1">
                  <p className="text-xs text-gray-400">
                    {selectedCount} of {nvrChannels.length} selected
                    {overrideCount > 0 && ` · ${overrideCount} with overrides`}
                  </p>
                  <div className="flex gap-3">
                    <Button variant="outline" onClick={() => {
                      setFocusedChannel(null);
                      setAddStep(nvrDiscovery === 'success' ? 'nvr_auth' : 'nvr_fallback');
                    }} className="border-gray-700">
                      <ChevronLeft className="h-4 w-4 mr-1" /> Back
                    </Button>
                    <Button onClick={() => {
                      if (!defaults.zone_id.trim()) { toast.error('Set a default Zone ID before continuing'); return; }
                      setAddStep('review');
                    }} disabled={selectedCount === 0} className="bg-blue-600 hover:bg-blue-700">
                      Review {selectedCount} <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Step: Review */}
            {addStep === 'review' && (
              <div className="space-y-4">
                <div className="rounded-lg border border-gray-800 overflow-hidden max-h-[50vh] overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-800 text-gray-500 uppercase tracking-wide">
                        <th className="px-3 py-2 text-left">Stream ID</th>
                        <th className="px-3 py-2 text-left">Zone</th>
                        <th className="px-3 py-2 text-left">Building</th>
                        <th className="px-3 py-2 text-left">Floor</th>
                        <th className="px-3 py-2 text-center w-8" />
                      </tr>
                    </thead>
                    <tbody>
                      {nvrChannels.filter((ch) => selectedChannels.has(ch.id)).map((ch) => {
                        const config = getMergedConfig(ch);
                        const hasOverride = channelOverrides.has(ch.id);
                        return (
                          <tr key={ch.id} className={`border-b border-gray-800/50 last:border-0 ${hasOverride ? 'bg-amber-900/5' : ''}`}>
                            <td className="px-3 py-2 text-white font-mono">{config.stream_id}</td>
                            <td className="px-3 py-2 text-gray-300">{config.zone_id}</td>
                            <td className="px-3 py-2 text-gray-400">{config.building || '—'}</td>
                            <td className="px-3 py-2 text-gray-400">{config.floor || '—'}</td>
                            <td className="px-3 py-2 text-center">
                              {hasOverride && <span className="h-1.5 w-1.5 rounded-full bg-amber-400 inline-block" title="Has overrides" />}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-gray-500">
                  Alert on unknown face: <span className="text-white">{defaults.alert_on_unknown_face ? 'ON' : 'OFF'}</span> for all
                  {overrideCount > 0 && ` (${overrideCount} with individual overrides)`}
                </p>
                <div className="flex gap-3 pt-1">
                  <Button variant="outline" onClick={() => setAddStep('channel_select')} className="border-gray-700 flex-1">
                    <ChevronLeft className="h-4 w-4 mr-1" /> Back
                  </Button>
                  <Button onClick={handleBatchSubmit} className="bg-blue-600 hover:bg-blue-700 flex-1">
                    Add {selectedCount} Camera{selectedCount !== 1 ? 's' : ''} <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step: Submitting */}
            {addStep === 'submitting' && (
              <div className="space-y-4">
                <div className="space-y-1.5 max-h-[50vh] overflow-y-auto">
                  {submitResults.map((r) => (
                    <div key={r.stream_id} className="flex items-center gap-2 text-xs px-3 py-2 rounded bg-[#0e0e18] border border-gray-800">
                      {r.status === 'pending' && <div className="h-4 w-4 rounded-full border-2 border-gray-600" />}
                      {r.status === 'sending' && <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />}
                      {r.status === 'success' && <CheckCircle2 className="h-4 w-4 text-green-400" />}
                      {r.status === 'failed' && <X className="h-4 w-4 text-red-400" />}
                      <span className={`font-mono ${r.status === 'failed' ? 'text-red-300' : 'text-white'}`}>{r.stream_id}</span>
                      {r.status === 'success' && <span className="text-green-500 ml-auto">Added</span>}
                      {r.status === 'failed' && <span className="text-red-400 ml-auto truncate max-w-[200px]">{r.error}</span>}
                    </div>
                  ))}
                </div>

                {submitResults.every((r) => r.status === 'success' || r.status === 'failed') && (
                  <div className="flex gap-3 pt-1">
                    {submitResults.some((r) => r.status === 'failed') ? (
                      <>
                        <Button variant="outline" onClick={closeAddDialog} className="border-gray-700 flex-1">Close</Button>
                        <Button onClick={handleRetryFailed} className="bg-amber-600 hover:bg-amber-500 flex-1">
                          Retry {submitResults.filter((r) => r.status === 'failed').length} Failed
                        </Button>
                      </>
                    ) : (
                      <Button onClick={closeAddDialog} className="bg-green-700 hover:bg-green-600 flex-1">
                        <CheckCircle2 className="h-4 w-4 mr-1" /> Done
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
