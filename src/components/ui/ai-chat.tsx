"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Send, Loader2, RotateCcw, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api-client";

interface Message {
  id: string;
  sender: "ai" | "user";
  text: string;
  timestamp: Date;
  toolsUsed?: string[];
  isError?: boolean;
}

interface AIChatCardProps {
  className?: string;
  userName?: string;
}

// Generate stable particle positions using a seed-based approach
function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

const WELCOME_MESSAGE = `Welcome to **FAZRI Campus Security Assistant**!

I can help you with:
- 🔍 **Finding anomalies** - "Show me critical anomalies today"
- 📍 **Zone occupancy** - "How many people are in the library?"
- 👤 **Locating people** - "Where is John Smith?"
- 📊 **Activity analysis** - "What happened in Lab 101 this morning?"
- 🚨 **Security alerts** - "Show me unresolved security alerts"

How can I assist you today?`;

const EXAMPLE_QUERIES = [
  "Show me critical anomalies",
  "What's the occupancy in Library?",
  "Any unusual activity today?",
  "List all active alerts",
];

export default function AIChatCard({ className, userName }: AIChatCardProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "ai",
      text: WELCOME_MESSAGE,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Generate stable random values based on index (deterministic)
  const particles = useMemo(() => {
    return Array.from({ length: 20 }).map((_, i) => ({
      left: `${seededRandom(i * 100) * 100}%`,
      xAnimation: [seededRandom(i * 200) * 200 - 100, seededRandom(i * 300) * 200 - 100],
      duration: 5 + seededRandom(i * 400) * 3,
    }));
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const result = await apiClient.sendChatMessage({
        message: userMessage.text,
        conversation_id: conversationId || undefined,
        context: userName ? { user_name: userName } : undefined,
      });

      // Update conversation ID for continuity
      if (result.conversation_id) {
        setConversationId(result.conversation_id);
      }

      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        sender: "ai",
        text: result.response,
        timestamp: new Date(),
        toolsUsed: result.tools_used,
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        sender: "ai",
        text: error instanceof Error
          ? `Sorry, I encountered an error: ${error.message}`
          : "Sorry, something went wrong. Please try again.",
        timestamp: new Date(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExampleQuery = (query: string) => {
    setInput(query);
  };

  const handleClearConversation = async () => {
    if (conversationId) {
      try {
        await apiClient.clearChatConversation(conversationId);
      } catch {
        // Ignore errors when clearing
      }
    }
    setMessages([
      {
        id: "welcome",
        sender: "ai",
        text: WELCOME_MESSAGE,
        timestamp: new Date(),
      },
    ]);
    setConversationId(null);
  };

  // Render markdown-like formatting (basic)
  const formatMessage = (text: string) => {
    return text
      .split('\n')
      .map((line, i) => {
        // Handle bold
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // Handle bullet points
        if (line.startsWith('- ')) {
          return `<div class="ml-2">${line}</div>`;
        }
        return line;
      })
      .join('<br/>');
  };

  return (
    <div className={cn("relative w-full max-w-4xl h-[600px] rounded-2xl overflow-hidden p-[2px]", className)}>
      {/* Animated Outer Border */}
      <motion.div
        className="absolute inset-0 rounded-2xl border-2 border-purple-500/30"
        animate={{ rotate: [0, 360] }}
        transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
      />

      {/* Inner Card */}
      <div className="relative flex flex-col w-full h-full rounded-xl border border-white/10 overflow-hidden bg-black/95 backdrop-blur-xl">
        {/* Inner Animated Background */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-br from-gray-900 via-black to-purple-950/30"
          animate={{ backgroundPosition: ["0% 0%", "100% 100%", "0% 0%"] }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          style={{ backgroundSize: "200% 200%" }}
        />

        {/* Floating Particles - only render after mount to avoid hydration mismatch */}
        {isMounted && particles.map((particle, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 rounded-full bg-purple-500/20"
            animate={{
              y: ["0%", "-140%"],
              x: particle.xAnimation,
              opacity: [0, 1, 0],
            }}
            transition={{
              duration: particle.duration,
              repeat: Infinity,
              delay: i * 0.5,
              ease: "easeInOut",
            }}
            style={{ left: particle.left, bottom: "-10%" }}
          />
        ))}

        {/* Header */}
        <div className="px-4 py-3 border-b border-white/10 relative z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-400" />
            <h2 className="text-lg font-semibold text-white">FAZRI Assistant</h2>
          </div>
          <button
            onClick={handleClearConversation}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
            title="Clear conversation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 px-4 py-3 overflow-y-auto space-y-4 text-sm flex flex-col relative z-10">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={cn(
                "px-4 py-3 rounded-xl max-w-[85%] shadow-lg",
                msg.sender === "ai"
                  ? cn(
                      "bg-white/5 border border-white/10 text-gray-100 self-start",
                      msg.isError && "border-red-500/30 bg-red-500/10"
                    )
                  : "bg-purple-600/30 border border-purple-500/30 text-white self-end"
              )}
            >
              <div
                className="whitespace-pre-wrap leading-relaxed"
                dangerouslySetInnerHTML={{ __html: formatMessage(msg.text) }}
              />
              {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                <div className="mt-2 pt-2 border-t border-white/10 flex flex-wrap gap-1">
                  {msg.toolsUsed.map((tool) => (
                    <span
                      key={tool}
                      className="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-300"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              )}
            </motion.div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <motion.div
              className="flex items-center gap-2 px-4 py-3 rounded-xl max-w-[60%] bg-white/5 border border-white/10 self-start"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />
              <span className="text-gray-400 text-sm">Analyzing your request...</span>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Example Queries - only show at start */}
        {messages.length === 1 && (
          <div className="px-4 pb-2 relative z-10">
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((query) => (
                <button
                  key={query}
                  onClick={() => handleExampleQuery(query)}
                  className="px-3 py-1.5 text-xs rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 hover:bg-purple-500/20 transition-colors"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="flex items-center gap-2 p-3 border-t border-white/10 relative z-10">
          <input
            className="flex-1 px-4 py-2.5 text-sm bg-white/5 rounded-lg border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
            placeholder="Ask about campus security, anomalies, or locations..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={cn(
              "p-2.5 rounded-lg transition-all",
              isLoading || !input.trim()
                ? "bg-white/5 text-gray-600 cursor-not-allowed"
                : "bg-purple-600 hover:bg-purple-500 text-white"
            )}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
