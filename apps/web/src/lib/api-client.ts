import { getSession } from "@/lib/auth-client";
import * as Sentry from "@sentry/nextjs";

const API_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Module-level token cache — avoids a round-trip on every API call.
// Invalidated on 401 and when org changes via OrgSwitcher.
let tokenCache: { value: string; expiresAt: number } | null = null;

// Deduplicates concurrent getSession() calls so that when the JWT cache
// expires and multiple queries fire at the same time (e.g. on alert polls),
// only one network round-trip is made.
let pendingJwtFetch: Promise<string> | null = null;

export function invalidateTokenCache() {
  tokenCache = null;
}

async function fetchFreshJwt(): Promise<string> {
  let jwt: string | null = null;
  const session = await getSession({
    fetchOptions: {
      onSuccess: (ctx) => {
        jwt = ctx.response.headers.get("set-auth-jwt");
      },
    },
  });

  if (!session?.data) {
    throw new ApiError("No active session. Please log in.", 401);
  }
  if (!jwt) {
    throw new ApiError("Could not retrieve auth token.", 401);
  }

  // Cache for 20 minutes — JWT is valid for 30 days, 20 min keeps it fresh
  // without hitting the auth service on every alert poll cycle.
  tokenCache = { value: jwt, expiresAt: Date.now() + 20 * 60 * 1000 };
  return jwt;
}

async function getAuthHeaders(): Promise<HeadersInit> {
  if (tokenCache && Date.now() < tokenCache.expiresAt) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${tokenCache.value}`,
    };
  }

  if (!pendingJwtFetch) {
    pendingJwtFetch = fetchFreshJwt().finally(() => {
      pendingJwtFetch = null;
    });
  }

  const jwt = await pendingJwtFetch;
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${jwt}`,
  };
}

async function handleResponse(response: Response) {
  if (response.status === 401) {
    // Invalidate the JWT cache so the next call fetches a fresh token.
    // Do NOT hard-redirect here — a transient 401 (network blip, brief
    // service restart) would boot the user out. The sidebar's useSession()
    // hook handles the redirect when the session is genuinely gone.
    invalidateTokenCache();
    Sentry.captureMessage('API returned 401 - invalidating JWT cache', {
      level: 'warning',
      tags: { type: 'auth_expired', status_code: '401' },
      extra: { url: response.url },
    });
    throw new ApiError('Session expired. Please log in again.', 401);
  }

  if (response.status === 403) {
    // Log permission errors to Sentry as warnings
    Sentry.captureMessage('Permission denied - insufficient privileges', {
      level: 'warning',
      tags: {
        type: 'permission_denied',
        status_code: '403',
      },
      extra: {
        url: response.url,
      },
    });

    throw new ApiError('You do not have permission to perform this action.', 403);
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    // Handle cases where detail is an object (e.g., validation errors)
    let message = 'API request failed';
    if (typeof error.detail === 'string') {
      message = error.detail;
    } else if (typeof error.message === 'string') {
      message = error.message;
    } else if (error.detail && typeof error.detail === 'object') {
      // Handle validation errors or structured error details
      message = JSON.stringify(error.detail);
    }

    // Capture API errors in Sentry
    const apiError = new ApiError(message, response.status, error);
    Sentry.captureException(apiError, {
      tags: {
        type: 'api_error',
        status_code: response.status.toString(),
      },
      extra: {
        url: response.url,
        response_body: error,
        error_message: message,
      },
      level: response.status >= 500 ? 'error' : 'warning',
    });

    throw apiError;
  }
  return response.json();
}

export const apiClient = {
  async getEntity(entityId: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/entities/${entityId}`, {
      headers: await getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getEntityFusionReport(entityId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/entities/${entityId}/fusion-report`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getTimeline(entityId: string, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const url = `${API_BASE_URL}/api/v1/graph/timeline/${entityId}${params.toString() ? `?${params}` : ''}`;
    const response = await fetch(url, {
      headers: await getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getTimelineWithGaps(entityId: string, gapThresholdHours = 2, startDate?: string, endDate?: string) {
    const params = new URLSearchParams({
      gap_threshold_hours: gapThresholdHours.toString(),
    });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/with-gaps?${params}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getTimelineSummary(entityId: string, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const url = `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/summary${params.toString() ? `?${params}` : ''}`;
    const response = await fetch(url, {
      headers: await getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async predictLocation(entityId: string, targetTime?: string, lookbackDays = 7) {
    const params = new URLSearchParams({
      lookback_days: lookbackDays.toString(),
    });
    if (targetTime) params.append('target_time', targetTime);

    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/predict/location/${entityId}?${params}`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
      }
    );
    return handleResponse(response);
  },

  async predictDuringGap(entityId: string, gapStart: string, gapEnd: string) {
    const params = new URLSearchParams({
      gap_start: gapStart,
      gap_end: gapEnd,
    });

    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/predict/gap/${entityId}?${params}`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
      }
    );
    return handleResponse(response);
  },

  async getActivityHeatmap(entityId: string, days = 7) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/heatmap?days=${days}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getDailySummary(entityId: string, date?: string) {
    const params = date ? `?date=${date}` : '';
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/daily-summary${params}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async detectActivityPatterns(entityId: string, days = 7) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/patterns?days=${days}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getEntitiesAtLocation(locationId: string, timestamp?: string) {
    const params = timestamp ? `?timestamp=${timestamp}` : '';
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/location/${locationId}/entities${params}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getMissingEntities(hours = 12) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/alerts/missing?hours=${hours}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getGraphStats() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/stats`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async listEntities(skip = 0, limit = 100, department?: string, entityType?: string) {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    if (department) params.append('department', department);
    if (entityType) params.append('entity_type', entityType);

    const response = await fetch(
      `${API_BASE_URL}/api/v1/entities/?${params}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async searchEntity(identifierType: string, identifierValue: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/entities/search`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          identifier_type: identifierType,
          identifier_value: identifierValue,
        }),
      }
    );
    return handleResponse(response);
  },

  async getAnomaliesByEntity(entityId: string, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const url = `${API_BASE_URL}/api/v1/anomalies/by-entity/${entityId}${params.toString() ? `?${params}` : ''}`;
    const response = await fetch(url, {
      headers: await getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getAllAnomalies(limit?: number, offset: number = 0) {
    const params = new URLSearchParams({
      offset: offset.toString(),
    });
    if (limit) params.append('limit', limit.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/v1/anomalies/all?${params}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  // NEW METHOD: getAnomalySummary for the first three cards
  async getAnomalySummary() {
    const response = await fetch(`${API_BASE_URL}/api/v1/anomalies/summary`, {
      headers: await getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getAnomaliesByDateRange(startDate: string, endDate: string) {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });

    const response = await fetch(
      `${API_BASE_URL}/api/v1/anomalies/date-range?${params}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  // Zone/Spatial endpoints
  async getAllZones() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getZoneDetails(zoneId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getZoneOccupancy(zoneId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}/occupancy`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getZoneHistory(zoneId: string, daysBack: number = 7) {
    const params = new URLSearchParams({
      days_back: daysBack.toString(),
    });

    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}/history?${params}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getZoneForecast(zoneId: string, hoursAhead: number = 24) {
    const params = new URLSearchParams({
      hours_ahead: hoursAhead.toString(),
    });

    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}/forecast?${params}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getZoneConnections(zoneId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}/connections`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getCampusSummary() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/campus/summary`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  // ===== ALERT ENDPOINTS =====

  async getAlerts(params?: {
    status?: string | string[];
    severity?: string | string[];
    assigned_to?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }) {
    const searchParams = new URLSearchParams();
    if (params?.status) {
      const statuses = Array.isArray(params.status) ? params.status : [params.status];
      statuses.forEach(s => searchParams.append('status', s));
    }
    if (params?.severity) {
      const severities = Array.isArray(params.severity) ? params.severity : [params.severity];
      severities.forEach(s => searchParams.append('severity', s));
    }
    if (params?.assigned_to) searchParams.append('assigned_to', params.assigned_to);
    if (params?.start_date) searchParams.append('start_date', params.start_date);
    if (params?.end_date) searchParams.append('end_date', params.end_date);
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts?${searchParams}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getAlert(alertId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/${alertId}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async createAlert(data: {
    title: string;
    description: string;
    severity: string;
    location: Record<string, unknown>;
    anomaly_type: string;
    affected_entities?: string[];
    data_sources?: string[];
    evidence?: Record<string, unknown>;
  }) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify(data),
      }
    );
    return handleResponse(response);
  },

  async assignAlert(alertId: string, staffId: string, reason?: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/${alertId}/assign`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify({ staff_id: staffId, reason }),
      }
    );
    return handleResponse(response);
  },

  async acknowledgeAlert(alertId: string, staffId: string) {
    // staff_id is a query parameter, not body
    const params = new URLSearchParams({ staff_id: staffId });
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/${alertId}/acknowledge?${params}`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
      }
    );
    return handleResponse(response);
  },

  async resolveAlert(alertId: string, data: {
    staff_id: string;
    resolution_type: string;
    resolution_notes: string;
  }) {
    // staff_id is a query parameter, resolution data is body
    const params = new URLSearchParams({ staff_id: data.staff_id });
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/${alertId}/resolve?${params}`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          resolution_type: data.resolution_type,
          resolution_notes: data.resolution_notes,
        }),
      }
    );
    return handleResponse(response);
  },

  async escalateAlert(alertId: string, data: {
    escalate_to: string;
    reason: string;
  }) {
    // escalate_to and reason are query parameters
    const params = new URLSearchParams({
      escalate_to: data.escalate_to,
      reason: data.reason,
    });
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/${alertId}/escalate?${params}`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
      }
    );
    return handleResponse(response);
  },

  async getAlertHistory(alertId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/${alertId}/history`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async addAlertNote(alertId: string, staffId: string, note: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/${staffId}/alerts/${alertId}/add-note`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify({ note }),
      }
    );
    return handleResponse(response);
  },

  // ===== STAFF ENDPOINTS =====

  async getStaffList(params?: { available_only?: boolean; role?: string }) {
    // Use /available endpoint if available_only is true, otherwise use main endpoint
    const endpoint = params?.available_only
      ? `${API_BASE_URL}/api/v1/staff/available`
      : `${API_BASE_URL}/api/v1/staff`;

    const searchParams = new URLSearchParams();
    if (params?.role) searchParams.append('role', params.role);
    // Also filter by on_duty for the main endpoint
    if (!params?.available_only && params?.available_only !== undefined) {
      searchParams.append('on_duty', 'true');
    }

    const queryString = searchParams.toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;

    const response = await fetch(url, {
      headers: await getAuthHeaders()
    });
    const data = await handleResponse(response);
    // Backend returns array directly, wrap it for consistent frontend interface
    return { staff: Array.isArray(data) ? data : data.staff || [] };
  },

  async getStaffMember(staffId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/${staffId}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getStaffByEmail(email: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/by-email/${encodeURIComponent(email)}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getStaffDashboard(staffId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/${staffId}/dashboard`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getStaffAlerts(staffId: string, params?: { status?: string; active_only?: boolean }) {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append('status', params.status);
    if (params?.active_only) searchParams.append('active_only', 'true');

    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/${staffId}/alerts?${searchParams}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  // ===== CHAT ENDPOINTS =====

  async sendChatMessage(data: {
    message: string;
    conversation_id?: string;
    context?: Record<string, unknown>;
  }): Promise<{
    response: string;
    conversation_id: string;
    tools_used: string[];
    data: Record<string, unknown> | null;
    metadata: Record<string, unknown>;
  }> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/message`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify(data),
      }
    );
    return handleResponse(response);
  },

  async clearChatConversation(conversationId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/conversation/${conversationId}`,
      {
        method: 'DELETE',
        headers: await getAuthHeaders(),
      }
    );
    return handleResponse(response);
  },

  async getChatHealth() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/health`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getChatTools() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/tools`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  // ===== GITLAB ENDPOINTS =====

  async getGitLabStatus(): Promise<{
    connected: boolean;
    project_name?: string;
    project_url?: string;
    default_branch?: string;
    latest_pipeline?: {
      id: number;
      status: string;
      ref: string;
      sha: string;
      web_url: string;
      created_at: string;
      source: string;
    };
    latest_commit?: {
      sha: string;
      short_sha: string;
      title: string;
      author_name: string;
      authored_date: string;
      web_url: string;
    };
    recent_pipelines: Array<{
      id: number;
      status: string;
      ref: string;
      sha: string;
      web_url: string;
      created_at: string;
      source: string;
    }>;
    pipeline_jobs: Array<{
      id: number;
      name: string;
      stage: string;
      status: string;
      web_url: string;
      duration?: number;
    }>;
    latest_deployment?: {
      id: number;
      status: string;
      environment: string;
      ref: string;
      sha: string;
      created_at: string;
      deployed_by?: string;
    };
    error?: string;
  }> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/gitlab/status`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async getGitLabHealth() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/gitlab/health`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  // ===== DEEPFACE / CAMERA STREAM ENDPOINTS =====

  async getCameraStreams() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/deepface/streams`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async createCameraStream(data: {
    stream_id: string;
    rtsp_url: string;
    zone_id: string;
    building?: string;
    floor?: string;
    alert_on_unknown_face: boolean;
  }) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/deepface/streams`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify(data),
      }
    );
    return handleResponse(response);
  },

  async deleteCameraStream(streamId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/deepface/streams/${encodeURIComponent(streamId)}`,
      {
        method: 'DELETE',
        headers: await getAuthHeaders(),
      }
    );
    if (response.status === 204) return;
    return handleResponse(response);
  },

  async getVapidPublicKey(): Promise<string> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/notifications/vapid-public-key`,
      { headers: await getAuthHeaders() }
    );
    const data = await handleResponse(response);
    return data.publicKey as string;
  },

  async subscribePush(subscription: { endpoint: string; p256dh: string; auth: string }) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/notifications/push-subscription`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify(subscription),
      }
    );
    return handleResponse(response);
  },

  async unsubscribePush(subscription: { endpoint: string; p256dh: string; auth: string }) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/notifications/push-subscription`,
      {
        method: 'DELETE',
        headers: await getAuthHeaders(),
        body: JSON.stringify(subscription),
      }
    );
    return handleResponse(response);
  },

  async getCameraSnapshot(streamId: string): Promise<string> {
    // <img src> cannot send Authorization headers, so we fetch the JPEG
    // through apiClient (which attaches the Bearer token) and convert it
    // to a blob object URL for use in <img src>.
    const headers = await getAuthHeaders();
    const response = await fetch(
      `${API_BASE_URL}/api/v1/deepface/streams/${encodeURIComponent(streamId)}/snapshot`,
      { headers },
    );
    if (!response.ok) throw new ApiError(`Snapshot failed: ${response.status}`, response.status);
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  },

  async webrtcOffer(streamId: string, sdpOffer: string): Promise<string> {
    const headers = await getAuthHeaders();
    const response = await fetch(
      `${API_BASE_URL}/api/v1/deepface/streams/${encodeURIComponent(streamId)}/webrtc`,
      {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/sdp' },
        body: sdpOffer,
      },
    );
    if (!response.ok) throw new ApiError(`WebRTC signaling failed: ${response.status}`, response.status);
    return response.text();
  },

  async getStreamDetections(streamId: string): Promise<{
    detections: Array<{
      img_name: string;
      entity_name: string | null;
      confidence: number;
      distance: number;
      facial_area: { x: number; y: number; w: number; h: number } | null;
      is_unknown: boolean;
    }>;
    cached: boolean;
  }> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/deepface/streams/${encodeURIComponent(streamId)}/detections`,
      { headers: await getAuthHeaders() },
    );
    return handleResponse(response);
  },

  async probeOnvif(data: {
    ip: string;
    port?: number;
    username?: string;
    password?: string;
    use_https?: boolean;
  }): Promise<{
    vendor?: string;
    model?: string;
    channels?: Array<{ id: string; name: string; rtsp_url: string }>;
    error?: string;
    message?: string;
  }> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/deepface/onvif/probe`,
      {
        method: 'POST',
        headers: await getAuthHeaders(),
        body: JSON.stringify(data),
      }
    );
    return handleResponse(response);
  },

  // ===== OUTGOING WEBHOOK ENDPOINTS =====

  async listWebhooks() {
    const response = await fetch(`${API_BASE_URL}/api/v1/webhooks`, {
      headers: await getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async createWebhook(url: string, events: string[]) {
    const response = await fetch(`${API_BASE_URL}/api/v1/webhooks`, {
      method: 'POST',
      headers: await getAuthHeaders(),
      body: JSON.stringify({ url, events }),
    });
    return handleResponse(response);
  },

  async updateWebhook(id: string, data: { url?: string; events?: string[]; active?: boolean }) {
    const response = await fetch(`${API_BASE_URL}/api/v1/webhooks/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: await getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  async deleteWebhook(id: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/webhooks/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: await getAuthHeaders(),
    });
    if (response.status === 204) return;
    return handleResponse(response);
  },

  async testWebhook(id: string): Promise<{ success: boolean; status?: number; error?: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/webhooks/${encodeURIComponent(id)}/test`, {
      method: 'POST',
      headers: await getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async fuzzySearchByName(name: string, threshold = 0.7) {
    const params = new URLSearchParams({ name, threshold: threshold.toString() });
    const response = await fetch(`${API_BASE_URL}/api/v1/entities/fuzzy-search?${params}`, {
      headers: await getAuthHeaders(),
    });
    const data = await handleResponse(response);
    // Backend returns { matches: [{ entity: {...}, similarity }] }
    // Map to flat EntityResult[] with `type` instead of `entity_type`
    const results = (data.matches ?? []).map((m: { entity: Record<string, unknown>; similarity: number }) => ({
      entity_id: m.entity.entity_id,
      name: m.entity.name,
      type: m.entity.entity_type,
      department: m.entity.department,
      face_id: m.entity.face_id,
    }));
    return { results };
  },

  async registerFace(entityId: string, file: File) {
    // Do NOT use getAuthHeaders() here — it sets Content-Type: application/json,
    // which prevents the browser from setting the multipart/form-data boundary that
    // FastAPI's UploadFile parser requires. Extract just the Bearer token instead.
    const headers = await getAuthHeaders();
    const token = (headers as Record<string, string>)['Authorization'];

    const formData = new FormData();
    formData.append('image', file);

    const response = await fetch(
      `${API_BASE_URL}/api/v1/deepface/entities/${encodeURIComponent(entityId)}/register`,
      {
        method: 'POST',
        headers: { Authorization: token },
        body: formData,
      }
    );
    return handleResponse(response);
  },

  // ── Sensor Events ────────────────────────────────────────────────────────

  async getSensorEvents(params: {
    sensor_type?: string;
    zone_id?: string;
    resolved?: boolean;
    since?: string;
    until?: string;
    limit?: number;
    offset?: number;
  } = {}) {
    const qs = new URLSearchParams();
    if (params.sensor_type) qs.set('sensor_type', params.sensor_type);
    if (params.zone_id) qs.set('zone_id', params.zone_id);
    if (params.resolved !== undefined) qs.set('resolved', String(params.resolved));
    if (params.since) qs.set('since', params.since);
    if (params.until) qs.set('until', params.until);
    if (params.limit !== undefined) qs.set('limit', String(params.limit));
    if (params.offset !== undefined) qs.set('offset', String(params.offset));

    const response = await fetch(
      `${API_BASE_URL}/api/v1/events${qs.toString() ? `?${qs}` : ''}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  // ── Entity timeline (sensor events) ─────────────────────────────────────

  async getEntitySensorTimeline(
    entityId: string,
    params: { since?: string; limit?: number } = {}
  ) {
    const qs = new URLSearchParams();
    if (params.since) qs.set('since', params.since);
    if (params.limit !== undefined) qs.set('limit', String(params.limit));

    const response = await fetch(
      `${API_BASE_URL}/api/v1/entities/${entityId}/timeline${qs.toString() ? `?${qs}` : ''}`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  // ── System health ────────────────────────────────────────────────────────

  async getSystemHealth() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/system/health`,
      { headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },

  async controlSimulator(sim: 'hikvision' | 'aruba', action: 'pause' | 'resume') {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/system/simulators/${sim}/${action}`,
      { method: 'POST', headers: await getAuthHeaders() }
    );
    return handleResponse(response);
  },
};

export { ApiError };