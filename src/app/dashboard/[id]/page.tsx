import { Suspense } from 'react';
import { EntityDashboard } from '@/components/dashboard/entity-dashboard';
import { DashboardSkeleton } from '@/components/dashboard/dashboard-skeleton';
import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await getServerSession()
  if(!session){
    redirect('/auth')
  }
  
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <Suspense fallback={<DashboardSkeleton />}>
        <EntityDashboard entityId={id} />
      </Suspense>
    </div>
  );
}