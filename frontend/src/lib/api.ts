import type { ChatResponse, PatientProfile, SessionDetail, SessionSummary } from "./types";
import { getStoredPatient } from "./patient";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function patientHeaders(): Record<string, string> {
  const patient = getStoredPatient();
  if (!patient?.patientId) return {};
  return { "X-Patient-Id": patient.patientId };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...patientHeaders(),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let detail = await response.text();
    try {
      const json = JSON.parse(detail);
      detail = json.detail ?? detail;
    } catch {
      /* plain text */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }

  return response.json() as Promise<T>;
}

export async function registerPatient(
  phoneNumber: string,
  displayName: string,
): Promise<PatientProfile> {
  return request<PatientProfile>("/api/patients/register", {
    method: "POST",
    body: JSON.stringify({ phone_number: phoneNumber, display_name: displayName }),
  });
}

export async function sendMessage(message: string, sessionId?: string): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export async function sendVoiceMessage(
  audio: Blob,
  sessionId?: string,
  durationSeconds?: number,
): Promise<ChatResponse> {
  const form = new FormData();
  form.append("file", audio, "recording.webm");
  if (sessionId) form.append("session_id", sessionId);
  if (durationSeconds !== undefined) {
    form.append("duration_seconds", String(durationSeconds));
  }
  return request<ChatResponse>("/api/chat/voice", { method: "POST", body: form });
}

export async function listSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>("/api/chat/sessions");
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  return request<SessionDetail>(`/api/chat/sessions/${sessionId}`);
}
