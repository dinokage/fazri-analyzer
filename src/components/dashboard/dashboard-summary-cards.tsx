
'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, Building2, Activity, AlertCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

interface CampusSummary {
  summary: {
    total_zones: number;
    total_capacity: number;
    total_occupancy: number;
    overall_occupancy_rate: number;
    status: string;
  };
  high_traffic_zones: Array<{ zone_id: string; zone_name: string; current_occupancy: number; capacity: number }>;
  underutilized_zones: Array<{ zone_id: string; zone_name: string; current_occupancy: number; capacity: number }>;
  last_updated: string;
}

const getStatusColors = (status: string) => {
  switch (status) {
    case 'critical':
      return 'bg-red-500';
    case 'high':
      return 'bg-yellow-500';
    case 'moderate':
      return 'bg-blue-500';
    case 'low':
      return 'bg-green-500';
    case 'minimal':
      return 'bg-gray-500';
    default:
      return 'bg-gray-500';
  }
};

export function DashboardSummaryCards() {
  const [summary, setSummary] = useState<CampusSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        const response = await apiClient.getCampusSummary();
        if (response.success) {
          setSummary(response.data);
        } else {
          setError(response.detail || 'Failed to fetch campus summary');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="bg-[#14141a] border-gray-800 animate-pulse">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 w-24 bg-gray-700 rounded"></div>
              <div className="h-6 w-6 bg-gray-700 rounded-full"></div>
            </CardHeader>
            <CardContent>
              <div className="h-6 w-1/2 bg-gray-700 rounded mb-2"></div>
              <div className="h-4 w-3/4 bg-gray-700 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-[#14141a] border-red-800 col-span-full">
          <CardHeader>
            <CardTitle className="text-red-500">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-400">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  const { summary: campusSummary, high_traffic_zones, underutilized_zones } = summary;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      <Card className="bg-[#14141a] border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Zones</CardTitle>
          <Building2 className="h-4 w-4 text-gray-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{campusSummary.total_zones}</div>
          <p className="text-xs text-gray-500">Overall zones in campus</p>
        </CardContent>
      </Card>

      <Card className="bg-[#14141a] border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Occupancy</CardTitle>
          <Users className="h-4 w-4 text-gray-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{campusSummary.total_occupancy} / {campusSummary.total_capacity}</div>
          <Progress value={campusSummary.overall_occupancy_rate} className="h-2 mt-2" />
          <p className="text-xs text-gray-500 mt-1">
            {campusSummary.overall_occupancy_rate.toFixed(1)}% occupied
          </p>
        </CardContent>
      </Card>

      <Card className="bg-[#14141a] border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Campus Status</CardTitle>
          <Activity className="h-4 w-4 text-gray-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold capitalize">{campusSummary.status}</div>
          <Badge className={`mt-2 ${getStatusColors(campusSummary.status)}`}>
            {campusSummary.status}
          </Badge>
        </CardContent>
      </Card>

      <Card className="bg-[#14141a] border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">High Traffic Zones</CardTitle>
          <ArrowUpRight className="h-4 w-4 text-red-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{high_traffic_zones.length}</div>
          <p className="text-xs text-gray-500 mt-1">
            {high_traffic_zones.map(zone => zone.zone_name).join(', ') || 'None'}
          </p>
        </CardContent>
      </Card>

      <Card className="bg-[#14141a] border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Underutilized Zones</CardTitle>
          <ArrowDownRight className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{underutilized_zones.length}</div>
          {/* <p className="text-xs text-gray-500 mt-1">
            {underutilized_zones.map(zone => zone.zone_name).join(', ') || 'None'}
          </p> */}
        </CardContent>
      </Card>
    </div>
  );
}
