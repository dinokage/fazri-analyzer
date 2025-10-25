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
  target_datetime: string;
  predicted_occupancy: number;
  confidence: number;
}

export interface CampusSummary {
  summary: {
    total_zones: number;
    total_capacity: number;
    total_occupancy: number;
    overall_occupancy_rate: number;
    status: string;
  };
  zone_details: Array<{
    zone_id: string;
    zone_name: string;
    zone_type: string;
    capacity: number;
    current_occupancy: number;
  }>;
  high_traffic_zones: Array<{
    zone_id: string;
    zone_name: string;
    capacity: number;
    current_occupancy: number;
  }>;
  underutilized_zones: Array<{
    zone_id: string;
    zone_name: string;
    capacity: number;
    current_occupancy: number;
  }>;
  last_updated: string;
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
