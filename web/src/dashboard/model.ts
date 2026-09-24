import { health, progressRadar, quizReviewDue, quizStats, type HealthResponse } from "../api";
import { latestTwo, type AssessmentRecord } from "../assessment/storage";
import { isPageId, type PageId } from "../navigation";
import type { StatusTone } from "../components/ui/StatusBadge";

export interface DashboardStats {
  total_attempts: number;
  avg_score: number;
  by_vendor?: Record<string, number>;
  review?: { total_cards: number; due_now: number };
}

export interface DashboardDue {
  items: Array<{ question: { id: string; question: string }; card?: unknown }>;
}

export interface RadarAxis {
  axis: string;
  value: number;
  detail?: string;
}

export interface DashboardRadar {
  quiz: { axes: RadarAxis[]; max?: number };
  mock: { axes: RadarAxis[]; max?: number };
}

export interface DashboardSources {
  health?: HealthResponse;
  stats?: DashboardStats;
  due?: DashboardDue;
  radar?: DashboardRadar;
  latestAssessment?: AssessmentRecord;
  lastPage?: PageId;
  failedSources: string[];
}

export interface DashboardTask {
  id: string;
  label: string;
  reason: string;
  target: PageId;
  status: "current" | "attention" | "pending";
}

export interface DashboardMetric {
  label: string;
  value: string | number;
  detail: string;
  tone?: StatusTone;
}

export interface DashboardSignal {
  id: string;
  label: string;
  value: number;
}

export interface DashboardViewModel {
  metrics: DashboardMetric[];
  tasks: DashboardTask[];
  signals: DashboardSignal[];
  resume?: { label: string; target: PageId };
  partialFailure: boolean;
}

const RESUMABLE_PAGES = new Set<PageId>(["learn", "quiz", "bank", "mock", "labs", "assess"]);

const AXIS_LABELS: Record<string, string> = {
  inference: "推理优化",
  rag: "RAG 检索",
  architecture: "架构设计",
  product: "产品理解",
  behavior: "行为表达",
  solution: "解决方案",
  agent: "Agent 编排",
  structure: "回答结构",
  depth: "技术深度",
  tradeoff: "权衡分析",
  compliance: "合规意识",
  communication: "表达沟通",
};

function axisLabel(axis: string): string {
  return AXIS_LABELS[axis] ?? axis;
}

function readLastPage(): PageId | undefined {
  if (typeof localStorage === "undefined") return undefined;
  const stored = localStorage.getItem("akh_last_page_v1");
  return stored && isPageId(stored) ? stored : undefined;
}

export async function loadDashboardSources(): Promise<DashboardSources> {
  const assessment = latestTwo().latest;
  const requests = [health(), quizStats(), quizReviewDue(5), progressRadar()] as const;
  const results = await Promise.allSettled(requests);
  const failedSources: string[] = [];
  const sources: DashboardSources = {
    failedSources,
    latestAssessment: assessment,
    lastPage: readLastPage(),
  };

  const assign = <K extends "health" | "stats" | "due" | "radar">(
    index: number,
    key: K,
  ) => {
    const result = results[index];
    if (result.status === "rejected") {
      failedSources.push(key);
      return;
    }
    (sources[key] as unknown) = result.value;
  };

  assign(0, "health");
  assign(1, "stats");
  assign(2, "due");
  assign(3, "radar");
  return sources;
}

function lowestRadarAxis(radar?: DashboardRadar): RadarAxis | undefined {
  return radar
    ? [...radar.quiz.axes, ...radar.mock.axes].sort((a, b) => a.value - b.value)[0]
    : undefined;
}

export function buildDashboardModel(sources: DashboardSources): DashboardViewModel {
  const dueCount = sources.stats?.review?.due_now ?? sources.due?.items.length;
  const lowest = lowestRadarAxis(sources.radar);
  const tasks: Omit<DashboardTask, "status">[] = [];

  if (dueCount && dueCount > 0) {
    tasks.push({ id: "review", label: "完成间隔复习", reason: `${dueCount} 道题已到复习时间`, target: "quiz" });
  }
  if (!sources.latestAssessment) {
    tasks.push({ id: "assessment", label: "完成首次技能测评", reason: "建立能力基线，让后续训练更聚焦", target: "assess" });
  }
  if (lowest) {
    const label = axisLabel(lowest.axis);
    tasks.push({ id: `axis-${lowest.axis}`, label: `强化${label}`, reason: `${label}当前覆盖 ${Math.round(lowest.value)}%`, target: "quiz" });
  }
  if (tasks.length < 3) {
    tasks.push({ id: "warmup", label: "随机题目热身", reason: "从正式题库抽取一道题，保持答题手感", target: "quiz" });
  }

  const statuses = ["current", "attention", "pending"] as const;
  const normalizedTasks = tasks.slice(0, 3).map((task, index) => ({
    ...task,
    status: statuses[index] ?? "pending",
  }));

  const assessmentSignals = sources.latestAssessment
    ? Object.entries(sources.latestAssessment.scores).map(([id, value]) => ({ id, label: axisLabel(id), value }))
    : [];
  const radarSignals = sources.radar
    ? [...sources.radar.quiz.axes, ...sources.radar.mock.axes]
        .sort((a, b) => a.value - b.value)
        .slice(0, 4)
        .map((axis) => ({ id: axis.axis, label: axisLabel(axis.axis), value: axis.value }))
    : [];

  return {
    metrics: [
      { label: "正式题库", value: sources.health?.questions ?? "—", detail: "已发布训练题", tone: "info" },
      { label: "能力评分", value: sources.latestAssessment?.overall ?? (sources.stats?.total_attempts ? Math.round(sources.stats.avg_score) : "—"), detail: "最近综合表现", tone: "success" },
      { label: "待复习", value: dueCount ?? "—", detail: "当前到期题目", tone: dueCount ? "warning" : "neutral" },
    ],
    tasks: normalizedTasks,
    signals: (assessmentSignals.length ? assessmentSignals : radarSignals).slice(0, 4),
    resume: sources.lastPage && RESUMABLE_PAGES.has(sources.lastPage)
      ? { label: "继续上次训练", target: sources.lastPage }
      : undefined,
    partialFailure: sources.failedSources.length > 0,
  };
}
