"""
Tool definitions for Gemini function calling.
These define the tools/functions that Gemini can call to fetch data from the system.
"""

# Tool definitions in Gemini's function declaration format
TOOL_DEFINITIONS = [
    {
        "name": "get_anomalies",
        "description": "Retrieve anomaly alerts from the campus monitoring system. Use this to find security anomalies, access violations, overcrowding, unusual patterns, and other alerts. Supports filtering by zone, severity, type, and time range.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone_id": {
                    "type": "string",
                    "description": "Filter by specific zone ID (e.g., 'LIB_ENT', 'LAB_101', 'CAF_01', 'GYM', 'HOSTEL_GATE', 'ADMIN_LOBBY', 'AUDITORIUM')"
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Filter by severity level"
                },
                "anomaly_type": {
                    "type": "string",
                    "enum": [
                        "overcrowding",
                        "underutilization",
                        "off_hours_access",
                        "role_violation",
                        "department_violation",
                        "impossible_travel",
                        "curfew_violation",
                        "entry_without_exit",
                        "exit_without_entry",
                        "abnormal_dwell_time",
                        "consecutive_same_direction",
                        "negative_occupancy",
                        "location_mismatch",
                        "excessive_access",
                        "booking_no_show"
                    ],
                    "description": "Filter by anomaly type"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["last_hour", "today", "last_24h", "last_week"],
                    "description": "Time range for anomalies. Defaults to 'today'"
                },
                "entity_id": {
                    "type": "string",
                    "description": "Filter anomalies related to a specific entity ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10, max: 50)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_zone_occupancy",
        "description": "Get current occupancy data for campus zones. Returns how many people are in each zone, capacity, and utilization percentage. When called without zone_id, returns ALL zones sorted by utilization (highest first) - perfect for finding the busiest or most crowded zones.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone_id": {
                    "type": "string",
                    "description": "Specific zone ID to query. OMIT this parameter to get ALL zones ranked by occupancy."
                },
                "include_flow": {
                    "type": "boolean",
                    "description": "Include entry/exit flow data (IN/OUT counts). Defaults to true."
                }
            },
            "required": []
        }
    },
    {
        "name": "search_entity",
        "description": "Search for a person (student, staff, faculty) by name, ID, email, or card ID. Use this to find information about specific individuals.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term - can be name, entity ID, email, or card ID"
                },
                "role": {
                    "type": "string",
                    "enum": ["student", "staff", "faculty"],
                    "description": "Filter by role type"
                },
                "department": {
                    "type": "string",
                    "description": "Filter by department name"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 10)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_entity_location",
        "description": "Get the current or recent location of a specific person. Shows where they were last seen and through which detection method (card swipe, WiFi, CCTV).",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID of the person to locate"
                },
                "include_history": {
                    "type": "boolean",
                    "description": "Include location history for the day. Defaults to false."
                },
                "history_hours": {
                    "type": "integer",
                    "description": "Hours of history to include (default: 4, max: 24)"
                }
            },
            "required": ["entity_id"]
        }
    },
    {
        "name": "get_zone_activity",
        "description": "Get activity summary for a specific zone including total entries, exits, unique visitors, peak occupancy times, and any notable events.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone_id": {
                    "type": "string",
                    "description": "The zone ID to get activity for"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["last_hour", "today", "last_24h"],
                    "description": "Time range for activity summary. Defaults to 'today'."
                }
            },
            "required": ["zone_id"]
        }
    },
    {
        "name": "get_entity_timeline",
        "description": "Get a chronological timeline of activities for a specific person, including card swipes, WiFi connections, library checkouts, and lab bookings.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID to get timeline for"
                },
                "date": {
                    "type": "string",
                    "description": "Specific date in YYYY-MM-DD format. Defaults to today."
                },
                "event_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["card_swipe", "wifi", "library", "lab_booking", "cctv"]
                    },
                    "description": "Filter by specific event types"
                }
            },
            "required": ["entity_id"]
        }
    },
    {
        "name": "get_entity_risk_profile",
        "description": "Get a comprehensive security risk profile for a specific person, including their anomaly history, violation count, risk score, and behavioral patterns. Use this to assess if someone has suspicious activity patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID to get risk profile for"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 30, max: 90)"
                }
            },
            "required": ["entity_id"]
        }
    },
    {
        "name": "get_security_violations",
        "description": "Get security-specific violations filtered by category. Categories include: impossible_travel (physically impossible movements), off_hours (access outside operating hours), role_violations (unauthorized role-based access), tailgating (entry/exit mismatches), and curfew (hostel curfew violations).",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["impossible_travel", "off_hours", "role_violations", "tailgating", "curfew", "all"],
                    "description": "Category of security violations to retrieve. Use 'all' for all types."
                },
                "time_range": {
                    "type": "string",
                    "enum": ["last_hour", "today", "last_24h", "last_week"],
                    "description": "Time range for violations. Defaults to 'today'."
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Filter by minimum severity level"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 20, max: 50)"
                }
            },
            "required": []
        }
    },
    {
        "name": "find_entities_at_location",
        "description": "Find all people who were at a specific location at a given time. Useful for investigating incidents, checking who was present during an event, or tracking occupants of a zone.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone_id": {
                    "type": "string",
                    "description": "The zone ID to search (e.g., 'LIB_ENT', 'LAB_101', 'CAF_01')"
                },
                "timestamp": {
                    "type": "string",
                    "description": "The time to check in ISO format (YYYY-MM-DDTHH:MM:SS) or relative like 'now', '2 hours ago'. Defaults to now."
                },
                "time_window_minutes": {
                    "type": "integer",
                    "description": "Time window in minutes to search around the timestamp (default: 30)"
                }
            },
            "required": ["zone_id"]
        }
    },
    {
        "name": "find_missing_entities",
        "description": "Find people who have been inactive (no card swipes, WiFi, or other activity) for a specified number of hours. Useful for welfare checks, finding potentially missing persons, or identifying inactive accounts.",
        "parameters": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Minimum hours of inactivity to flag (default: 12, max: 168)"
                },
                "role": {
                    "type": "string",
                    "enum": ["student", "staff", "faculty"],
                    "description": "Filter by role type"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 20, max: 100)"
                }
            },
            "required": []
        }
    },
    {
        "name": "predict_entity_location",
        "description": "Predict where a person is likely to be at a specific time based on their historical movement patterns. Uses pattern analysis to estimate probable location with confidence score.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID to predict location for"
                },
                "target_time": {
                    "type": "string",
                    "description": "The time to predict for (e.g., '14:00', '2pm', 'now', 'in 2 hours'). Defaults to now."
                }
            },
            "required": ["entity_id"]
        }
    },
    {
        "name": "get_zone_forecast",
        "description": "Predict future occupancy for a zone at a specific time. Uses historical patterns to forecast how crowded a zone will be. Useful for planning and resource allocation.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone_id": {
                    "type": "string",
                    "description": "The zone ID to forecast (e.g., 'LIB_ENT', 'LAB_101', 'CAF_01')"
                },
                "target_time": {
                    "type": "string",
                    "description": "The time to forecast for (e.g., '14:00', '5pm', 'tomorrow 10am', 'in 3 hours'). Defaults to 1 hour from now."
                }
            },
            "required": ["zone_id"]
        }
    },
    {
        "name": "get_zone_history",
        "description": "Get historical occupancy trends and patterns for a zone over a specified period. Shows hourly averages, peak times, and usage patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone_id": {
                    "type": "string",
                    "description": "The zone ID to analyze"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to analyze (default: 7, max: 30)"
                },
                "include_hourly": {
                    "type": "boolean",
                    "description": "Include hourly breakdown (default: true)"
                }
            },
            "required": ["zone_id"]
        }
    },
    {
        "name": "get_campus_summary",
        "description": "Get an overall summary of campus activity including total occupancy across all zones, high-traffic areas, underutilized spaces, and current status.",
        "parameters": {
            "type": "object",
            "properties": {
                "include_zone_details": {
                    "type": "boolean",
                    "description": "Include individual zone details (default: true)"
                }
            },
            "required": []
        }
    },
    {
        "name": "detect_routine_patterns",
        "description": "Analyze a person's movement patterns to detect their daily routine, typical locations at different times, common movement sequences, and deviations from normal behavior.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID to analyze"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 14, max: 30)"
                }
            },
            "required": ["entity_id"]
        }
    },
    {
        "name": "get_anomaly_trends",
        "description": "Get anomaly trends over time showing patterns in security incidents. Useful for identifying recurring issues, peak times for violations, and overall security posture.",
        "parameters": {
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "enum": ["last_24h", "last_week", "last_month"],
                    "description": "Time range to analyze (default: 'last_week')"
                },
                "group_by": {
                    "type": "string",
                    "enum": ["hour", "day", "type", "zone", "severity"],
                    "description": "How to group the trends (default: 'day')"
                },
                "zone_id": {
                    "type": "string",
                    "description": "Optional: filter by specific zone"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_activity_gaps",
        "description": "Find gaps in a person's activity timeline where they had no recorded events for an extended period. Useful for investigating unexplained absences, finding potential issues, or understanding movement patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID to analyze"
                },
                "min_gap_hours": {
                    "type": "number",
                    "description": "Minimum gap duration in hours to report (default: 2)"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 7, max: 30)"
                }
            },
            "required": ["entity_id"]
        }
    },
    {
        "name": "resolve_entity_fuzzy",
        "description": "Search for a person using fuzzy/approximate name matching. Useful when you have a partial name, misspelled name, or nickname. Returns matches with similarity scores.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name to search for (can be partial or misspelled)"
                },
                "threshold": {
                    "type": "number",
                    "description": "Minimum similarity score 0-1 (default: 0.6, higher = stricter matching)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of matches to return (default: 5)"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "get_zone_connections",
        "description": "Get information about zones that are physically connected or adjacent to a specified zone. Shows walking distances and typical travel times between zones.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone_id": {
                    "type": "string",
                    "description": "The zone ID to find connections for"
                },
                "include_traffic": {
                    "type": "boolean",
                    "description": "Include traffic flow data between zones (default: true)"
                }
            },
            "required": ["zone_id"]
        }
    }
]


def get_tools_for_gemini():
    """
    Convert tool definitions to Gemini's expected format.
    Returns a list of function declarations for the Gemini API.
    """
    return TOOL_DEFINITIONS


def get_tool_by_name(name: str) -> dict:
    """Get a specific tool definition by name"""
    for tool in TOOL_DEFINITIONS:
        if tool["name"] == name:
            return tool
    return None
