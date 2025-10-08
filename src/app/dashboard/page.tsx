import EntitiesTanStackTable from '@/components/entities-tanstack-table'
import { getServerSession } from 'next-auth'
import { OPTIONS } from "@/auth";
import { redirect } from 'next/navigation'
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Dashboard `,
};
export default async function EntitiesPage() {
  const session = await getServerSession(OPTIONS);
  if(!session){
    redirect('/auth')
  }
  if (session.user.role !== "SUPER_ADMIN") {
    redirect("/dashboard/profile");
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