// components/dashboard/activity-frequency.tsx
'use client';

import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell, CartesianGrid } from 'recharts';
import { format, parseISO, startOfDay, differenceInCalendarDays } from 'date-fns';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Calendar, TrendingUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { useState } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface HeatmapEntry {
  date: string;
  hour: number;
  count: number;
}

export interface HeatmapData {
  entity_id: string;
  start_date: string;
  end_date: string;
  heatmap: HeatmapEntry[];
}

interface ActivityFrequencyProps {
  heatmap: HeatmapData | null;
}

type ViewMode = 'daily' | 'hourly' | 'weekly';

export function ActivityFrequency({ heatmap }: ActivityFrequencyProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('daily');

  // Helper to get color based on activity intensity
  const getBarColor = (count: number, maxCount: number) => {
    if (maxCount === 0) return '#93c5fd';
    const intensity = count / maxCount;
    if (intensity > 0.7) return '#3b82f6'; // High activity - bright blue
    if (intensity > 0.4) return '#60a5fa'; // Medium activity - medium blue
    return '#93c5fd'; // Low activity - light blue
  };

  // Handle no heatmap data
  if (!heatmap) {
    return (
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-6">Activity Frequency</h2>
        <Alert className="bg-[#1a1a24] border-gray-700">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No activity frequency data available. Historical activity data is required to generate this visualization.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Handle empty heatmap array
  if (!heatmap.heatmap || !Array.isArray(heatmap.heatmap) || heatmap.heatmap.length === 0) {
    return (
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">Activity Frequency</h2>
          {heatmap.start_date && heatmap.end_date && (
            <span className="text-xs text-gray-400">
              {format(parseISO(heatmap.start_date), 'MMM dd')} - {format(parseISO(heatmap.end_date), 'MMM dd')}
            </span>
          )}
        </div>
        <Alert className="bg-[#1a1a24] border-gray-700">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No activity recorded during this period.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Process heatmap data based on view mode
  const processDataByMode = () => {
    try {
      switch (viewMode) {
        case 'daily': {
          // Aggregate by date
          const dailyMap = new Map<string, number>();
          
          heatmap.heatmap.forEach(entry => {
            if (!entry.date) return;
            const dateKey = entry.date;
            dailyMap.set(dateKey, (dailyMap.get(dateKey) || 0) + (entry.count || 0));
          });

          return Array.from(dailyMap.entries())
            .map(([date, count]) => ({
              date: format(parseISO(date), 'MMM dd'),
              fullDate: date,
              count,
            }))
            .sort((a, b) => a.fullDate.localeCompare(b.fullDate));
        }

        case 'hourly': {
          // Aggregate by hour
          const hourlyMap = new Map<number, number>();
          
          heatmap.heatmap.forEach(entry => {
            const hour = entry.hour ?? 0;
            hourlyMap.set(hour, (hourlyMap.get(hour) || 0) + (entry.count || 0));
          });

          return Array.from(hourlyMap.entries())
            .map(([hour, count]) => ({
              date: `${hour.toString().padStart(2, '0')}:00`,
              hour,
              count,
            }))
            .sort((a, b) => a.hour - b.hour);
        }

        case 'weekly': {
          // Aggregate by week
          const weeklyMap = new Map<string, number>();
          
          heatmap.heatmap.forEach(entry => {
            if (!entry.date) return;
            const date = parseISO(entry.date);
            const weekStart = startOfDay(date);
            const weekKey = format(weekStart, 'yyyy-MM-dd');
            weeklyMap.set(weekKey, (weeklyMap.get(weekKey) || 0) + (entry.count || 0));
          });

          return Array.from(weeklyMap.entries())
            .map(([weekStart, count]) => ({
              date: format(parseISO(weekStart), 'MMM dd'),
              fullDate: weekStart,
              count,
            }))
            .sort((a, b) => a.fullDate.localeCompare(b.fullDate))
            .slice(0, 10); // Limit to 10 weeks
        }

        default:
          return [];
      }
    } catch (error) {
      console.error('Error processing heatmap data:', error);
      return [];
    }
  };

  const chartData = processDataByMode();

  // Calculate statistics
  const calculateStats = () => {
    try {
      const totalCount = heatmap.heatmap.reduce((sum, entry) => sum + (entry.count || 0), 0);
      const uniqueDays = new Set(heatmap.heatmap.map(e => e.date).filter(Boolean)).size;
      const avgPerDay = uniqueDays > 0 ? totalCount / uniqueDays : 0;

      // Find peak hour
      const hourlyTotals = new Map<number, number>();
      heatmap.heatmap.forEach(entry => {
        const hour = entry.hour ?? 0;
        hourlyTotals.set(hour, (hourlyTotals.get(hour) || 0) + (entry.count || 0));
      });
      const peakHour = Array.from(hourlyTotals.entries())
        .reduce((max, [hour, count]) => count > max[1] ? [hour, count] : max, [0, 0]);

      // Find most active day
      const dailyTotals = new Map<string, number>();
      heatmap.heatmap.forEach(entry => {
        if (!entry.date) return;
        dailyTotals.set(entry.date, (dailyTotals.get(entry.date) || 0) + (entry.count || 0));
      });
      const mostActiveDay = Array.from(dailyTotals.entries())
        .reduce((max, [date, count]) => count > max[1] ? [date, count] : max, ['', 0]);

      return {
        totalCount,
        uniqueDays,
        avgPerDay,
        peakHour: peakHour[0],
        mostActiveDay: mostActiveDay[0] ? format(parseISO(mostActiveDay[0]), 'MMM dd') : 'N/A',
        dateRange: heatmap.start_date && heatmap.end_date 
          ? differenceInCalendarDays(parseISO(heatmap.end_date), parseISO(heatmap.start_date)) + 1
          : 0,
      };
    } catch (error) {
      console.error('Error calculating statistics:', error);
      return {
        totalCount: 0,
        uniqueDays: 0,
        avgPerDay: 0,
        peakHour: 0,
        mostActiveDay: 'N/A',
        dateRange: 0,
      };
    }
  };

  const stats = calculateStats();
  const maxCount = Math.max(...chartData.map((d) => d.count), 1);

  return (
    <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold">Activity Frequency</h2>
          {heatmap.start_date && heatmap.end_date && (
            <p className="text-xs text-gray-400 mt-1">
              {format(parseISO(heatmap.start_date), 'MMM dd, yyyy')} - {format(parseISO(heatmap.end_date), 'MMM dd, yyyy')}
            </p>
          )}
        </div>
        
        {/* View mode selector */}
        <Select value={viewMode} onValueChange={(value) => setViewMode(value as ViewMode)}>
          <SelectTrigger className="w-[130px] h-8 bg-[#1a1a24] border-gray-700 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-[#1a1a24] border-gray-700">
            <SelectItem value="daily" className="text-xs">Daily View</SelectItem>
            <SelectItem value="hourly" className="text-xs">Hourly View</SelectItem>
            <SelectItem value="weekly" className="text-xs">Weekly View</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      {chartData.length > 0 ? (
        <>
          {/* Chart */}
          <div className="h-48 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="#6b7280"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  angle={chartData.length > 15 ? -45 : 0}
                  textAnchor={chartData.length > 15 ? "end" : "middle"}
                  height={chartData.length > 15 ? 60 : 30}
                />
                <YAxis 
                  stroke="#6b7280"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1a1a24', 
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                  labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                  cursor={{ fill: 'rgba(59, 130, 246, 0.1)' }}
                  formatter={(value) => [`${value} events`, 'Count']}
                />
                <Bar 
                  dataKey="count" 
                  radius={[4, 4, 0, 0]}
                  maxBarSize={50}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getBarColor(entry.count, maxCount)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Statistics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-[#1a1a24] rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Calendar className="h-3 w-3 text-gray-400" />
                <p className="text-xs text-gray-400">Total Events</p>
              </div>
              <p className="text-lg font-bold">{stats.totalCount}</p>
            </div>

            <div className="bg-[#1a1a24] rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="h-3 w-3 text-gray-400" />
                <p className="text-xs text-gray-400">Avg/Day</p>
              </div>
              <p className="text-lg font-bold">{stats.avgPerDay.toFixed(1)}</p>
            </div>

            <div className="bg-[#1a1a24] rounded-lg p-3">
              <p className="text-xs text-gray-400 mb-1">Peak Hour</p>
              <p className="text-lg font-bold">
                {stats.peakHour.toString().padStart(2, '0')}:00
              </p>
            </div>

            <div className="bg-[#1a1a24] rounded-lg p-3">
              <p className="text-xs text-gray-400 mb-1">Active Days</p>
              <p className="text-lg font-bold">{stats.uniqueDays}</p>
            </div>
          </div>

          {/* Additional insights */}
          <div className="mt-4 pt-4 border-t border-gray-800">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary" className="bg-[#1a1a24] text-gray-300 text-xs">
                Most Active: {stats.mostActiveDay}
              </Badge>
              <Badge variant="secondary" className="bg-[#1a1a24] text-gray-300 text-xs">
                {stats.dateRange} days tracked
              </Badge>
              {viewMode === 'hourly' && (
                <Badge variant="secondary" className="bg-[#1a1a24] text-gray-300 text-xs">
                  {chartData.length} hours with activity
                </Badge>
              )}
            </div>
          </div>
        </>
      ) : (
        <div className="h-48 flex items-center justify-center">
          <Alert className="bg-[#1a1a24] border-gray-700">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Unable to generate {viewMode} view. Data may be insufficient or improperly formatted.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Data quality indicator */}
      {chartData.length > 0 && chartData.length < 3 && (
        <Alert className="mt-4 bg-amber-950/20 border-amber-900/50">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          <AlertDescription className="text-amber-200 text-xs">
            Limited data available. Visualization may not represent typical activity patterns.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}