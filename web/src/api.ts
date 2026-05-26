const API = import.meta.env.VITE_API_URL || "";

function headers(adminKey?: string): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (adminKey) h["X-Admin-Key"] = adminKey;
  return h;
}

export async function health() {
  const r = await fetch(`${API}/api/health`);
  return r.json();
}

export async function ask(question: string, corpus: string) {
  const r = await fetch(`${API}/api/ask`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ question, corpus }),
  });
  return r.json();
}

export async function contentFeed() {
  const r = await fetch(`${API}/api/content/feed`);
  return r.json();
}

export async function quizNext(vendor?: string, category?: string) {
  const q = new URLSearchParams();
  if (vendor) q.set("vendor", vendor);
  if (category) q.set("category", category);
  const r = await fetch(`${API}/api/quiz/next?${q}`);
  if (!r.ok) throw new Error("no question");
  return r.json();
}

export async function quizSubmit(body: {
  question_id: string;
  answer_text: string;
  self_score?: number;
  use_ai?: boolean;
}) {
  const r = await fetch(`${API}/api/quiz/submit`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  return r.json();
}

export async function quizStats() {
  const r = await fetch(`${API}/api/quiz/stats`);
  return r.json();
}

export async function quizReviewDue(limit = 5) {
  const r = await fetch(`${API}/api/quiz/review/due?limit=${limit}`);
  return r.json();
}

export async function quizReviewCalendar(year: number, month: number) {
  const r = await fetch(`${API}/api/quiz/review/calendar?year=${year}&month=${month}`);
  return r.json();
}

export async function quizReviewGrade(questionId: string, quality: number) {
  const r = await fetch(`${API}/api/quiz/review/grade`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ question_id: questionId, quality }),
  });
  return r.json();
}

export async function progressRadar() {
  const r = await fetch(`${API}/api/progress/radar`);
  return r.json();
}

export async function mockCreate(mode: string, vendor: string, focus: string) {
  const r = await fetch(`${API}/api/mock/sessions`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ mode, vendor, focus }),
  });
  return r.json();
}

export async function mockMessage(sessionId: string, message: string, wantHint: boolean) {
  const r = await fetch(`${API}/api/mock/sessions/${sessionId}/message`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ message, want_hint: wantHint }),
  });
  return r.json();
}

export async function mockFinish(sessionId: string) {
  const r = await fetch(`${API}/api/mock/sessions/${sessionId}/finish`, {
    method: "POST",
    headers: headers(),
  });
  return r.json();
}

export function mockReportPdfUrl(sessionId: string) {
  return `${API}/api/mock/sessions/${sessionId}/report.pdf`;
}

export async function labsList() {
  const r = await fetch(`${API}/api/labs`);
  return r.json();
}

export async function labsRecommend() {
  const r = await fetch(`${API}/api/labs/recommend`);
  return r.json();
}

export async function labComplete(labId: string, notes: string) {
  const r = await fetch(`${API}/api/labs/${labId}/complete`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ notes }),
  });
  return r.json();
}

export async function adminPending(adminKey: string) {
  const r = await fetch(`${API}/api/admin/content/pending`, { headers: headers(adminKey) });
  return r.json();
}

export async function adminApprove(adminKey: string, itemId: string) {
  const r = await fetch(`${API}/api/admin/content/${itemId}/approve`, {
    method: "POST",
    headers: headers(adminKey),
  });
  return r.json();
}

export async function adminReject(adminKey: string, itemId: string, note: string) {
  const r = await fetch(`${API}/api/admin/content/${itemId}/reject`, {
    method: "POST",
    headers: headers(adminKey),
    body: JSON.stringify({ note }),
  });
  return r.json();
}

export async function adminRunUpdate(adminKey: string) {
  const r = await fetch(`${API}/api/admin/content/run-update`, {
    method: "POST",
    headers: headers(adminKey),
  });
  return r.json();
}

export async function adminPublishLogs(adminKey: string) {
  const r = await fetch(`${API}/api/admin/content/publish-logs`, { headers: headers(adminKey) });
  return r.json();
}

export async function adminIngest(adminKey: string, full = false) {
  const r = await fetch(`${API}/api/ingest`, {
    method: "POST",
    headers: headers(adminKey),
    body: JSON.stringify({ full }),
  });
  return r.json();
}

export async function adminRollback(adminKey: string, logId: string) {
  const r = await fetch(`${API}/api/admin/content/rollback/${logId}`, {
    method: "POST",
    headers: headers(adminKey),
  });
  return r.json();
}
