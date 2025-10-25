// components/dashboard/entity-dashboard.tsx - Update the timeline section
'use client';

import { useEffect, useState } from 'react';
import { EntityProfile } from './entity-profile';
import { ActivityTimeline } from './activity-timeline';
import { PredictionData, PredictiveInsights } from './predictive-insights';
import { ActivityFrequency, HeatmapData } from './activity-frequency';
import { AnomalyList } from './anomaly-list';
// import { CCTVSnapshots } from './cctv-snapshots';
import { DashboardFilters } from './dashboard-filters';
import { apiClient } from '@/lib/api-client';
import { Entity } from '@/types/entity';
import { Anomaly } from '@/types/anomaly';
// import { useToast } from '@/hooks/use-toast';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

interface TimelineData {
  entity_id: string;
  start_date: string;
  end_date: string;
  total_events: number;
  events: Array<{
    event_id: string;
    event_type: string;
    timestamp: string;
    location: string;
    location_id: string;
    location_type: string;
  }>;
  gaps: Array<{
    start_time: string;
    end_time: string;
    duration_hours: number;
    last_location: string;
    next_location: string;
    last_event_type: string;
    next_event_type: string;
  }>;
  statistics?: {
    event_type_distribution?: Record<string, number>;
    location_frequency?: Record<string, number>;
    most_visited_location?: string;
    hourly_distribution?: Record<string, number>;
    day_of_week_distribution?: Record<string, number>;
    activity_periods?: Record<string, number>;
    total_gaps?: number;
    total_gap_hours?: number;
    avg_events_per_day?: number;
  };
}

export function EntityDashboard({ entityId }: { entityId: string }) {
  const [entity, setEntity] = useState<Entity | null>(null);
  // const [fusionReport, setFusionReport] = useState<any>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapData | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[] | null>(null);
  // const [patterns, setPatterns] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);
  // const { toast } = useToast();

  useEffect(() => {
    loadDashboardData();
  }, [entityId]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setErrors([]);
      const errorList: string[] = [];

      // Fetch all data in parallel with individual error handling
      const results = await Promise.allSettled([
        apiClient.getEntity(entityId),
        apiClient.getTimelineWithGaps(entityId, 2), // This now returns the new format
        apiClient.predictLocation(entityId),
        apiClient.getActivityHeatmap(entityId, 7),
        apiClient.getAnomaliesByEntity(entityId),
      ]);

      // Process entity data
      if (results[0].status === 'fulfilled') {
        setEntity(results[0].value.entity);
      } else {
        errorList.push('Failed to load entity data');
        console.error('Entity fetch failed:', results[0].reason);
      }

      // Process timeline data
      if (results[1].status === 'fulfilled') {
        setTimeline(results[1].value as TimelineData);
      } else {
        console.error('Timeline report fetch failed:', results[1].reason);
      }

      // Process prediction
      if (results[2].status === 'fulfilled') {
        setPrediction(results[2].value);
      } else {
        errorList.push('Failed to load timeline data');
        console.error('Prediction fetch failed:', results[2].reason);
      }

      // Process heatmap
      if (results[3].status === 'fulfilled') {
        setHeatmap(results[3].value);
        console.log('Heatmap data:', results[3].value);
      } else {
        console.error('Heatmap fetch failed:', results[3].reason);
      }

      // Process anomalies
      if (results[4].status === 'fulfilled') {
        const anomalyResponse = results[4].value;
        setAnomalies(anomalyResponse.data?.anomalies || []);
        console.log('Anomalies data:', anomalyResponse);
      } else {
        console.error('Anomalies fetch failed:', results[4].reason);
      }

      if (errorList.length > 0) {
        setErrors(errorList);
      }
    } catch (error) {
      console.error('Unexpected error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-12 bg-gray-800 rounded w-full" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-6">
              <div className="h-48 bg-gray-800 rounded" />
              <div className="h-96 bg-gray-800 rounded" />
            </div>
            <div className="space-y-6">
              <div className="h-80 bg-gray-800 rounded" />
              <div className="h-64 bg-gray-800 rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!entity) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Entity with ID &quot;{entityId}&quot; could not be found. Please check the ID and try again.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {errors.length > 0 && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Some data failed to load: {errors.join(', ')}
          </AlertDescription>
        </Alert>
      )}
      
      <DashboardFilters />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          <EntityProfile entity={entity} />
          <ActivityTimeline
            timeline={timeline}
            entityId={entityId}
            onRefresh={loadDashboardData}
          />
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          <AnomalyList anomalies={anomalies} loading={loading} />
          <PredictiveInsights prediction={prediction} />
          <ActivityFrequency heatmap={heatmap} />
          {/* <CCTVSnapshots entityId={entityId} timeline={timeline} /> */}
        </div>
      </div>
    </div>
  );
}