export interface Zone {
  zone_id: string;
  name: string;
  zone_type: string;
  capacity: number;
  building: string;
  floor: number;
  coordinates?: {
    lat: number;
    lng: number;
  };
  department?: string;
  description?: string;
  operating_hours?: {
    start: string;
    end: string;
  };
  facilities?: string[];
}

export interface ZoneOccupancy {
  zone_id: string;
  zone_name: string;
  current_occupancy: number;
  capacity: number;
  occupancy_rate: number;
  last_updated: string;
  status: 'normal' | 'crowded' | 'full';
}

export interface ZoneForecast {
  zone_id: string;
  forecasts: Array<{
    timestamp: string;
    predicted_occupancy: number;
    confidence: number;
  }>;
}

export interface ZoneHistoryData {
  timestamp: string;
  occupancy: number;
  hour: number;
  day_of_week: number;
  is_weekend: boolean;
}

export interface ZoneHistory {
  zone_id: string;
  data: ZoneHistoryData[];
  period_days: number;
  data_points: number;
}

export interface ZoneConnection {
  zone_id: string;
  zone_name: string;
  distance_meters: number;
  walking_time_minutes: number;
}

export interface ZoneForecast {
  target_datetime: string;
  predicted_occupancy: number;
  confidence: number;
}

export interface CampusSummary {
  total_zones: number;
  total_capacity: number;
  total_current_occupancy: number;
  average_occupancy_rate: number;
  most_crowded_zone?: {
    zone_id: string;
    zone_name: string;
    occupancy_rate: number;
  };
  least_crowded_zone?: {
    zone_id: string;
    zone_name: string;
    occupancy_rate: number;
  };
  zones_by_type?: Record<string, number>;
  zones_by_building?: Record<string, number>;
}

export interface ZonesResponse {
  success: boolean;
  data: Zone[];
  count: number;
}

export interface ZoneDetailsResponse {
  success: boolean;
  data: Zone;
}

export interface ZoneOccupancyResponse {
  success: boolean;
  data: ZoneOccupancy;
}

export interface CampusSummaryResponse {
  success: boolean;
  data: CampusSummary;
}
