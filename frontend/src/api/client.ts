import type {
  Alarm,
  ChatRequest,
  ChatResponse,
  ContinueReviewResponse,
  Device,
  HealthResponse,
  ReviewRequest,
  ThreadDetail,
  ThreadSummary,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8015";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function sendChat(payload: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listThreads(): Promise<ThreadSummary[]> {
  const data = await request<{ threads: ThreadSummary[] }>("/threads");
  return data.threads;
}

export function getThread(threadId: string): Promise<ThreadDetail> {
  return request<ThreadDetail>(`/threads/${encodeURIComponent(threadId)}`);
}

export async function listReviews(status = "pending"): Promise<ReviewRequest[]> {
  const data = await request<{ reviews: ReviewRequest[] }>(`/reviews?status=${encodeURIComponent(status)}`);
  return data.reviews;
}

export async function listDevices(): Promise<Device[]> {
  const data = await request<{ devices: Device[] }>("/devices");
  return data.devices;
}

export async function listAlarms(): Promise<Alarm[]> {
  const data = await request<{ alarms: Alarm[] }>("/alarms");
  return data.alarms;
}

export function continueReview(reviewId: number, approve: boolean): Promise<ContinueReviewResponse> {
  return request<ContinueReviewResponse>("/review/continue", {
    method: "POST",
    body: JSON.stringify({
      review_id: reviewId,
      approve,
      operator_id: "ops_001",
    }),
  });
}
