import { Suspense } from 'react';
import { EntityDashboard } from '@/components/dashboard/entity-dashboard';
import { DashboardSkeleton } from '@/components/dashboard/dashboard-skeleton';
import { getServerSession } from 'next-auth';
import { OPTIONS } from "@/auth";
import { redirect } from 'next/navigation';

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await getServerSession(OPTIONS);
  if(!session){
    redirect('/auth')
  }
  if (session.user.role !== "SUPER_ADMIN") {
    redirect("/profile");
  }
  
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <Suspense fallback={<DashboardSkeleton />}>
        <EntityDashboard entityId={id} />
      </Suspense>
    </div>
  );
}