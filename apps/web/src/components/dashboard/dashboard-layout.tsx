
'use client';

import { ReactNode } from 'react';
import { Bell, BellOff } from 'lucide-react';
import { DashboardSummaryCards } from './dashboard-summary-cards';
import { RecentAlertsCard } from '@/components/alerts';
import { AlertNotificationListener } from '@/components/alert-notification-listener';
import { GitLabDeploymentStatus } from './gitlab-deployment-status';
import { usePushNotifications } from '@/hooks/usePushNotifications';

interface DashboardLayoutProps {
  children: ReactNode;
}

function PushNotificationToggle() {
  const { supported, permission, subscribed, loading, subscribe, unsubscribe } = usePushNotifications();
  if (!supported || permission === 'denied') return null;
  return (
    <button
      type="button"
      onClick={subscribed ? unsubscribe : subscribe}
      disabled={loading}
      title={subscribed ? 'Disable push notifications' : 'Enable push notifications'}
      className={`p-1.5 rounded-md transition-colors ${
        subscribed
          ? 'text-blue-400 hover:text-blue-300 hover:bg-blue-900/20'
          : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
      } disabled:opacity-40`}
    >
      {subscribed ? <Bell className="h-4 w-4" /> : <BellOff className="h-4 w-4" />}
    </button>
  );
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <>
      <AlertNotificationListener enabled pollInterval={30000} />
      <div className="flex flex-col space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <PushNotificationToggle />
        </div>
        <DashboardSummaryCards />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            {children}
          </div>
          <div className="lg:col-span-1 space-y-4 lg:pt-[44px]">
            <GitLabDeploymentStatus />
            <RecentAlertsCard maxItems={5} />
          </div>
        </div>
      </div>
    </>
  );
}
