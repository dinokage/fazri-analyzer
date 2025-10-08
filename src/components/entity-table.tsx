"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { type ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table"

export type EntityRow = {
  id: string
  name: string
  last_seen: string
  last_location: string
}

export function EntitiesTable({ data }: { data: EntityRow[] }) {
  const router = useRouter()
  const columns = React.useMemo<ColumnDef<EntityRow>[]>(
    () => [
      { header: "Entity ID", accessorKey: "id" },
      { header: "Name", accessorKey: "name" },
      { header: "Last Seen", accessorKey: "last_seen" },
      { header: "Last Location", accessorKey: "last_location" },
    ],
    [],
  )

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="rounded-lg border bg-card text-card-foreground">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b">
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="px-3 py-2 text-left font-medium text-foreground">
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
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
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {table.getRowModel().rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-3 py-6 text-center text-muted-foreground">
                No entities found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
