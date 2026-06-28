"use client";

import { FormEvent, KeyboardEvent, useRef, useEffect } from "react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
  centered?: boolean;
  isRecording?: boolean;
  recordingSeconds?: number;
  onStartRecording?: () => void;
  onStopRecording?: () => void;
  voiceError?: string | null;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Tell Joy what's been bothering you...",
  centered = false,
  isRecording = false,
  recordingSeconds = 0,
  onStartRecording,
  onStopRecording,
  voiceError,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!value.trim() || disabled || isRecording) return;
    onSubmit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleVoiceClick = () => {
    if (disabled) return;
    if (isRecording) {
      onStopRecording?.();
    } else {
      onStartRecording?.();
    }
  };

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={`w-full ${centered ? "max-w-2xl mx-auto" : "max-w-3xl mx-auto px-4"}`}
    >
      {isRecording && (
        <div className="mb-2 flex items-center justify-center gap-2 text-sm text-joy-peach">
          <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
          Recording {formatTime(recordingSeconds)} / 1:00
        </div>
      )}
      {voiceError && (
        <p className="mb-2 text-center text-sm text-red-600">{voiceError}</p>
      )}
      <div
        className={`relative flex items-end gap-2 rounded-2xl border bg-white p-2 shadow-sm focus-within:ring-2 focus-within:ring-joy-sage ${
          isRecording
            ? "border-joy-peach ring-2 ring-joy-peach/30"
            : "border-joy-border focus-within:border-joy-green/40"
        }`}
      >
        {onStartRecording && (
          <button
            type="button"
            onClick={handleVoiceClick}
            disabled={disabled && !isRecording}
            className={`mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors ${
              isRecording
                ? "bg-red-500 text-white hover:bg-red-600"
                : "text-joy-green hover:bg-joy-sage"
            } disabled:cursor-not-allowed disabled:opacity-40`}
            aria-label={isRecording ? "Stop recording" : "Record voice note"}
          >
            {isRecording ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                <path fillRule="evenodd" d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9Z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
                <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
              </svg>
            )}
          </button>
        )}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isRecording ? "Recording..." : placeholder}
          disabled={disabled || isRecording}
          rows={1}
          className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] text-joy-text placeholder:text-joy-text-muted/60 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim() || isRecording}
          className="mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-joy-green text-white transition-colors hover:bg-joy-green-hover disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Send message"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
            <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
          </svg>
        </button>
      </div>
      <p className="mt-2 text-center text-xs text-joy-text-muted">
        Joy provides physiotherapy guidance, not medical diagnosis. In an emergency, call 112.
        {onStartRecording && " Tap the mic to send a voice note (max 1 min)."}
      </p>
    </form>
  );
}
