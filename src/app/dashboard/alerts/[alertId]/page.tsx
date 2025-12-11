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

async function getStaffIdByEmail(email: string): Promise<string | null> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL || 'http://localhost:8000';
    const response = await fetch(
      `${baseUrl}/api/v1/staff/by-email/${encodeURIComponent(email)}`,
      {
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-store'
      }
    );
    if (!response.ok) return null;
    const data = await response.json();
    return data.id || null;
  } catch {
    return null;
  }
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

  // Look up the staff profile ID from the backend using the user's email
  const staffId = await getStaffIdByEmail(session.user.email || '');

  if (!staffId) {
    // User doesn't have a staff profile - show an error or create one
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Staff Profile Not Found</h2>
          <p className="text-gray-400">
            Your account is not linked to a staff profile. Please contact an administrator.
          </p>
        </div>
      </div>
    );
  }

  return <AlertDetailPageContent alertId={alertId} staffId={staffId} />;
}
