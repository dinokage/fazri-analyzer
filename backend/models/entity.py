# backend/app/models/entity.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from services.confidence_scorer import ConfidenceScorer

class Identifier(BaseModel):
    """Single identifier with metadata"""
    type: str  # e.g., "student_id", "card_id", "email"
    value: str
    source: str  # Which dataset it came from
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    first_seen: datetime
    last_seen: datetime

class Entity(BaseModel):
    """Unified entity representing a person (student/staff)"""
    entity_id: str  # Primary entity_id from profiles
    identifiers: List[Identifier] = []
    
    # Core attributes
    name: Optional[str] = None
    email: Optional[str] = None
    entity_type: Optional[str] = None  # "student", "staff", or "unknown"
    department: Optional[str] = None
    
    # Linking metadata
    linked_entity_ids: List[str] = []  # Other entity_ids this might be
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Provenance
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def recalculate_confidence(self):
        """Recalculate confidence score based on identifiers"""
        identifier_dicts = [
            {
                'type': id.type,
                'source': id.source,
                'confidence': id.confidence
            }
            for id in self.identifiers
        ]
        self.confidence_score = ConfidenceScorer.calculate_entity_confidence(identifier_dicts)
        self.updated_at = datetime.now()
    
    def get_provenance(self) -> Dict[str, List[str]]:
        """Get provenance information - which sources contributed which identifiers"""
        provenance = {}
        for identifier in self.identifiers:
            if identifier.source not in provenance:
                provenance[identifier.source] = []
            provenance[identifier.source].append(f"{identifier.type}:{identifier.value}")
        return provenance
    
    def get_identifier(self, id_type: str) -> Optional[Identifier]:
        """Get identifier by type"""
        for identifier in self.identifiers:
            if identifier.type == id_type:
                return identifier
        return None
    
    def add_identifier(self, identifier: Identifier):
        """Add new identifier if not exists"""
        existing = self.get_identifier(identifier.type)
        if not existing:
            self.identifiers.append(identifier)
            self.updated_at = datetime.now()
        elif existing.value != identifier.value:
            # Conflict - lower confidence
            self.confidence_score *= 0.9

class ActivityEvent(BaseModel):
    """Single activity event from any source"""
    event_id: str
    entity_id: Optional[str] = None  # Resolved entity
    
    # Event details
    event_type: str  # "swipe", "wifi", "library", "booking", "cctv"
    timestamp: datetime
    location: Optional[str] = None
    
    # Source data
    source_dataset: str
    source_identifiers: Dict[str, str] = {}  # e.g., {"card_id": "C12345"}
    
    # Additional metadata
    metadata: Dict[str, Any] = {}
    confidence: float = 1.0

class Timeline(BaseModel):
    """Chronological timeline for an entity"""
    entity_id: str
    events: List[ActivityEvent] = []
    start_time: datetime
    end_time: datetime
    
    # Summary stats
    total_events: int = 0
    event_types: Dict[str, int] = {}
    locations_visited: List[str] = []
    
    # Gaps and predictions
    gaps: List[Dict[str, Any]] = []  # Time periods with no data
    predictions: List[Dict[str, Any]] = []  # Predicted locations during gaps