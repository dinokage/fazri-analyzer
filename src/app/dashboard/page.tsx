import EntitiesTanStackTable from '@/components/entities-tanstack-table'
import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
export default async function EntitiesPage() {
  const session = await getServerSession()
  if(!session){
    redirect('/auth')
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Entities</h2>
      </div>
      <EntitiesTanStackTable />
    </div>
  )
}