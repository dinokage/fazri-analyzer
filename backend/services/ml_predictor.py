# backend/app/services/ml_predictor.py
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pickle
from pathlib import Path

class LocationPredictor:
    """ML-based location predictor with explainability"""
    
    def __init__(self):
        self.model = None
        self.location_encoder = LabelEncoder()
        self.event_encoder = LabelEncoder()
        self.is_trained = False
        self.feature_importance = {}
    
    def train(self, events: List[Dict], min_samples: int = 10):
        """
        Train predictor on historical events
        
        Features:
        - hour of day
        - day of week
        - previous location
        - previous event type
        - time since last event
        """
        if len(events) < min_samples:
            return {
                'success': False,
                'message': f'Insufficient training data. Need at least {min_samples} events, got {len(events)}'
            }
        
        # Prepare training data
        df = pd.DataFrame(events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Extract features
        features = []
        targets = []
        
        for i in range(1, len(df)):
            curr_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Time features
            hour = curr_row['timestamp'].hour
            day_of_week = curr_row['timestamp'].dayofweek
            
            # Previous location and event type
            prev_location = prev_row['location']
            prev_event_type = prev_row['event_type']
            
            # Time since last event (in hours)
            time_diff = (curr_row['timestamp'] - prev_row['timestamp']).total_seconds() / 3600
            
            features.append({
                'hour': hour,
                'day_of_week': day_of_week,
                'prev_location': prev_location,
                'prev_event_type': prev_event_type,
                'time_since_last': time_diff
            })
            
            targets.append(curr_row['location'])
        
        # Convert to DataFrame
        X_df = pd.DataFrame(features)
        y = targets
        
        # Encode categorical features
        self.location_encoder.fit(df['location'].unique())
        self.event_encoder.fit(df['event_type'].unique())
        
        X_df['prev_location_encoded'] = self.location_encoder.transform(X_df['prev_location'])
        X_df['prev_event_type_encoded'] = self.event_encoder.transform(X_df['prev_event_type'])
        
        # Select numeric features
        X = X_df[['hour', 'day_of_week', 'prev_location_encoded', 
                  'prev_event_type_encoded', 'time_since_last']].values
        y_encoded = self.location_encoder.transform(y)
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.model.fit(X, y_encoded)
        self.is_trained = True
        
        # Store feature importance
        feature_names = ['hour', 'day_of_week', 'prev_location', 'prev_event_type', 'time_since_last']
        self.feature_importance = dict(zip(feature_names, self.model.feature_importances_))
        
        return {
            'success': True,
            'training_samples': len(X),
            'unique_locations': len(self.location_encoder.classes_),
            'feature_importance': self.feature_importance
        }
    
    def predict(
        self, 
        target_time: datetime,
        recent_events: List[Dict],
        top_k: int = 3
    ) -> Dict:
        """
        Predict location at target_time with explanations
        
        Returns:
        - Top K predictions with probabilities
        - Explanation for each prediction
        - Evidence from historical data
        """
        if not self.is_trained:
            return self._fallback_predict(target_time, recent_events)
        
        if not recent_events:
            return {
                'predictions': [],
                'method': 'no_data',
                'explanation': 'No recent events available for prediction'
            }
        
        # Get most recent event
        df = pd.DataFrame(recent_events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        last_event = df.iloc[-1]
        
        # Extract features for target time
        hour = target_time.hour
        day_of_week = target_time.weekday()
        prev_location = last_event['location']
        prev_event_type = last_event['event_type']
        time_since_last = (target_time - last_event['timestamp']).total_seconds() / 3600
        
        # Encode categorical features
        try:
            prev_location_encoded = self.location_encoder.transform([prev_location])[0]
            prev_event_encoded = self.event_encoder.transform([prev_event_type])[0]
        except ValueError:
            # Unknown category, use fallback
            return self._fallback_predict(target_time, recent_events)
        
        # Make prediction
        X = np.array([[hour, day_of_week, prev_location_encoded, prev_event_encoded, time_since_last]])
        
        # Get probabilities for all classes
        probabilities = self.model.predict_proba(X)[0]
        
        # Get top K predictions
        top_indices = np.argsort(probabilities)[-top_k:][::-1]
        
        predictions = []
        for idx in top_indices:
            location = self.location_encoder.inverse_transform([idx])[0]
            probability = probabilities[idx]
            
            # Generate explanation
            explanation = self._generate_explanation(
                location, probability, hour, day_of_week, 
                prev_location, recent_events
            )
            
            predictions.append({
                'location': location,
                'confidence': round(float(probability), 3),
                'explanation': explanation
            })
        
        return {
            'target_time': target_time.isoformat(),
            'predictions': predictions,
            'method': 'random_forest_ml',
            'model_info': {
                'feature_importance': self.feature_importance,
                'training_samples': 'trained'
            }
        }
    
    def _generate_explanation(
        self,
        predicted_location: str,
        confidence: float,
        hour: int,
        day_of_week: int,
        prev_location: str,
        recent_events: List[Dict]
    ) -> Dict:
        """Generate human-readable explanation for prediction"""
        
        # Analyze historical patterns
        df = pd.DataFrame(recent_events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        # Count occurrences at this hour
        same_hour_events = df[df['hour'] == hour]
        if len(same_hour_events) > 0:
            location_at_hour = same_hour_events['location'].value_counts()
            if predicted_location in location_at_hour:
                hour_frequency = location_at_hour[predicted_location] / len(same_hour_events)
                hour_evidence = f"Entity is at {predicted_location} {hour_frequency:.0%} of the time at {hour}:00"
            else:
                hour_evidence = f"Prediction based on ML model patterns"
        else:
            hour_evidence = "No historical data for this hour"
        
        # Transition pattern
        prev_to_pred = df[df['location'].shift(1) == prev_location]
        if len(prev_to_pred) > 0:
            next_locations = prev_to_pred['location'].value_counts()
            if predicted_location in next_locations:
                transition_prob = next_locations[predicted_location] / len(prev_to_pred)
                transition_evidence = f"After {prev_location}, entity moves to {predicted_location} {transition_prob:.0%} of the time"
            else:
                transition_evidence = None
        else:
            transition_evidence = None
        
        # Feature importance
        top_features = sorted(
            self.feature_importance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:2]
        
        evidence_items = [hour_evidence]
        if transition_evidence:
            evidence_items.append(transition_evidence)
        
        return {
            'confidence_level': 'high' if confidence > 0.6 else 'medium' if confidence > 0.3 else 'low',
            'evidence': evidence_items,
            'key_factors': [f[0] for f in top_features],
            'reasoning': f"ML model predicts {predicted_location} with {confidence:.0%} confidence based on time patterns and movement history"
        }
    
    def _fallback_predict(
        self, 
        target_time: datetime, 
        recent_events: List[Dict]
    ) -> Dict:
        """Rule-based fallback when ML model not available"""
        if not recent_events:
            return {
                'predictions': [],
                'method': 'no_data',
                'explanation': 'Insufficient data for prediction'
            }
        
        df = pd.DataFrame(recent_events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        
        target_hour = target_time.hour
        
        # Find events at same hour
        same_hour = df[df['hour'] == target_hour]
        
        if len(same_hour) > 0:
            location_counts = same_hour['location'].value_counts()
            top_location = location_counts.index[0]
            confidence = location_counts.iloc[0] / len(same_hour)
            
            return {
                'target_time': target_time.isoformat(),
                'predictions': [{
                    'location': top_location,
                    'confidence': round(confidence, 3),
                    'explanation': {
                        'confidence_level': 'medium',
                        'evidence': [f'Most common location at {target_hour}:00 based on history'],
                        'key_factors': ['hour_of_day'],
                        'reasoning': 'Rule-based prediction using hourly patterns'
                    }
                }],
                'method': 'rule_based_fallback'
            }
        
        # Last known location
        last_event = df.iloc[-1]
        return {
            'target_time': target_time.isoformat(),
            'predictions': [{
                'location': last_event['location'],
                'confidence': 0.5,
                'explanation': {
                    'confidence_level': 'low',
                    'evidence': [f'Last seen at {last_event["location"]}'],
                    'key_factors': ['last_known_location'],
                    'reasoning': 'Using last known location as fallback'
                }
            }],
            'method': 'last_known_fallback'
        }
    
    def save_model(self, filepath: Path):
        """Save trained model to disk"""
        if not self.is_trained:
            raise ValueError("No trained model to save")
        
        model_data = {
            'model': self.model,
            'location_encoder': self.location_encoder,
            'event_encoder': self.event_encoder,
            'feature_importance': self.feature_importance
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, filepath: Path):
        """Load trained model from disk"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.location_encoder = model_data['location_encoder']
        self.event_encoder = model_data['event_encoder']
        self.feature_importance = model_data['feature_importance']
        self.is_trained = True