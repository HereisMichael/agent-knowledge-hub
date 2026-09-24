const API = import.meta.env.VITE_API_URL || "";

export type LlmProtocol = "openai_chat" | "anthropic_messages";

export interface ModelSettingsUpdate {
  llm_protocol?: LlmProtocol;
  llm_base_url?: string;
  llm_model?: string;
  llm_api_key?: string;
  force_demo?: boolean;
}

export interface UserIdentity {
  id: string;
  email: string;
  role: "admin" | "member";
}

export interface AuthResponse {
  user: UserIdentity;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string) {
    super(code);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function headers(): HeadersInit {
  return { "Content-Type": "application/json" };
}

async function getJSON(url: string, init?: RequestInit): Promise<any> {
  const r = await fetch(url, { ...init, credentials: "include" });
  let payload: any = null;
  try {
    payload = await r.json();
  } catch {
    payload = null;
  }
  if (!r.ok) {
    throw new ApiError(r.status, payload?.detail || "request_failed");
  }
  return payload;
}

async function postJSON(url: string, body?: unknown): Promise<any> {
  return getJSON(url, {
    method: "POST",
    headers: headers(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function putJSON(url: string, body: unknown): Promise<any> {
  return getJSON(url, {
    method: "PUT",
    headers: headers(),
    body: JSON.stringify(body),
  });
}

export interface HealthResponse {
  questions?: number;
  demo_mode?: boolean;
}

export interface ExerciseItem {
  id: string;
  set_id: string;
  title: string;
  kind: "single_choice" | "blank_fill" | "implementation_challenge";
  level: number;
  topics: string[];
  prompt_markdown: string;
  options: Record<string, string>;
  blanks: { id: string }[];
  answer_mode: "choice_exact" | "normalized_blank_match" | "manual_review";
  source_anchor: { path: string; heading?: string; line: number };
  estimated_minutes?: number;
}

export interface ExerciseProgress {
  total_attempts: number;
  completed_items: number;
  items: { exercise_id: string; attempts: number; best_score: number | null; last_attempt_at: string }[];
  attempts?: number;
  graded_average?: number | null;
  recorded_challenges?: number;
  by_topic?: Record<string, { attempts: number; graded_average: number | null }>;
  by_level?: Record<string, { attempts: number; graded_average: number | null }>;
}

export interface ExerciseAttemptResult {
  attempt_id: string;
  status: "graded" | "partially_graded" | "recorded";
  score: number | null;
  feedback: { message?: string; correct?: boolean; correct_blanks?: string[]; total_blanks?: number };
  progress: ExerciseProgress;
  reference_markdown?: string;
}

export async function exercisesList(): Promise<{ items: ExerciseItem[]; total: number }> {
  return getJSON(`${API}/api/exercises`);
}

export async function exerciseGet(id: string): Promise<ExerciseItem> {
  return getJSON(`${API}/api/exercises/${encodeURIComponent(id)}`);
}

export async function exerciseProgress(): Promise<ExerciseProgress> {
  return getJSON(`${API}/api/exercises/progress`);
}

export async function exerciseSubmit(
  id: string,
  answers: Record<string, unknown>,
  requestReveal = true,
): Promise<ExerciseAttemptResult> {
  return postJSON(`${API}/api/exercises/${encodeURIComponent(id)}/attempts`, {
    answers,
    request_reveal: requestReveal,
  });
}

export async function health(): Promise<HealthResponse> {
  return getJSON(`${API}/api/health`);
}

export async function getCurrentUser(): Promise<AuthResponse> {
  return getJSON(`${API}/api/auth/me`);
}

export async function login(body: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return postJSON(`${API}/api/auth/login`, body);
}

export async function registerAccount(body: {
  email: string;
  password: string;
  invite_code: string;
}): Promise<AuthResponse> {
  return postJSON(`${API}/api/auth/register`, body);
}

export async function logout(): Promise<void> {
  await postJSON(`${API}/api/auth/logout`);
}

export async function ask(question: string, corpus: string) {
  return postJSON(`${API}/api/ask`, { question, corpus });
}

export async function contentFeed() {
  return getJSON(`${API}/api/content/feed`);
}

export async function quizNext(vendor?: string, category?: string) {
  const q = new URLSearchParams();
  if (vendor) q.set("vendor", vendor);
  if (category) q.set("category", category);
  return getJSON(`${API}/api/quiz/next?${q}`);
}

export async function quizSubmit(body: {
  question_id: string;
  answer_text: string;
  reference_answer?: string;
  save_reference?: boolean;
  self_score?: number;
  use_ai?: boolean;
}) {
  return postJSON(`${API}/api/quiz/submit`, body);
}

export async function quizStats() {
  return getJSON(`${API}/api/quiz/stats`);
}

export async function fetchAllQuestions() {
  return getJSON(`${API}/api/questions/all`);
}

export async function quizGetReference(questionId: string) {
  return getJSON(`${API}/api/quiz/questions/${questionId}/reference`);
}

export async function quizPutReference(questionId: string, referenceText: string) {
  return putJSON(`${API}/api/quiz/questions/${questionId}/reference`, {
    reference_text: referenceText,
  });
}

export async function quizAnalytics() {
  return getJSON(`${API}/api/quiz/analytics`);
}

export async function quizHistory(limit = 30) {
  return getJSON(`${API}/api/quiz/history?limit=${limit}`);
}

export async function getSettings() {
  return getJSON(`${API}/api/settings`);
}

export async function updateSettings(body: ModelSettingsUpdate) {
  return putJSON(`${API}/api/settings`, body);
}

export async function testSettings() {
  return postJSON(`${API}/api/settings/test`);
}

export async function exportAccountData(): Promise<Blob> {
  const response = await fetch(`${API}/api/account/export`, {
    credentials: "include",
  });
  if (!response.ok) {
    let code = "request_failed";
    try {
      code = (await response.json())?.detail || code;
    } catch {
      // Keep the stable public error code.
    }
    throw new ApiError(response.status, code);
  }
  return response.blob();
}

export async function deleteAccount(password: string): Promise<void> {
  await getJSON(`${API}/api/account`, {
    method: "DELETE",
    headers: headers(),
    body: JSON.stringify({ password }),
  });
}

export async function quizReviewDue(limit = 5) {
  return getJSON(`${API}/api/quiz/review/due?limit=${limit}`);
}

export async function quizReviewCalendar(year: number, month: number) {
  return getJSON(`${API}/api/quiz/review/calendar?year=${year}&month=${month}`);
}

export async function quizReviewGrade(questionId: string, quality: number) {
  return postJSON(`${API}/api/quiz/review/grade`, { question_id: questionId, quality });
}

export async function progressRadar() {
  return getJSON(`${API}/api/progress/radar`);
}

export async function mockCreate(mode: string, vendor: string, focus: string) {
  return postJSON(`${API}/api/mock/sessions`, { mode, vendor, focus });
}

export async function mockMessage(sessionId: string, message: string, wantHint: boolean) {
  return postJSON(`${API}/api/mock/sessions/${sessionId}/message`, {
    message,
    want_hint: wantHint,
  });
}

export async function mockFinish(sessionId: string) {
  return postJSON(`${API}/api/mock/sessions/${sessionId}/finish`);
}

export function mockReportPdfUrl(sessionId: string) {
  return `${API}/api/mock/sessions/${sessionId}/report.pdf`;
}

export async function labsList() {
  return getJSON(`${API}/api/labs`);
}

export async function labsRecommend() {
  return getJSON(`${API}/api/labs/recommend`);
}

export async function labComplete(labId: string, notes: string) {
  return postJSON(`${API}/api/labs/${labId}/complete`, { notes });
}

export async function adminPending() {
  return getJSON(`${API}/api/admin/content/pending`);
}

export async function adminApprove(itemId: string) {
  return postJSON(`${API}/api/admin/content/${itemId}/approve`);
}

export async function adminReject(itemId: string, note: string) {
  return postJSON(`${API}/api/admin/content/${itemId}/reject`, { note });
}

export async function adminRunUpdate() {
  return postJSON(`${API}/api/admin/content/run-update`);
}

export async function adminPublishLogs() {
  return getJSON(`${API}/api/admin/content/publish-logs`);
}

export async function adminIngest(full = false) {
  return postJSON(`${API}/api/ingest`, { full });
}

export async function adminRollback(logId: string) {
  return postJSON(`${API}/api/admin/content/rollback/${logId}`);
}

export interface AssessmentGradeResponse {
  ai_score: number;
  matched_points: string[];
  missing_points: string[];
  feedback: string;
  demo: boolean;
}

export async function gradeAssessmentAnswer(body: {
  question: string;
  answer_text: string;
  key_points: string[];
  rubric: Record<string, number>;
  reference_answer?: string;
}): Promise<AssessmentGradeResponse> {
  return postJSON(`${API}/api/assessment/grade`, body);
}
