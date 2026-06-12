import { useState, useRef, useEffect, useCallback } from "react";
import Markdown from "react-markdown";
import { streamChat } from "../api/advisor";
import { useConversations, useDeleteConversation } from "../api/queries";
import type { SSEEvent } from "../types/advisor";

// Friendly labels for tool names
const TOOL_LABELS: Record<string, string> = {
  get_net_worth_summary: "Looking up net worth...",
  get_spending_analysis: "Analyzing spending...",
  get_spending_trends: "Checking spending trends...",
  get_savings_rate: "Calculating savings rate...",
  get_recurring_expenses: "Finding recurring expenses...",
  search_transactions: "Searching transactions...",
};

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function AdvisorPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [model] = useState<"sonnet" | "opus">("sonnet");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { data: convList } = useConversations();
  const deleteConversation = useDeleteConversation();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, toolStatus, scrollToBottom]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSend = async (overrideMessage?: string) => {
    const msg = (overrideMessage ?? input).trim();
    if (!msg || isStreaming) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text: msg }]);
    setIsStreaming(true);
    setToolStatus(null);

    let assistantText = "";
    setMessages((prev) => [...prev, { role: "assistant", text: "" }]);

    try {
      for await (const event of streamChat(msg, conversationId, null, model)) {
        const e = event as SSEEvent;
        if (e.type === "text") {
          assistantText += (e as { text: string }).text;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "assistant", text: assistantText };
            return updated;
          });
        } else if (e.type === "tool_use") {
          const toolName = (e as { tool: string }).tool;
          setToolStatus(TOOL_LABELS[toolName] ?? `Using ${toolName}...`);
        } else if (e.type === "done") {
          const doneEvent = e as { conversation_id: string };
          setConversationId(doneEvent.conversation_id);
          setToolStatus(null);
        } else if (e.type === "error") {
          setError((e as { error: string }).error);
          // Remove the empty assistant message
          if (!assistantText) {
            setMessages((prev) => prev.slice(0, -1));
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
      if (!assistantText) {
        setMessages((prev) => prev.slice(0, -1));
      }
    } finally {
      setIsStreaming(false);
      setToolStatus(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    setShowHistory(false);
  };

  const loadConversation = async (id: string) => {
    try {
      const res = await fetch(`/api/advisor/conversations/${id}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });
      if (!res.ok) throw new Error("Failed to load conversation");
      const data = await res.json();

      // Flatten messages into displayable format
      const displayMessages: Message[] = [];
      for (const msg of data.messages) {
        if (msg.role === "user" && typeof msg.content === "string") {
          displayMessages.push({ role: "user", text: msg.content });
        } else if (msg.role === "assistant" && Array.isArray(msg.content)) {
          const textParts = msg.content
            .filter((b: { type: string }) => b.type === "text")
            .map((b: { text: string }) => b.text)
            .join("");
          if (textParts) {
            displayMessages.push({ role: "assistant", text: textParts });
          }
        }
      }

      setMessages(displayMessages);
      setConversationId(id);
      setShowHistory(false);
    } catch {
      setError("Failed to load conversation");
    }
  };

  return (
    <>
      {/* Floating button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-all hover:scale-110"
          style={{
            background: "linear-gradient(135deg, #4d8eff, #00d4aa)",
          }}
          title="Ask your AI advisor"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </button>
      )}

      {/* Slide-out panel */}
      {isOpen && (
        <div className="fixed right-0 top-0 h-full z-50 flex" style={{ width: 440 }}>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 -z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Panel */}
          <div className="w-full h-full flex flex-col border-l border-[var(--border)]" style={{ background: "var(--bg-primary)" }}>
            {/* Header */}
            <div className="h-14 shrink-0 flex items-center justify-between px-4 border-b border-[var(--border)]" style={{ background: "var(--bg-secondary)" }}>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold" style={{ background: "linear-gradient(135deg, #4d8eff, #00d4aa)", color: "white" }}>
                  AI
                </div>
                <span className="text-sm font-semibold text-[var(--text-primary)]">Financial Advisor</span>
              </div>
              <div className="flex items-center gap-1">
                <span
                  className="px-2 py-1 rounded text-xs font-medium"
                  style={{ background: "var(--bg-card)", color: "var(--text-secondary)" }}
                  title="Claude Sonnet 4"
                >
                  Sonnet
                </span>
                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className="p-2 rounded hover:bg-[var(--bg-card)] text-[var(--text-secondary)] transition-colors"
                  title="Conversation history"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                </button>
                <button
                  onClick={startNewConversation}
                  className="p-2 rounded hover:bg-[var(--bg-card)] text-[var(--text-secondary)] transition-colors"
                  title="New conversation"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 rounded hover:bg-[var(--bg-card)] text-[var(--text-secondary)] transition-colors"
                  title="Close"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Conversation history dropdown */}
            {showHistory && (
              <div className="border-b border-[var(--border)] max-h-64 overflow-y-auto" style={{ background: "var(--bg-secondary)" }}>
                {convList?.conversations.length ? (
                  convList.conversations.map((conv) => (
                    <div
                      key={conv.id}
                      className={`flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-[var(--bg-card)] transition-colors ${conv.id === conversationId ? "bg-[var(--bg-card)]" : ""}`}
                    >
                      <div className="flex-1 min-w-0 mr-2" onClick={() => loadConversation(conv.id)}>
                        <div className="text-sm text-[var(--text-primary)] truncate">
                          {conv.title || "Untitled"}
                        </div>
                        <div className="text-xs text-[var(--text-secondary)]">
                          {new Date(conv.updated_at).toLocaleDateString()} · {conv.message_count} msgs
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteConversation.mutate(conv.id);
                          if (conv.id === conversationId) startNewConversation();
                        }}
                        className="p-1 rounded hover:bg-[var(--bg-primary)] text-[var(--text-secondary)] hover:text-[var(--red)] transition-colors shrink-0"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="px-4 py-6 text-sm text-[var(--text-secondary)] text-center">
                    No previous conversations
                  </div>
                )}
              </div>
            )}

            {/* Messages area */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center px-6">
                  <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4" style={{ background: "linear-gradient(135deg, #4d8eff20, #00d4aa20)" }}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                  </div>
                  <h3 className="text-base font-semibold text-[var(--text-primary)] mb-2">
                    FIRE Master Advisor
                  </h3>
                  <p className="text-sm text-[var(--text-secondary)] mb-6">
                    Ask me anything about your finances. I have access to your real data — net worth, spending, savings rate, transactions.
                  </p>
                  <div className="grid gap-2 w-full max-w-xs">
                    {[
                      "Where am I spending too much?",
                      "What's my savings rate trend?",
                      "How's my net worth doing?",
                      "Find my largest expenses this month",
                    ].map((q) => (
                      <button
                        key={q}
                        onClick={() => handleSend(q)}
                        className="text-left text-sm px-3 py-2 rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--green)]! hover:bg-[var(--bg-card)] transition-all"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-[var(--blue)] text-white rounded-br-md"
                        : "bg-[var(--bg-card)] text-[var(--text-primary)] rounded-bl-md"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      <div className="advisor-markdown">
                        <Markdown>{msg.text || "\u00A0"}</Markdown>
                      </div>
                    ) : (
                      msg.text
                    )}
                  </div>
                </div>
              ))}

              {/* Tool use indicator */}
              {toolStatus && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 px-4 py-2 rounded-2xl rounded-bl-md text-sm" style={{ background: "var(--bg-card)" }}>
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)] animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)] animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)] animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span className="text-[var(--text-secondary)]">{toolStatus}</span>
                  </div>
                </div>
              )}

              {/* Streaming indicator (no tool active) */}
              {isStreaming && !toolStatus && messages.length > 0 && messages[messages.length - 1].text === "" && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-1 px-4 py-2 rounded-2xl rounded-bl-md" style={{ background: "var(--bg-card)" }}>
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)] animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)] animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)] animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="flex justify-center">
                  <div className="text-sm text-[var(--red)] bg-[rgba(255,77,106,0.1)] px-4 py-2 rounded-lg">
                    {error}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="shrink-0 border-t border-[var(--border)] p-3" style={{ background: "var(--bg-secondary)" }}>
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about your finances..."
                  rows={1}
                  className="flex-1 resize-none rounded-xl px-4 py-2.5 text-sm border border-[var(--border)] focus:border-[var(--green)] focus:outline-none transition-colors"
                  style={{
                    background: "var(--bg-primary)",
                    color: "var(--text-primary)",
                    maxHeight: 120,
                  }}
                  disabled={isStreaming}
                />
                <button
                  onClick={() => handleSend()}
                  disabled={isStreaming || !input.trim()}
                  className="shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all disabled:opacity-30"
                  style={{
                    background: input.trim() && !isStreaming ? "linear-gradient(135deg, #4d8eff, #00d4aa)" : "var(--bg-card)",
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
