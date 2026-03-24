import AlertsPageContent from './alerts-page';
import { getServerSession } from 'next-auth';
import { OPTIONS } from '@/auth';
import { redirect } from 'next/navigation';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Security Alerts',
};

export default async function AlertsPage() {
  const session = await getServerSession(OPTIONS);

  if (!session) {
    redirect('/auth');
  }

  if (session.user.role !== 'SUPER_ADMIN') {
    redirect('/dashboard/profile');
  }

  return <AlertsPageContent />;
}
