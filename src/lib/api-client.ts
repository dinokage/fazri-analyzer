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
    throw new ApiError(
      error.detail || error.message || 'API request failed',
      response.status,
      error
    );
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
};

export { ApiError };