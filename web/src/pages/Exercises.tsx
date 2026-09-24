import { useEffect, useMemo, useState } from "react";
import { BookOpen, ChevronRight } from "lucide-react";
import {
  exerciseGet, exerciseProgress, exerciseSubmit, exercisesList,
  type ExerciseAttemptResult, type ExerciseItem, type ExerciseProgress,
} from "../api";
import { ExerciseCard } from "../components/exercises/ExerciseCard";
import { ExerciseResult } from "../components/exercises/ExerciseResult";
import { ExerciseWorkbench } from "../components/exercises/ExerciseWorkbench";
import { MathTitle } from "../components/exercises/MathContent";
import { FeedbackState } from "../components/ui/FeedbackState";
import { PageHeader } from "../components/ui/PageHeader";
import type { PageId } from "../navigation";


export function ExercisesPage({ onNavigate, targetExerciseId }: { onNavigate?: (page: PageId) => void; targetExerciseId?: string }) {
  const [items, setItems] = useState<ExerciseItem[]>([]);
  const [active, setActive] = useState<ExerciseItem | null>(null);
  const [progress, setProgress] = useState<ExerciseProgress | null>(null);
  const [result, setResult] = useState<ExerciseAttemptResult | null>(null);
  const [catalogState, setCatalogState] = useState<"loading" | "ready" | "error">("loading");
  const [detailLoading, setDetailLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [level, setLevel] = useState("");
  const [kind, setKind] = useState("");
  const [topic, setTopic] = useState("");

  useEffect(() => {
    let mounted = true;
    exercisesList()
      .then((response) => { if (mounted) { setItems(response.items); setCatalogState("ready"); } })
      .catch(() => { if (mounted) setCatalogState("error"); });
    exerciseProgress().then((value) => { if (mounted) setProgress(value); }).catch(() => undefined);
    return () => { mounted = false; };
  }, []);

  const filtered = useMemo(() => items.filter((item) => (
    (!level || item.level === Number(level))
    && (!kind || item.kind === kind)
    && (!topic || item.topics.some((value) => value.toLocaleLowerCase().includes(topic.toLocaleLowerCase())))
  )), [items, level, kind, topic]);

  async function select(item: ExerciseItem) {
    setDetailLoading(true);
    setError("");
    setResult(null);
    try {
      setActive(await exerciseGet(item.id));
    } catch {
      setError("题目加载失败，请重新选择。目录仍可使用。");
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    const match = items.find((item) => item.id === targetExerciseId);
    if (match && active?.id !== match.id) void select(match);
  }, [items, targetExerciseId, active?.id]);

  async function submit(answers: Record<string, unknown>) {
    if (!active || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await exerciseSubmit(active.id, answers, true);
      setResult(response);
      setProgress(response.progress);
    } catch (cause) {
      setError("作答尚未保存，请检查连接后重试。");
      throw cause;
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="exercise-page">
      <PageHeader eyebrow="LLM PRACTICE" title="LLM 练习" description="从概念判断到完整实现，按知识点练习；代码仅记录，不在服务器运行。" />
      <div className="exercise-overview">
        <span><strong>{items.length}</strong> 道练习</span>
        <span><strong>{progress?.completed_items ?? 0}</strong> 已尝试</span>
        <span><strong>{progress?.total_attempts ?? 0}</strong> 次提交</span>
      </div>
      <div className="exercise-layout">
        <aside className="exercise-catalog" aria-label="练习目录">
          <div className="exercise-catalog__heading">
            <h2>选择练习</h2>
            <span>{filtered.length} 项</span>
          </div>
          <div className="exercise-filters">
            <label>级别
              <select value={level} onChange={(event) => setLevel(event.target.value)}>
                <option value="">全部</option><option value="1">Level 1</option><option value="2">Level 2</option><option value="3">Level 3</option><option value="4">Level 4</option>
              </select>
            </label>
            <label>题型
              <select value={kind} onChange={(event) => setKind(event.target.value)}>
                <option value="">全部</option><option value="single_choice">选择题</option><option value="blank_fill">代码填空</option><option value="implementation_challenge">实现挑战</option>
              </select>
            </label>
            <label className="exercise-filters__topic">知识点
              <input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="如 attention、RAG" />
            </label>
          </div>
          {catalogState === "loading" && <FeedbackState kind="loading" title="正在读取练习" description="加载已发布题目。" />}
          {catalogState === "error" && <FeedbackState kind="error" title="练习目录暂不可用" description="请检查服务连接后刷新页面。" />}
          {catalogState === "ready" && items.length === 0 && <FeedbackState kind="empty" title="暂无已发布练习" description="练习需要完成来源和内容审核后才会出现在这里。" />}
          {catalogState === "ready" && items.length > 0 && filtered.length === 0 && <FeedbackState kind="empty" title="没有匹配的练习" description="换个级别、题型或知识点试试。" />}
          <div className="exercise-catalog__list">
            {filtered.map((item) => (
              <ExerciseCard key={item.id} item={item} selected={active?.id === item.id} onSelect={() => void select(item)} />
            ))}
          </div>
        </aside>
        <main className="exercise-detail" aria-label="练习工作区">
          {error && <p className="inline-message" data-tone="danger" role="alert">{error}</p>}
          {detailLoading && <FeedbackState kind="loading" title="正在打开题目" description="读取题面与练习要求。" />}
          {!detailLoading && !active && (
            <div className="exercise-detail__empty"><BookOpen size={32} aria-hidden="true" /><h2>从目录选择一道练习</h2><p>选择题可直接判分；代码填空和实现挑战可以先提交，再对照参考答案自查。</p></div>
          )}
          {!detailLoading && active && (
            <>
              <header className="exercise-detail__header">
                <div><p>Level {active.level} / {active.topics.slice(0, 3).join(" · ")}</p><MathTitle text={active.title} /></div>
                {active.estimated_minutes && <span>约 {active.estimated_minutes} 分钟</span>}
              </header>
              <p className="exercise-source">来源：{active.source_anchor.path} · 第 {active.source_anchor.line} 行</p>
              <ExerciseWorkbench key={active.id} item={active} onSubmit={submit} busy={submitting} />
              {result && <ExerciseResult result={result} />}
              {active.kind === "implementation_challenge" && onNavigate && (
                <button type="button" className="exercise-lab-link" onClick={() => onNavigate("labs")}>前往实操 Lab 继续打卡 <ChevronRight size={16} aria-hidden="true" /></button>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
