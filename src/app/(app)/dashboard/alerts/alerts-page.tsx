'use client';

import { ShieldAlert } from 'lucide-react';
import { AlertList } from '@/components/alerts';
import { AlertNotificationListener } from '@/components/alert-notification-listener';
import { useSession } from '@/lib/auth-client';

export default function AlertsPageContent() {
  const { data: session, isPending } = useSession();

  if (isPending) return null;

  const role = (session?.user as Record<string, unknown>)?.role;
  if (role !== 'SUPER_ADMIN') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Access Denied</h2>
          <p className="text-gray-400">You do not have permission to view this page.</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <AlertNotificationListener enabled pollInterval={30000} />

      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-red-950/50 flex items-center justify-center">
            <ShieldAlert className="h-5 w-5 text-red-500" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Security Alerts</h1>
            <p className="text-sm text-gray-400">
              Monitor and manage security alerts across the campus
            </p>
          </div>
        </div>

        {/* Alert List */}
        <AlertList showFilters />
      </div>
    </>
  );
}
