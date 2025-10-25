'use client';

import { useEffect, useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  ColumnDef,
  flexRender,
  ColumnFiltersState,
  SortingState,
} from '@tanstack/react-table';
import { apiClient } from '@/lib/api-client';
import { Anomaly, AnomalySeverity } from '@/types/anomaly';
import { format } from 'date-fns';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowUpDown, ChevronLeft, ChevronRight, AlertCircle, ShieldAlert, TrendingUp, MapPin } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { PieChart, Pie, Cell, Legend, ResponsiveContainer } from 'recharts';

const severityColors = {
  low: 'bg-blue-600',
  medium: 'bg-yellow-600',
  high: 'bg-orange-600',
  critical: 'bg-red-600',
};

const severityChartColors = {
  low: '#2563eb',
  medium: '#ca8a04',
  high: '#ea580c',
  critical: '#dc2626',
};

const formatAnomalyType = (type: string) => {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'timestamp', desc: true }
  ]);

  // Calculate statistics
  const statistics = useMemo(() => {
    const severityCount: Record<AnomalySeverity, number> = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    };

    const typeCount: Record<string, number> = {};
    const locationCount: Record<string, number> = {};

    anomalies.forEach((anomaly) => {
      severityCount[anomaly.severity]++;
      typeCount[anomaly.type] = (typeCount[anomaly.type] || 0) + 1;
      locationCount[anomaly.location] = (locationCount[anomaly.location] || 0) + 1;
    });

    const severityData = Object.entries(severityCount).map(([severity, count]) => ({
      severity: severity.toUpperCase(),
      count,
      fill: severityChartColors[severity as AnomalySeverity],
    }));

    const topTypes = Object.entries(typeCount)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5);

    const topLocations = Object.entries(locationCount)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5);

    return {
      total: anomalies.length,
      severityCount,
      severityData,
      topTypes,
      topLocations,
      criticalCount: severityCount.critical,
      highCount: severityCount.high,
    };
  }, [anomalies]);

  const columns: ColumnDef<Anomaly>[] = [
    {
      accessorKey: 'timestamp',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="hover:bg-gray-800"
          >
            Timestamp
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const date = new Date(row.getValue('timestamp'));
        return (
          <div className="text-sm">
            <div>{format(date, 'MMM dd, yyyy')}</div>
            <div className="text-gray-400">{format(date, 'HH:mm:ss')}</div>
          </div>
        );
      },
    },
    {
      accessorKey: 'type',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="hover:bg-gray-800"
          >
            Type
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => formatAnomalyType(row.getValue('type')),
      filterFn: 'includesString',
    },
    {
      accessorKey: 'severity',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="hover:bg-gray-800"
          >
            Severity
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        const severity = row.getValue('severity') as keyof typeof severityColors;
        return (
          <Badge className={severityColors[severity]}>
            {severity.toUpperCase()}
          </Badge>
        );
      },
      filterFn: 'equals',
    },
    {
      accessorKey: 'entity_name',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="hover:bg-gray-800"
          >
            Entity
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div className="text-sm">
          <div className="font-medium">{row.getValue('entity_name')}</div>
          <div className="text-gray-400">{row.original.entity_id}</div>
        </div>
      ),
      filterFn: 'includesString',
    },
    {
      accessorKey: 'location_name',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="hover:bg-gray-800"
          >
            Location
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{row.getValue('location_name')}</div>
          <div className="text-gray-400 text-xs">{row.original.location}</div>
        </div>
      ),
      filterFn: 'includesString',
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <div className="max-w-md text-sm text-gray-300">
          {row.getValue('description')}
        </div>
      ),
      filterFn: 'includesString',
    },
  ];

  const table = useReactTable({
    data: anomalies,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onColumnFiltersChange: setColumnFilters,
    onSortingChange: setSorting,
    state: {
      columnFilters,
      sorting,
    },
    initialState: {
      pagination: {
        pageSize: 20,
      },
    },
  });

  useEffect(() => {
    loadAnomalies();
  }, []);

  const loadAnomalies = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getAllAnomalies();

      if (response.success && response.data?.anomalies) {
        setAnomalies(response.data.anomalies);
      } else {
        setError('Failed to load anomalies');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load anomalies');
      console.error('Error loading anomalies:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-800 rounded w-48" />
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
        <h1 className="text-3xl font-bold">Anomalies</h1>
        <Badge variant="secondary" className="text-sm">
          {anomalies.length} Total Anomalies
        </Badge>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Anomalies Card */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Total Anomalies</p>
              <p className="text-3xl font-bold">{statistics.total}</p>
            </div>
            <div className="p-3 bg-blue-600/10 rounded-lg">
              <ShieldAlert className="h-6 w-6 text-blue-500" />
            </div>
          </div>
        </div>

        {/* Critical Anomalies Card */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Critical</p>
              <p className="text-3xl font-bold text-red-500">{statistics.criticalCount}</p>
            </div>
            <div className="p-3 bg-red-600/10 rounded-lg">
              <AlertCircle className="h-6 w-6 text-red-500" />
            </div>
          </div>
        </div>

        {/* High Severity Card */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">High Severity</p>
              <p className="text-3xl font-bold text-orange-500">{statistics.highCount}</p>
            </div>
            <div className="p-3 bg-orange-600/10 rounded-lg">
              <TrendingUp className="h-6 w-6 text-orange-500" />
            </div>
          </div>
        </div>

        {/* Top Location Card */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Top Location</p>
              <p className="text-xl font-bold truncate">
                {statistics.topLocations[0]?.[0] || 'N/A'}
              </p>
              <p className="text-sm text-gray-500">
                {statistics.topLocations[0]?.[1] || 0} anomalies
              </p>
            </div>
            <div className="p-3 bg-purple-600/10 rounded-lg">
              <MapPin className="h-6 w-6 text-purple-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity Distribution Pie Chart */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Severity Distribution</h2>
          <div className="h-[300px] flex items-center justify-center">
            <ChartContainer
              config={{
                low: { label: 'Low', color: severityChartColors.low },
                medium: { label: 'Medium', color: severityChartColors.medium },
                high: { label: 'High', color: severityChartColors.high },
                critical: { label: 'Critical', color: severityChartColors.critical },
              }}
              className="w-full h-full"
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statistics.severityData}
                    cx="50%"
                    cy="45%"
                    innerRadius={60}
                    outerRadius={90}
                    fill="#8884d8"
                    dataKey="count"
                    paddingAngle={2}
                  >
                    {statistics.severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <ChartTooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-[#1a1a24] border border-gray-700 rounded-lg p-3 shadow-xl">
                            <p className="text-sm font-medium">{payload[0].payload.severity}</p>
                            <p className="text-lg font-bold text-blue-400">{payload[0].value}</p>
                            <p className="text-xs text-gray-400">
                              {((payload[0].value as number / statistics.total) * 100).toFixed(1)}%
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    //eslint-disable-next-line @typescript-eslint/no-explicit-any
                    formatter={(value, entry: any) => (
                      <span className="text-sm">
                        {value} ({entry.payload.count})
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </ChartContainer>
          </div>
        </div>

        {/* Top Anomaly Types */}
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Top Anomaly Types</h2>
          <div className="space-y-3">
            {statistics.topTypes.map(([type, count], index) => (
              <div key={type} className="flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <span className="text-gray-400 font-mono text-sm w-6">
                    #{index + 1}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{formatAnomalyType(type)}</p>
                    <div className="w-full bg-gray-800 rounded-full h-2 mt-1">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{
                          width: `${(count / statistics.total) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
                <span className="text-sm font-bold ml-4">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="text-sm text-gray-400 mb-2 block">Entity Name</label>
            <Input
              placeholder="Filter by entity..."
              value={(table.getColumn('entity_name')?.getFilterValue() as string) ?? ''}
              onChange={(event) =>
                table.getColumn('entity_name')?.setFilterValue(event.target.value)
              }
              className="bg-[#1a1a24] border-gray-700"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 mb-2 block">Type</label>
            <Input
              placeholder="Filter by type..."
              value={(table.getColumn('type')?.getFilterValue() as string) ?? ''}
              onChange={(event) =>
                table.getColumn('type')?.setFilterValue(event.target.value)
              }
              className="bg-[#1a1a24] border-gray-700"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 mb-2 block">Severity</label>
            <Select
              value={(table.getColumn('severity')?.getFilterValue() as string) ?? 'all'}
              onValueChange={(value) =>
                table.getColumn('severity')?.setFilterValue(value === 'all' ? '' : value)
              }
            >
              <SelectTrigger className="bg-[#1a1a24] border-gray-700">
                <SelectValue placeholder="All severities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All severities</SelectItem>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm text-gray-400 mb-2 block">Location</label>
            <Input
              placeholder="Filter by location..."
              value={(table.getColumn('location_name')?.getFilterValue() as string) ?? ''}
              onChange={(event) =>
                table.getColumn('location_name')?.setFilterValue(event.target.value)
              }
              className="bg-[#1a1a24] border-gray-700"
            />
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.resetColumnFilters()}
            className="bg-[#1a1a24] border-gray-700 hover:bg-[#242430]"
          >
            Clear Filters
          </Button>
          <span className="text-sm text-gray-400">
            Showing {table.getFilteredRowModel().rows.length} of {anomalies.length} anomalies
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="bg-[#14141a] rounded-lg border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="border-gray-800 hover:bg-transparent">
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id} className="text-gray-400">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    className="border-gray-800 hover:bg-[#1a1a24]"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={columns.length} className="h-24 text-center text-gray-400">
                    No anomalies found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-4 border-t border-gray-800">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Rows per page:</span>
            <Select
              value={`${table.getState().pagination.pageSize}`}
              onValueChange={(value) => {
                table.setPageSize(Number(value));
              }}
            >
              <SelectTrigger className="h-8 w-[70px] bg-[#1a1a24] border-gray-700">
                <SelectValue placeholder={table.getState().pagination.pageSize} />
              </SelectTrigger>
              <SelectContent side="top">
                {[10, 20, 30, 40, 50].map((pageSize) => (
                  <SelectItem key={pageSize} value={`${pageSize}`}>
                    {pageSize}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-6">
            <span className="text-sm text-gray-400">
              Page {table.getState().pagination.pageIndex + 1} of{' '}
              {table.getPageCount()}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="bg-[#1a1a24] border-gray-700 hover:bg-[#242430]"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="bg-[#1a1a24] border-gray-700 hover:bg-[#242430]"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
