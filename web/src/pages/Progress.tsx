import { useEffect, useMemo, useState } from "react";
import { exerciseProgress, progressRadar, quizAnalytics, quizStats, type ExerciseProgress } from "../api";
import { RadarChart } from "../components/RadarChart";
import { ReviewCalendar } from "../components/ReviewCalendar";
import { ScoreHistoryTable } from "../components/ScoreHistoryTable";
import { FeedbackState } from "../components/ui/FeedbackState";
import { MetricTile } from "../components/ui/MetricTile";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { StatusBadge } from "../components/ui/StatusBadge";
import { QUESTION_SOURCE_LABELS, type QuestionSource } from "../questions/catalog";

type LoadState = "loading" | "ready" | "error";
type Stats = { total_attempts: number; avg_score: number; by_vendor: Record<string, number>; review?: { total_cards: number; due_now: number } };
type RadarData = { quiz: { axes: { axis: string; value: number; detail?: string }[] }; mock: { axes: { axis: string; value: number }[] } };
type Analytics = {
  summary: { total_attempts: number; questions_practiced: number; overall_avg: number; by_category: Record<string, number>; by_vendor: Record<string, number> };
  questions: Parameters<typeof ScoreHistoryTable>[0]["rows"];
};

const AXIS_LABELS: Record<string, string> = { architecture: "架构设计", product: "产品理解", behavior: "行为表达", solution: "解决方案", agent: "Agent 编排", inference: "推理优化", rag: "RAG 检索", structure: "回答结构", depth: "技术深度", tradeoff: "权衡分析", compliance: "合规意识", communication: "表达沟通" };

function axisLabel(axis: string) { return AXIS_LABELS[axis] ?? axis; }

export function ProgressPage() {
  const [stats, setStats] = useState<Stats>();
  const [statsState, setStatsState] = useState<LoadState>("loading");
  const [radar, setRadar] = useState<RadarData>();
  const [radarState, setRadarState] = useState<LoadState>("loading");
  const [analytics, setAnalytics] = useState<Analytics>();
  const [analyticsState, setAnalyticsState] = useState<LoadState>("loading");
  const [modelProgress, setModelProgress] = useState<ExerciseProgress>();
  const [modelProgressState, setModelProgressState] = useState<LoadState>("loading");

  useEffect(() => {
    let active = true;
    quizStats().then((data) => { if (active) { setStats(data); setStatsState("ready"); } }).catch(() => active && setStatsState("error"));
    progressRadar().then((data) => { if (active) { setRadar(data); setRadarState("ready"); } }).catch(() => active && setRadarState("error"));
    quizAnalytics().then((data) => { if (active) { setAnalytics(data); setAnalyticsState("ready"); } }).catch(() => active && setAnalyticsState("error"));
    exerciseProgress().then((data) => { if (active) { setModelProgress(data); setModelProgressState("ready"); } }).catch(() => active && setModelProgressState("error"));
    return () => { active = false; };
  }, []);

  const weakest = useMemo(() => radar ? [...radar.quiz.axes, ...radar.mock.axes].sort((a, b) => a.value - b.value)[0] : undefined, [radar]);
  const weeklySignal = stats
    ? weakest ? `本周优先加强${axisLabel(weakest.axis)}；当前信号为 ${Math.round(weakest.value)}，建议从一轮针对性刷题开始。`
      : stats.review?.due_now ? `当前有 ${stats.review.due_now} 道到期复习题，先清空复习队列再开始新题。`
      : `已完成 ${stats.total_attempts} 次作答，继续保持稳定训练节奏。`
    : "正在汇总本周训练信号。";

  return (
    <div className="insights-page">
      <PageHeader eyebrow="LEARNING SIGNALS" title="学习进度" description="把刷题、复习与模拟面试数据整理成下一步可执行的训练信号。" />

      <section className="insight-metrics" aria-label="学习指标">
        <MetricTile label="作答次数" value={statsState === "ready" ? stats!.total_attempts : "—"} detail={statsState === "error" ? "统计暂不可用" : "累计训练"} tone="info" />
        <MetricTile label="平均得分" value={statsState === "ready" ? stats!.avg_score : "—"} detail="最近综合表现" tone="success" />
        <MetricTile label="待复习" value={statsState === "ready" ? stats!.review?.due_now ?? 0 : "—"} detail="当前到期题目" tone="warning" />
        <MetricTile label="复习卡片" value={statsState === "ready" ? stats!.review?.total_cards ?? 0 : "—"} detail="已建立记忆卡" />
      </section>
      {statsState === "error" && <div className="inline-message" data-tone="danger" role="alert">训练统计加载失败，其他洞察仍可继续查看。</div>}

      <Panel className="weekly-signal" eyebrow="WEEKLY SIGNAL" title="本周信号" actions={statsState === "ready" ? <StatusBadge tone="info">建议已更新</StatusBadge> : undefined}><p>{weeklySignal}</p></Panel>

      <Panel className="model-exercise-progress" eyebrow="MODEL ENGINEERING" title="模型工程练习">
        {modelProgressState === "loading" && <p className="empty-hint">正在读取练习进度…</p>}
        {modelProgressState === "error" && <FeedbackState kind="error" title="模型练习进度暂不可用" description="面试训练统计不受影响。" />}
        {modelProgress && <>
          <p className="insight-summary">{modelProgress.attempts ?? modelProgress.total_attempts} 次提交 · {modelProgress.completed_items} 道已尝试 · 自动判分均分 {modelProgress.graded_average == null ? "—" : modelProgress.graded_average}</p>
          <p>{modelProgress.recorded_challenges ?? 0} 次实现挑战仅记录完成，不参与均分</p>
          <div className="model-exercise-progress__breakdown">
            <div><h3>按级别</h3><ul>{Object.entries(modelProgress.by_level ?? {}).map(([level, entry]) => <li key={level}>Level {level}：{entry.attempts} 次{entry.graded_average == null ? " · 未判分" : ` · 均分 ${entry.graded_average}`}</li>)}</ul></div>
            <div><h3>按知识点</h3><ul>{Object.entries(modelProgress.by_topic ?? {}).sort((a, b) => b[1].attempts - a[1].attempts).slice(0, 8).map(([topic, entry]) => <li key={topic}>{topic}：{entry.attempts} 次</li>)}</ul></div>
          </div>
        </>}
      </Panel>

      <section className="insights-grid">
        <Panel className="insight-history" eyebrow="PRACTICE HISTORY" title="答题水平">
          {analyticsState === "loading" && <FeedbackState kind="loading" title="正在读取答题历史" description="聚合每道题的首次、最近和最佳得分。" />}
          {analyticsState === "error" && <FeedbackState kind="error" title="答题历史加载失败" description="统计和能力雷达不受影响。" />}
          {analytics && <><p className="insight-summary">已练 {analytics.summary.questions_practiced} 题 · 总作答 {analytics.summary.total_attempts} 次 · 均分 {analytics.summary.overall_avg}</p><ScoreHistoryTable rows={analytics.questions} /></>}
        </Panel>

        <Panel className="insight-radar" eyebrow="CAPABILITY RADAR" title="能力雷达">
          {radarState === "loading" && <FeedbackState kind="loading" title="正在计算能力雷达" description="读取刷题覆盖和模拟面试得分。" />}
          {radarState === "error" && <div role="alert" aria-label="能力雷达"><FeedbackState kind="error" title="雷达数据加载失败" description="答题指标与历史仍然可用。" /></div>}
          {radar && <div className="radar-grid"><RadarInsight title="刷题覆盖" axes={radar.quiz.axes} /><RadarInsight title="模拟面试均分" axes={radar.mock.axes} /></div>}
        </Panel>

        <Panel className="insight-coverage" eyebrow="SOURCE COVERAGE" title="题库覆盖">
          {statsState === "loading" && <p className="empty-hint">正在读取来源覆盖…</p>}
          {stats && <ul className="vendor-list">{Object.entries(stats.by_vendor || {}).map(([vendor, count]) => <li key={vendor}><span>{QUESTION_SOURCE_LABELS[vendor as QuestionSource] ?? vendor}</span><strong>{count} 题</strong></li>)}</ul>}
        </Panel>

        <Panel className="insight-calendar" eyebrow="REVIEW SCHEDULE" title="复习日历（SM-2）"><ReviewCalendar /></Panel>
      </section>
    </div>
  );
}

function RadarInsight({ title, axes }: { title: string; axes: { axis: string; value: number; detail?: string }[] }) {
  return <section className="radar-cell" aria-label={title}><h3>{title}</h3>{axes.length ? <><RadarChart axes={axes} max={100} /><ul className="radar-text-summary">{axes.map((axis) => <li key={axis.axis}><span>{axisLabel(axis.axis)}</span><strong>{Math.round(axis.value)}%</strong>{axis.detail && <small>{axis.detail}</small>}</li>)}</ul></> : <p className="empty-hint">完成训练后生成</p>}</section>;
}
