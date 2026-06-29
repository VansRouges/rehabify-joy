export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  redFlag?: boolean;
  messageType?: "text" | "voice";
  transcription?: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  mode: string;
  red_flag_triggered?: boolean;
  off_topic?: boolean;
  transcription?: string;
  audio_url?: string | null;
  audio_stored?: boolean;
}

export interface PatientProfile {
  patient_id: string;
  phone_number: string;
  display_name: string;
}

export interface SessionSummary {
  id: string;
  title: string | null;
  mode: string;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail {
  id: string;
  title: string | null;
  mode: string;
  triage_complete: boolean;
  messages: {
    id: string;
    direction: string;
    content: string;
    message_type: string;
    audio_url: string | null;
    red_flag_triggered: boolean;
    created_at: string;
  }[];
}
