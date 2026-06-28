import type { ChatResponse, SessionDetail, SessionSummary } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function sendMessage(message: string, sessionId?: string): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export async function createSession(): Promise<SessionSummary> {
  return request<SessionSummary>("/api/chat/sessions", { method: "POST" });
}

export async function listSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>("/api/chat/sessions");
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  return request<SessionDetail>(`/api/chat/sessions/${sessionId}`);
}
