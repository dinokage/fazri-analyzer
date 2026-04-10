// components/dashboard/dashboard-filters.tsx
'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export function DashboardFilters() {
  return (
    <div className="flex gap-4 p-4 bg-[#14141a] rounded-lg border border-gray-800">
      <Select defaultValue="all">
        <SelectTrigger className="w-[200px] bg-[#1a1a24] border-gray-700">
          <SelectValue placeholder="Entity Type" />
        </SelectTrigger>
        <SelectContent className="bg-[#1a1a24] border-gray-700">
          <SelectItem value="all">Entity Type</SelectItem>
          <SelectItem value="student">Student</SelectItem>
          <SelectItem value="staff">Staff</SelectItem>
          <SelectItem value="visitor">Visitor</SelectItem>
        </SelectContent>
      </Select>

      <Select defaultValue="all">
        <SelectTrigger className="w-[200px] bg-[#1a1a24] border-gray-700">
          <SelectValue placeholder="Name/ID" />
        </SelectTrigger>
        <SelectContent className="bg-[#1a1a24] border-gray-700">
          <SelectItem value="all">Name/ID</SelectItem>
        </SelectContent>
      </Select>

      <Select defaultValue="7days">
        <SelectTrigger className="w-[200px] bg-[#1a1a24] border-gray-700">
          <SelectValue placeholder="Time Range" />
        </SelectTrigger>
        <SelectContent className="bg-[#1a1a24] border-gray-700">
          <SelectItem value="today">Today</SelectItem>
          <SelectItem value="7days">Last 7 days</SelectItem>
          <SelectItem value="30days">Last 30 days</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}