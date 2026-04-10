// Alert System Types
// Matches backend schemas from /api/v1/alerts

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';

export type AlertStatus =
  | 'created'
  | 'assigned'
  | 'acknowledged'
  | 'investigating'
  | 'resolved'
  | 'escalated';

export type ResolutionType =
  | 'false_alarm'
  | 'resolved'
  | 'escalated'
  | 'no_action_required';

export type StaffRole = 'security' | 'supervisor' | 'admin' | 'maintenance';

export type StaffStatus = 'available' | 'busy' | 'off_duty';

export interface AlertLocation {
  zone_id: string;
  building?: string;
  floor?: string;
  coordinates?: {
    lat: number;
    lng: number;
  };
}

export interface Alert {
  id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  status: AlertStatus;
  location: AlertLocation;
  anomaly_type: string;
  anomaly_id?: string;
  affected_entities: string[];
  data_sources: string[];
  evidence: Record<string, unknown>;
  assigned_to?: string;
  assigned_staff_name?: string;
  assigned_at?: string;
  acknowledged_at?: string;
  resolved_at?: string;
  resolved_by?: string;
  resolver_name?: string;
  resolution_type?: ResolutionType;
  resolution_notes?: string;
  escalation_count: number;
  is_mock: boolean;
  mock_scenario?: string;
  created_at: string;
  updated_at: string;
}

export interface AlertsResponse {
  total: number;
  alerts: Alert[];
  page: number;
  page_size: number;
}

export interface StaffMember {
  id: string;
  name: string;
  email: string;
  phone?: string;
  role: StaffRole;
  department?: string;
  on_duty: boolean;
  max_concurrent_assignments: number;
  current_assignment_count: number;
  is_mock_user: boolean;
  created_at: string;
  updated_at: string;
  // Computed/alias fields for backward compatibility
  current_workload?: number;
  max_workload?: number;
}

export interface StaffListResponse {
  total: number;
  staff: StaffMember[];
}

export interface AlertHistoryEntry {
  id: string;
  alert_id: string;
  action: string;
  actor_type: 'system' | 'staff' | 'admin';
  actor_id?: string;
  actor_name?: string;
  details?: Record<string, unknown>;
  ip_address?: string;
  user_agent?: string;
  timestamp: string;
}

export interface AlertHistoryResponse {
  alert_id: string;
  total: number;
  history: AlertHistoryEntry[];
}

export interface StaffDashboard {
  staff: StaffMember;
  stats: {
    active_alerts: number;
    resolved_today: number;
    avg_response_time_minutes: number;
    escalation_rate: number;
  };
  current_alerts: Alert[];
}

// Filter types for alert queries
export interface AlertFilters {
  status?: AlertStatus | AlertStatus[];
  severity?: AlertSeverity | AlertSeverity[];
  assigned_to?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

// Severity configuration for UI styling
export interface SeverityConfig {
  icon: string;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline';
}

export const SEVERITY_CONFIG: Record<AlertSeverity, SeverityConfig> = {
  critical: {
    icon: 'ShieldAlert',
    label: 'Critical',
    color: 'text-red-500',
    bgColor: 'bg-red-950/30',
    borderColor: 'border-red-900/50',
    badgeVariant: 'destructive',
  },
  high: {
    icon: 'AlertTriangle',
    label: 'High',
    color: 'text-orange-500',
    bgColor: 'bg-orange-950/30',
    borderColor: 'border-orange-900/50',
    badgeVariant: 'default',
  },
  medium: {
    icon: 'AlertCircle',
    label: 'Medium',
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-950/30',
    borderColor: 'border-yellow-900/50',
    badgeVariant: 'secondary',
  },
  low: {
    icon: 'Info',
    label: 'Low',
    color: 'text-blue-500',
    bgColor: 'bg-blue-950/30',
    borderColor: 'border-blue-900/50',
    badgeVariant: 'outline',
  },
};

// Status configuration for UI styling
export interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
}

export const STATUS_CONFIG: Record<AlertStatus, StatusConfig> = {
  created: {
    label: 'Created',
    color: 'text-gray-400',
    bgColor: 'bg-gray-800',
  },
  assigned: {
    label: 'Assigned',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
  },
  acknowledged: {
    label: 'Acknowledged',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-900/30',
  },
  investigating: {
    label: 'Investigating',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/30',
  },
  resolved: {
    label: 'Resolved',
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
  },
  escalated: {
    label: 'Escalated',
    color: 'text-red-400',
    bgColor: 'bg-red-900/30',
  },
};
