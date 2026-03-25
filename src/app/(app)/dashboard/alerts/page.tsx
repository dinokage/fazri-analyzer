import AlertsPageContent from './alerts-page';
import { getAuthSession } from '@/lib/auth-server';
import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Security Alerts',
};

export default async function AlertsPage() {
  const session = await getAuthSession(await headers());

  if (!session) {
    redirect('/auth');
  }

  if (session.user.role !== 'SUPER_ADMIN') {
    redirect('/dashboard/profile');
  }

  return <AlertsPageContent />;
}
