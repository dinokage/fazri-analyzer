import { Metadata } from 'next';
import CamerasPageContent from './cameras-page';

export const metadata: Metadata = {
  title: 'Camera Streams',
};

export default function CamerasPage() {
  return <CamerasPageContent />;
}
