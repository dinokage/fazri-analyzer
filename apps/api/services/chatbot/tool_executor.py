"""
Tool executor service that maps Gemini tool calls to existing backend services.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import logging

from services.graph_builder import get_graph_builder
from services.timeline_service import TimelineService

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes tool calls by delegating to existing services"""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password

        # Initialize services lazily
        self._graph_builder = None
        self._timeline_service = None

    @property
    def graph_builder(self):
        if self._graph_builder is None:
            self._graph_builder = get_graph_builder()
        return self._graph_builder

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with the given parameters.
        Returns a dictionary with the tool result.
        """
        logger.info(f"Executing tool: {tool_name} with params: {parameters}")

        try:
            if tool_name == "get_anomalies":
                return self._execute_get_anomalies(parameters)
            elif tool_name == "get_zone_occupancy":
                return self._execute_get_zone_occupancy(parameters)
            elif tool_name == "search_entity":
                return self._execute_search_entity(parameters)
            elif tool_name == "get_entity_location":
                return self._execute_get_entity_location(parameters)
            elif tool_name == "get_zone_activity":
                return self._execute_get_zone_activity(parameters)
            elif tool_name == "get_entity_timeline":
                return self._execute_get_entity_timeline(parameters)
            elif tool_name == "get_entity_risk_profile":
                return self._execute_get_entity_risk_profile(parameters)
            elif tool_name == "get_security_violations":
                return self._execute_get_security_violations(parameters)
            elif tool_name == "find_entities_at_location":
                return self._execute_find_entities_at_location(parameters)
            elif tool_name == "find_missing_entities":
                return self._execute_find_missing_entities(parameters)
            elif tool_name == "predict_entity_location":
                return self._execute_predict_entity_location(parameters)
            elif tool_name == "get_zone_forecast":
                return self._execute_get_zone_forecast(parameters)
            elif tool_name == "get_zone_history":
                return self._execute_get_zone_history(parameters)
            elif tool_name == "get_campus_summary":
                return self._execute_get_campus_summary(parameters)
            elif tool_name == "detect_routine_patterns":
                return self._execute_detect_routine_patterns(parameters)
            elif tool_name == "get_anomaly_trends":
                return self._execute_get_anomaly_trends(parameters)
            elif tool_name == "get_activity_gaps":
                return self._execute_get_activity_gaps(parameters)
            elif tool_name == "resolve_entity_fuzzy":
                return self._execute_resolve_entity_fuzzy(parameters)
            elif tool_name == "get_zone_connections":
                return self._execute_get_zone_connections(parameters)
            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"error": str(e), "tool": tool_name}

    def _get_time_range(self, time_range: str) -> tuple[datetime, datetime]:
        """Convert time range string to datetime objects.

        Note: Uses local time (no timezone) to match how data is stored in Neo4j.
        The simulator creates SpatialActivity nodes with local timestamps.
        """
        now = datetime.now()  # Local time, no timezone - matches Neo4j data

        if time_range == "last_hour":
            start = now - timedelta(hours=1)
        elif time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == "last_24h":
            start = now - timedelta(hours=24)
        elif time_range == "last_week":
            start = now - timedelta(days=7)
        else:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        return start, now

    def _execute_get_anomalies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_anomalies tool"""
        return {"error": "This tool is disabled pending pipeline migration."}

    def _execute_get_zone_occupancy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_zone_occupancy tool"""
        return {"error": "Spatial forecasting service removed. Zone data will be available in the new zone management system."}

    def _execute_search_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search_entity tool"""
        query = params.get("query", "")
        role = params.get("role")
        department = params.get("department")
        limit = min(params.get("limit", 10), 50)

        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Build the query based on parameters
                cypher = """
                    MATCH (e:Entity)
                    WHERE (toLower(e.name) CONTAINS toLower($query)
                           OR e.entity_id CONTAINS $query
                           OR toLower(e.email) CONTAINS toLower($query)
                           OR e.card_id = $query)
                """

                if role:
                    cypher += " AND e.role = $role"
                if department:
                    cypher += " AND toLower(e.department) CONTAINS toLower($department)"

                cypher += """
                    RETURN e.entity_id as entity_id,
                           e.name as name,
                           e.role as role,
                           e.department as department,
                           e.email as email,
                           e.card_id as card_id
                    LIMIT $limit
                """

                result = session.run(cypher, {
                    "query": query,
                    "role": role,
                    "department": department,
                    "limit": limit
                })

                entities = []
                for record in result:
                    entities.append({
                        "entity_id": record["entity_id"],
                        "name": record["name"],
                        "role": record["role"],
                        "department": record["department"],
                        "email": record["email"],
                        "card_id": record["card_id"]
                    })

            driver.close()

            return {
                "entities": entities,
                "count": len(entities),
                "query": query,
                "filters": {"role": role, "department": department}
            }

        except Exception as e:
            logger.error(f"Error searching entity: {str(e)}")
            return {"error": str(e)}

    def _execute_get_entity_location(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_entity_location tool"""
        entity_id = params.get("entity_id")
        include_history = params.get("include_history", False)
        history_hours = min(params.get("history_hours", 4), 24)

        if not entity_id:
            return {"error": "entity_id is required"}

        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Get the most recent location from card swipes
                result = session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})-[r:SWIPED_CARD]->(z:Zone)
                    RETURN z.zone_id as zone_id,
                           z.name as zone_name,
                           r.timestamp as timestamp,
                           r.direction as direction,
                           'card_swipe' as source
                    ORDER BY r.timestamp DESC
                    LIMIT 1
                """, {"entity_id": entity_id})

                record = result.single()

                if record:
                    timestamp = record["timestamp"]
                    if hasattr(timestamp, "to_native"):
                        timestamp = timestamp.to_native()

                    current_location = {
                        "zone_id": record["zone_id"],
                        "zone_name": record["zone_name"],
                        "last_seen": timestamp.isoformat() if timestamp else None,
                        "direction": record["direction"],
                        "source": record["source"]
                    }
                else:
                    current_location = None

                # Get location history if requested
                location_history = []
                if include_history:
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=history_hours)

                    history_result = session.run("""
                        MATCH (e:Entity {entity_id: $entity_id})-[r:SWIPED_CARD]->(z:Zone)
                        WHERE r.timestamp >= datetime($cutoff)
                        RETURN z.zone_id as zone_id,
                               z.name as zone_name,
                               r.timestamp as timestamp,
                               r.direction as direction
                        ORDER BY r.timestamp DESC
                    """, {"entity_id": entity_id, "cutoff": cutoff.isoformat()})

                    for rec in history_result:
                        ts = rec["timestamp"]
                        if hasattr(ts, "to_native"):
                            ts = ts.to_native()

                        location_history.append({
                            "zone_id": rec["zone_id"],
                            "zone_name": rec["zone_name"],
                            "timestamp": ts.isoformat() if ts else None,
                            "direction": rec["direction"]
                        })

            driver.close()

            response = {
                "entity_id": entity_id,
                "current_location": current_location,
                "status": "found" if current_location else "not_found"
            }

            if include_history:
                response["location_history"] = location_history
                response["history_hours"] = history_hours

            return response

        except Exception as e:
            logger.error(f"Error getting entity location: {str(e)}")
            return {"error": str(e)}

    def _execute_get_zone_activity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_zone_activity tool"""
        zone_id = params.get("zone_id")
        time_range = params.get("time_range", "today")

        if not zone_id:
            return {"error": "zone_id is required"}

        start_time, end_time = self._get_time_range(time_range)

        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Get activity summary
                result = session.run("""
                    MATCH (z:Zone {zone_id: $zone_id})<-[:OCCURRED_IN]-(sa:SpatialActivity)
                    WHERE sa.timestamp >= datetime($start_time)
                    AND sa.timestamp <= datetime($end_time)
                    RETURN sum(sa.entry_count) as total_entries,
                           sum(sa.exit_count) as total_exits,
                           max(sa.entry_count) as peak_entries,
                           avg(sa.entry_count) as avg_entries,
                           sum(sa.unique_visitors) as unique_visitors,
                           z.name as zone_name,
                           z.capacity as capacity
                """, {
                    "zone_id": zone_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat()
                })

                record = result.single()

                if record and record["total_entries"]:
                    activity = {
                        "zone_id": zone_id,
                        "zone_name": record["zone_name"],
                        "capacity": record["capacity"],
                        "total_entries": record["total_entries"] or 0,
                        "total_exits": record["total_exits"] or 0,
                        "net_flow": (record["total_entries"] or 0) - (record["total_exits"] or 0),
                        "peak_entries_per_hour": record["peak_entries"] or 0,
                        "avg_entries_per_hour": round(record["avg_entries"] or 0, 1),
                        "unique_visitors": record["unique_visitors"] or 0,
                        "time_range": time_range
                    }
                else:
                    activity = {
                        "zone_id": zone_id,
                        "message": "No activity data found for this time range",
                        "time_range": time_range
                    }

            driver.close()
            return activity

        except Exception as e:
            logger.error(f"Error getting zone activity: {str(e)}")
            return {"error": str(e)}

    def _execute_get_entity_timeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_entity_timeline tool"""
        entity_id = params.get("entity_id")
        date_str = params.get("date")
        event_types = params.get("event_types", [])

        if not entity_id:
            return {"error": "entity_id is required"}

        try:
            # Parse date or use today
            if date_str:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                target_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            start_time = target_date
            end_time = target_date + timedelta(days=1)

            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            events = []

            with driver.session() as session:
                # Get card swipes
                if not event_types or "card_swipe" in event_types:
                    swipe_result = session.run("""
                        MATCH (e:Entity {entity_id: $entity_id})-[r:SWIPED_CARD]->(z:Zone)
                        WHERE r.timestamp >= datetime($start_time)
                        AND r.timestamp < datetime($end_time)
                        RETURN 'card_swipe' as event_type,
                               r.timestamp as timestamp,
                               z.zone_id as location,
                               z.name as location_name,
                               r.direction as direction
                        ORDER BY r.timestamp
                    """, {
                        "entity_id": entity_id,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    })

                    for rec in swipe_result:
                        ts = rec["timestamp"]
                        if hasattr(ts, "to_native"):
                            ts = ts.to_native()
                        events.append({
                            "event_type": rec["event_type"],
                            "timestamp": ts.isoformat() if ts else None,
                            "location": rec["location"],
                            "location_name": rec["location_name"],
                            "details": {"direction": rec["direction"]}
                        })

                # Get WiFi connections
                if not event_types or "wifi" in event_types:
                    wifi_result = session.run("""
                        MATCH (e:Entity {entity_id: $entity_id})-[r:CONNECTED_TO_WIFI]->(z:Zone)
                        WHERE r.timestamp >= datetime($start_time)
                        AND r.timestamp < datetime($end_time)
                        RETURN 'wifi' as event_type,
                               r.timestamp as timestamp,
                               z.zone_id as location,
                               z.name as location_name,
                               r.ap_id as ap_id
                        ORDER BY r.timestamp
                    """, {
                        "entity_id": entity_id,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    })

                    for rec in wifi_result:
                        ts = rec["timestamp"]
                        if hasattr(ts, "to_native"):
                            ts = ts.to_native()
                        events.append({
                            "event_type": rec["event_type"],
                            "timestamp": ts.isoformat() if ts else None,
                            "location": rec["location"],
                            "location_name": rec["location_name"],
                            "details": {"ap_id": rec["ap_id"]}
                        })

            driver.close()

            # Sort all events by timestamp
            events.sort(key=lambda x: x["timestamp"] or "")

            # Calculate summary
            zones_visited = list(set(e["location"] for e in events if e.get("location")))

            return {
                "entity_id": entity_id,
                "date": target_date.strftime("%Y-%m-%d"),
                "events": events,
                "event_count": len(events),
                "zones_visited": zones_visited,
                "first_seen": events[0]["timestamp"] if events else None,
                "last_seen": events[-1]["timestamp"] if events else None
            }

        except Exception as e:
            logger.error(f"Error getting entity timeline: {str(e)}")
            return {"error": str(e)}

    def _execute_get_entity_risk_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_entity_risk_profile tool - comprehensive security assessment"""
        return {"error": "This tool is disabled pending pipeline migration."}

    def _execute_get_security_violations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_security_violations tool - categorized security violations"""
        return {"error": "This tool is disabled pending pipeline migration."}

    def _execute_find_entities_at_location(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute find_entities_at_location tool - who was at a location at a time"""
        zone_id = params.get("zone_id")
        timestamp_str = params.get("timestamp", "now")
        time_window = params.get("time_window_minutes", 30)

        if not zone_id:
            return {"error": "zone_id is required"}

        try:
            # Parse timestamp
            if timestamp_str == "now":
                target_time = datetime.now(timezone.utc)
            elif "ago" in timestamp_str.lower():
                # Parse "X hours ago" or "X minutes ago"
                parts = timestamp_str.lower().split()
                try:
                    amount = int(parts[0])
                    if "hour" in parts[1]:
                        target_time = datetime.now(timezone.utc) - timedelta(hours=amount)
                    else:
                        target_time = datetime.now(timezone.utc) - timedelta(minutes=amount)
                except:
                    target_time = datetime.now(timezone.utc)
            else:
                try:
                    target_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except:
                    target_time = datetime.now(timezone.utc)

            # Calculate time window
            window_start = target_time - timedelta(minutes=time_window)
            window_end = target_time + timedelta(minutes=time_window)

            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Find entities who swiped into this zone during the time window
                result = session.run("""
                    MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone {zone_id: $zone_id})
                    WHERE r.timestamp >= datetime($window_start)
                    AND r.timestamp <= datetime($window_end)
                    WITH e, r, z
                    ORDER BY r.timestamp DESC
                    WITH e, collect({timestamp: r.timestamp, direction: r.direction})[0] as latest
                    RETURN e.entity_id as entity_id,
                           e.name as name,
                           e.role as role,
                           e.department as department,
                           latest.timestamp as last_seen,
                           latest.direction as last_direction
                    ORDER BY latest.timestamp DESC
                """, {
                    "zone_id": zone_id,
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat()
                })

                entities = []
                for rec in result:
                    ts = rec["last_seen"]
                    if hasattr(ts, "to_native"):
                        ts = ts.to_native()

                    entities.append({
                        "entity_id": rec["entity_id"],
                        "name": rec["name"],
                        "role": rec["role"],
                        "department": rec["department"],
                        "last_seen": ts.isoformat() if ts else None,
                        "direction": rec["last_direction"]
                    })

                # Get zone info
                zone_result = session.run("""
                    MATCH (z:Zone {zone_id: $zone_id})
                    RETURN z.name as name, z.capacity as capacity
                """, {"zone_id": zone_id})

                zone_info = zone_result.single()

            driver.close()

            return {
                "zone_id": zone_id,
                "zone_name": zone_info["name"] if zone_info else zone_id,
                "target_time": target_time.isoformat(),
                "time_window_minutes": time_window,
                "entities_found": len(entities),
                "entities": entities,
                "capacity": zone_info["capacity"] if zone_info else None
            }

        except Exception as e:
            logger.error(f"Error finding entities at location: {str(e)}")
            return {"error": str(e)}

    def _execute_find_missing_entities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute find_missing_entities tool - find inactive people"""
        hours = min(params.get("hours", 12), 168)  # Max 1 week
        role_filter = params.get("role")
        limit = min(params.get("limit", 20), 100)

        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            with driver.session() as session:
                # Build query
                role_clause = "AND e.role = $role" if role_filter else ""

                result = session.run(f"""
                    MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone)
                    WHERE e.role IN ['student', 'staff', 'faculty']
                    {role_clause}
                    WITH e, max(r.timestamp) as last_activity
                    WHERE last_activity < datetime($cutoff)
                    RETURN e.entity_id as entity_id,
                           e.name as name,
                           e.role as role,
                           e.department as department,
                           last_activity,
                           duration.between(last_activity, datetime()).hours as hours_inactive
                    ORDER BY last_activity ASC
                    LIMIT $limit
                """, {
                    "cutoff": cutoff_time.isoformat(),
                    "role": role_filter,
                    "limit": limit
                })

                missing_entities = []
                for rec in result:
                    ts = rec["last_activity"]
                    if hasattr(ts, "to_native"):
                        ts = ts.to_native()

                    missing_entities.append({
                        "entity_id": rec["entity_id"],
                        "name": rec["name"],
                        "role": rec["role"],
                        "department": rec["department"],
                        "last_activity": ts.isoformat() if ts else None,
                        "hours_inactive": rec["hours_inactive"]
                    })

            driver.close()

            # Categorize by urgency
            urgent = [e for e in missing_entities if e.get("hours_inactive", 0) > 48]
            concerning = [e for e in missing_entities if 24 < e.get("hours_inactive", 0) <= 48]
            watch = [e for e in missing_entities if e.get("hours_inactive", 0) <= 24]

            return {
                "missing_entities": missing_entities,
                "count": len(missing_entities),
                "threshold_hours": hours,
                "role_filter": role_filter,
                "summary": {
                    "urgent_48h_plus": len(urgent),
                    "concerning_24_48h": len(concerning),
                    "watch_under_24h": len(watch)
                },
                "recommendations": [
                    "Consider welfare check for entities inactive > 48 hours",
                    "Verify if extended absence is expected (leave, travel)",
                    "Cross-reference with leave management system"
                ] if urgent else ["No immediate concerns - continue monitoring"]
            }

        except Exception as e:
            logger.error(f"Error finding missing entities: {str(e)}")
            return {"error": str(e)}

    def _execute_predict_entity_location(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute predict_entity_location tool - predict where someone will be"""
        entity_id = params.get("entity_id")
        target_time_str = params.get("target_time", "now")

        if not entity_id:
            return {"error": "entity_id is required"}

        try:
            # Parse target time
            now = datetime.now(timezone.utc)

            if target_time_str == "now":
                target_time = now
            elif "in " in target_time_str.lower():
                # Parse "in X hours" or "in X minutes"
                parts = target_time_str.lower().replace("in ", "").split()
                try:
                    amount = int(parts[0])
                    if "hour" in parts[1]:
                        target_time = now + timedelta(hours=amount)
                    else:
                        target_time = now + timedelta(minutes=amount)
                except:
                    target_time = now
            elif ":" in target_time_str:
                # Parse time like "14:00" or "2pm"
                try:
                    time_parts = target_time_str.replace("pm", "").replace("am", "").split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0

                    if "pm" in target_time_str.lower() and hour < 12:
                        hour += 12

                    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except:
                    target_time = now
            else:
                target_time = now

            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            # Get historical events for this entity (last 30 days)
            history_start = now - timedelta(days=30)

            with driver.session() as session:
                # Get entity info
                entity_result = session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})
                    RETURN e.name as name, e.role as role
                """, {"entity_id": entity_id})

                entity_info = entity_result.single()
                if not entity_info:
                    return {"error": f"Entity {entity_id} not found"}

                # Get historical events
                events_result = session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})-[r:SWIPED_CARD]->(z:Zone)
                    WHERE r.timestamp >= datetime($start)
                    RETURN z.zone_id as location,
                           z.name as location_name,
                           r.timestamp as timestamp,
                           r.timestamp.hour as hour,
                           r.timestamp.dayOfWeek as day_of_week
                    ORDER BY r.timestamp
                """, {
                    "entity_id": entity_id,
                    "start": history_start.isoformat()
                })

                events = []
                for rec in events_result:
                    ts = rec["timestamp"]
                    if hasattr(ts, "to_native"):
                        ts = ts.to_native()
                    events.append({
                        "location": rec["location"],
                        "location_name": rec["location_name"],
                        "timestamp": ts.isoformat() if ts else None,
                        "hour": rec["hour"],
                        "day_of_week": rec["day_of_week"]
                    })

            driver.close()

            if not events:
                return {
                    "entity_id": entity_id,
                    "name": entity_info["name"],
                    "prediction": None,
                    "confidence": 0.0,
                    "method": "insufficient_data",
                    "message": "Not enough historical data to make a prediction"
                }

            # PatternDetector removed - return stub prediction
            prediction = {"predicted_location": None, "confidence": 0.0, "method": "removed", "evidence": []}

            return {
                "entity_id": entity_id,
                "name": entity_info["name"],
                "role": entity_info["role"],
                "target_time": target_time.isoformat(),
                "prediction": {
                    "location": prediction.get("predicted_location"),
                    "confidence": prediction.get("confidence"),
                    "method": prediction.get("method"),
                    "evidence": prediction.get("evidence")
                },
                "historical_data_points": len(events),
                "analysis_period": "last 30 days"
            }

        except Exception as e:
            logger.error(f"Error predicting entity location: {str(e)}")
            return {"error": str(e)}

    def _execute_get_zone_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_zone_forecast tool - predict future zone occupancy"""
        return {"error": "Spatial forecasting service removed. Zone data will be available in the new zone management system."}

    def _execute_get_zone_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_zone_history tool - historical occupancy trends"""
        return {"error": "Spatial forecasting service removed. Zone data will be available in the new zone management system."}

    def _execute_get_campus_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_campus_summary tool - overall campus activity"""
        return {"error": "Spatial forecasting service removed. Zone data will be available in the new zone management system."}

    def _execute_detect_routine_patterns(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute detect_routine_patterns tool - analyze entity behavior patterns"""
        entity_id = params.get("entity_id")
        days = min(params.get("days", 14), 30)

        if not entity_id:
            return {"error": "entity_id is required"}

        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            history_start = datetime.now(timezone.utc) - timedelta(days=days)

            with driver.session() as session:
                # Get entity info
                entity_result = session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})
                    RETURN e.name as name, e.role as role, e.department as department
                """, {"entity_id": entity_id})

                entity_info = entity_result.single()
                if not entity_info:
                    return {"error": f"Entity {entity_id} not found"}

                # Get historical events
                events_result = session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})-[r:SWIPED_CARD]->(z:Zone)
                    WHERE r.timestamp >= datetime($start)
                    RETURN z.zone_id as location,
                           z.name as location_name,
                           r.timestamp as timestamp
                    ORDER BY r.timestamp
                """, {
                    "entity_id": entity_id,
                    "start": history_start.isoformat()
                })

                events = []
                for rec in events_result:
                    ts = rec["timestamp"]
                    if hasattr(ts, "to_native"):
                        ts = ts.to_native()
                    events.append({
                        "location": rec["location"],
                        "location_name": rec["location_name"],
                        "timestamp": ts.isoformat() if ts else None
                    })

            driver.close()

            if len(events) < 10:
                return {
                    "entity_id": entity_id,
                    "name": entity_info["name"],
                    "message": "Insufficient data to detect routine patterns",
                    "events_found": len(events),
                    "minimum_required": 10
                }

            # PatternDetector removed - return stub routine analysis
            routine_analysis = {"typical_hours": {}, "routine_strength": 0.0}

            # Format typical hours for readability
            typical_schedule = []
            if routine_analysis.get("typical_hours"):
                for hour, data in sorted(routine_analysis["typical_hours"].items()):
                    typical_schedule.append({
                        "hour": f"{hour}:00",
                        "typical_location": data["location"],
                        "confidence": round(data["confidence"] * 100, 1)
                    })

            return {
                "entity_id": entity_id,
                "name": entity_info["name"],
                "role": entity_info["role"],
                "department": entity_info["department"],
                "analysis_period": f"Last {days} days",
                "events_analyzed": len(events),
                "routine_detected": routine_analysis.get("has_routine", False),
                "routine_strength": f"{routine_analysis.get('routine_strength', 0) * 100:.1f}%",
                "typical_schedule": typical_schedule,
                "common_movement_patterns": routine_analysis.get("common_sequences", []),
                "behavioral_anomalies": routine_analysis.get("anomalies", [])[:5],
                "insights": self._generate_routine_insights(routine_analysis, entity_info)
            }

        except Exception as e:
            logger.error(f"Error detecting routine patterns: {str(e)}")
            return {"error": str(e)}

    def _generate_routine_insights(self, routine_analysis: Dict, entity_info: Dict) -> List[str]:
        """Generate insights from routine analysis"""
        insights = []

        strength = routine_analysis.get("routine_strength", 0)
        if strength > 0.7:
            insights.append("Highly predictable daily routine detected")
        elif strength > 0.4:
            insights.append("Moderately consistent routine detected")
        else:
            insights.append("Irregular schedule with no clear routine")

        sequences = routine_analysis.get("common_sequences", [])
        if sequences:
            insights.append(f"Most common movement: {sequences[0]['sequence']}")

        anomalies = routine_analysis.get("anomalies", [])
        if len(anomalies) > 5:
            insights.append("Multiple behavioral deviations detected - may warrant review")

        return insights

    def _execute_get_anomaly_trends(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_anomaly_trends tool - analyze anomaly patterns over time"""
        return {"error": "This tool is disabled pending pipeline migration."}

    def _execute_get_activity_gaps(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_activity_gaps tool - find gaps in entity's timeline"""
        entity_id = params.get("entity_id")
        min_gap_hours = params.get("min_gap_hours", 2)
        days = min(params.get("days", 7), 30)

        if not entity_id:
            return {"error": "entity_id is required"}

        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            history_start = datetime.now(timezone.utc) - timedelta(days=days)

            with driver.session() as session:
                # Get entity info
                entity_result = session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})
                    RETURN e.name as name, e.role as role
                """, {"entity_id": entity_id})

                entity_info = entity_result.single()
                if not entity_info:
                    return {"error": f"Entity {entity_id} not found"}

                # Get all events ordered by timestamp
                events_result = session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})-[r:SWIPED_CARD]->(z:Zone)
                    WHERE r.timestamp >= datetime($start)
                    RETURN z.zone_id as location,
                           z.name as location_name,
                           r.timestamp as timestamp
                    ORDER BY r.timestamp
                """, {
                    "entity_id": entity_id,
                    "start": history_start.isoformat()
                })

                events = []
                for rec in events_result:
                    ts = rec["timestamp"]
                    if hasattr(ts, "to_native"):
                        ts = ts.to_native()
                    events.append({
                        "location": rec["location"],
                        "location_name": rec["location_name"],
                        "timestamp": ts
                    })

            driver.close()

            if len(events) < 2:
                return {
                    "entity_id": entity_id,
                    "name": entity_info["name"],
                    "message": "Insufficient data to analyze gaps",
                    "events_found": len(events)
                }

            # Find gaps
            gaps = []
            min_gap_seconds = min_gap_hours * 3600

            for i in range(len(events) - 1):
                current_event = events[i]
                next_event = events[i + 1]

                gap_duration = (next_event["timestamp"] - current_event["timestamp"]).total_seconds()

                if gap_duration >= min_gap_seconds:
                    gap_hours = gap_duration / 3600
                    gaps.append({
                        "start_time": current_event["timestamp"].isoformat(),
                        "end_time": next_event["timestamp"].isoformat(),
                        "duration_hours": round(gap_hours, 1),
                        "last_location": current_event["location"],
                        "last_location_name": current_event["location_name"],
                        "next_location": next_event["location"],
                        "next_location_name": next_event["location_name"],
                        "category": self._categorize_gap(gap_hours, current_event["timestamp"])
                    })

            # Sort gaps by duration (longest first)
            gaps.sort(key=lambda x: x["duration_hours"], reverse=True)

            # Calculate statistics
            total_gap_hours = sum(g["duration_hours"] for g in gaps)
            avg_gap = total_gap_hours / len(gaps) if gaps else 0

            return {
                "entity_id": entity_id,
                "name": entity_info["name"],
                "role": entity_info["role"],
                "analysis_period": f"Last {days} days",
                "min_gap_threshold_hours": min_gap_hours,
                "total_events_analyzed": len(events),
                "gaps_found": len(gaps),
                "total_gap_time_hours": round(total_gap_hours, 1),
                "average_gap_hours": round(avg_gap, 1),
                "gaps": gaps[:10],  # Top 10 longest gaps
                "insights": self._generate_gap_insights(gaps, entity_info)
            }

        except Exception as e:
            logger.error(f"Error getting activity gaps: {str(e)}")
            return {"error": str(e)}

    def _categorize_gap(self, gap_hours: float, start_time: datetime) -> str:
        """Categorize a gap based on duration and time of day"""
        start_hour = start_time.hour

        # Overnight gaps (roughly 10pm - 6am)
        if start_hour >= 22 or start_hour < 6:
            if 6 <= gap_hours <= 12:
                return "overnight (normal)"
            elif gap_hours > 12:
                return "extended overnight"

        # Daytime gaps
        if gap_hours < 4:
            return "short break"
        elif gap_hours < 8:
            return "extended absence"
        elif gap_hours < 24:
            return "day-long absence"
        else:
            return "multi-day absence"

    def _generate_gap_insights(self, gaps: List, entity_info: Dict) -> List[str]:
        """Generate insights from activity gaps"""
        insights = []

        if not gaps:
            insights.append("No significant activity gaps detected - consistent presence on campus")
            return insights

        # Check for concerning patterns
        long_gaps = [g for g in gaps if g["duration_hours"] > 24]
        if long_gaps:
            insights.append(f"Found {len(long_gaps)} gaps longer than 24 hours - may indicate extended absences")

        # Check for unusual daytime gaps
        daytime_gaps = [g for g in gaps if "absence" in g.get("category", "")]
        if len(daytime_gaps) > 3:
            insights.append("Multiple extended daytime absences detected")

        # Most common last location before gaps
        last_locations = [g["last_location"] for g in gaps]
        if last_locations:
            from collections import Counter
            common_location = Counter(last_locations).most_common(1)[0]
            insights.append(f"Most common location before gaps: {common_location[0]}")

        return insights

    def _execute_resolve_entity_fuzzy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute resolve_entity_fuzzy tool - fuzzy name matching"""
        name_query = params.get("name", "")
        threshold = params.get("threshold", 0.6)
        limit = min(params.get("limit", 5), 20)

        if not name_query:
            return {"error": "name is required"}

        try:
            from neo4j import GraphDatabase
            from difflib import SequenceMatcher

            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Get all entities with names
                result = session.run("""
                    MATCH (e:Entity)
                    WHERE e.name IS NOT NULL
                    RETURN e.entity_id as entity_id,
                           e.name as name,
                           e.role as role,
                           e.department as department,
                           e.email as email
                """)

                all_entities = [dict(record) for record in result]

            driver.close()

            # Calculate similarity scores
            matches = []
            name_lower = name_query.lower()

            for entity in all_entities:
                entity_name = entity.get("name", "")
                if not entity_name:
                    continue

                entity_name_lower = entity_name.lower()

                # Calculate similarity using multiple methods
                # 1. Sequence matcher (handles typos well)
                seq_ratio = SequenceMatcher(None, name_lower, entity_name_lower).ratio()

                # 2. Substring match bonus
                substring_bonus = 0
                if name_lower in entity_name_lower or entity_name_lower in name_lower:
                    substring_bonus = 0.2

                # 3. Word-level matching (handles partial names)
                name_words = set(name_lower.split())
                entity_words = set(entity_name_lower.split())
                word_overlap = len(name_words & entity_words) / max(len(name_words), 1)
                word_bonus = word_overlap * 0.3

                # Combined score
                final_score = min(1.0, seq_ratio + substring_bonus + word_bonus)

                if final_score >= threshold:
                    matches.append({
                        "entity_id": entity["entity_id"],
                        "name": entity["name"],
                        "role": entity["role"],
                        "department": entity["department"],
                        "email": entity["email"],
                        "similarity_score": round(final_score, 3),
                        "match_type": self._get_match_type(seq_ratio, substring_bonus, word_bonus)
                    })

            # Sort by similarity score
            matches.sort(key=lambda x: x["similarity_score"], reverse=True)
            matches = matches[:limit]

            return {
                "query": name_query,
                "threshold": threshold,
                "matches_found": len(matches),
                "matches": matches,
                "suggestion": self._get_fuzzy_suggestion(matches, name_query)
            }

        except Exception as e:
            logger.error(f"Error resolving entity fuzzy: {str(e)}")
            return {"error": str(e)}

    def _get_match_type(self, seq_ratio: float, substring_bonus: float, word_bonus: float) -> str:
        """Determine the type of match"""
        if seq_ratio > 0.9:
            return "exact"
        elif substring_bonus > 0:
            return "substring"
        elif word_bonus > 0.2:
            return "partial_name"
        else:
            return "similar"

    def _get_fuzzy_suggestion(self, matches: List, query: str) -> str:
        """Generate a suggestion based on matches"""
        if not matches:
            return f"No matches found for '{query}'. Try a different spelling or partial name."
        elif len(matches) == 1 and matches[0]["similarity_score"] > 0.8:
            return f"High confidence match: {matches[0]['name']}"
        elif len(matches) > 1:
            return f"Multiple possible matches found. Top match: {matches[0]['name']} ({matches[0]['similarity_score']:.0%} confidence)"
        else:
            return f"Possible match: {matches[0]['name']} - please verify"

    def _execute_get_zone_connections(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_zone_connections tool - find connected zones"""
        return {"error": "Spatial forecasting service removed. Zone data will be available in the new zone management system."}

