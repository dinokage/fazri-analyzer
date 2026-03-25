import { getAuthSession } from '@/lib/auth-server';
import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { Metadata } from 'next';
import ChatPageContent from './chat-page';

export const metadata: Metadata = {
  title: 'AI Assistant',
};

export default async function ChatPage() {
  const session = await getAuthSession(await headers());

  if (!session) {
    redirect('/auth');
  }

  if (session.user.role !== 'SUPER_ADMIN') {
    redirect('/dashboard/profile');
  }

  return <ChatPageContent />;
}
