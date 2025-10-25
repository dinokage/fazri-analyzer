
'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { ZoneForecast } from '@/types/zone';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ChartContainer } from '@/components/ui/chart';
import { TrendingUp } from 'lucide-react';

interface PredictiveZoneForecastProps {
  zoneId: string;
}

export function PredictiveZoneForecast({ zoneId }: PredictiveZoneForecastProps) {
  const [forecast, setForecast] = useState<ZoneForecast[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadForecastData = async () => {
      try {
        setLoading(true);
        setError(null);
        const forecastRes = await apiClient.getZoneForecast(zoneId);
        console.log('Forecast API Response:', forecastRes);
        if (forecastRes.success) {
          setForecast(forecastRes.data.forecasts);
        } else {
          setError(forecastRes.detail || 'Failed to load forecast data');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    loadForecastData();
  }, [zoneId]);

  if (loading) {
    return (
      <Card className="bg-[#14141a] border-gray-800">
        <CardHeader>
          <CardTitle>Predictive Zone Forecast</CardTitle>
          <CardDescription>Forecasting future zone occupancy.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] flex items-center justify-center">
            <div className="animate-pulse h-full w-full bg-gray-800 rounded-md" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-[#14141a] border-gray-800">
        <CardHeader>
          <CardTitle>Predictive Zone Forecast</CardTitle>
          <CardDescription>Forecasting future zone occupancy.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] flex items-center justify-center text-red-500">
            <p>{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-[#14141a] border-gray-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-blue-500" />
          Predictive Zone Forecast
        </CardTitle>
        <CardDescription>
          Predicted occupancy for the next 24 hours.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            predicted_occupancy: {
              label: 'Predicted Occupancy',
              color: '#3b82f6',
            },
          }}
          className="h-[400px] w-full"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={forecast} margin={{ left: 12, right: 12, top: 12, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
              <XAxis
                dataKey="target_datetime"
                stroke="#6b7280"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              />
              <YAxis
                stroke="#6b7280"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                label={{ value: 'Predicted Occupancy', angle: -90, position: 'insideLeft', style: { fill: '#6b7280', fontSize: 12 } }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-[#1a1a24] border border-gray-700 rounded-lg p-3 shadow-xl">
                        <p className="text-sm font-medium mb-1">{new Date(payload[0].payload.target_datetime).toLocaleString()}</p>
                        <p className="text-xs text-gray-400">Predicted Occupancy: <span className="text-lg font-bold text-blue-400">{payload[0].payload.predicted_occupancy}</span></p>
                        <p className="text-xs text-gray-400">Confidence: <span className="text-sm font-semibold text-green-400">{(payload[0].payload.confidence * 100).toFixed(0)}%</span></p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Line
                type="monotone"
                dataKey="predicted_occupancy"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
