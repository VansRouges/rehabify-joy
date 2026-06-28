import type { ChatMessage } from "@/lib/types";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-[15px] leading-relaxed ${
          isUser
            ? "bg-joy-green text-white rounded-br-md"
            : message.redFlag
              ? "bg-red-50 text-red-900 border border-red-200 rounded-bl-md"
              : "bg-white text-joy-text border border-joy-border shadow-sm rounded-bl-md"
        }`}
      >
        {!isUser && (
          <p className="mb-1 text-xs font-semibold text-joy-peach">Joy</p>
        )}
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl rounded-bl-md border border-joy-border bg-white px-4 py-3 shadow-sm">
        <p className="mb-2 text-xs font-semibold text-joy-peach">Joy</p>
        <div className="flex items-center gap-1">
          <span className="typing-dot h-2 w-2 rounded-full bg-joy-peach" />
          <span className="typing-dot h-2 w-2 rounded-full bg-joy-peach" />
          <span className="typing-dot h-2 w-2 rounded-full bg-joy-peach" />
        </div>
      </div>
    </div>
  );
}
