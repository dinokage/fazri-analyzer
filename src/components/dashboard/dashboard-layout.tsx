
'use client';

import { ReactNode } from 'react';
import { DashboardSummaryCards } from './dashboard-summary-cards';
import { RecentAlertsCard } from '@/components/alerts';
import { AlertNotificationListener } from '@/components/alert-notification-listener';
import { GitLabDeploymentStatus } from './gitlab-deployment-status';

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <>
      <AlertNotificationListener enabled pollInterval={30000} />
      <div className="flex flex-col space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
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
