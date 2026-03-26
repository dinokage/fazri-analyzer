import { Metadata } from 'next';
import ChatPageContent from './chat-page';

export const metadata: Metadata = {
  title: 'AI Assistant',
};

export default function ChatPage() {
  return <ChatPageContent />;
}
