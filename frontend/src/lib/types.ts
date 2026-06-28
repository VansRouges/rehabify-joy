export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  redFlag?: boolean;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  mode: string;
  red_flag_triggered?: boolean;
  off_topic?: boolean;
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
    red_flag_triggered: boolean;
    created_at: string;
  }[];
}
