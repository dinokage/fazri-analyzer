"use client";
import React from "react";
import {
  useReactTable,
  getCoreRowModel,
  ColumnDef,
  flexRender,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, ChevronLeft, ChevronRight } from "lucide-react";

const API_BASE_URL = 'https://ecell.rdpdc.in';

// Types
type Identifier = {
  type: string;
  value: string;
  source: string;
  confidence: number;
  first_seen: string;
  last_seen: string;
};

type Entity = {
  entity_id: string;
  identifiers: Identifier[];
  name: string;
  email: string;
  entity_type: string;
  department: string;
  linked_entity_ids: string[];
  confidence_score: number;
  created_at: string;
  updated_at: string;
};

type EntitiesResponse = {
  entities: Entity[];
  total: number;
  limit: number;
  skip: number;
};

// Custom hook for fetching entities
function useEntities(
  limit: number,
  skip: number,
  department?: string,
  entityType?: string
) {
  const [data, setData] = React.useState<EntitiesResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const fetchEntities = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          limit: limit.toString(),
          skip: skip.toString(),
        });

        if (department && department !== "all") {
          params.append("department", department);
        }

        if (entityType && entityType !== "all") {
          params.append("entity_type", entityType);
        }

        const response = await fetch(
          `${API_BASE_URL}/api/v1/entities/?${params}`
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
        console.error("Error fetching entities:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchEntities();
  }, [limit, skip, department, entityType]);

  return { data, isLoading, error };
}

// Table columns definition
const columns: ColumnDef<Entity>[] = [
  {
    accessorKey: "entity_id",
    header: "Entity ID",
    cell: ({ row }) => (
      <span className="font-mono text-sm">{row.getValue("entity_id")}</span>
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <div className="font-medium">{row.getValue("name")}</div>
    ),
  },
  {
    accessorKey: "email",
    header: "Email",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {row.getValue("email")}
      </span>
    ),
  },
  {
    accessorKey: "entity_type",
    header: "Type",
    cell: ({ row }) => (
      <Badge variant="outline" className="capitalize">
        {row.getValue("entity_type")}
      </Badge>
    ),
  },
  {
    accessorKey: "department",
    header: "Department",
    cell: ({ row }) => (
      <Badge variant="secondary">{row.getValue("department")}</Badge>
    ),
  },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => {
      const entityId = row.getValue("entity_id") as string;
      return (
        <Button variant="outline" size="sm" asChild>
          <a href={`/dashboard/${entityId}`}> View Profile</a>
        </Button>
      );
    },
  },
];

// Main component
export default function EntitiesTanStackTable() {
  const [pageSize, setPageSize] = React.useState(10);
  const [pageIndex, setPageIndex] = React.useState(0);
  const [department, setDepartment] = React.useState<string>("all");
  const [entityType, setEntityType] = React.useState<string>("all");

  const skip = pageIndex * pageSize;
  const { data, isLoading, error } = useEntities(
    pageSize,
    skip,
    department,
    entityType
  );

  const table = useReactTable({
    data: data?.entities ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: data ? Math.ceil(data.total / pageSize) : 0,
    state: {
      pagination: {
        pageIndex,
        pageSize,
      },
    },
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  // Get unique departments
  const departments = React.useMemo(() => {
    if (!data?.entities) return [];
    const depts = new Set(data.entities.map((e) => e.department));
    return Array.from(depts).sort();
  }, [data]);

  return (
    <div className="space-y-4">
      {/* Controls */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Show:</span>
            <Select
              value={pageSize.toString()}
              onValueChange={(value) => {
                setPageSize(Number(value));
                setPageIndex(0);
              }}
            >
              <SelectTrigger className="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-sm text-muted-foreground">entries</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Department:</span>
            <Select
              value={department}
              onValueChange={(value) => {
                setDepartment(value);
                setPageIndex(0);
              }}
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {departments.map((dept) => (
                  <SelectItem key={dept} value={dept}>
                    {dept}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Type:</span>
            <Select
              value={entityType}
              onValueChange={(value) => {
                setEntityType(value);
                setPageIndex(0);
              }}
            >
              <SelectTrigger className="w-[130px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="student">Student</SelectItem>
                <SelectItem value="staff">Staff</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card>
        <div className="relative">
          {isLoading && (
            <div className="absolute inset-0 bg-background/50 backdrop-blur-sm flex items-center justify-center z-10">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {error && (
            <div className="p-8 text-center">
              <p className="text-destructive font-medium">Error loading data</p>
              <p className="text-sm text-muted-foreground mt-1">{error}</p>
            </div>
          )}

          {!error && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b">
                  {table.getHeaderGroups().map((headerGroup) => (
                    <tr key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <th
                          key={header.id}
                          className="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
                        >
                          {header.isPlaceholder
                            ? null
                            : flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows?.length ? (
                    table.getRowModel().rows.map((row) => (
                      <tr
                        key={row.id}
                        className="border-b hover:bg-muted/50 transition-colors"
                      >
                        {row.getVisibleCells().map((cell) => (
                          <td key={cell.id} className="px-4 py-3">
                            {flexRender(
                              cell.column.columnDef.cell,
                              cell.getContext()
                            )}
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td
                        colSpan={columns.length}
                        className="h-24 text-center text-muted-foreground"
                      >
                        No results.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      {/* Pagination */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Page {pageIndex + 1} of {totalPages || 1}
          </div>

          {data && (
          <div className="text-sm text-muted-foreground">
            Showing {skip + 1} to {Math.min(skip + pageSize, data.total)} of{" "}
            {data.total} entries
            {(department !== "all" || entityType !== "all") && " (filtered)"}
          </div>
        )}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageIndex(0)}
              disabled={pageIndex === 0 || isLoading}
            >
              First
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageIndex((prev) => Math.max(0, prev - 1))}
              disabled={pageIndex === 0 || isLoading}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setPageIndex((prev) => Math.min(totalPages - 1, prev + 1))
              }
              disabled={pageIndex >= totalPages - 1 || isLoading}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageIndex(totalPages - 1)}
              disabled={pageIndex >= totalPages - 1 || isLoading}
            >
              Last
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
