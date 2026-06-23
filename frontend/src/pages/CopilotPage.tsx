import { useRef, useEffect, useState } from "react";
import {
  CheckCircle2,
  FilePenLine,
  LetterText,
  MessageSquareMore,
  MessageSquareQuote,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Bot,
} from "lucide-react";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { GhostText } from "@/components/copilot/GhostText";
import { useGhostCompletion } from "@/components/copilot/useGhostCompletion";
import { copilotService } from "@/services/copilot";
import * as haptics from "@/lib/haptics";
import type { CopilotChatResponse, ConfidenceLevel } from "@/types/api";

// ── Types ────────────────────────────────────────────────────────────────────

type MessageRole = "user" | "assistant" | "error";

interface ChatMessage {
  role: MessageRole;
  content: string;
  meta?: CopilotChatResponse;
}

interface QuickAction {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

// ── Constants ────────────────────────────────────────────────────────────────

const QUICK_ACTIONS: QuickAction[] = [
  { label: "Generate STAR Story", icon: MessageSquareQuote },
  { label: "Generate Resume Bullet", icon: FilePenLine },
  { label: "Generate Cover Letter", icon: LetterText },
  { label: "Generate Interview Answer", icon: MessageSquareMore },
];

const MAX_HISTORY = 10;

// ── Sub-components ───────────────────────────────────────────────────────────

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[72%] shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_12px_30px_rgba(0,0,0,0.22)] backdrop-blur-[20px] rounded-[22px] bg-[#4c8dff]/22 text-neutral-50 text-sm leading-7 border border-neutral-200/20 px-5 py-4">
        {content}
      </div>
    </div>
  );
}

function AssistantCard({ content, meta }: { content: string; meta?: CopilotChatResponse }) {
  // Try to split content into numbered paragraphs for styled rendering
  const paragraphs = content.split(/\n+/).filter(Boolean);
  const hasPoints = paragraphs.length > 1;

  return (
    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_16px_40px_rgba(0,0,0,0.24)] rounded-3xl bg-white/5 border border-white/10 mt-5 p-6">
      {/* Purple gradient bar */}
      <div className="bg-[linear-gradient(90deg,oklch(0.627_0.265_303.9),oklch(0.488_0.243_264.376))] rounded-full mb-4 w-full h-1" />

      <div className="space-y-4 text-[#a1a1a1] text-sm leading-7">
        {hasPoints ? (
          paragraphs.map((para, idx) => (
            <div key={idx} className="flex gap-3">
              <div className="size-7 shrink-0 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] font-semibold rounded-full bg-neutral-800 text-neutral-50/70 text-xs leading-4 flex justify-center items-center">
                {idx + 1}
              </div>
              <p className="text-neutral-50/80 mt-0.5">{para}</p>
            </div>
          ))
        ) : (
          <p className="text-neutral-50/80">{content}</p>
        )}
      </div>

      {/* Confidence + intent footer */}
      {meta && (
        <div className="border-t border-white/10 mt-5 pt-4 flex flex-wrap items-center gap-3">
          <ConfidenceBadge level={meta.confidence} />
          {meta.intent && (
            <span className="inline-flex items-center rounded-full border border-neutral-200/20 bg-neutral-200/10 px-2.5 py-0.5 text-[11px] font-medium text-neutral-200">
              {meta.intent}
            </span>
          )}
          {meta.evidence_count > 0 && (
            <span className="text-[#a1a1a1] text-[11px]">
              {meta.evidence_count} evidence record{meta.evidence_count !== 1 ? "s" : ""} referenced
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function ErrorMessage({ content }: { content: string }) {
  return (
    <div className="rounded-2xl bg-red-500/10 border border-red-500/20 px-5 py-4 text-sm text-red-300 leading-relaxed">
      {content}
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_16px_40px_rgba(0,0,0,0.24)] rounded-3xl bg-white/5 border border-white/10 mt-5 p-6">
      <div className="bg-[linear-gradient(90deg,oklch(0.627_0.265_303.9),oklch(0.488_0.243_264.376))] rounded-full mb-4 w-full h-1" />
      <div className="flex items-center gap-3 text-[#a1a1a1] text-sm">
        <LoadingSpinner size="sm" />
        <span>Thinking…</span>
      </div>
    </div>
  );
}

function CitationCard({
  source,
  text,
  confidence,
}: {
  source: string;
  text: string;
  confidence: ConfidenceLevel;
}) {
  return (
    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-[18px] bg-neutral-900/80 border border-white/10 p-4">
      <div className="flex justify-between items-start gap-3 mb-2">
        <div className="font-semibold text-neutral-50 text-sm leading-5 truncate">{source}</div>
        <ConfidenceBadge level={confidence} />
      </div>
      <p className="text-[#a1a1a1] text-xs leading-5">{text}</p>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function CopilotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // One AbortController per in-flight generation (12.4 cancellation).
  const controllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Cancel any in-flight stream when leaving the page — frees the Ollama job.
  useEffect(() => () => controllerRef.current?.abort(), []);

  // Mutate the most recent message in place — used to append streamed tokens.
  const updateLast = (fn: (m: ChatMessage) => ChatMessage) =>
    setMessages((prev) =>
      prev.length === 0 ? prev : [...prev.slice(0, -1), fn(prev[prev.length - 1])]
    );

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    // Starting a new generation aborts the in-flight one — never two concurrent
    // Ollama jobs (spec §4.3). The abort propagates to the backend disconnect.
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    // History from prior turns must be read before we append the new messages.
    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-MAX_HISTORY)
      .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setLoading(true);

    let meta: CopilotChatResponse | undefined;
    let started = false; // assistant bubble created on the first token
    try {
      for await (const delta of copilotService.chatStream(
        { message: trimmed, conversation_history: history },
        controller.signal,
        (m) => {
          meta = { ...m, response: "" };
        }
      )) {
        if (!started) {
          started = true;
          setLoading(false); // first token in — drop the thinking state, stream live
          setMessages((prev) => [...prev, { role: "assistant", content: delta, meta }]);
        } else {
          updateLast((m) => ({ ...m, content: m.content + delta }));
        }
      }
      // A clean abort ends the generator WITHOUT throwing (streamSSE returns on
      // signal.aborted), so a superseded turn reaches here, not the catch. Bail
      // before touching state that now belongs to the newer generation.
      if (controllerRef.current !== controller) return;
      if (!started) {
        // No visible tokens (reasoning-only budget, or empty fallback) — show a
        // graceful answer instead of leaving the user turn unanswered.
        setLoading(false);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: meta?.response || "I couldn't find anything to answer that. Try rephrasing.",
            meta,
          },
        ]);
      } else {
        // Backfill meta.response so downstream consumers see the full answer text.
        updateLast((m) => (m.meta ? { ...m, meta: { ...m.meta, response: m.content } } : m));
      }
      haptics.success();
    } catch {
      if (controller.signal.aborted) return; // superseded by a newer send — stay quiet
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          content: "Something went wrong. Please check that the backend is running and try again.",
        },
      ]);
      haptics.warn();
    } finally {
      // Only the latest generation owns the shared loading/focus state.
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setLoading(false);
        inputRef.current?.focus();
      }
    }
  };

  const handleSend = () => sendMessage(input);

  // Inline ghost completion (COP-003). Tab/Esc are consumed by the hook before
  // the chat keymap; accepting fills the input and gives a light haptic tap.
  const { ghost, onKeyDown: onGhostKey, onValueChange } = useGhostCompletion(
    input,
    (full) => {
      setInput(full);
      haptics.tap();
    },
    !loading,
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (onGhostKey(e)) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickAction = (label: string) => {
    sendMessage(label);
  };

  // Find citations from the most recent assistant message
  const lastAssistantMeta = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && m.meta?.citations && m.meta.citations.length > 0)?.meta;

  const hasCitations = (lastAssistantMeta?.citations?.length ?? 0) > 0;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Page Header */}
      <header className="border-b border-white/10 flex px-9 py-7 justify-between items-center flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="size-12 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_10px_30px_rgba(0,0,0,0.25)] rounded-2xl bg-neutral-900/80 text-neutral-200 border border-white/10 flex justify-center items-center">
            <Sparkles className="size-6" />
          </div>
          <div className="space-y-1">
            <div className="font-bold text-neutral-50 text-[28px] tracking-tight">
              Career Copilot
            </div>
            <div className="text-[#a1a1a1] text-sm leading-5">
              Powered by your Career Knowledge Graph — Local First
            </div>
          </div>
        </div>
        <div className="inline-flex shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] font-semibold rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] border border-emerald-500/20 px-3 py-1 items-center gap-2">
          <CheckCircle2 className="size-3.5" />
          Knowledge Graph Active
        </div>
      </header>

      {/* Body: chat + sidebar */}
      <div className="flex min-h-0 px-8 py-6 flex-1 gap-6 overflow-hidden">
        {/* ── Chat Panel ── */}
        <section className="min-w-0 flex justify-center flex-1 overflow-hidden">
          <div className="max-w-[900px] shadow-[0_30px_90px_rgba(0,0,0,0.42)] backdrop-blur-[50px] rounded-[30px] bg-white/5 border border-white/10 flex flex-col w-full h-full overflow-hidden">
            {/* Chat panel header */}
            <div className="border-b border-white/10 flex px-6 py-4 justify-between items-center flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="size-9 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-xl bg-neutral-200/15 text-neutral-200 flex justify-center items-center">
                  <Bot className="size-4" />
                </div>
                <div>
                  <div className="font-semibold text-neutral-50 text-sm leading-5">
                    Career Copilot
                  </div>
                  <div className="text-[#a1a1a1] text-xs leading-4">
                    Context-aware, evidence-backed responses
                  </div>
                </div>
              </div>
              <div className="text-[#a1a1a1] text-xs leading-4 flex items-center gap-2">
                <ShieldCheck className="size-4 text-emerald-400" />
                Traceable output
              </div>
            </div>

            {/* Messages area */}
            <div className="min-h-0 overflow-y-auto p-6 flex-1">
              {/* Empty state */}
              {messages.length === 0 && !loading && (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                  <div className="size-14 rounded-2xl bg-[#4c8dff]/10 flex items-center justify-center">
                    <Bot className="size-7 text-[#4c8dff]" />
                  </div>
                  <div>
                    <p className="font-semibold text-neutral-200 text-base">
                      How can I help with your career?
                    </p>
                    <p className="text-[#a1a1a1] text-sm mt-1 max-w-sm">
                      Ask me about your experience, interview prep, job matching, or anything career-related.
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 w-full max-w-sm mt-2">
                    {[
                      "What are my strongest skills?",
                      "Help me prepare for a PM interview",
                      "What roles should I target?",
                    ].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => sendMessage(suggestion)}
                        className="text-sm px-4 py-2 rounded-xl bg-white/[0.04] border border-white/10 text-[#a1a1a1] hover:text-neutral-200 hover:bg-white/[0.08] transition-colors text-left"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Message list */}
              {messages.map((msg, i) => {
                if (msg.role === "user") {
                  return <UserBubble key={i} content={msg.content} />;
                }
                if (msg.role === "error") {
                  return <ErrorMessage key={i} content={msg.content} />;
                }
                return (
                  <AssistantCard key={i} content={msg.content} meta={msg.meta} />
                );
              })}

              {/* Thinking indicator */}
              {loading && <ThinkingIndicator />}

              <div ref={bottomRef} />
            </div>

            {/* Input area */}
            <div className="border-t border-white/10 px-6 py-5 flex-shrink-0">
              {/* Input bar */}
              <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-[20px] rounded-[18px] bg-neutral-900/80 border border-white/10 flex px-4 py-3 items-center gap-3">
                <Search className="size-4 text-[#a1a1a1] flex-shrink-0" />
                <div className="relative min-w-0 flex-1">
                  <input
                    ref={inputRef}
                    value={input}
                    onChange={(e) => {
                      setInput(e.target.value);
                      onValueChange();
                    }}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask your Career Copilot anything..."
                    disabled={loading}
                    className="w-full bg-transparent text-neutral-200 text-sm leading-5 placeholder-[#a1a1a1] focus:outline-none disabled:opacity-60"
                  />
                  <GhostText value={input} ghost={ghost} />
                </div>
                <button
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                  className="size-10 shadow-[0_10px_24px_rgba(76,141,255,0.35)] rounded-xl bg-neutral-200 text-neutral-900 flex justify-center items-center flex-shrink-0 disabled:opacity-40 hover:opacity-90 transition-opacity"
                  aria-label="Send message"
                >
                  <Send className="size-4" />
                </button>
              </div>

              {/* Quick action buttons */}
              <div className="flex mt-4 flex-wrap gap-3">
                {QUICK_ACTIONS.map(({ label, icon: Icon }) => (
                  <button
                    key={label}
                    onClick={() => handleQuickAction(label)}
                    disabled={loading}
                    className="inline-flex shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] font-medium rounded-xl bg-neutral-800 text-neutral-50 text-[13px] border border-white/10 px-4 py-3 items-center gap-2 hover:bg-neutral-700 transition-colors disabled:opacity-40"
                  >
                    <Icon className="size-4" />
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── Right Sidebar ── */}
        <aside className="backdrop-blur-[40px] bg-white/[0.03] border-l border-white/10 px-5 py-6 w-75 flex-shrink-0 overflow-y-auto">
          <div className="space-y-6">
            {/* Referenced Evidence */}
            <div>
              <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[3.84px] mb-3">
                Referenced Evidence
              </div>
              {hasCitations ? (
                <div className="space-y-3">
                  {lastAssistantMeta!.citations.map((c, i) => (
                    <CitationCard
                      key={i}
                      source={c.source}
                      text={c.text}
                      confidence={c.confidence}
                    />
                  ))}
                </div>
              ) : (
                <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-[18px] bg-neutral-900/80 border border-white/10 p-4">
                  <p className="text-[#a1a1a1] text-xs leading-5">
                    Evidence citations will appear here after your first response.
                  </p>
                </div>
              )}
            </div>

            {/* Experiences section — static context from verified career data */}
            <div>
              <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[3.84px] mb-3">
                Experiences
              </div>
              <div className="space-y-2">
                {[
                  "Litigation Consulting",
                  "Product Development",
                  "AI Development",
                  "Analytics Consulting",
                ].map((exp) => (
                  <div
                    key={exp}
                    className="rounded-[14px] bg-neutral-900/80 border border-white/10 flex px-4 py-3 justify-between items-center"
                  >
                    <div className="text-neutral-50/80 text-[13px]">{exp}</div>
                    <span className="inline-flex font-semibold rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] border border-emerald-500/20 px-2.5 py-1 items-center gap-1">
                      Verified
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
