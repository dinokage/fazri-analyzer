// components/dashboard/activity-timeline.tsx
'use client';

import { Wifi, BookOpen, Camera, MapPin, DoorOpen, Calendar, RefreshCw, AlertTriangle, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { format, formatDistanceToNow } from 'date-fns';
import { Badge } from '@/components/ui/badge';

interface TimelineEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  location: string;
  location_id: string;
  location_type: string | null;
}

interface TimelineGap {
  start_time: string;
  end_time: string;
  duration_hours: number;
  last_location: string;
  next_location: string;
  last_event_type: string;
  next_event_type: string;
}

interface TimelineData {
  entity_id: string;
  start_date: string;
  end_date: string;
  total_events: number;
  events: TimelineEvent[];
  gaps: TimelineGap[];
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

interface ActivityTimelineProps {
  timeline: TimelineData | null;
  entityId: string;
  onRefresh?: () => void;
}

type TimelineItem = {
  type: 'event' | 'gap';
  data: TimelineEvent | TimelineGap;
  timestamp: Date;
};

export function ActivityTimeline({ timeline, onRefresh }: ActivityTimelineProps) {
  const [selectedItem, setSelectedItem] = useState<TimelineItem | null>(null);
  const [showStatistics, setShowStatistics] = useState(false);

  const getEventIcon = (eventType: string) => {
    const type = eventType?.toLowerCase() || '';
    
    if (type.includes('wifi')) return <Wifi className="h-5 w-5" />;
    if (type.includes('library') || type.includes('book')) return <BookOpen className="h-5 w-5" />;
    if (type.includes('cctv') || type.includes('camera')) return <Camera className="h-5 w-5" />;
    if (type.includes('swipe') || type.includes('door')) return <DoorOpen className="h-5 w-5" />;
    if (type.includes('room') || type.includes('booking')) return <Calendar className="h-5 w-5" />;
    
    return <MapPin className="h-5 w-5" />;
  };

  const getLocationTypeIcon = (locationType: string | null | undefined) => {
    if (!locationType) return '📍'; // Default fallback
    
    const type = locationType.toLowerCase();
    
    if (type.includes('camera') || type.includes('cctv')) return '📹';
    if (type.includes('room')) return '🚪';
    if (type.includes('building')) return '🏢';
    if (type.includes('lab')) return '🔬';
    if (type.includes('door')) return '🚪';
    if (type.includes('gate')) return '🚧';
    if (type.includes('wifi') || type.includes('access')) return '📡';
    
    return '📍'; // Default fallback
  };

  const formatEventType = (eventType: string) => {
    if (!eventType) return 'Unknown Event';
    return eventType
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const formatLocationType = (locationType: string | null | undefined) => {
    if (!locationType) return 'Unknown location type';
    return locationType
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const formatTime = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'h:mm a');
    } catch {
      return timestamp;
    }
  };

  const formatDuration = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)} minutes`;
    if (hours < 24) return `${hours.toFixed(1)} hours`;
    const days = Math.floor(hours / 24);
    const remainingHours = Math.round(hours % 24);
    return `${days}d ${remainingHours}h`;
  };

  if (!timeline) {
    return (
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-6">Activity Timeline</h2>
        <p className="text-gray-400 text-center py-8">No timeline data available</p>
      </div>
    );
  }

  // Merge events and gaps into a single chronological timeline
  const timelineItems: TimelineItem[] = [];

  // Add all events with null checking
  if (timeline.events && Array.isArray(timeline.events)) {
    timeline.events.forEach(event => {
      timelineItems.push({
        type: 'event',
        data: event,
        timestamp: new Date(event.timestamp),
      });
    });
  }

  // Add all gaps with null checking
  if (timeline.gaps && Array.isArray(timeline.gaps)) {
    timeline.gaps.forEach(gap => {
      timelineItems.push({
        type: 'gap',
        data: gap,
        timestamp: new Date(gap.start_time),
      });
    });
  }

  // Sort by timestamp (most recent first)
  timelineItems.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

  return (
    <>
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold">Activity Timeline</h2>
            <p className="text-xs text-gray-400 mt-1">
              {timeline.total_events || 0} events • {timeline.statistics?.total_gaps || 0} gaps
            </p>
          </div>
          <div className="flex gap-2">
            {timeline.statistics && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowStatistics(true)}
                className="text-gray-400 hover:text-white"
              >
                Stats
              </Button>
            )}
            {onRefresh && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                className="text-gray-400 hover:text-white"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        
        <ScrollArea className="h-[500px] pr-4">
          <div className="space-y-4 relative">
            {/* Vertical timeline line */}
            <div className="absolute left-6 top-8 bottom-8 w-px bg-gray-700" />
            
            {timelineItems.length === 0 ? (
              <p className="text-gray-400 text-center py-8">No activity recorded</p>
            ) : (
              timelineItems.map((item, idx) => (
                <div key={idx} className="relative pl-14">
                  {item.type === 'gap' ? (
                    // Gap indicator
                    <div className="flex items-center gap-2 py-2">
                      <div className="flex-1 border-t-2 border-dashed border-amber-600/50" />
                      <div className="flex items-center gap-2 text-amber-500 text-sm">
                        <AlertTriangle className="h-4 w-4" />
                        <span>
                          Gap: {formatDuration((item.data as TimelineGap).duration_hours)}
                        </span>
                      </div>
                      <div className="flex-1 border-t-2 border-dashed border-amber-600/50" />
                    </div>
                  ) : (
                    // Event card
                    <>
                      {/* Icon */}
                      <div className="absolute left-0 top-0 w-12 h-12 rounded-lg bg-[#1a1a24] flex items-center justify-center">
                        {getEventIcon((item.data as TimelineEvent).event_type)}
                      </div>

                      {/* Event Card */}
                      <div 
                        className={cn(
                          "bg-[#1a1a24] rounded-lg p-4 cursor-pointer transition-colors hover:bg-[#242430]",
                          selectedItem === item && "bg-[#242430] border border-blue-500/30"
                        )}
                        onClick={() => setSelectedItem(item === selectedItem ? null : item)}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-medium">
                                {formatEventType((item.data as TimelineEvent).event_type)}
                              </h4>
                              <Badge 
                                variant="secondary" 
                                className="text-xs bg-[#14141a]"
                              >
                                {(item.data as TimelineEvent).event_id}
                              </Badge>
                            </div>
                            
                            <div className="flex items-center gap-2 text-sm text-gray-400">
                              <span>{getLocationTypeIcon((item.data as TimelineEvent).location_type)}</span>
                              <span>{(item.data as TimelineEvent).location || 'Unknown Location'}</span>
                            </div>

                            {/* Location type with fallback */}
                            <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                              {(item.data as TimelineEvent).location_type ? (
                                <span>{formatLocationType((item.data as TimelineEvent).location_type)}</span>
                              ) : (
                                <span className="flex items-center gap-1">
                                  <HelpCircle className="h-3 w-3" />
                                  Location type not specified
                                </span>
                              )}
                            </div>
                          </div>
                          
                          <div className="text-right">
                            <span className="text-sm text-gray-400 block">
                              {formatTime((item.data as TimelineEvent).timestamp)}
                            </span>
                            <span className="text-xs text-gray-500">
                              {formatDistanceToNow(new Date((item.data as TimelineEvent).timestamp), { 
                                addSuffix: true 
                              })}
                            </span>
                          </div>
                        </div>

                        {/* Expanded details */}
                        {selectedItem === item && (
                          <div className="mt-4 pt-4 border-t border-gray-700">
                            <div className="grid grid-cols-2 gap-3 text-sm">
                              <div>
                                <p className="text-gray-400 text-xs mb-1">Event ID</p>
                                <p className="font-mono text-xs">{(item.data as TimelineEvent).event_id}</p>
                              </div>
                              <div>
                                <p className="text-gray-400 text-xs mb-1">Location ID</p>
                                <p className="font-mono text-xs">{(item.data as TimelineEvent).location_id || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-400 text-xs mb-1">Event Type</p>
                                <p className="text-xs">{(item.data as TimelineEvent).event_type || 'Unknown'}</p>
                              </div>
                              <div>
                                <p className="text-gray-400 text-xs mb-1">Location Type</p>
                                <p className="text-xs">
                                  {(item.data as TimelineEvent).location_type || (
                                    <span className="text-gray-500 italic">Not specified</span>
                                  )}
                                </p>
                              </div>
                              <div className="col-span-2">
                                <p className="text-gray-400 text-xs mb-1">Full Timestamp</p>
                                <p className="text-xs font-mono">
                                  {format(new Date((item.data as TimelineEvent).timestamp), 'PPpp')}
                                </p>
                              </div>
                            </div>

                            {/* Debug info - show raw data if location_type is null */}
                            {!(item.data as TimelineEvent).location_type && (
                              <div className="mt-3 pt-3 border-t border-gray-700">
                                <p className="text-xs text-gray-500 mb-2">Raw event data:</p>
                                <pre className="text-xs bg-[#14141a] p-2 rounded overflow-x-auto text-gray-400">
                                  {JSON.stringify(item.data, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </ScrollArea>

        {/* Timeline summary */}
        {timeline.start_date && timeline.end_date && (
          <div className="mt-4 pt-4 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
            <span>
              From: {format(new Date(timeline.start_date), 'MMM dd, yyyy')}
            </span>
            <span>
              To: {format(new Date(timeline.end_date), 'MMM dd, yyyy')}
            </span>
          </div>
        )}
      </div>

      {/* Statistics Dialog */}
      <Dialog open={showStatistics} onOpenChange={setShowStatistics}>
        <DialogContent className="bg-[#14141a] border-gray-800 max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Timeline Statistics</DialogTitle>
            <DialogDescription>
              Activity analysis for {timeline.entity_id}
            </DialogDescription>
          </DialogHeader>
          
          {timeline.statistics && (
            <div className="space-y-6">
              {/* Overview */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[#1a1a24] rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Total Events</p>
                  <p className="text-2xl font-bold">{timeline.total_events || 0}</p>
                </div>
                <div className="bg-[#1a1a24] rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Total Gaps</p>
                  <p className="text-2xl font-bold">{timeline.statistics.total_gaps || 0}</p>
                </div>
                <div className="bg-[#1a1a24] rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Gap Hours</p>
                  <p className="text-2xl font-bold">
                    {timeline.statistics.total_gap_hours?.toFixed(0) || 0}
                  </p>
                </div>
                <div className="bg-[#1a1a24] rounded-lg p-4">
                  <p className="text-xs text-gray-400 mb-1">Avg/Day</p>
                  <p className="text-2xl font-bold">
                    {timeline.statistics.avg_events_per_day?.toFixed(1) || 0}
                  </p>
                </div>
              </div>

              {/* Event Type Distribution */}
              {timeline.statistics.event_type_distribution && 
               Object.keys(timeline.statistics.event_type_distribution).length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Event Types</h4>
                  <div className="space-y-2">
                    {Object.entries(timeline.statistics.event_type_distribution).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between bg-[#1a1a24] rounded p-3">
                        <span className="capitalize">{formatEventType(type)}</span>
                        <Badge variant="secondary" className="bg-[#14141a]">
                          {count}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Location Frequency */}
              {timeline.statistics.location_frequency && 
               Object.keys(timeline.statistics.location_frequency).length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">
                    Location Frequency
                    {timeline.statistics.most_visited_location && (
                      <span className="text-sm text-gray-400 ml-2">
                        (Most visited: {timeline.statistics.most_visited_location})
                      </span>
                    )}
                  </h4>
                  <div className="space-y-2">
                    {Object.entries(timeline.statistics.location_frequency)
                      .sort(([, a], [, b]) => (b as number) - (a as number))
                      .map(([location, count]) => {
                        const maxCount = Math.max(...Object.values(timeline.statistics?.location_frequency || {}));
                        return (
                          <div key={location} className="flex items-center justify-between bg-[#1a1a24] rounded p-3">
                            <span className="font-mono text-sm">{location}</span>
                            <div className="flex items-center gap-3">
                              <div className="w-24 bg-gray-700 rounded-full h-2">
                                <div 
                                  className="bg-blue-600 h-2 rounded-full" 
                                  style={{ 
                                    width: `${((count as number) / maxCount) * 100}%` 
                                  }}
                                />
                              </div>
                              <Badge variant="secondary" className="bg-[#14141a] w-12 justify-center">
                                {count}
                              </Badge>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}

              {/* Activity Periods */}
              {timeline.statistics.activity_periods && 
               Object.keys(timeline.statistics.activity_periods).length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Activity by Time of Day</h4>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(timeline.statistics.activity_periods).map(([period, count]) => (
                      <div key={period} className="bg-[#1a1a24] rounded-lg p-4">
                        <p className="text-xs text-gray-400 mb-1 capitalize">{period}</p>
                        <p className="text-xl font-bold">{count}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Day of Week Distribution */}
              {timeline.statistics.day_of_week_distribution && 
               Object.keys(timeline.statistics.day_of_week_distribution).length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Activity by Day</h4>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(timeline.statistics.day_of_week_distribution).map(([day, count]) => (
                      <div key={day} className="bg-[#1a1a24] rounded p-3 text-center">
                        <p className="text-xs text-gray-400 mb-1">{day}</p>
                        <p className="text-lg font-bold">{count}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hourly Distribution */}
              {timeline.statistics.hourly_distribution && 
               Object.keys(timeline.statistics.hourly_distribution).length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Hourly Activity</h4>
                  <div className="grid grid-cols-6 gap-2">
                    {Object.entries(timeline.statistics.hourly_distribution)
                      .sort(([a], [b]) => parseInt(a) - parseInt(b))
                      .map(([hour, count]) => (
                        <div key={hour} className="bg-[#1a1a24] rounded p-2 text-center">
                          <p className="text-xs text-gray-400">{hour}:00</p>
                          <p className="text-sm font-bold">{count}</p>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}