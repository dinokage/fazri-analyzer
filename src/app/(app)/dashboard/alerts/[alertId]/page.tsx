import AlertDetailPageContent from './alert-detail-page';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Alert Details',
};

export default async function AlertDetailPage({
  params,
}: {
  params: Promise<{ alertId: string }>;
}) {
  const { alertId } = await params;
  return <AlertDetailPageContent alertId={alertId} />;
}
