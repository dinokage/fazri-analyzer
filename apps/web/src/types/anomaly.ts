export type AnomalySeverity = 'low' | 'medium' | 'high' | 'critical';

export type AnomalyType =
  | 'off_hours_access'
  | 'role_violation'
  | 'department_violation'
  | 'impossible_travel'
  | 'location_mismatch'
  | 'curfew_violation'
  | 'excessive_access'
  | 'booking_no_show'
  | 'overcrowding'
  | 'unauthorized_access'
  | 'equipment_misuse'
  | 'security_anomaly'
  | 'security_drift'
  | 'queue_congestion'
  | 'data_integrity_anomaly';

export interface Anomaly {
  id: string;
  type: AnomalyType;
  severity: AnomalySeverity;
  entity_id: string;
  entity_name: string;
  entity_role?: string;
  location: string;
  location_name: string;
  timestamp: string; // Timestamps are now always ISO strings from the backend
  description: string;
  details?: Record<string, unknown>;
  recommended_actions?: string[];
}

export interface AnomalyResponse {
  success: boolean;
  data: {
    entity?: {
      entity_id: string;
      name: string;
      role: string;
      department: string;
      card_id?: string;
    };
    anomalies: Anomaly[];
    total_count: number;
    time_range: string;
    detection_time: string;
  };
}
