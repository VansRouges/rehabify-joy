"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChatInput } from "./ChatInput";
import { MessageBubble, TypingIndicator } from "./MessageBubble";
import { OnboardingModal } from "./OnboardingModal";
import { Sidebar } from "./Sidebar";
import { getSession, listSessions, sendMessage, sendVoiceMessage, startThread } from "@/lib/api";
import { getStoredPatient } from "@/lib/patient";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import type { ChatMessage, SessionSummary } from "@/lib/types";

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatApp() {
  const [patientName, setPatientName] = useState<string | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const hasMessages = messages.length > 0;
  const isReady = patientName !== null;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  useEffect(() => {
    const stored = getStoredPatient();
    if (stored) {
      setPatientName(stored.displayName);
    } else {
      setShowOnboarding(true);
    }
  }, []);

  const refreshSessions = useCallback(async () => {
    if (!getStoredPatient()) return;
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      /* backend unavailable */
    }
  }, []);

  useEffect(() => {
    if (isReady) refreshSessions();
  }, [isReady, refreshSessions]);

  const handleVoiceComplete = useCallback(
    async (blob: Blob, duration: number) => {
      if (loading) return;
      setLoading(true);
      setError(null);

      const placeholder: ChatMessage = {
        id: generateId(),
        role: "user",
        content: "🎤 Voice note...",
        messageType: "voice",
      };
      setMessages((prev) => [...prev, placeholder]);

      try {
        const response = await sendVoiceMessage(blob, activeSessionId ?? undefined, duration);
        setActiveSessionId(response.session_id);

        setMessages((prev) => {
          const updated = [...prev];
          const idx = updated.findIndex((m) => m.id === placeholder.id);
          const userMsg: ChatMessage = {
            id: generateId(),
            role: "user",
            content: response.transcription || "Voice note",
            messageType: "voice",
          };
          if (idx >= 0) updated[idx] = userMsg;
          else updated.push(userMsg);
          updated.push({
            id: generateId(),
            role: "assistant",
            content: response.reply,
            redFlag: response.red_flag_triggered,
          });
          return updated;
        });
        await refreshSessions();
      } catch {
        setError("Joy couldn't process your voice note. Try again or type instead.");
        setMessages((prev) => prev.filter((m) => m.id !== placeholder.id));
      } finally {
        setLoading(false);
      }
    },
    [activeSessionId, loading, refreshSessions],
  );

  const {
    isRecording,
    seconds: recordingSeconds,
    startRecording,
    stopRecording,
    error: voiceError,
  } = useVoiceRecorder(handleVoiceComplete);

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
          messageType: m.message_type as "text" | "voice",
        })),
      );
      setError(null);
    } catch {
      setError("Could not load this conversation.");
    }
  };

  const handleNewChat = async () => {
    setInput("");
    setError(null);
    setLoading(true);
    try {
      const started = await startThread();
      setActiveSessionId(started.id);
      if (started.opening_message) {
        setMessages([
          {
            id: generateId(),
            role: "assistant",
            content: started.opening_message,
          },
        ]);
      } else {
        setMessages([]);
      }
      await refreshSessions();
    } catch {
      setActiveSessionId(null);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading || isRecording) return;

    const userMessage: ChatMessage = { id: generateId(), role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await sendMessage(text, activeSessionId ?? undefined);
      setActiveSessionId(response.session_id);

      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          role: "assistant",
          content: response.reply,
          redFlag: response.red_flag_triggered,
        },
      ]);
      await refreshSessions();
    } catch {
      setError("Joy couldn't respond right now. Check that the backend is running.");
      setMessages((prev) => prev.slice(0, -1));
      setInput(text);
    } finally {
      setLoading(false);
    }
  };

  const greeting = patientName
    ? `Hi ${patientName}! My name is Joy`
    : "Hi! My name is Joy";

  const inputProps = {
    value: input,
    onChange: setInput,
    onSubmit: handleSend,
    disabled: loading || !isReady,
    isRecording,
    recordingSeconds,
    onStartRecording: startRecording,
    onStopRecording: stopRecording,
    voiceError,
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {showOnboarding && (
        <OnboardingModal
          onComplete={(name) => {
            setPatientName(name);
            setShowOnboarding(false);
          }}
        />
      )}

      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={loadSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
        patientName={patientName}
      />

      <main className="joy-gradient-bg flex flex-1 flex-col overflow-hidden">
        {!hasMessages ? (
          <div className="flex flex-1 flex-col items-center justify-center px-4 pb-8">
            <div className="mb-8 text-center">
              <span className="mb-4 inline-block rounded-full bg-joy-sage px-3 py-1 text-xs font-semibold uppercase tracking-wider text-joy-green">
                Now piloting in Lagos & Abuja
              </span>
              <h1 className="font-serif text-4xl font-semibold text-joy-green sm:text-5xl">
                {greeting.split("Joy")[0]}
                <span className="italic text-joy-peach">Joy</span>
              </h1>
              <p className="mt-4 max-w-md text-base text-joy-text-muted">
                I help with physiotherapy triage, recovery, and exercise guidance.
                Tell me what&apos;s been bothering you — by text or voice.
              </p>
            </div>
            <ChatInput {...inputProps} centered />
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
              <ChatInput {...inputProps} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
