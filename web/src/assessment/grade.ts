import type { ObjectiveQuestion } from "./objectiveBank";
import type { OpenQuestion } from "./openBank";

export type QuestionKind = "single" | "multi" | "boolean" | "open" | "architecture";

export interface UserAnswer {
  questionId: string;
  dimId: string;
  kind: QuestionKind;
  /** 选择题/判断：单一索引；多选：数组；开放：文本 */
  value: number | number[] | string;
  /** 开放题判分结果（仅 open/architecture 有） */
  grading?: {
    aiScore: number;
    matched: string[];
    missing: string[];
    feedback: string;
    demo: boolean;
  };
}

export interface DimResult {
  dimId: string;
  /** 0..100 */
  score: number;
}

export function gradeObjective(q: ObjectiveQuestion, ans: number | number[]): {
  correct: boolean;
  score: number;
} {
  if (q.type === "multi") {
    const expected = Array.isArray(q.correct) ? [...q.correct].sort((a, b) => a - b) : [q.correct];
    const got = Array.isArray(ans) ? [...ans].sort((a, b) => a - b) : [ans];
    if (expected.length !== got.length) return { correct: false, score: 0 };
    const match = expected.every((v, i) => v === got[i]);
    return { correct: match, score: match ? 100 : 0 };
  }
  const expectedIdx = Array.isArray(q.correct) ? q.correct[0] : q.correct;
  const gotIdx = Array.isArray(ans) ? ans[0] : ans;
  return { correct: gotIdx === expectedIdx, score: gotIdx === expectedIdx ? 100 : 0 };
}

/** 维度分 = 该维所有题目得分均值。开放题 LLM 判分已是 0..100；客观题 0/100。 */
export function computeDimensionScores(
  answers: UserAnswer[],
  objectiveIndex: Map<string, ObjectiveQuestion>,
): DimResult[] {
  const byDim = new Map<string, number[]>();
  for (const a of answers) {
    let s = 0;
    if (a.kind === "open" || a.kind === "architecture") {
      if (!a.grading) continue;
      s = a.grading.aiScore;
    } else {
      const q = objectiveIndex.get(a.questionId);
      if (!q) continue;
      s = gradeObjective(q, a.value as number | number[]).score;
    }
    const arr = byDim.get(a.dimId) ?? [];
    arr.push(s);
    byDim.set(a.dimId, arr);
  }
  const results: DimResult[] = [];
  for (const [dimId, scores] of byDim.entries()) {
    const score = scores.length === 0 ? 0 : Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    results.push({ dimId, score });
  }
  return results;
}

export function buildOpenGradingRequest(q: OpenQuestion, answerText: string) {
  return {
    question: q.stem,
    answer_text: answerText,
    key_points: q.keyPoints,
    rubric: q.rubric,
  };
}