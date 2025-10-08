import EntitiesTanStackTable from '@/components/entities-tanstack-table'

export default function EntitiesPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Entities</h2>
      </div>
      <EntitiesTanStackTable />
    </div>
  )
}