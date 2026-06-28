"use client";

import Link from "next/link";
import { JoyLogo } from "./JoyLogo";
import type { SessionSummary } from "@/lib/types";

interface SidebarProps {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  patientName?: string | null;
}

export function Sidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  collapsed,
  onToggleCollapse,
  patientName,
}: SidebarProps) {
  if (collapsed) {
    return (
      <aside className="flex w-14 shrink-0 flex-col items-center border-r border-joy-border bg-joy-white py-4">
        <button
          onClick={onToggleCollapse}
          className="mb-4 rounded-lg p-2 text-joy-text-muted hover:bg-joy-cream-dark"
          aria-label="Expand sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
        <button
          onClick={onNewChat}
          className="rounded-lg p-2 text-joy-green hover:bg-joy-sage"
          aria-label="New chat"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z" />
          </svg>
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-joy-border bg-joy-white">
      <div className="flex items-center justify-between border-b border-joy-border px-4 py-4">
        <JoyLogo size="sm" />
        <button
          onClick={onToggleCollapse}
          className="rounded-lg p-1.5 text-joy-text-muted hover:bg-joy-cream-dark"
          aria-label="Collapse sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
      </div>

      <div className="p-3">
        <button
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-xl bg-joy-green px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-joy-green-hover"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-4 w-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-2 pb-4">
        <p className="px-2 py-2 text-[11px] font-semibold uppercase tracking-wider text-joy-text-muted">
          Recent
        </p>
        {sessions.length === 0 ? (
          <p className="px-2 py-4 text-sm text-joy-text-muted">No conversations yet</p>
        ) : (
          <ul className="space-y-0.5">
            {sessions.map((session) => (
              <li key={session.id}>
                <button
                  onClick={() => onSelectSession(session.id)}
                  className={`w-full truncate rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                    activeSessionId === session.id
                      ? "bg-joy-sage text-joy-green font-medium"
                      : "text-joy-text hover:bg-joy-cream-dark"
                  }`}
                >
                  {session.title || "New conversation"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border-t border-joy-border p-4">
        {patientName && (
          <p className="mb-2 truncate text-sm font-medium text-joy-text">{patientName}</p>
        )}
        <div className="rounded-xl bg-joy-sage px-3 py-2.5">
          <p className="text-xs font-medium text-joy-green">Piloting in Lagos & Abuja</p>
          <Link href="https://physioaroundme.com" target="_blank" className="mt-0.5 text-[11px] text-joy-text-muted">physioaroundme.com</Link>
        </div>
      </div>
    </aside>
  );
}
