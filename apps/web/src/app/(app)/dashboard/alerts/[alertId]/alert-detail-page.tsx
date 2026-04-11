'use client';

import { AlertDetail } from '@/components/alerts';
import { AlertNotificationListener } from '@/components/alert-notification-listener';
import { useSession } from '@/lib/auth-client';

export default function AlertDetailPageContent({ alertId }: { alertId: string }) {
  const { data: session, isPending } = useSession();

  if (isPending) return null;

  const user = session?.user as Record<string, unknown> | undefined;
  const staffId = user?.staff_id as string | null ?? null;
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';

  if (!staffId && !isSuperAdmin) {
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

  return (
    <>
      <AlertNotificationListener enabled pollInterval={30000} />
      <AlertDetail alertId={alertId} staffId={staffId} />
    </>
  );
}
