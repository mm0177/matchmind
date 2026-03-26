const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type TokenProvider = () => Promise<string | null>;

let tokenProvider: TokenProvider | null = null;

export const setAuthTokenProvider = (provider: TokenProvider | null) => {
  tokenProvider = provider;
};

// ─── Typed fetch helper ───────────────────────────────────────────────────────
async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = tokenProvider ? await tokenProvider() : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─── Types ────────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  display_name: string;
  gender: string | null;
  birth_date: string | null;
  preferred_gender?: string | null;
  location?: string | null;
  age_pref_min?: number | null;
  age_pref_max?: number | null;
  is_verified: boolean;
  is_matchable: boolean;
  onboarding_completed: boolean;
  is_open_to_long_distance?: boolean;
}

export interface Session {
  id: string;
  title: string;
  is_active: boolean;
  created_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  day_number: number | null;
  created_at: string;
}

export interface DayStatus {
  current_day: number;
  theme: string;
  goal: string;
  is_complete: boolean;
  days_covered: number[];
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  me: () => apiFetch<User>("/auth/me"),

  completeProfile: (data: {
    display_name?: string;
    gender?: string;
    preferred_gender?: string;
    birth_date?: string;
    location?: string;
    age_pref_min?: number;
    age_pref_max?: number;
    is_open_to_long_distance?: boolean;
  }) =>
    apiFetch<User>("/auth/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

// ─── Chat ─────────────────────────────────────────────────────────────────────
export const chatApi = {
  createSession: (title?: string) =>
    apiFetch<Session>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title ?? "New Chat" }),
    }),

  listSessions: () => apiFetch<Session[]>("/chat/sessions"),

  getMessages: (sessionId: string) =>
    apiFetch<Message[]>(`/chat/sessions/${sessionId}/messages`),

  sendMessage: (sessionId: string, content: string) =>
    apiFetch<Message>(`/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  getDayStatus: () => apiFetch<DayStatus>("/chat/day-status"),
};

// ─── Dev / Testing ──────────────────────────────────────────────────────────
export const devApi = {
  allDays: () => apiFetch<Record<string, { theme: string; goal: string; target_traits: string[] }>>("/chat/dev/all-days"),

  dayPreview: (day: number) =>
    apiFetch<{
      day: number;
      theme: string;
      goal: string;
      target_traits: string[];
      sample_prompts: string[];
      system_context?: string;
    }>(`/chat/dev/day-preview/${day}`),

  setDay: (day: number) =>
    apiFetch<{ message: string; theme: string; goal: string }>(`/chat/dev/set-day/${day}`, { method: "POST" }),

  makeMatchable: () =>
    apiFetch<{ message: string }>("/chat/dev/make-me-matchable", { method: "POST" }),

  triggerExtraction: () =>
    apiFetch<{
      message: string;
      snapshot_version?: number;
      overall_confidence?: number;
      mbti_label?: string;
      big_five?: Record<string, number>;
      communication?: Record<string, number>;
      relationship?: {
        attachment_style?: string;
        conflict_style?: string;
        pace?: string;
        religious_profile?: {
          affiliation?: string | null;
          observance_level?: string | null;
          partner_requirement?: string | null;
        };
        dealbreakers?: string[];
        must_haves?: string[];
      };
      authenticity?: {
        overall: number | null;
        social_desirability: number | null;
        specificity: number | null;
        self_awareness: number | null;
        consistency: number | null;
      };
      financial?: {
        scarcity_response: number | null;
        wealth_vision: number | null;
        risk_tolerance: number | null;
      };
      self_perception?: {
        self_perception_gap: number | null;
        empathy_vs_apathy: number | null;
      };
      entities?: Array<{
        label: string;
        relationship: string;
        emotional_weight: string;
        context_note: string;
        day_extracted: number;
      }>;
      has_embedding?: boolean;
    }>("/chat/dev/trigger-extraction", { method: "POST" }),

  triggerMatching: () =>
    apiFetch<{
      message: string;
      run_date?: string;
      total_users_eligible?: number;
      total_matches_created?: number;
      algorithm_ver?: string;
    }>("/chat/dev/trigger-matching", { method: "POST" }),
};

// ─── Matches ──────────────────────────────────────────────────────────────────
export interface MatchDetail {
  id: string;
  partner_display_name: string;
  partner_age: number | null;
  conversation_id: string | null;
  status: string;
  created_at: string;
}

export interface MatchMessage {
  id: string;
  sender_id: string;
  content: string;
  created_at: string;
}

export const matchesApi = {
  list: () => apiFetch<MatchDetail[]>("/matches"),

  getMessages: (conversationId: string) =>
    apiFetch<MatchMessage[]>(`/matches/${conversationId}/messages`),

  sendMessage: (conversationId: string, content: string) =>
    apiFetch<MatchMessage>(`/matches/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
};

// ─── Notifications ────────────────────────────────────────────────────────────
export const notificationsApi = {
  list: (unreadOnly = false) =>
    apiFetch<Notification[]>(`/notifications${unreadOnly ? "?unread_only=true" : ""}`),

  unreadCount: () => apiFetch<{ unread_count: number }>("/notifications/unread-count"),

  markRead: (id: string) =>
    apiFetch<void>(`/notifications/${id}/read`, { method: "PATCH" }),
};
