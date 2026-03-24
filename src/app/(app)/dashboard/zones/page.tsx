import ZonesPage from './zones'
import { getServerSession } from 'next-auth'
import { OPTIONS } from "@/auth";
import { redirect } from 'next/navigation'
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Zones `,
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
    <ZonesPage />
  )
}