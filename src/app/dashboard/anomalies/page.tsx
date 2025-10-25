import AnomaliesPage from './anomalies'
import { getServerSession } from 'next-auth'
import { OPTIONS } from "@/auth";
import { redirect } from 'next/navigation'
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Anomalies `,
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
    <AnomaliesPage />
  )
}