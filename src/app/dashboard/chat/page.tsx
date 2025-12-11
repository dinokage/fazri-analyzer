import { getServerSession } from 'next-auth';
import { OPTIONS } from '@/auth';
import { redirect } from 'next/navigation';
import { Metadata } from 'next';
import ChatPageContent from './chat-page';

export const metadata: Metadata = {
  title: 'AI Assistant',
};

export default async function ChatPage() {
  const session = await getServerSession(OPTIONS);

  if (!session) {
    redirect('/auth');
  }

  if (session.user.role !== 'SUPER_ADMIN') {
    redirect('/dashboard/profile');
  }

  return <ChatPageContent />;
}
