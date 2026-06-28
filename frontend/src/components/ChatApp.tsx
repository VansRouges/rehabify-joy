"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChatInput } from "./ChatInput";
import { MessageBubble, TypingIndicator } from "./MessageBubble";
import { Sidebar } from "./Sidebar";
import { getSession, listSessions, sendMessage } from "@/lib/api";
import type { ChatMessage, SessionSummary } from "@/lib/types";

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatApp() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const hasMessages = messages.length > 0;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      // Backend may not be running yet — sidebar stays empty
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const loadSession = async (sessionId: string) => {
    try {
      const detail = await getSession(sessionId);
      setActiveSessionId(sessionId);
      setMessages(
        detail.messages.map((m) => ({
          id: m.id,
          role: m.direction === "in" ? "user" : "assistant",
          content: m.content,
          redFlag: m.red_flag_triggered,
        })),
      );
      setError(null);
    } catch {
      setError("Could not load this conversation.");
    }
  };

  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setInput("");
    setError(null);
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMessage: ChatMessage = { id: generateId(), role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await sendMessage(text, activeSessionId ?? undefined);
      setActiveSessionId(response.session_id);

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: response.reply,
        redFlag: response.red_flag_triggered,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      await refreshSessions();
    } catch {
      setError("Joy couldn't respond right now. Check that the backend is running.");
      setMessages((prev) => prev.slice(0, -1));
      setInput(text);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={loadSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
      />

      <main className="joy-gradient-bg flex flex-1 flex-col overflow-hidden">
        {!hasMessages ? (
          <div className="flex flex-1 flex-col items-center justify-center px-4 pb-8">
            <div className="mb-8 text-center">
              <span className="mb-4 inline-block rounded-full bg-joy-sage px-3 py-1 text-xs font-semibold uppercase tracking-wider text-joy-green">
                Now piloting in Lagos, Abuja & every major city in the world
              </span>
              <h1 className="font-serif text-4xl font-semibold text-joy-green sm:text-5xl">
                Hi! My name is{" "}
                <span className="italic text-joy-peach">Joy</span>
              </h1>
              <p className="mt-4 max-w-md text-base text-joy-text-muted">
                I help with physiotherapy triage, recovery, and exercise guidance.
                Tell me what&apos;s been bothering you.
              </p>
            </div>
            <ChatInput
              value={input}
              onChange={setInput}
              onSubmit={handleSend}
              disabled={loading}
              centered
            />
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-6">
              <div className="mx-auto flex max-w-3xl flex-col gap-4">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                {loading && <TypingIndicator />}
                <div ref={messagesEndRef} />
              </div>
            </div>

            <div className="border-t border-joy-border/60 bg-joy-cream/80 pb-4 pt-3 backdrop-blur-sm">
              {error && (
                <p className="mb-2 text-center text-sm text-red-600">{error}</p>
              )}
              <ChatInput
                value={input}
                onChange={setInput}
                onSubmit={handleSend}
                disabled={loading}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
