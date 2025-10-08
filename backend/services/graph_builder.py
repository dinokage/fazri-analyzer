# backend/app/services/graph_builder.py
from neo4j import GraphDatabase
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime
from pathlib import Path

from config import settings
from services.entity_resolver import EntityResolver

class CampusGraphBuilder:
    """Build and manage Neo4j graph database"""
    
    def __init__(self, uri: str, user: str, password: str):
        auth = (user, password)
        self.driver = GraphDatabase.driver(uri, auth=auth)
        self._verify_connectivity()
    
    def close(self):
        self.driver.close()
    
    def _verify_connectivity(self):
        """Test Neo4j connection"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as num")
                result.single()
                print("✅ Neo4j connection successful")
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
            raise
    
    def clear_database(self):
        """Clear all nodes and relationships (use with caution!)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Database cleared")
    
    @staticmethod
    def format_neo4j_datetime(timestamp_str: str) -> str:
        """Convert pandas timestamp to Neo4j-compatible datetime string"""
        try:
            # Parse various timestamp formats
            if isinstance(timestamp_str, pd.Timestamp):
                dt = timestamp_str
            else:
                dt = pd.to_datetime(timestamp_str)
            
            # Format as ISO 8601 which Neo4j understands
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            print(f"Warning: Could not parse timestamp {timestamp_str}: {e}")
            return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')   
    def create_indexes(self):
        """Create indexes for faster lookups"""
        indexes = [
            "CREATE INDEX entity_id_index IF NOT EXISTS FOR (e:Entity) ON (e.entity_id)",
            "CREATE INDEX card_id_index IF NOT EXISTS FOR (e:Entity) ON (e.card_id)",
            "CREATE INDEX device_hash_index IF NOT EXISTS FOR (e:Entity) ON (e.device_hash)",
            "CREATE INDEX face_id_index IF NOT EXISTS FOR (e:Entity) ON (e.face_id)",
            "CREATE INDEX email_index IF NOT EXISTS FOR (e:Entity) ON (e.email)",
            "CREATE INDEX timestamp_index IF NOT EXISTS FOR (e:Event) ON (e.timestamp)",
        ]
        
        with self.driver.session() as session:
            for index_query in indexes:
                session.run(index_query)
        
        print("✅ Created indexes")
    
    def create_entity_node(self, entity_data: Dict):
        """Create or update entity node"""
        query = """
        MERGE (e:Entity {entity_id: $entity_id})
        SET e.name = $name,
            e.email = $email,
            e.entity_type = $entity_type,
            e.department = $department,
            e.role = $role,
            e.card_id = $card_id,
            e.device_hash = $device_hash,
            e.face_id = $face_id,
            e.student_id = $student_id,
            e.staff_id = $staff_id,
            e.updated_at = datetime()
        RETURN e
        """
        
        with self.driver.session() as session:
            result = session.run(query, **entity_data)
            return result.single()
    
    def create_event_node(self, event_data: Dict):
        """Create event node and link to entity"""
        query = """
        MATCH (e:Entity {entity_id: $entity_id})
        CREATE (ev:Event {
            event_id: $event_id,
            event_type: $event_type,
            timestamp: datetime($timestamp),
            location: $location,
            source_dataset: $source_dataset
        })
        CREATE (e)-[:PERFORMED]->(ev)
        RETURN ev
        """
        
        with self.driver.session() as session:
            result = session.run(query, **event_data)
            return result.single()
    
    def create_location_node(self, location_id: str, location_type: str = "Unknown"):
        """Create location node"""
        query = """
        MERGE (l:Location {location_id: $location_id})
        SET l.type = $location_type
        RETURN l
        """
        
        with self.driver.session() as session:
            result = session.run(query, location_id=location_id, location_type=location_type)
            return result.single()
    
    def link_event_to_location(self, event_id: str, location_id: str):
        """Create relationship between event and location"""
        query = """
        MATCH (ev:Event {event_id: $event_id})
        MATCH (l:Location {location_id: $location_id})
        MERGE (ev)-[:AT_LOCATION]->(l)
        RETURN ev, l
        """
        
        with self.driver.session() as session:
            result = session.run(query, event_id=event_id, location_id=location_id)
            return result.single()
    
    def create_same_as_relationship(self, entity_id1: str, entity_id2: str, confidence: float):
        """Create SAME_AS relationship between potentially duplicate entities"""
        query = """
        MATCH (e1:Entity {entity_id: $entity_id1})
        MATCH (e2:Entity {entity_id: $entity_id2})
        MERGE (e1)-[r:SAME_AS {confidence: $confidence}]->(e2)
        RETURN r
        """
        
        with self.driver.session() as session:
            result = session.run(query, entity_id1=entity_id1, entity_id2=entity_id2, confidence=confidence)
            return result.single()
    
    def build_from_resolver(self, resolver: EntityResolver):
        """Build complete graph from EntityResolver"""
        print("\n🔧 Building Neo4j graph from resolver...")
        
        # Create entity nodes
        print("Creating entity nodes...")
        for entity_id, entity in resolver.entities.items():
            entity_data = {
                'entity_id': entity.entity_id,
                'name': entity.name,
                'email': entity.email,
                'entity_type': entity.entity_type,
                'department': entity.department,
                'role': None,  # Will be enriched from profiles later
                'card_id': None,
                'device_hash': None,
                'face_id': None,
                'student_id': None,
                'staff_id': None
            }
            
            # Extract identifiers from entity
            for identifier in entity.identifiers:
                if identifier.type in entity_data:
                    entity_data[identifier.type] = identifier.value
            
            self.create_entity_node(entity_data)
        
        print(f"✅ Created {len(resolver.entities)} entity nodes")
        
        # Create relationships for linked entities
        print("Creating SAME_AS relationships...")
        relationship_count = 0
        processed_pairs = set()  # Avoid duplicate relationships
        
        for entity_id, entity in resolver.entities.items():
            linked = resolver.resolve_transitive(entity_id)
            for linked_entity in linked:
                # Create unique pair key to avoid duplicates
                pair = tuple(sorted([entity_id, linked_entity.entity_id]))
                
                if pair not in processed_pairs:
                    self.create_same_as_relationship(entity_id, linked_entity.entity_id, 0.8)
                    processed_pairs.add(pair)
                    relationship_count += 1
        
        print(f"✅ Created {relationship_count} SAME_AS relationships")
    
    def ingest_swipe_events(self, swipes_df: pd.DataFrame):
        """Ingest card swipe events"""
        print("\n📥 Ingesting swipe events...")
        
        # Convert timestamp column once
        swipes_df = swipes_df.copy()
        swipes_df['timestamp'] = pd.to_datetime(swipes_df['timestamp'])
        
        ingested = 0
        for idx, row in swipes_df.iterrows():
            try:
                # Find entity by card_id
                query_entity = """
                MATCH (e:Entity {card_id: $card_id})
                RETURN e.entity_id as entity_id
                LIMIT 1
                """
                
                with self.driver.session() as session:
                    result = session.run(query_entity, card_id=str(row['card_id']))
                    record = result.single()
                    
                    if record:
                        entity_id = record['entity_id']
                        
                        # Create event with formatted timestamp
                        event_data = {
                            'entity_id': entity_id,
                            'event_id': f"SWIPE_{idx}",
                            'event_type': 'swipe',
                            'timestamp': self.format_neo4j_datetime(row['timestamp']),
                            'location': str(row['location_id']),
                            'source_dataset': 'swipes'
                        }
                        
                        self.create_event_node(event_data)
                        
                        # Create location node and link
                        self.create_location_node(str(row['location_id']), 'swipe_location')
                        self.link_event_to_location(f"SWIPE_{idx}", str(row['location_id']))
                        
                        ingested += 1
            except Exception as e:
                if idx % 100 == 0:  # Only print occasional errors
                    print(f"Warning at row {idx}: {str(e)[:100]}")
                continue
        
        print(f"✅ Ingested {ingested} swipe events")
    
    def ingest_wifi_events(self, wifi_df: pd.DataFrame):
        """Ingest Wi-Fi connection events"""
        print("\n📥 Ingesting Wi-Fi events...")
        
        # Convert timestamp column once
        wifi_df = wifi_df.copy()
        wifi_df['timestamp'] = pd.to_datetime(wifi_df['timestamp'])
        
        ingested = 0
        for idx, row in wifi_df.iterrows():
            try:
                # Find entity by device_hash
                query_entity = """
                MATCH (e:Entity {device_hash: $device_hash})
                RETURN e.entity_id as entity_id
                LIMIT 1
                """
                
                with self.driver.session() as session:
                    result = session.run(query_entity, device_hash=str(row['device_hash']))
                    record = result.single()
                    
                    if record:
                        entity_id = record['entity_id']
                        
                        # Create event with formatted timestamp
                        event_data = {
                            'entity_id': entity_id,
                            'event_id': f"WIFI_{idx}",
                            'event_type': 'wifi',
                            'timestamp': self.format_neo4j_datetime(row['timestamp']),
                            'location': str(row['ap_id']),
                            'source_dataset': 'wifi'
                        }
                        
                        self.create_event_node(event_data)
                        
                        # Create location node (access point) and link
                        self.create_location_node(str(row['ap_id']), 'access_point')
                        self.link_event_to_location(f"WIFI_{idx}", str(row['ap_id']))
                        
                        ingested += 1
            except Exception as e:
                if idx % 100 == 0:
                    print(f"Warning at row {idx}: {str(e)[:100]}")
                continue
        
        print(f"✅ Ingested {ingested} Wi-Fi events")
    
    def ingest_library_events(self, library_df: pd.DataFrame):
        """Ingest library checkout events"""
        print("\n📥 Ingesting library events...")
        
        # Library uses 'timestamp' column
        library_df = library_df.copy()
        library_df['timestamp'] = pd.to_datetime(library_df['timestamp'])
        
        ingested = 0
        errors = 0
        
        for idx, row in library_df.iterrows():
            try:
                # Check if entity exists
                event_data = {
                    'entity_id': str(row['entity_id']),
                    'event_id': str(row['checkout_id']),  # Use actual checkout_id
                    'event_type': 'library_checkout',
                    'timestamp': self.format_neo4j_datetime(row['timestamp']),
                    'location': 'Library',
                    'source_dataset': 'library'
                }
                
                self.create_event_node(event_data)
                ingested += 1
                
                # Progress indicator
                if (idx + 1) % 200 == 0:
                    print(f"   Progress: {idx + 1} rows processed, {ingested} ingested, {errors} errors")
                    
            except Exception as e:
                errors += 1
                if errors == 1:  # Print first error for debugging
                    print(f"   Sample error: {str(e)[:150]}")
                continue
        
        print(f"✅ Ingested {ingested} library events ({errors} errors)")
    
    def ingest_booking_events(self, bookings_df: pd.DataFrame):
        """Ingest room booking events"""
        print("\n📥 Ingesting booking events...")
        
        # Bookings use 'start_time' column
        bookings_df = bookings_df.copy()
        
        # Parse the date format: "9/5/2025 16:46"
        bookings_df['start_time'] = pd.to_datetime(bookings_df['start_time'], format='ISO8601')
        
        ingested = 0
        errors = 0
        
        for idx, row in bookings_df.iterrows():
            try:
                event_data = {
                    'entity_id': str(row['entity_id']),
                    'event_id': str(row['booking_id']),  # Use actual booking_id
                    'event_type': 'room_booking',
                    'timestamp': self.format_neo4j_datetime(row['start_time']),
                    'location': str(row['room_id']),
                    'source_dataset': 'bookings'
                }
                
                self.create_event_node(event_data)
                self.create_location_node(str(row['room_id']), 'room')
                self.link_event_to_location(str(row['booking_id']), str(row['room_id']))
                ingested += 1
                
                # Progress indicator
                if (idx + 1) % 200 == 0:
                    print(f"   Progress: {idx + 1} rows processed, {ingested} ingested, {errors} errors")
                    
            except Exception as e:
                errors += 1
                if errors == 1:  # Print first error for debugging
                    print(f"   Sample error: {str(e)[:150]}")
                continue
        
        print(f"✅ Ingested {ingested} booking events ({errors} errors)")

    def ingest_helpdesk_events(self, helpdesk_df: pd.DataFrame):
        """Ingest helpdesk ticket events"""
        print("\n📥 Ingesting helpdesk events...")
        
        # Convert timestamp
        helpdesk_df = helpdesk_df.copy()
        helpdesk_df['timestamp'] = pd.to_datetime(helpdesk_df['timestamp'])
        
        ingested = 0
        errors = 0
        
        for idx, row in helpdesk_df.iterrows():
            try:
                event_data = {
                    'entity_id': str(row['entity_id']),
                    'event_id': str(row['note_id']),
                    'event_type': 'helpdesk_ticket',
                    'timestamp': self.format_neo4j_datetime(row['timestamp']),
                    'location': 'Helpdesk',
                    'source_dataset': 'helpdesk'
                }
                
                # Create event with additional metadata
                query = """
                MATCH (e:Entity {entity_id: $entity_id})
                CREATE (ev:Event {
                    event_id: $event_id,
                    event_type: $event_type,
                    timestamp: datetime($timestamp),
                    location: $location,
                    source_dataset: $source_dataset,
                    ticket_category: $category,
                    notes_preview: $notes_preview
                })
                CREATE (e)-[:PERFORMED]->(ev)
                RETURN ev
                """

                # Get first 100 chars of text for preview
                notes_preview = str(row['text'])[:100] if pd.notna(row['text']) else "No text"

                with self.driver.session() as session:
                    session.run(query, 
                        entity_id=event_data['entity_id'],
                        event_id=event_data['event_id'],
                        event_type=event_data['event_type'],
                        timestamp=event_data['timestamp'],
                        location=event_data['location'],
                        source_dataset=event_data['source_dataset'],
                        category=str(row['category']) if 'category' in row else 'General',
                        notes_preview=notes_preview
                    )
                
                ingested += 1
                
                # Progress indicator
                if (idx + 1) % 200 == 0:
                    print(f"   Progress: {idx + 1} rows processed, {ingested} ingested, {errors} errors")
                    
            except Exception as e:
                errors += 1
                if errors == 1:
                    print(f"   Sample error: {str(e)[:150]}")
                continue
        
        print(f"✅ Ingested {ingested} helpdesk events ({errors} errors)")

    def ingest_cctv_events(self, cctv_df: pd.DataFrame):
        """Ingest CCTV sighting events"""
        print("\n📥 Ingesting CCTV events...")
        
        # Convert timestamp
        cctv_df = cctv_df.copy()
        cctv_df['timestamp'] = pd.to_datetime(cctv_df['timestamp'])
        
        ingested = 0
        errors = 0
        
        for idx, row in cctv_df.iterrows():
            try:
                # Find entity by face_id
                query_entity = """
                MATCH (e:Entity {face_id: $face_id})
                RETURN e.entity_id as entity_id
                LIMIT 1
                """
                
                with self.driver.session() as session:
                    result = session.run(query_entity, face_id=str(row['face_id']))
                    record = result.single()
                    
                    if record:
                        entity_id = record['entity_id']
                        
                        # Create event
                        event_data = {
                            'entity_id': entity_id,
                            'event_id': str(row['frame_id']),  # Use image_id as event_id
                            'event_type': 'cctv_sighting',
                            'timestamp': self.format_neo4j_datetime(row['timestamp']),
                            'location': str(row['location_id']),
                            'source_dataset': 'cctv'
                        }
                        
                        self.create_event_node(event_data)
                        
                        # Create location node (camera) and link
                        self.create_location_node(str(row['location_id']), 'cctv_camera')
                        self.link_event_to_location(str(row['frame_id']), str(row['location_id']))

                        ingested += 1
                        
                        # Progress indicator
                        if (idx + 1) % 200 == 0:
                            print(f"   Progress: {idx + 1} rows processed, {ingested} ingested, {errors} errors")
            except Exception as e:
                errors += 1
                if errors == 1:
                    print(f"   Sample error: {str(e)[:150]}")
                continue
        
        print(f"✅ Ingested {ingested} CCTV events ({errors} errors - likely unmapped face_ids)")
    
    
    def create_profile_metadata(self, profiles_df: pd.DataFrame):
        """Add additional profile metadata to entity nodes"""
        print("\n📥 Enriching entity nodes with profile metadata...")
        
        query = """
        UNWIND $profiles AS profile
        MATCH (e:Entity {entity_id: profile.entity_id})
        SET e.role = profile.role,
            e.department = profile.department
        RETURN count(e) as updated
        """
        
        profiles_list = []
        for idx, row in profiles_df.iterrows():
            profile = {
                'entity_id': str(row['entity_id']),
                'role': str(row['role']) if pd.notna(row.get('role')) else None,
                'department': str(row['department']) if pd.notna(row.get('department')) else None
            }
            profiles_list.append(profile)
        
        try:
            with self.driver.session() as session:
                result = session.run(query, profiles=profiles_list)
                record = result.single()
                count = record['updated'] if record else 0
                print(f"✅ Enriched {count} entity nodes with role and department metadata")
        except Exception as e:
            print(f"❌ Error enriching profiles: {str(e)[:150]}")

    def get_entity_timeline(self, entity_id: str, start_date: str = None, end_date: str = None):
        """Get chronological timeline of events for entity"""
        query = """
        MATCH (e:Entity {entity_id: $entity_id})-[:PERFORMED]->(ev:Event)
        OPTIONAL MATCH (ev)-[:AT_LOCATION]->(l:Location)
        WHERE ($start_date IS NULL OR ev.timestamp >= datetime($start_date))
        AND ($end_date IS NULL OR ev.timestamp <= datetime($end_date))
        RETURN ev.event_id as event_id,
            ev.event_type as event_type,
            ev.timestamp as timestamp,
            ev.location as location,
            l.location_id as location_id,
            l.type as location_type
        ORDER BY ev.timestamp ASC
        """
        
        with self.driver.session() as session:
            result = session.run(query, entity_id=entity_id, start_date=start_date, end_date=end_date)
            events = []
            for record in result:
                event_dict = dict(record)
                # Convert Neo4j datetime to ISO string
                if event_dict.get('timestamp'):
                    event_dict['timestamp'] = event_dict['timestamp'].isoformat()
                events.append(event_dict)
            return events
    
    def find_entities_at_location(self, location_id: str, timestamp: str):
        """Find all entities at a location at a specific time"""
        query = """
        MATCH (e:Entity)-[:PERFORMED]->(ev:Event)-[:AT_LOCATION]->(l:Location {location_id: $location_id})
        WHERE ev.timestamp <= datetime($timestamp)
        WITH e, ev
        ORDER BY ev.timestamp DESC
        WITH e, collect(ev)[0] as latest_event
        WHERE latest_event.location = $location_id
        RETURN e.entity_id as entity_id,
               e.name as name,
               latest_event.timestamp as last_seen
        """
        
        with self.driver.session() as session:
            result = session.run(query, location_id=location_id, timestamp=timestamp)
            return [dict(record) for record in result]
    
    def find_missing_entities(self, hours: int = 12):
        """Find entities with no activity in last N hours"""
        query = """
        MATCH (e:Entity)-[:PERFORMED]->(ev:Event)
        WITH e, max(ev.timestamp) as last_seen
        WHERE last_seen < datetime() - duration({hours: $hours})
        RETURN e.entity_id as entity_id,
               e.name as name,
               e.entity_type as entity_type,
               last_seen
        ORDER BY last_seen DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, hours=hours)
            return [dict(record) for record in result]

# Global instance
graph_builder = None

def get_graph_builder() -> CampusGraphBuilder:
    """Get or create graph builder instance"""
    global graph_builder
    if graph_builder is None:
        graph_builder = CampusGraphBuilder(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        graph_builder.create_indexes()
    return graph_builder