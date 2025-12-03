'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Zone, ZoneOccupancy } from '@/types/zone';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Building2, Users, MapPin, Clock, AlertCircle, Activity } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { PredictiveZoneForecast } from '@/components/dashboard/predictive-zone-forecast';


const zoneTypeColors: Record<string, string> = {
  LAB: '#3b82f6',
  CAFETERIA: '#10b981',
  AUDITORIUM: '#8b5cf6',
  LOBBY: '#f59e0b',
  ENTRANCE: '#ef4444',
  GYM: '#06b6d4',
};

const getOccupancyStatus = (rate: number): { color: string; bgColor: string; status: string } => {
  if (rate >= 90) return { color: 'text-red-500', bgColor: 'bg-red-600', status: 'Full' };
  if (rate >= 70) return { color: 'text-yellow-500', bgColor: 'bg-yellow-600', status: 'Crowded' };
  return { color: 'text-green-500', bgColor: 'bg-green-600', status: 'Normal' };
};



export default function ZoneDetailPage() {
  const params = useParams();
  const router = useRouter();
  const zoneId = params.zoneId as string;

  const [zone, setZone] = useState<Zone | null>(null);
  const [occupancy, setOccupancy] = useState<ZoneOccupancy | null>(null);
  //eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [connections, setConnections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadZoneData();
  }, [zoneId]);

  const loadZoneData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [zoneRes, occupancyRes, connectionsRes] = await Promise.allSettled([
        apiClient.getZoneDetails(zoneId),
        apiClient.getZoneOccupancy(zoneId),
        apiClient.getZoneConnections(zoneId),
      ]);

      if (zoneRes.status === 'fulfilled' && zoneRes.value.success) {
        setZone(zoneRes.value.data);
      } else {
        setError('Failed to load zone details');
      }

      if (occupancyRes.status === 'fulfilled' && occupancyRes.value.success) {
        setOccupancy(occupancyRes.value.data);
      }

      if (connectionsRes.status === 'fulfilled' && connectionsRes.value.success) {
        setConnections(connectionsRes.value.data || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load zone data');
      console.error('Error loading zone:', err);
    } finally {
      setLoading(false);
    }
  };



  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-800 rounded w-48" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-gray-800 rounded" />
            ))}
          </div>
          <div className="h-96 bg-gray-800 rounded" />
        </div>
      </div>
    );
  }

  if (error || !zone) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || 'Zone not found'}</AlertDescription>
        </Alert>
        <Button
          onClick={() => router.push('/dashboard/zones')}
          className="mt-4"
          variant="outline"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Zones
        </Button>
      </div>
    );
  }

  const occupancyRate = occupancy ? occupancy.occupancy_rate : 0;
  const status = getOccupancyStatus(occupancyRate);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => router.push('/dashboard/zones')}
            className="bg-[#1a1a24] border-gray-700 hover:bg-[#242430]"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{zone.name}</h1>
            <p className="text-gray-400 mt-1">
              {zone.building} - Floor {zone.floor}
            </p>
          </div>
        </div>
        <Badge
          style={{ backgroundColor: zoneTypeColors[zone.zone_type] || '#6b7280' }}
          className="text-sm"
        >
          {zone.zone_type}
        </Badge>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Capacity Card */}
        <Card className="bg-[#14141a] border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400">
              Capacity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold">{zone.capacity}</p>
                <p className="text-xs text-gray-500 mt-1">Total capacity</p>
              </div>
              <div className="p-3 bg-blue-600/10 rounded-lg">
                <Users className="h-6 w-6 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Current Occupancy Card */}
        <Card className="bg-[#14141a] border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400">
              Current Occupancy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-3xl font-bold">
                    {occupancy?.current_occupancy || 0}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {occupancyRate.toFixed(1)}% occupied
                  </p>
                </div>
                <div className={`p-3 ${status.bgColor}/10 rounded-lg`}>
                  <Activity className={`h-6 w-6 ${status.color}`} />
                </div>
              </div>
              <Progress value={occupancyRate} className="h-2" />
              <Badge variant="secondary" className="text-xs">
                {status.status}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Department Card */}
        <Card className="bg-[#14141a] border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400">
              Location
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-gray-400" />
                <span className="text-sm">{zone.building}</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-gray-400" />
                <span className="text-sm">Floor {zone.floor}</span>
              </div>
              {zone.department && (
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-gray-400" />
                  <span className="text-sm">{zone.department}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Predictive Forecast Chart */}
      <PredictiveZoneForecast zoneId={zoneId} />

      {/* Connected Zones */}
      {connections.length > 0 && (
        <Card className="bg-[#14141a] border-gray-800">
          <CardHeader>
            <CardTitle>Connected Zones</CardTitle>
            <CardDescription>
              Zones connected to {zone.name}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {connections.map((connection) => (
                <div
                  key={connection.zone_id}
                  className="bg-[#1a1a24] rounded-lg p-4 border border-gray-800 hover:border-gray-700 transition-colors cursor-pointer"
                  onClick={() => router.push(`/dashboard/zones/${connection.zone_id}`)}
                >
                  <h4 className="font-medium mb-2">{connection.zone_name}</h4>
                  <div className="space-y-1 text-sm text-gray-400">
                    <div className="flex items-center gap-2">
                      <MapPin className="h-3 w-3" />
                      <span>{connection.distance_meters}m away</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="h-3 w-3" />
                      <span>{connection.walking_time_minutes} min walk</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Zone Details */}
      {zone.description && (
        <Card className="bg-[#14141a] border-gray-800">
          <CardHeader>
            <CardTitle>About</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-300">{zone.description}</p>
            {zone.facilities && zone.facilities.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-medium text-gray-400 mb-2">Facilities:</p>
                <div className="flex flex-wrap gap-2">
                  {zone.facilities.map((facility, idx) => (
                    <Badge key={idx} variant="secondary" className="bg-[#1a1a24]">
                      {facility}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
