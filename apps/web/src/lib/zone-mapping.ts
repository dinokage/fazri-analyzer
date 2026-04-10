// Mapping between location IDs and zone information
export interface ZoneInfo {
  zoneId: string;
  zoneName: string;
  building: string;
  zoneType: string;
}

// Define zone mappings based on location patterns
const ZONE_MAPPINGS: Record<string, ZoneInfo> = {
  'ADMIN_LOBBY': {
    zoneId: 'ADMIN_LOBBY',
    zoneName: 'Administrative Block Lobby',
    building: 'Administrative Block',
    zoneType: 'LOBBY'
  },
  'AUDITORIUM': {
    zoneId: 'AUDITORIUM',
    zoneName: 'Main Auditorium',
    building: 'Academic Block B',
    zoneType: 'AUDITORIUM'
  },
  'CAF_01': {
    zoneId: 'CAF_01',
    zoneName: 'Central Cafeteria',
    building: 'Student Center',
    zoneType: 'CAFETERIA'
  },
  'GYM': {
    zoneId: 'GYM',
    zoneName: 'Fitness Center',
    building: 'Sports Complex',
    zoneType: 'GYM'
  },
  'HOSTEL_GATE': {
    zoneId: 'HOSTEL_GATE',
    zoneName: 'Hostel Main Gate',
    building: 'Hostel Block A',
    zoneType: 'ENTRANCE'
  },
  'LAB_101': {
    zoneId: 'LAB_101',
    zoneName: 'Computer Science Lab 101',
    building: 'Academic Block A',
    zoneType: 'LAB'
  },
  'LAB_306': {
    zoneId: 'LAB_306',
    zoneName: 'Electronics Lab 306',
    building: 'Engineering Block',
    zoneType: 'LAB'
  },
  'LIB_ENT': {
    zoneId: 'LIB_ENT',
    zoneName: 'Library Main Entrance',
    building: 'Library Building',
    zoneType: 'ENTRANCE'
  }
};

/**
 * Get zone name from location ID
 * Handles both zone IDs directly and access point mappings
 */
export function getZoneNameFromLocation(locationId: string): string {
  if (!locationId) return locationId;

  // Check if it's a known zone ID
  const zone = ZONE_MAPPINGS[locationId];
  if (zone) {
    return zone.zoneName;
  }

  // If it's an access point (AP-XXX), try to map it to a zone
  // This is a fallback - ideally this mapping would come from the backend
  if (locationId.startsWith('AP-')) {
    // Extract the room/area number and try to find a matching zone
    // For now, return a formatted version of the location ID
    return locationId;
  }

  // Return the original location ID if no mapping found
  return locationId;
}

/**
 * Get full zone information from location ID
 */
export function getZoneInfoFromLocation(locationId: string): ZoneInfo | null {
  if (!locationId) return null;

  const zone = ZONE_MAPPINGS[locationId];
  return zone || null;
}

/**
 * Check if a location is a known zone
 */
export function isKnownZone(locationId: string): boolean {
  return locationId in ZONE_MAPPINGS;
}
