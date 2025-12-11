import AlertDetailPageContent from './alert-detail-page';
import { getServerSession } from 'next-auth';
import { OPTIONS } from '@/auth';
import { redirect } from 'next/navigation';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Alert Details',
};

interface AlertDetailPageProps {
  params: Promise<{ alertId: string }>;
}

export default async function AlertDetailPage({ params }: AlertDetailPageProps) {
  const session = await getServerSession(OPTIONS);
  const { alertId } = await params;

  if (!session) {
    redirect('/auth');
  }

  if (session.user.role !== 'SUPER_ADMIN') {
    redirect('/dashboard/profile');
  }

  // Use the user's ID as staff ID for now
  // In a real app, this would be the staff member's actual ID from the backend
  const staffId = session.user.id || 'admin-staff-id';

  return <AlertDetailPageContent alertId={alertId} staffId={staffId} />;
}
