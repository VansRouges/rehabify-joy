"use client";

import { FormEvent, KeyboardEvent, useRef, useEffect } from "react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
  centered?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Tell Joy what's been bothering you...",
  centered = false,
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
    if (!value.trim() || disabled) return;
    onSubmit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={`w-full ${centered ? "max-w-2xl mx-auto" : "max-w-3xl mx-auto px-4"}`}
    >
      <div className="relative flex items-end gap-2 rounded-2xl border border-joy-border bg-white p-2 shadow-sm focus-within:border-joy-green/40 focus-within:ring-2 focus-within:ring-joy-sage">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] text-joy-text placeholder:text-joy-text-muted/60 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
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
      </p>
    </form>
  );
}
