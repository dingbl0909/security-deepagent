export type Evidence = {
  title: string;
  source: string;
  snippet: string;
  score: number;
};

export type ChatRequest = {
  message: string;
  thread_id: string;
  user_id: string;
};

export type ChatResponse = {
  answer: string;
  thread_id: string;
  user_id: string;
  react_trace: string[];
  evidence: Evidence[];
  tasks: SecurityTask[];
  needs_review: boolean;
  review_id: number | null;
  risk_level: string;
  review_reason?: string | null;
  proposed_action?: string | null;
  risk_keywords?: string[];
};

export type SecurityTask = {
  id?: string;
  title: string;
  status: string;
  priority?: string;
  details?: string;
};

export type Message = {
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
};

export type ThreadSummary = {
  thread_id: string;
  user_id: string;
  title: string | null;
  summary: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  pending_review_count: number;
};

export type ReviewRequest = {
  id: number;
  thread_id: string;
  risk_level: string;
  reason: string;
  proposed_action: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ThreadDetail = {
  thread: ThreadSummary;
  messages: Message[];
  tasks: SecurityTask[];
  reviews: ReviewRequest[];
};

export type Device = {
  id: string;
  name: string;
  location: string;
  status: string;
  ip?: string;
  last_seen?: string;
  metadata_json?: Record<string, unknown>;
};

export type Alarm = {
  id: string;
  device_id: string;
  alarm_type: string;
  severity: string;
  status: string;
  occurred_at: string;
  summary: string;
  metadata_json?: Record<string, unknown>;
};

export type ContinueReviewResponse = {
  review_id: number;
  status: string;
};

export type HealthResponse = {
  status: string;
  app: string;
  llm_enabled: boolean;
};
