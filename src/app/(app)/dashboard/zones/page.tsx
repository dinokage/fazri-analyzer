import ZonesPage from './zones'
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Zones `,
};

export default function EntitiesPage() {
  return <ZonesPage />
}