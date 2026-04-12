import { Metadata } from 'next';
import FaceEnrollmentPageContent from './face-enrollment-page';

export const metadata: Metadata = {
  title: 'Face Enrollment',
};

export default function FaceEnrollmentPage() {
  return <FaceEnrollmentPageContent />;
}
