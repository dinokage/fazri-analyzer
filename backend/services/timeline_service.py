from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

class TimelineService:
    """Generate and analyze entity timelines"""
    
    def __init__(self, graph_builder):
        self.graph = graph_builder
    
    def get_timeline_with_gaps(
    self, 
    entity_id: str, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    gap_threshold_hours: int = 2
) -> Dict:
        """
        Get timeline with gap detection
        """
        try:
            # Get raw events from Neo4j
            events = self.graph.get_entity_timeline(entity_id, start_date, end_date)
            
            if not events:
                return {
                    'entity_id': entity_id,
                    'events': [],
                    'gaps': [],
                    'statistics': {},
                    'total_events': 0,
                    'message': 'No activity found for this entity'
                }
            
            # Convert to pandas for easier manipulation
            df = pd.DataFrame(events)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Detect gaps
            gaps = self._detect_gaps(df, gap_threshold_hours)
            
            # Calculate statistics
            stats = self._calculate_statistics(df, gaps)
            
            return {
                'entity_id': entity_id,
                'start_date': df['timestamp'].min().isoformat(),
                'end_date': df['timestamp'].max().isoformat(),
                'total_events': len(events),
                'events': events,
                'gaps': gaps,
                'statistics': stats
            }
        except Exception as e:
            print(f"Error in get_timeline_with_gaps: {str(e)}")
            raise e
    
    def _detect_gaps(self, df: pd.DataFrame, threshold_hours: int) -> List[Dict]:
        """Detect gaps in activity timeline"""
        gaps = []
        
        for i in range(len(df) - 1):
            current_time = df.iloc[i]['timestamp']
            next_time = df.iloc[i + 1]['timestamp']
            
            time_diff = (next_time - current_time).total_seconds() / 3600  # hours
            
            if time_diff >= threshold_hours:
                gaps.append({
                    'start_time': current_time.isoformat(),
                    'end_time': next_time.isoformat(),
                    'duration_hours': round(time_diff, 2),
                    'last_location': df.iloc[i]['location'],
                    'next_location': df.iloc[i + 1]['location'],
                    'last_event_type': df.iloc[i]['event_type'],
                    'next_event_type': df.iloc[i + 1]['event_type']
                })
        
        return gaps
    
    def _calculate_statistics(self, df: pd.DataFrame, gaps: List[Dict]) -> Dict:
        """Calculate timeline statistics"""
        # Event type distribution
        event_type_counts = df['event_type'].value_counts().to_dict()
        
        # Location frequency
        location_counts = df['location'].value_counts().to_dict()
        
        # Hourly distribution
        df['hour'] = df['timestamp'].dt.hour
        hourly_counts = df['hour'].value_counts().sort_index().to_dict()
        
        # Day of week distribution
        df['day_of_week'] = df['timestamp'].dt.day_name()
        day_counts = df['day_of_week'].value_counts().to_dict()
        
        # Activity periods
        morning = len(df[(df['hour'] >= 6) & (df['hour'] < 12)])
        afternoon = len(df[(df['hour'] >= 12) & (df['hour'] < 18)])
        evening = len(df[(df['hour'] >= 18) & (df['hour'] < 22)])
        night = len(df[(df['hour'] >= 22) | (df['hour'] < 6)])
        
        return {
            'event_type_distribution': event_type_counts,
            'location_frequency': location_counts,
            'most_visited_location': max(location_counts.items(), key=lambda x: x[1])[0] if location_counts else None,
            'hourly_distribution': hourly_counts,
            'day_of_week_distribution': day_counts,
            'activity_periods': {
                'morning': morning,
                'afternoon': afternoon,
                'evening': evening,
                'night': night
            },
            'total_gaps': len(gaps),
            'total_gap_hours': sum([g['duration_hours'] for g in gaps]),
            'avg_events_per_day': len(df) / max(1, (df['timestamp'].max() - df['timestamp'].min()).days or 1)
        }
    
    def generate_summary(
        self, 
        entity_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Generate human-readable timeline summary
        
        Returns natural language description of entity's activity
        """
        timeline_data = self.get_timeline_with_gaps(entity_id, start_date, end_date)
        
        if not timeline_data['events']:
            return {
                'entity_id': entity_id,
                'summary': f'No activity recorded for entity {entity_id} in the specified period.',
                'detailed_summary': {},
                'timeline_data': timeline_data
            }
        
        stats = timeline_data['statistics']
        events = timeline_data['events']
        gaps = timeline_data['gaps']
        
        # Build natural language summary
        summary_parts = []
        
        # Overall activity
        total_events = timeline_data['total_events']
        date_range = f"from {timeline_data['start_date'][:10]} to {timeline_data['end_date'][:10]}"
        summary_parts.append(
            f"Entity showed {total_events} activities {date_range}."
        )
        
        # Most visited location
        if stats['most_visited_location']:
            most_visited = stats['most_visited_location']
            visit_count = stats['location_frequency'][most_visited]
            summary_parts.append(
                f"Most frequently visited location: {most_visited} ({visit_count} times)."
            )
        
        # Activity patterns
        activity_periods = stats['activity_periods']
        most_active_period = max(activity_periods.items(), key=lambda x: x[1])[0]
        summary_parts.append(
            f"Most active during {most_active_period} hours ({activity_periods[most_active_period]} events)."
        )
        
        # Event types
        event_types = stats['event_type_distribution']
        most_common_event = max(event_types.items(), key=lambda x: x[1])
        summary_parts.append(
            f"Primary activity type: {most_common_event[0]} ({most_common_event[1]} occurrences)."
        )
        
        # Gaps
        if gaps:
            longest_gap = max(gaps, key=lambda x: x['duration_hours'])
            summary_parts.append(
                f"Detected {len(gaps)} activity gap(s). Longest gap: {longest_gap['duration_hours']} hours."
            )
        
        # Detailed summary by time period
        detailed = self._generate_detailed_summary(timeline_data)
        
        return {
            'entity_id': entity_id,
            'summary': ' '.join(summary_parts),
            'detailed_summary': detailed,
            'timeline_data': timeline_data
        }
    
    def _generate_detailed_summary(self, timeline_data: Dict) -> Dict:
        """Generate detailed breakdown by time periods"""
        df = pd.DataFrame(timeline_data['events'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        detailed = {}
        
        # Morning summary (6 AM - 12 PM)
        morning = df[(df['timestamp'].dt.hour >= 6) & (df['timestamp'].dt.hour < 12)]
        if len(morning) > 0:
            morning_locations = morning['location'].value_counts().head(3).index.tolist()
            detailed['morning'] = {
                'total_events': len(morning),
                'locations': morning_locations,
                'description': f"Morning activity ({len(morning)} events): Primarily at {', '.join(morning_locations[:2])}"
            }
        
        # Afternoon summary (12 PM - 6 PM)
        afternoon = df[(df['timestamp'].dt.hour >= 12) & (df['timestamp'].dt.hour < 18)]
        if len(afternoon) > 0:
            afternoon_locations = afternoon['location'].value_counts().head(3).index.tolist()
            detailed['afternoon'] = {
                'total_events': len(afternoon),
                'locations': afternoon_locations,
                'description': f"Afternoon activity ({len(afternoon)} events): Primarily at {', '.join(afternoon_locations[:2])}"
            }
        
        # Evening summary (6 PM - 10 PM)
        evening = df[(df['timestamp'].dt.hour >= 18) & (df['timestamp'].dt.hour < 22)]
        if len(evening) > 0:
            evening_locations = evening['location'].value_counts().head(3).index.tolist()
            detailed['evening'] = {
                'total_events': len(evening),
                'locations': evening_locations,
                'description': f"Evening activity ({len(evening)} events): Primarily at {', '.join(evening_locations[:2])}"
            }
        
        return detailed
    
    def get_activity_heatmap(self, entity_id: str, days: int = 7) -> Dict:
        """
        Generate activity heatmap data (hour x day)
        Useful for visualization
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        timeline_data = self.get_timeline_with_gaps(
            entity_id, 
            start_date.isoformat(), 
            end_date.isoformat()
        )
        
        if not timeline_data['events']:
            return {
                'entity_id': entity_id,
                'heatmap': [],
                'message': 'No activity data'
            }
        
        df = pd.DataFrame(timeline_data['events'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['date'] = df['timestamp'].dt.date
        
        # Create heatmap matrix
        heatmap = df.groupby(['date', 'hour']).size().reset_index(name='count')
        heatmap['date'] = heatmap['date'].astype(str)
        
        return {
            'entity_id': entity_id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'heatmap': heatmap.to_dict('records')
        }