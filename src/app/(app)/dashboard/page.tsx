import EntitiesTanStackTable from '@/components/entities-tanstack-table'
import { Metadata } from 'next';
import { DashboardLayout } from '@/components/dashboard/dashboard-layout';

export const metadata:Metadata = {
  title: `Dashboard `,
};

export default function EntitiesPage() {
  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Entities</h2>
      </div>
      <EntitiesTanStackTable />
    </DashboardLayout>
  )
}