import AnomaliesPage from './anomalies'
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Anomalies `,
};

export default function EntitiesPage() {
  return <AnomaliesPage />
}