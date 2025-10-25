# backend/app/services/entity_resolver.py
import pandas as pd
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import Levenshtein  # pip install python-Levenshtein

from models.entity import Entity, Identifier, ActivityEvent
from services.confidence_scorer import ConfidenceScorer

class EntityResolver:
    """Core entity resolution engine"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.entities: Dict[str, Entity] = {}
        self.identifier_index: Dict[str, List[str]] = defaultdict(list)
        
        # Load datasets
        self._load_datasets()
        
    def _load_datasets(self):
        """Load all CSV datasets"""
        self.profiles = pd.read_csv(self.data_dir / "student_staff_profiles.csv")
        self.swipes = pd.read_csv(self.data_dir / "campus_card_swipes_augmented.csv")
        self.wifi = pd.read_csv(self.data_dir / "wifi_associations_logs_augmented.csv")
        self.library = pd.read_csv(self.data_dir / "library_checkouts_augmented.csv")
        self.bookings = pd.read_csv(self.data_dir / "lab_bookings_augmented.csv")
        self.helpdesk = pd.read_csv(self.data_dir / "helpdesk_augmented.csv")
        self.cctv = pd.read_csv(self.data_dir / "cctv_frames_augmented.csv")
        self.face_embeddings = pd.read_csv(self.data_dir / "face_embeddings.csv")
        
        print(f"✅ Loaded {len(self.profiles)} profiles")
        
    def build_entity_graph(self):
        """Build complete entity graph from profiles"""
        print("\n🔧 Building entity graph from profiles...")
        
        for idx, row in self.profiles.iterrows():
            entity_id = str(row['entity_id'])
            
            # Create entity
            entity = Entity(
                entity_id=entity_id,
                name=row.get('name'),
                role=row.get('role'),
                email=row.get('email'),
                entity_type=self._determine_entity_type(row),
                department=row.get('department')
            )
            
            # Add all identifiers from profile
            identifier_types = [
                'entity_id', 'student_id', 'staff_id', 'email', 
                'card_id', 'device_hash', 'face_id'
            ]
            
            for id_type in identifier_types:
                if id_type in row and pd.notna(row[id_type]):
                    identifier = Identifier(
                        type=id_type,
                        value=str(row[id_type]),
                        source="profiles",
                        confidence=1.0,
                        first_seen=datetime.now(),
                        last_seen=datetime.now()
                    )
                    entity.add_identifier(identifier)
                    
                    # Index for fast lookup
                    self.identifier_index[f"{id_type}:{row[id_type]}"].append(entity_id)
            
            # Calculate confidence score
            entity.recalculate_confidence()
            
            self.entities[entity_id] = entity
        
        print(f"✅ Created {len(self.entities)} entities")
        print(f"✅ Indexed {len(self.identifier_index)} identifiers")
    
    def _determine_entity_type(self, row: pd.Series) -> str:
        """Determine if entity is student or staff"""
        if row.role == 'student' and pd.notna(row.get('student_id')):
            return "student"
        elif row.role == 'staff' and pd.notna(row.get('staff_id')):
            return "staff"
        elif row.role == "faculty" and pd.notna(row.get('faculty_id')):
            return "faculty"
        return "unknown"
    
    def resolve_by_identifier(
        self, 
        identifier_type: str, 
        identifier_value: str
    ) -> Optional[Entity]:
        """Resolve entity by any identifier - DIRECT MATCH"""
        lookup_key = f"{identifier_type}:{identifier_value}"
        entity_ids = self.identifier_index.get(lookup_key, [])
        
        if entity_ids:
            return self.entities[entity_ids[0]]  # Return first match
        
        return None
    
    def resolve_by_fuzzy_name(
        self, 
        name: str, 
        threshold: float = 0.85
    ) -> List[Tuple[Entity, float]]:
        """Fuzzy name matching using Levenshtein distance"""
        matches = []
        
        for entity in self.entities.values():
            if entity.name:
                # Calculate similarity ratio
                ratio = Levenshtein.ratio(name.lower(), entity.name.lower())
                
                if ratio >= threshold:
                    matches.append((entity, ratio))
        
        # Sort by similarity descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def resolve_transitive(
        self, 
        entity_id: str
    ) -> List[Entity]:
        """Find all entities linked through shared identifiers"""
        if entity_id not in self.entities:
            return []
        
        entity = self.entities[entity_id]
        linked_entities = set()
        
        # For each identifier, find other entities with same identifier
        for identifier in entity.identifiers:
            lookup_key = f"{identifier.type}:{identifier.value}"
            related_entity_ids = self.identifier_index.get(lookup_key, [])
            
            for related_id in related_entity_ids:
                if related_id != entity_id:
                    linked_entities.add(related_id)
        
        return [self.entities[eid] for eid in linked_entities]
    
    def get_all_identifiers_for_entity(
        self, 
        entity_id: str
    ) -> Dict[str, List[str]]:
        """Get all known identifiers for an entity (including transitive)"""
        if entity_id not in self.entities:
            return {}
        
        entity = self.entities[entity_id]
        all_identifiers = defaultdict(list)
        
        # Direct identifiers
        for identifier in entity.identifiers:
            all_identifiers[identifier.type].append(identifier.value)
        
        # Transitive identifiers
        linked = self.resolve_transitive(entity_id)
        for linked_entity in linked:
            for identifier in linked_entity.identifiers:
                if identifier.value not in all_identifiers[identifier.type]:
                    all_identifiers[identifier.type].append(identifier.value)
        
        return dict(all_identifiers)

# Initialize resolver (will be used in API)
resolver = None

def get_resolver() -> EntityResolver:
    """Get or create resolver instance"""
    global resolver
    if resolver is None:
        data_dir = Path(__file__).parent.parent / "augmented"
        resolver = EntityResolver(data_dir)
        resolver.build_entity_graph()
    return resolver