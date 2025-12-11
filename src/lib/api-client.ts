// lib/api-client.ts
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

async function handleResponse(response: Response) {
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
    throw new ApiError(message, response.status, error);
  }
  return response.json();
}

export const apiClient = {
  async getEntity(entityId: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/entities/${entityId}`, {
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  },

  async getEntityFusionReport(entityId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/entities/${entityId}/fusion-report`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getTimeline(entityId: string, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const url = `${API_BASE_URL}/api/v1/graph/timeline/${entityId}${params.toString() ? `?${params}` : ''}`;
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
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
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getTimelineSummary(entityId: string, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const url = `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/summary${params.toString() ? `?${params}` : ''}`;
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
      }
    );
    return handleResponse(response);
  },

  async getActivityHeatmap(entityId: string, days = 7) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/heatmap?days=${days}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getDailySummary(entityId: string, date?: string) {
    const params = date ? `?date=${date}` : '';
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/daily-summary${params}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async detectActivityPatterns(entityId: string, days = 7) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/timeline/${entityId}/patterns?days=${days}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getEntitiesAtLocation(locationId: string, timestamp?: string) {
    const params = timestamp ? `?timestamp=${timestamp}` : '';
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/location/${locationId}/entities${params}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getMissingEntities(hours = 12) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/alerts/missing?hours=${hours}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getGraphStats() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/graph/stats`,
      { headers: { 'Content-Type': 'application/json' } }
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
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async searchEntity(identifierType: string, identifierValue: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/entities/search`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identifier_type: identifierType,
          identifier_value: identifierValue,
        }),
      }
    );
    return handleResponse(response);
  },

  async fuzzySearchByName(name: string, threshold = 0.85) {
    const params = new URLSearchParams({
      name,
      threshold: threshold.toString(),
    });

    const response = await fetch(
      `${API_BASE_URL}/api/v1/entities/fuzzy-search?${params}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getAnomaliesByEntity(entityId: string, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const url = `${API_BASE_URL}/api/v1/anomalies/by-entity/${entityId}${params.toString() ? `?${params}` : ''}`;
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
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
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  // NEW METHOD: getAnomalySummary for the first three cards
  async getAnomalySummary() {
    const response = await fetch(`${API_BASE_URL}/api/v1/anomalies/summary`, {
      headers: { 'Content-Type': 'application/json' },
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
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  // Zone/Spatial endpoints
  async getAllZones() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getZoneDetails(zoneId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getZoneOccupancy(zoneId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}/occupancy`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getZoneHistory(zoneId: string, daysBack: number = 7) {
    const params = new URLSearchParams({
      days_back: daysBack.toString(),
    });

    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}/history?${params}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getZoneForecast(zoneId: string, hoursAhead: number = 24) {
    const params = new URLSearchParams({
      hours_ahead: hoursAhead.toString(),
    });

    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}/forecast?${params}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getZoneConnections(zoneId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/zones/${zoneId}/connections`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getCampusSummary() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/spatial/campus/summary`,
      { headers: { 'Content-Type': 'application/json' } }
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
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getAlert(alertId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/${alertId}`,
      { headers: { 'Content-Type': 'application/json' } }
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
      }
    );
    return handleResponse(response);
  },

  async getAlertHistory(alertId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/${alertId}/history`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async addAlertNote(alertId: string, staffId: string, note: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/${staffId}/alerts/${alertId}/add-note`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await handleResponse(response);
    // Backend returns array directly, wrap it for consistent frontend interface
    return { staff: Array.isArray(data) ? data : data.staff || [] };
  },

  async getStaffMember(staffId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/${staffId}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getStaffByEmail(email: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/by-email/${encodeURIComponent(email)}`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getStaffDashboard(staffId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/${staffId}/dashboard`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getStaffAlerts(staffId: string, params?: { status?: string; active_only?: boolean }) {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append('status', params.status);
    if (params?.active_only) searchParams.append('active_only', 'true');

    const response = await fetch(
      `${API_BASE_URL}/api/v1/staff/${staffId}/alerts?${searchParams}`,
      { headers: { 'Content-Type': 'application/json' } }
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
      }
    );
    return handleResponse(response);
  },

  async getChatHealth() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/health`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getChatTools() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/tools`,
      { headers: { 'Content-Type': 'application/json' } }
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
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },

  async getGitLabHealth() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/gitlab/health`,
      { headers: { 'Content-Type': 'application/json' } }
    );
    return handleResponse(response);
  },
};

export { ApiError };