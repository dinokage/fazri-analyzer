import SigninPage from '@/components/auth/SigninForm';
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Sign In `,
};

export default function page() {
  return <SigninPage />;
}