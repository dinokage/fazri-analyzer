"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { Button } from "@/components/ui/button"

export type EntityRow = {
  id: string
  name: string
  email: string
  entity_type: string
  department: string
}

const columns: ColumnDef<EntityRow>[] = [
  {
    header: "ID",
    accessorKey: "id",
    cell: ({ row }) => <span>{row.original.id}</span>,
  },
  {
    header: "Name",
    accessorKey: "name",
  },
  {
    header: "Email",
    accessorKey: "email",
  },
  {
    header: "Type",
    accessorKey: "entity_type",
  },
  {
    header: "Department",
    accessorKey: "department",
  },
]

export function EntitiesTable() {
  const router = useRouter()
  const [data, setData] = React.useState<EntityRow[]>([])
  const [page, setPage] = React.useState(0)
  const [total, setTotal] = React.useState(0)
  const limit = 10

  const fetchEntities = React.useCallback(async () => {
    try {
      const res = await fetch(
        `http://dino.hextasphere.com:8000/api/v1/entities/?skip=${page * limit}&limit=${limit}`,
        { headers: { accept: "application/json" } }
      )
      const json = await res.json()
      setTotal(json.total)
      const mapped = json.entities.map((e: any) => ({
        id: e.entity_id,
        name: e.name,
        email: e.email,
        entity_type: e.entity_type,
        department: e.department,
      }))
      setData(mapped)
    } catch (err) {
      console.error("Failed to fetch entities:", err)
    }
  }, [page])

  React.useEffect(() => {
    fetchEntities()
  }, [fetchEntities])

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  const totalPages = Math.ceil(total / limit)

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card text-card-foreground overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-3 py-2 text-left font-medium text-foreground"
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
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                role="button"
                tabIndex={0}
                onClick={() => router.push(`/dashboard/${row.original.id}`)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    router.push(`/dashboard/${row.original.id}`)
                  }
                }}
                className="border-b hover:bg-accent cursor-pointer"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2 align-middle">
                    {flexRender(
                      cell.column.columnDef.cell,
                      cell.getContext()
                    )}
                  </td>
                ))}
              </tr>
            ))}
            {table.getRowModel().rows.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-6 text-center text-muted-foreground"
                >
                  No entities found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          disabled={page === 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
        >
          Previous
        </Button>
        <span className="text-sm text-muted-foreground">
          Page {page + 1} of {totalPages || 1}
        </span>
        <Button
          variant="outline"
          disabled={(page + 1) >= totalPages}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
