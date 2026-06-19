import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, BookOpen } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { copilotService } from "@/services/copilot";
import type { CopilotChatResponse } from "@/types/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  meta?: CopilotChatResponse;
}

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    try {
      const history = messages.slice(-4).map((m) => ({ role: m.role, content: m.content }));
      const res = await copilotService.chat({ message: text, conversation_history: history });
      setMessages((prev) => [...prev, { role: "assistant", content: res.response, meta: res }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I encountered an error. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.meta);

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 flex flex-col p-8 gap-4">
        <div>
          <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight flex items-center gap-3">
            <div className="size-9 rounded-xl bg-[#4c8dff]/20 flex items-center justify-center">
              <Bot className="size-5 text-[#4c8dff]" />
            </div>
            Career Copilot
          </h1>
          <p className="text-[#a1a1a1] text-sm mt-1 ml-12">AI assistant grounded in your verified career evidence</p>
        </div>

        <GlassCard className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-auto p-5 flex flex-col gap-4">
            {messages.length === 0 && (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center max-w-sm">
                  <div className="size-14 rounded-2xl bg-[#4c8dff]/10 flex items-center justify-center mx-auto mb-4">
                    <Bot className="size-7 text-[#4c8dff]" />
                  </div>
                  <p className="font-semibold text-neutral-200 text-base">How can I help with your career?</p>
                  <p className="text-[#a1a1a1] text-sm mt-2">Ask me about your experience, interview prep, job matching, or anything career-related.</p>
                  <div className="mt-4 flex flex-col gap-2">
                    {[
                      "What are my strongest skills?",
                      "Help me prepare for a PM interview",
                      "What roles should I target?",
                    ].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => { setInput(suggestion); }}
                        className="text-sm px-4 py-2 rounded-xl bg-white/[0.04] border border-white/10 text-[#a1a1a1] hover:text-neutral-200 hover:bg-white/[0.08] transition-colors text-left"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                <div className={`size-8 rounded-xl flex-shrink-0 flex items-center justify-center ${
                  msg.role === "user" ? "bg-[#4c8dff]/20" : "bg-neutral-200/[0.08]"
                }`}>
                  {msg.role === "user" ? <User className="size-4 text-[#4c8dff]" /> : <Bot className="size-4 text-neutral-400" />}
                </div>
                <div className={`max-w-[75%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-1`}>
                  <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-[#4c8dff]/20 text-neutral-100 rounded-tr-sm"
                      : "bg-white/[0.06] text-neutral-200 rounded-tl-sm"
                  }`}>
                    {msg.content}
                  </div>
                  {msg.meta && (
                    <div className="flex items-center gap-2 px-1">
                      <ConfidenceBadge level={msg.meta.confidence} />
                      <span className="text-[#a1a1a1] text-[11px]">{msg.meta.intent}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="size-8 rounded-xl bg-neutral-200/[0.08] flex items-center justify-center">
                  <Bot className="size-4 text-neutral-400" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-white/[0.06] rounded-tl-sm">
                  <LoadingSpinner size="sm" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="p-4 border-t border-white/10">
            <div className="flex gap-3">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                placeholder="Ask about your career…"
                disabled={loading}
                className="flex-1 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-[#4c8dff]/40 transition-colors disabled:opacity-60"
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="size-10 rounded-xl bg-[#4c8dff] flex items-center justify-center disabled:opacity-40 hover:opacity-90 transition-opacity flex-shrink-0"
              >
                <Send className="size-4 text-white" />
              </button>
            </div>
          </div>
        </GlassCard>
      </div>

      {lastAssistant?.meta?.citations && lastAssistant.meta.citations.length > 0 && (
        <div className="w-72 p-8 pl-0 flex-shrink-0">
          <GlassCard className="p-4 h-full overflow-auto">
            <p className="text-xs font-medium text-[#a1a1a1] mb-3 flex items-center gap-2">
              <BookOpen className="size-3.5" /> Evidence Citations
            </p>
            <div className="flex flex-col gap-3">
              {lastAssistant.meta.citations.map((c, i) => (
                <div key={i} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-medium text-neutral-300 truncate">{c.source}</span>
                    <ConfidenceBadge level={c.confidence} />
                  </div>
                  <p className="text-[#a1a1a1] text-xs leading-relaxed">{c.text}</p>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
