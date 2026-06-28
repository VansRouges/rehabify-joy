import type { ChatMessage } from "@/lib/types";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isVoice = message.messageType === "voice";

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
        {isUser && isVoice && (
          <p className="mb-1 flex items-center gap-1 text-xs opacity-80">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3">
              <path d="M8 1a2.5 2.5 0 0 0-2.5 2.5v5A2.5 2.5 0 0 0 8 11a2.5 2.5 0 0 0 2.5-2.5v-5A2.5 2.5 0 0 0 8 1Z" />
              <path d="M4 7.5a.5.5 0 0 1 1 0v.5a3 3 0 0 0 6 0V7.5a.5.5 0 0 1 1 0v.5a4 4 0 0 1-3 3.874V13.5H11a.5.5 0 0 1 0 1H5a.5.5 0 0 1 0-1h2v-2.126A4 4 0 0 1 4 8V7.5Z" />
            </svg>
            Voice note
          </p>
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
