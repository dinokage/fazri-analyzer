'use client';

import { useState } from 'react';
import { Search, Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { AlertSeverity, AlertStatus } from '@/types/alert';

interface AlertFiltersProps {
  onFiltersChange: (filters: {
    status?: AlertStatus[];
    severity?: AlertSeverity[];
    search?: string;
  }) => void;
  activeFilters: {
    status?: AlertStatus[];
    severity?: AlertSeverity[];
    search?: string;
  };
}

const STATUS_OPTIONS: { value: AlertStatus; label: string }[] = [
  { value: 'created', label: 'Created' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'escalated', label: 'Escalated' },
];

const SEVERITY_OPTIONS: { value: AlertSeverity; label: string }[] = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

export function AlertFilters({ onFiltersChange, activeFilters }: AlertFiltersProps) {
  const [searchInput, setSearchInput] = useState(activeFilters.search || '');

  const handleStatusChange = (value: string) => {
    if (value === 'all') {
      onFiltersChange({ ...activeFilters, status: undefined });
    } else if (value === 'active') {
      onFiltersChange({
        ...activeFilters,
        status: ['created', 'assigned', 'acknowledged', 'investigating'],
      });
    } else {
      onFiltersChange({
        ...activeFilters,
        status: [value as AlertStatus],
      });
    }
  };

  const handleSeverityChange = (value: string) => {
    if (value === 'all') {
      onFiltersChange({ ...activeFilters, severity: undefined });
    } else {
      onFiltersChange({
        ...activeFilters,
        severity: [value as AlertSeverity],
      });
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onFiltersChange({ ...activeFilters, search: searchInput || undefined });
  };

  const clearFilters = () => {
    setSearchInput('');
    onFiltersChange({});
  };

  const hasActiveFilters =
    activeFilters.status?.length ||
    activeFilters.severity?.length ||
    activeFilters.search;

  const getStatusValue = () => {
    if (!activeFilters.status?.length) return 'all';
    if (
      activeFilters.status.length === 4 &&
      activeFilters.status.includes('created') &&
      activeFilters.status.includes('assigned') &&
      activeFilters.status.includes('acknowledged') &&
      activeFilters.status.includes('investigating')
    ) {
      return 'active';
    }
    return activeFilters.status[0];
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[200px] max-w-sm">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <Input
              placeholder="Search alerts..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9 bg-gray-900 border-gray-800"
            />
          </div>
        </form>

        {/* Status Filter */}
        <Select value={getStatusValue()} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-[160px] bg-gray-900 border-gray-800">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent className="bg-gray-900 border-gray-800">
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active Only</SelectItem>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Severity Filter */}
        <Select
          value={activeFilters.severity?.[0] || 'all'}
          onValueChange={handleSeverityChange}
        >
          <SelectTrigger className="w-[160px] bg-gray-900 border-gray-800">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent className="bg-gray-900 border-gray-800">
            <SelectItem value="all">All Severity</SelectItem>
            {SEVERITY_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="text-gray-400 hover:text-white"
          >
            <X className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="flex flex-wrap gap-2">
          {activeFilters.search && (
            <Badge variant="secondary" className="gap-1">
              Search: {activeFilters.search}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() => {
                  setSearchInput('');
                  onFiltersChange({ ...activeFilters, search: undefined });
                }}
              />
            </Badge>
          )}
          {activeFilters.status?.map((status) => (
            <Badge key={status} variant="secondary" className="gap-1">
              {STATUS_OPTIONS.find((o) => o.value === status)?.label || status}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() =>
                  onFiltersChange({
                    ...activeFilters,
                    status: activeFilters.status?.filter((s) => s !== status),
                  })
                }
              />
            </Badge>
          ))}
          {activeFilters.severity?.map((severity) => (
            <Badge key={severity} variant="secondary" className="gap-1">
              {SEVERITY_OPTIONS.find((o) => o.value === severity)?.label || severity}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() =>
                  onFiltersChange({
                    ...activeFilters,
                    severity: activeFilters.severity?.filter((s) => s !== severity),
                  })
                }
              />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
