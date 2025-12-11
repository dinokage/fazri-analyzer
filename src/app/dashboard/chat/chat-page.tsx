'use client';

import { useSession } from 'next-auth/react';
import { Sparkles, Shield, Zap } from 'lucide-react';
import AIChatCard from '@/components/ui/ai-chat';

export default function ChatPageContent() {
  const { data: session } = useSession();
  const userName = session?.user?.name || undefined;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-purple-950/50 border border-purple-500/30 flex items-center justify-center">
            <Sparkles className="h-6 w-6 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">AI Assistant</h1>
            <p className="text-sm text-gray-400">
              Powered by Gemini with campus security intelligence
            </p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="hidden md:flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/30">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs text-green-400">Online</span>
          </div>
        </div>
      </div>

      {/* Feature Pills */}
      <div className="flex flex-wrap gap-2">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
          <Shield className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-xs text-gray-300">Anomaly Detection</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
          <Zap className="w-3.5 h-3.5 text-yellow-400" />
          <span className="text-xs text-gray-300">Real-time Analysis</span>
        </div>
      </div>

      {/* Chat Card Container */}
      <div className="flex justify-center items-start">
        <AIChatCard className="shadow-2xl" userName={userName} />
      </div>

      {/* Footer Info */}
      <div className="text-center text-xs text-gray-500">
        <p>
          The AI assistant can query campus data including zones, entities, anomalies, and security alerts.
        </p>
        <p className="mt-1">
          Conversation history is preserved during your session.
        </p>
      </div>
    </div>
  );
}
