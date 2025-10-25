
'use client';

import { ReactNode } from 'react';
import { DashboardSummaryCards } from './dashboard-summary-cards';

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="flex flex-col space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
      </div>
      <DashboardSummaryCards />
      <div>
        {children}
      </div>
    </div>
  );
}
