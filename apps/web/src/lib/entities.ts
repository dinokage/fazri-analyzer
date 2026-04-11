export type Role = "staff" | "student"

export type Entity = {
  id: string
  name: string
  last_seen: string
  last_location: string
  enrollId: string
  branch: string
  bio: string
  role: Role
}

export type Activity = {
  id: string
  entityId: string
  timestamp: string // ISO string
  title: string
  description: string
  location?: string
}

export const entities: Entity[] = [
  {
    id: "E-1001",
    name: "Aarav Sharma",
    last_seen: "2025-10-05 18:45",
    last_location: "SAC Building",
    enrollId: "ENR-23-CS-001",
    branch: "CSE",
    bio: "Curious builder, loves networks and distributed systems.",
    role: "student",
  },
  {
    id: "E-1002",
    name: "Riya Verma",
    last_seen: "2025-10-05 17:10",
    last_location: "Central Library",
    enrollId: "ENR-22-EE-019",
    branch: "EE",
    bio: "Robotics enthusiast and avid reader.",
    role: "student",
  },
  {
    id: "E-0034",
    name: "Dr. K. Menon",
    last_seen: "2025-10-05 16:30",
    last_location: "ECE Block",
    enrollId: "EMP-STAFF-034",
    branch: "ECE",
    bio: "Faculty, embedded systems researcher.",
    role: "staff",
  },
]

export const activities: Activity[] = [
  // Aarav
  {
    id: "act-1",
    entityId: "E-1001",
    timestamp: "2025-10-05T09:05:00Z",
    title: "Connected to campus Wi‑Fi",
    description: "Authenticated on cafe hotspot",
    location: "North Cafe",
  },
  {
    id: "act-2",
    entityId: "E-1001",
    timestamp: "2025-10-05T12:15:00Z",
    title: "Checked out a book",
    description: "Borrowed 'Designing Data-Intensive Applications'",
    location: "Central Library",
  },
  {
    id: "act-3",
    entityId: "E-1001",
    timestamp: "2025-10-05T16:50:00Z",
    title: "CCTV frame match",
    description: "Face matched at hostel entrance",
    location: "Hostel A Gate",
  },
  {
    id: "act-4",
    entityId: "E-1001",
    timestamp: "2025-10-05T18:30:00Z",
    title: "Event attended",
    description: "AI club meetup (pre-registered)",
    location: "SAC Building",
  },

  // Riya
  {
    id: "act-5",
    entityId: "E-1002",
    timestamp: "2025-10-05T08:45:00Z",
    title: "Connected to campus Wi‑Fi",
    description: "Device authenticated on main SSID",
    location: "Hostel B",
  },
  {
    id: "act-6",
    entityId: "E-1002",
    timestamp: "2025-10-05T11:20:00Z",
    title: "Lab session",
    description: "Completed power systems experiment",
    location: "EE Lab 2",
  },
  {
    id: "act-7",
    entityId: "E-1002",
    timestamp: "2025-10-05T17:05:00Z",
    title: "Reading session",
    description: "Reserved reading room",
    location: "Central Library",
  },

  // Dr. Menon
  {
    id: "act-8",
    entityId: "E-0034",
    timestamp: "2025-10-05T07:55:00Z",
    title: "Lecture delivered",
    description: "Embedded Systems (ES-401)",
    location: "ECE Block",
  },
  {
    id: "act-9",
    entityId: "E-0034",
    timestamp: "2025-10-05T13:30:00Z",
    title: "Research meeting",
    description: "Weekly lab sync",
    location: "ECE Research Lab",
  },
]

export const entitiesForTable = entities.map((e) => ({
  id: e.id,
  name: e.name,
  last_seen: e.last_seen,
  last_location: e.last_location,
}))

export function getEntityById(id: string): Entity | undefined {
  return entities.find((e) => e.id === id)
}

export function getActivitiesByEntity(entityId: string): Activity[] {
  return activities
    .filter((a) => a.entityId === entityId)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
}
