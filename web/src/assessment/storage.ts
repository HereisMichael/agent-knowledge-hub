import { MAAS_DIMENSIONS, RATING_MAX } from "./dimensions";
import type { UserAnswer } from "./grade";

const STORAGE_KEY = "akh_maas_assessments_v2";

export interface AssessmentRecord {
  id: string;
  createdAt: string;
  /** dimId -> 各测评项评分数组（0..RATING_MAX），老格式保留兼容 */
  ratings: Record<string, number[]>;
  /** dimId -> 归一化维度分（0..100） */
  scores: Record<string, number>;
  /** 总分（0..100） */
  overall: number;
  /** v2 增量：每题作答详情（含客观/开放题判分结果） */
  answers: UserAnswer[];
  /** 本次测评选中的维度；缺省表示全 8 维（兼容旧记录） */
  dimIds?: string[];
}

export type RatingsInput = Record<string, number[]>;

function safeRead(): AssessmentRecord[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as AssessmentRecord[]) : [];
  } catch {
    return [];
  }
}

function safeWrite(records: AssessmentRecord[]): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
  } catch {
    /* ignore quota / serialization errors */
  }
}

function averageTo100(ratings: number[]): number {
  if (ratings.length === 0) return 0;
  const sum = ratings.reduce((a, b) => a + b, 0);
  return Math.round((sum / (ratings.length * RATING_MAX)) * 100);
}

export function computeScores(ratings: RatingsInput): {
  scores: Record<string, number>;
  overall: number;
} {
  const scores: Record<string, number> = {};
  for (const dim of MAAS_DIMENSIONS) {
    scores[dim.id] = averageTo100(ratings[dim.id] ?? []);
  }
  const values = MAAS_DIMENSIONS.map((d) => scores[d.id]);
  const overall = Math.round(values.reduce((a, b) => a + b, 0) / values.length);
  return { scores, overall };
}

export function listAssessments(): AssessmentRecord[] {
  return safeRead().sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export interface SaveAssessmentInput {
  ratings: RatingsInput;
  scores: Record<string, number>;
  overall: number;
  answers: UserAnswer[];
  dimIds?: string[];
}

export function saveAssessment(input: SaveAssessmentInput): AssessmentRecord {
  const record: AssessmentRecord = {
    id: `as_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    ratings: input.ratings,
    scores: input.scores,
    overall: input.overall,
    answers: input.answers,
    dimIds: input.dimIds,
  };
  const records = safeRead();
  records.push(record);
  safeWrite(records);
  return record;
}

export function deleteAssessment(id: string): void {
  safeWrite(safeRead().filter((r) => r.id !== id));
}

/** 最近一次与上一次（用于计算增量），latest 在前 */
export function latestTwo(): { latest?: AssessmentRecord; previous?: AssessmentRecord } {
  const sorted = listAssessments();
  return { latest: sorted[0], previous: sorted[1] };
}

/** 每维相对上次的增量（正=进步） */
export function dimensionDeltas(
  latest: AssessmentRecord,
  previous?: AssessmentRecord,
): Record<string, number | null> {
  const deltas: Record<string, number | null> = {};
  for (const dim of MAAS_DIMENSIONS) {
    if (!previous) {
      deltas[dim.id] = null;
      continue;
    }
    deltas[dim.id] = latest.scores[dim.id] - (previous.scores[dim.id] ?? 0);
  }
  return deltas;
}

/** 历次总分趋势（按时间正序） */
export function overallTrend(): { createdAt: string; overall: number }[] {
  return safeRead()
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
    .map((r) => ({ createdAt: r.createdAt, overall: r.overall }));
}
