import AlertsPageContent from './alerts-page';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Security Alerts',
};

export default function AlertsPage() {
  return <AlertsPageContent />;
}
