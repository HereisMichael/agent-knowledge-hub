import { MAAS_DIMENSIONS } from "./dimensions";

export interface OpenQuestion {
  id: string;
  dimId: string;
  type: "open" | "architecture";
  stem: string;
  keyPoints: string[];
  rubric: Record<string, number>;
  source: { ref: string; where: string };
}

interface BankQuestion {
  id: string;
  category: string;
  subcategory?: string;
  difficulty: number;
  question: string;
  key_points: string[];
  rubric?: Record<string, number>;
}

/**
 * 从真实题库（183 题）按维度映射开放题。题库每题都带 source id 与
 * key_points/rubric，开放题无需编造，全部来自 questions.jsonl。
 */
export async function loadOpenQuestions(): Promise<OpenQuestion[]> {
  let qs: BankQuestion[] = [];
  try {
    const data = (await fetch("/api/questions/all").then((r) => r.json())) as {
      questions?: BankQuestion[];
    };
    qs = data.questions ?? [];
  } catch {
    return [];
  }

  const out: OpenQuestion[] = [];
  for (const dim of MAAS_DIMENSIONS) {
    if (dim.quizCategories.length === 0) continue;
    const pool = qs.filter((q) => dim.quizCategories.includes(q.category));
    if (pool.length === 0) continue;

    // 架构设计题优先从 ai-arch 取
    const arch =
      pool.find((q) => q.category === "ai-arch") ?? pool[0];
    // 普通开放论证题取同维度其他题
    const open = pool.find((q) => q.id !== arch.id) ?? arch;

    out.push(toOpenQuestion(dim.id, "architecture", arch));
    out.push(toOpenQuestion(dim.id, "open", open));
  }
  return out;
}

function toOpenQuestion(
  dimId: string,
  type: "open" | "architecture",
  q: BankQuestion,
): OpenQuestion {
  return {
    id: `open-${q.id}`,
    dimId,
    type,
    stem: q.question,
    keyPoints: q.key_points ?? [],
    rubric: q.rubric ?? { depth: 60, structure: 40 },
    source: { ref: q.id, where: `题库 / ${q.category}${q.subcategory ? " / " + q.subcategory : ""}` },
  };
}

export function openQuestionsByDim(all: OpenQuestion[], dimId: string): OpenQuestion[] {
  return all.filter((q) => q.dimId === dimId);
}
