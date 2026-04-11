from typing import Dict, List
from datetime import datetime, timedelta

class ConfidenceScorer:
    """Calculate confidence scores for entity resolution and predictions"""
    
    # Weights for different identifier types
    IDENTIFIER_WEIGHTS = {
        'student_id': 1.0,      # Highest confidence
        'staff_id': 1.0,
        'email': 0.95,
        'card_id': 0.9,
        'face_id': 0.85,
        'device_hash': 0.7,     # Devices can be shared
        'name': 0.6             # Names can be similar
    }
    
    # Weights for different data sources
    SOURCE_WEIGHTS = {
        'profiles': 1.0,        # Official records
        'swipes': 0.9,
        'library': 0.85,
        'bookings': 0.85,
        'wifi': 0.75,           # Less reliable
        'cctv': 0.8,
        'helpdesk': 0.7
    }
    
    @staticmethod
    def calculate_entity_confidence(identifiers: List[Dict]) -> float:
        """
        Calculate overall confidence for an entity based on its identifiers
        
        Factors:
        - Number of different identifier types
        - Quality of identifiers
        - Source reliability
        """
        if not identifiers:
            return 0.0
        
        # Base confidence from identifier types
        identifier_scores = []
        for identifier in identifiers:
            id_type = identifier.get('type', 'unknown')
            source = identifier.get('source', 'unknown')
            
            id_weight = ConfidenceScorer.IDENTIFIER_WEIGHTS.get(id_type, 0.5)
            source_weight = ConfidenceScorer.SOURCE_WEIGHTS.get(source, 0.5)
            
            # Combined score
            score = (id_weight * 0.7) + (source_weight * 0.3)
            identifier_scores.append(score)
        
        # Average score, with bonus for multiple identifiers
        avg_score = sum(identifier_scores) / len(identifier_scores)
        diversity_bonus = min(0.2, len(set([i['type'] for i in identifiers])) * 0.05)
        
        final_confidence = min(1.0, avg_score + diversity_bonus)
        return round(final_confidence, 2)
    
    @staticmethod
    def calculate_link_confidence(
        entity1_ids: List[Dict], 
        entity2_ids: List[Dict], 
        shared_identifiers: List[str]
    ) -> float:
        """
        Calculate confidence that two entities are the same person
        
        Factors:
        - Number of shared identifiers
        - Type of shared identifiers
        - Quality of match
        """
        if not shared_identifiers:
            return 0.0
        
        # Base confidence from shared identifiers
        shared_scores = []
        for shared_id in shared_identifiers:
            id_type = shared_id.split(':')[0] if ':' in shared_id else 'unknown'
            weight = ConfidenceScorer.IDENTIFIER_WEIGHTS.get(id_type, 0.5)
            shared_scores.append(weight)
        
        # Calculate final confidence
        base_confidence = max(shared_scores)  # Highest quality match
        
        # Bonus for multiple shared identifiers
        multi_match_bonus = min(0.2, (len(shared_scores) - 1) * 0.1)
        
        final_confidence = min(1.0, base_confidence + multi_match_bonus)
        return round(final_confidence, 2)
    
    @staticmethod
    def calculate_event_confidence(
        event_type: str,
        source_dataset: str,
        timestamp: datetime,
        has_location: bool = True
    ) -> float:
        """
        Calculate confidence for an activity event
        
        Factors:
        - Event type reliability
        - Source reliability
        - Recency
        - Location availability
        """
        # Base confidence from source
        base_confidence = ConfidenceScorer.SOURCE_WEIGHTS.get(source_dataset, 0.5)
        
        # Recency factor (events within 24 hours get bonus)
        time_diff = datetime.now() - timestamp
        if time_diff < timedelta(hours=24):
            recency_bonus = 0.1
        elif time_diff < timedelta(days=7):
            recency_bonus = 0.05
        else:
            recency_bonus = 0.0
        
        # Location bonus
        location_bonus = 0.1 if has_location else 0.0
        
        final_confidence = min(1.0, base_confidence + recency_bonus + location_bonus)
        return round(final_confidence, 2)