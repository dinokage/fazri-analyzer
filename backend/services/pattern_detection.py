# backend/app/services/pattern_detector.py
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import pandas as pd

class PatternDetector:
    """Detect patterns in entity activity"""
    
    @staticmethod
    def detect_routine(events: List[Dict], days: int = 7) -> Dict:
        """
        Detect daily routine patterns
        
        Returns:
        - Typical locations by time of day
        - Regular activity sequences
        - Anomalies
        """
        if not events:
            return {'has_routine': False, 'message': 'Insufficient data'}
        
        df = pd.DataFrame(events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        # Group by hour to find typical locations
        hourly_patterns = defaultdict(Counter)
        
        for _, row in df.iterrows():
            hour = row['hour']
            location = row['location']
            hourly_patterns[hour][location] += 1
        
        # Build routine
        routine = {}
        for hour in range(24):
            if hour in hourly_patterns:
                most_common = hourly_patterns[hour].most_common(1)[0]
                total_at_hour = sum(hourly_patterns[hour].values())
                
                # Only include if appears regularly (>50% of time)
                if most_common[1] / total_at_hour > 0.5:
                    routine[hour] = {
                        'location': most_common[0],
                        'frequency': most_common[1],
                        'confidence': most_common[1] / total_at_hour
                    }
        
        # Detect sequences (common transitions)
        sequences = PatternDetector._detect_sequences(df)
        
        # Detect anomalies
        anomalies = PatternDetector._detect_anomalies(df, hourly_patterns)
        
        return {
            'has_routine': len(routine) > 0,
            'typical_hours': routine,
            'common_sequences': sequences,
            'anomalies': anomalies,
            'routine_strength': len(routine) / 24  # How predictable they are
        }
    
    @staticmethod
    def _detect_sequences(df: pd.DataFrame, min_occurrences: int = 3) -> List[Dict]:
        """Detect common location sequences (A -> B -> C)"""
        sequences = Counter()
        
        # Look for 2-location sequences
        for i in range(len(df) - 1):
            loc1 = df.iloc[i]['location']
            loc2 = df.iloc[i + 1]['location']
            
            if loc1 != loc2:  # Skip same location
                sequences[(loc1, loc2)] += 1
        
        # Filter by minimum occurrences
        common_sequences = [
            {
                'sequence': f"{seq[0]} → {seq[1]}",
                'count': count,
                'description': f"Commonly moves from {seq[0]} to {seq[1]}"
            }
            for seq, count in sequences.most_common(5)
            if count >= min_occurrences
        ]
        
        return common_sequences
    
    @staticmethod
    def _detect_anomalies(df: pd.DataFrame, hourly_patterns: Dict) -> List[Dict]:
        """Detect unusual activities"""
        anomalies = []
        
        # Check for activities at unusual hours
        for _, row in df.iterrows():
            hour = row['hour']
            location = row['location']
            
            # Is this location unusual for this hour?
            if hour in hourly_patterns:
                total_at_hour = sum(hourly_patterns[hour].values())
                location_count = hourly_patterns[hour].get(location, 0)
                
                # If this location is rare at this hour
                if location_count / total_at_hour < 0.1:
                    anomalies.append({
                        'timestamp': row['timestamp'].isoformat(),
                        'location': location,
                        'hour': hour,
                        'reason': f'Unusual location for {hour}:00 hour',
                        'frequency': location_count / total_at_hour
                    })
        
        return anomalies[:10]  # Top 10 anomalies
    
    @staticmethod
    def predict_next_location(
        events: List[Dict],
        current_time: Optional[datetime] = None
    ) -> Dict:
        """
        Predict most likely next location based on patterns
        
        This is a simple rule-based predictor
        ML-based predictor will be in next task
        """
        if not events:
            return {'prediction': None, 'confidence': 0.0, 'method': 'insufficient_data'}
        
        if not current_time:
            current_time = datetime.now()
        
        df = pd.DataFrame(events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        
        target_hour = current_time.hour
        
        # Method 1: Most common location at this hour
        hour_data = df[df['hour'] == target_hour]
        
        if len(hour_data) > 0:
            location_counts = hour_data['location'].value_counts()
            most_common = location_counts.index[0]
            confidence = location_counts.iloc[0] / len(hour_data)
            
            return {
                'predicted_location': most_common,
                'confidence': round(confidence, 2),
                'method': 'hourly_pattern',
                'evidence': f'Entity is typically at {most_common} at {target_hour}:00 ({int(confidence*100)}% of time)'
            }
        
        # Method 2: Last known location
        last_event = df.sort_values('timestamp').iloc[-1]
        
        return {
            'predicted_location': last_event['location'],
            'confidence': 0.5,
            'method': 'last_known_location',
            'evidence': f'Last seen at {last_event["location"]} on {last_event["timestamp"]}'
        }