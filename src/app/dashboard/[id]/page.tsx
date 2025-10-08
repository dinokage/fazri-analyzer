// app/dashboard/[id]/page.tsx
import { Suspense } from 'react';
import { EntityDashboard } from '@/components/dashboard/entity-dashboard';
import { DashboardSkeleton } from '@/components/dashboard/dashboard-skeleton';

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <Suspense fallback={<DashboardSkeleton />}>
        <EntityDashboard entityId={id} />
      </Suspense>
    </div>
  );
}