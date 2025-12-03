'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Zone, ZoneOccupancy, CampusSummary } from '@/types/zone';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Building2, Users, TrendingUp, MapPin, Search, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { ChartContainer } from '@/components/ui/chart';
import { PieChart, Pie, Cell, Legend, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

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

export default function ZonesPage() {
  const router = useRouter();
  const [zones, setZones] = useState<Zone[]>([]);
  const [occupancyData, setOccupancyData] = useState<Record<string, ZoneOccupancy>>({});
  const [campusSummary, setCampusSummary] = useState<CampusSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');

  // Statistics
  const statistics = useMemo(() => {
    const typeCount: Record<string, number> = {};
    const buildingCount: Record<string, number> = {};
    const occupancyByZone: Array<{ name: string; occupancy: number; capacity: number; rate: number }> = [];

    let totalCapacity = 0;
    let totalCurrentOccupancy = 0;
    let occupancyCount = 0;
    let maxOccupancyRate = 0;
    let mostCrowdedZone: { name: string; rate: number } | null = null;

    zones.forEach((zone) => {
      typeCount[zone.zone_type] = (typeCount[zone.zone_type] || 0) + 1;
      buildingCount[zone.building] = (buildingCount[zone.building] || 0) + 1;
      totalCapacity += zone.capacity;

      const occupancy = occupancyData[zone.zone_id];
      if (occupancy) {
        totalCurrentOccupancy += occupancy.current_occupancy;
        occupancyCount++;

        const rate = occupancy.occupancy_rate * 100;
        if (rate > maxOccupancyRate) {
          maxOccupancyRate = rate;
          mostCrowdedZone = { name: zone.name, rate: occupancy.occupancy_rate };
        }

        occupancyByZone.push({
          name: zone.name,
          occupancy: occupancy.current_occupancy,
          capacity: zone.capacity,
          rate: occupancy.occupancy_rate,
        });
      }
    });

    const typeData = Object.entries(typeCount).map(([type, count]) => ({
      type,
      count,
      fill: zoneTypeColors[type] || '#6b7280',
    }));

    const topOccupied = occupancyByZone
      .sort((a, b) => b.rate - a.rate)
      .slice(0, 5);

    const averageOccupancyRate = occupancyCount > 0
      ? totalCurrentOccupancy / totalCapacity
      : 0;

    return {
      totalZones: zones.length,
      totalCapacity,
      totalCurrentOccupancy,
      averageOccupancyRate,
      mostCrowdedZone,
      typeCount,
      typeData,
      buildingCount,
      topOccupied,
    };
  }, [zones, occupancyData]);

  // Filtered zones
  const filteredZones = useMemo(() => {
    return zones.filter((zone) => {
      const matchesSearch = zone.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        zone.building.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = filterType === 'all' || zone.zone_type === filterType;
      return matchesSearch && matchesType;
    });
  }, [zones, searchTerm, filterType]);

  useEffect(() => {
    loadZonesData();
  }, []);

  const loadZonesData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch zones and campus summary in parallel
      const [zonesResponse, summaryResponse] = await Promise.allSettled([
        apiClient.getAllZones(),
        apiClient.getCampusSummary(),
      ]);

      if (zonesResponse.status === 'fulfilled' && zonesResponse.value.success) {
        const zonesData = zonesResponse.value.data;
        console.log('Zones loaded:', zonesData.length);
        setZones(zonesData);

        // Fetch occupancy for each zone
        const occupancyPromises = zonesData.map((zone: Zone) =>
          apiClient.getZoneOccupancy(zone.zone_id)
            .then(res => ({ zoneId: zone.zone_id, data: res.data }))
            .catch((err) => {
              console.error(`Failed to load occupancy for ${zone.zone_id}:`, err);
              return { zoneId: zone.zone_id, data: null };
            })
        );

        const occupancyResults = await Promise.all(occupancyPromises);
        const occupancyMap: Record<string, ZoneOccupancy> = {};
        occupancyResults.forEach(result => {
          if (result.data) {
            occupancyMap[result.zoneId] = result.data;
          }
        });
        console.log('Occupancy data loaded for zones:', Object.keys(occupancyMap).length);
        setOccupancyData(occupancyMap);
      } else {
        const errorMsg = zonesResponse.status === 'fulfilled'
          ? 'API returned success: false'
          : zonesResponse.reason;
        console.error('Failed to load zones:', errorMsg);
        setError('Failed to load zones data');
      }

      if (summaryResponse.status === 'fulfilled' && summaryResponse.value.success) {
        console.log('Campus summary loaded:', summaryResponse.value.data);
        setCampusSummary(summaryResponse.value.data);
      } else if (summaryResponse.status === 'rejected') {
        console.error('Failed to load campus summary:', summaryResponse.reason);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load zones');
      console.error('Error loading zones:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-800 rounded w-48" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-32 bg-gray-800 rounded" />
            ))}
          </div>
          <div className="h-96 bg-gray-800 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Campus Zones</h1>
        <Badge variant="secondary" className="text-sm">
          {statistics.totalZones} Zones
        </Badge>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Zones */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Total Zones</p>
              <p className="text-3xl font-bold">
                {campusSummary?.summary.total_zones || statistics.totalZones}
              </p>
            </div>
            <div className="p-3 bg-blue-600/10 rounded-lg">
              <Building2 className="h-6 w-6 text-blue-500" />
            </div>
          </div>
        </div>

        {/* Total Capacity */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Total Capacity</p>
              <p className="text-3xl font-bold">
                {campusSummary?.summary.total_capacity || statistics.totalCapacity}
              </p>
            </div>
            <div className="p-3 bg-green-600/10 rounded-lg">
              <Users className="h-6 w-6 text-green-500" />
            </div>
          </div>
        </div>

        {/* Current Occupancy */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Current Occupancy</p>
              <p className="text-3xl font-bold">
                {campusSummary?.zone_details[0]?.current_occupancy || statistics.totalCurrentOccupancy}
              </p>
            </div>
            <div className="p-3 bg-purple-600/10 rounded-lg">
              <TrendingUp className="h-6 w-6 text-purple-500" />
            </div>
          </div>
        </div>

        {/* Most Crowded Zone */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Most Crowded</p>
              <p className="text-xl font-bold truncate">
                {campusSummary?.high_traffic_zones[0]?.zone_name || 'N/A'}
              </p>
              <p className="text-sm text-orange-500">
                {(() => {
                  const zone = campusSummary?.high_traffic_zones[0];
                  if (zone) {
                    const rate = (zone.current_occupancy / zone.capacity) * 100;
                    return `${rate.toFixed(0)}%`;
                  }
                  return '0%';
                })()}
              </p>
            </div>
            <div className="p-3 bg-orange-600/10 rounded-lg">
              <MapPin className="h-6 w-6 text-orange-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Zone Type Distribution */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Zone Type Distribution</h2>
          <div className="h-[300px] flex items-center justify-center">
            <ChartContainer
              config={Object.fromEntries(
                Object.entries(zoneTypeColors).map(([key, color]) => [
                  key,
                  { label: key, color },
                ])
              )}
              className="w-full h-full"
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statistics.typeData}
                    cx="50%"
                    cy="45%"
                    innerRadius={60}
                    outerRadius={90}
                    dataKey="count"
                    paddingAngle={2}
                  >
                    {statistics.typeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-[#1a1a24] border border-gray-700 rounded-lg p-3 shadow-xl">
                            <p className="text-sm font-medium">{payload[0].payload.type}</p>
                            <p className="text-lg font-bold text-blue-400">{payload[0].value}</p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    formatter={(value) => <span className="text-sm">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </ChartContainer>
          </div>
        </div>

        {/* Top Occupied Zones */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Top Occupied Zones</h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statistics.topOccupied} layout="vertical">
                <XAxis type="number" stroke="#6b7280" />
                <YAxis type="category" dataKey="name" width={120} stroke="#6b7280" />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-[#1a1a24] border border-gray-700 rounded-lg p-3 shadow-xl">
                          <p className="text-sm font-medium">{data.name}</p>
                          <p className="text-lg font-bold text-blue-400">
                            {data.occupancy}/{data.capacity}
                          </p>
                          <p className="text-xs text-gray-400">{data.rate.toFixed(0)}% occupied</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="rate" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search zones or buildings..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-[#1a1a24] border-gray-700"
            />
          </div>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="bg-[#1a1a24] border-gray-700 md:justify-self-end mt-4 md:mt-0">
              <SelectValue placeholder="All zone types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All zone types</SelectItem>
              {Object.keys(statistics.typeCount).map((type) => (
                <SelectItem key={type} value={type}>
                  {type} ({statistics.typeCount[type]})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Zone Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredZones.map((zone) => {
          const occupancy = occupancyData[zone.zone_id];
          const occupancyRate = occupancy ? occupancy.occupancy_rate : 0;
          const status = getOccupancyStatus(occupancyRate);

          return (
            <div
              key={zone.zone_id}
              onClick={() => router.push(`/dashboard/zones/${zone.zone_id}`)}
              className="bg-[#14141a] rounded-lg border border-gray-800 p-6 hover:border-gray-700 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg mb-1">{zone.name}</h3>
                  <p className="text-sm text-gray-400">{zone.building} - Floor {zone.floor}</p>
                </div>
                <Badge
                  style={{ backgroundColor: zoneTypeColors[zone.zone_type] || '#6b7280' }}
                  className="text-xs"
                >
                  {zone.zone_type}
                </Badge>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Capacity</span>
                  <span className="font-medium">{zone.capacity}</span>
                </div>

                {occupancy && (
                  <>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Current Occupancy</span>
                      <span className={`font-medium ${status.color}`}>
                        {occupancy.current_occupancy}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Occupancy Rate</span>
                        <span className={status.color}>{occupancyRate.toFixed(0)}%</span>
                      </div>
                      <Progress value={occupancyRate} className="h-2" />
                    </div>

                    <div className="pt-2 border-t border-gray-800">
                      <Badge variant="secondary" className="text-xs">
                        {status.status}
                      </Badge>
                    </div>
                  </>
                )}

                {!occupancy && (
                  <p className="text-sm text-gray-500 italic">No occupancy data</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {filteredZones.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400">No zones found matching your filters.</p>
        </div>
      )}
    </div>
  );
}
