import { entitiesForTable } from "@/lib/entities"
import { EntitiesTable } from "@/components/entity-table"

export default function EntitiesPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-pretty">Entities</h2>
      </div>
      <EntitiesTable data={entitiesForTable} />
    </div>
  )
}
