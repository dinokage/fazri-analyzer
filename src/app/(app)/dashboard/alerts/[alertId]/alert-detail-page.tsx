'use client';

import { AlertDetail } from '@/components/alerts';
import { AlertNotificationListener } from '@/components/alert-notification-listener';

interface AlertDetailPageContentProps {
  alertId: string;
  staffId: string;
}

export default function AlertDetailPageContent({
  alertId,
  staffId,
}: AlertDetailPageContentProps) {
  return (
    <>
      <AlertNotificationListener enabled pollInterval={30000} />
      <AlertDetail alertId={alertId} staffId={staffId} />
    </>
  );
}
