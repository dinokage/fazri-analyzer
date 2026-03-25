import AnomaliesPage from './anomalies'
import { getAuthSession } from '@/lib/auth-server'
import { headers } from 'next/headers'
import { redirect } from 'next/navigation'
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Anomalies `,
};
export default async function EntitiesPage() {
  const session = await getAuthSession(await headers());
  if (!session) {
    redirect('/auth')
  }
  if (session.user.role !== "SUPER_ADMIN") {
    redirect("/dashboard/profile");
  }
  return (
    <AnomaliesPage />
  )
}