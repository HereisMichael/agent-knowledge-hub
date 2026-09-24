import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Save } from "lucide-react";
import {
  quizGetReference,
  quizNext,
  quizPutReference,
  quizReviewDue,
  quizReviewGrade,
  quizSubmit,
} from "../api";
import { CoachPanel } from "../components/training/CoachPanel";
import { Workbench } from "../components/training/Workbench";
import { FeedbackState } from "../components/ui/FeedbackState";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { StatusBadge } from "../components/ui/StatusBadge";
import { QUESTION_SOURCES, QUESTION_SOURCE_LABELS, type QuestionSource } from "../questions/catalog";

type ScorePoint = { score: number | null; created_at: string };
type CurrentQuestion = {
  question: { id: string; question: string; vendor: string; category: string };
  saved_reference?: string;
  score_history?: ScorePoint[];
};
type DueItem = { card: { question_id: string }; question: { id: string; question: string } };

export function QuizPage() {
  const [source, setSource] = useState<QuestionSource>("general");
  const [category, setCategory] = useState("");
  const [current, setCurrent] = useState<CurrentQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [reference, setReference] = useState("");
  const [saveRef, setSaveRef] = useState(true);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [dueItems, setDueItems] = useState<DueItem[]>([]);
  const [pending, setPending] = useState<"next" | "submit" | "save" | "reference" | "review" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refreshDue = useCallback(async () => {
    try {
      const data = await quizReviewDue(5);
      setDueItems(data.items || []);
    } catch {
      setMessage("复习队列暂不可用");
    }
  }, []);

  useEffect(() => { void refreshDue(); }, [refreshDue, result]);

  async function gradeReview(questionId: string, quality: number) {
    setPending("review");
    setError("");
    try {
      await quizReviewGrade(questionId, quality);
      await refreshDue();
      setMessage("复习记录已更新");
    } catch {
      setError("复习记录保存失败，请重试。");
    } finally {
      setPending(null);
    }
  }

  async function loadNext() {
    if (pending) return;
    setPending("next");
    setError("");
    setMessage("");
    try {
      const data = await quizNext(source, category || undefined);
      setCurrent(data);
      setAnswer("");
      setReference(data.saved_reference || "");
      setResult(null);
    } catch {
      setError("题目加载失败，请检查连接或更换筛选条件后重试。");
    } finally {
      setPending(null);
    }
  }

  async function loadReferenceOnly() {
    if (!current || pending) return;
    setPending("reference");
    setError("");
    try {
      const data = await quizGetReference(current.question.id);
      if (data.reference?.reference_text) setReference(data.reference.reference_text);
      setMessage(data.reference?.reference_text ? "已重新载入参考答案" : "当前题目还没有已存参考答案");
    } catch {
      setError("参考答案载入失败，请稍后重试。");
    } finally {
      setPending(null);
    }
  }

  async function saveReferenceOnly() {
    if (!current || !reference.trim() || pending) return;
    setPending("save");
    setError("");
    try {
      await quizPutReference(current.question.id, reference);
      setMessage("参考答案已保存");
    } catch {
      setError("参考答案保存失败，内容已保留，请重试。");
    } finally {
      setPending(null);
    }
  }

  async function submit() {
    if (!current || !answer.trim() || pending) return;
    setPending("submit");
    setError("");
    try {
      const response = await quizSubmit({
        question_id: current.question.id,
        answer_text: answer,
        reference_answer: reference,
        save_reference: saveRef,
        use_ai: true,
      });
      setResult(response);
      setMessage("评分已完成");
      if (response.score_history) {
        setCurrent({ ...current, score_history: response.score_history as ScorePoint[] });
      }
    } catch {
      setError("评分请求失败，你的本次作答已保留，可以直接重试。");
    } finally {
      setPending(null);
    }
  }

  const primary = (
    <div className="training-stack">
      <Panel eyebrow="QUESTION ROUTER" title="选择训练范围">
        <div className="training-filter-row">
          <div className="field">
            <label htmlFor="quiz-source">题目来源</label>
            <select id="quiz-source" value={source} onChange={(event) => setSource(event.target.value as QuestionSource)}>
              {QUESTION_SOURCES.map((item) => <option key={item} value={item}>{QUESTION_SOURCE_LABELS[item]}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="quiz-cat">分类</label>
            <select id="quiz-cat" value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="">全部分类</option>
              <option value="architecture">架构</option>
              <option value="product">产品</option>
              <option value="behavior">行为</option>
              <option value="solution">方案</option>
              <option value="agent">Agent</option>
              <option value="ai_infra">AI Infra</option>
            </select>
          </div>
        </div>
        <button type="button" className="btn btn-primary" onClick={loadNext} disabled={pending !== null}>
          {pending === "next" ? "正在取题…" : "下一题"} <ArrowRight size={16} aria-hidden="true" />
        </button>
      </Panel>

      {error && <div className="inline-message" data-tone="danger" role="alert">{error}</div>}
      {message && <div className="inline-message" role="status" aria-live="polite">{message}</div>}

      {!current ? (
        <FeedbackState kind="empty" title="等待题目" description="选择来源与分类后获取题目；推荐从通用 / AI Infra 开始。" />
      ) : (
        <Panel
          eyebrow="ACTIVE QUESTION"
          title="本次作答"
          actions={<div className="quiz-meta"><StatusBadge tone="info">{QUESTION_SOURCE_LABELS[current.question.vendor as QuestionSource] ?? current.question.vendor}</StatusBadge><StatusBadge tone="neutral">{current.question.category}</StatusBadge></div>}
        >
          <p className="quiz-question">{current.question.question}</p>
          <div className="field">
            <label htmlFor="quiz-answer">本次作答</label>
            <textarea id="quiz-answer" rows={8} placeholder="先给结论，再说明原理、权衡和适用边界…" value={answer} onChange={(event) => setAnswer(event.target.value)} />
          </div>
          <button type="button" className="btn btn-primary" onClick={submit} disabled={pending !== null || !answer.trim()}>
            {pending === "submit" ? "评分中…" : "提交并对比评分"}
          </button>
        </Panel>
      )}
    </div>
  );

  const aside = (
    <div className="training-stack">
      <CoachPanel title="参考答案" status={current ? <StatusBadge tone={reference ? "success" : "neutral"}>{reference ? "已填写" : "未填写"}</StatusBadge> : undefined}>
        {!current ? <p className="empty-hint">获取题目后可编辑或载入参考答案</p> : (
          <>
            <div className="field">
              <label htmlFor="quiz-reference">我的参考答案</label>
              <textarea id="quiz-reference" rows={7} placeholder="写下你认可的完整答案…" value={reference} onChange={(event) => setReference(event.target.value)} />
            </div>
            <label className="field-checkbox"><input type="checkbox" checked={saveRef} onChange={(event) => setSaveRef(event.target.checked)} />提交时保存参考答案</label>
            <div className="quiz-action-row">
              <button type="button" className="btn btn-quiet" onClick={saveReferenceOnly} disabled={pending !== null || !reference.trim()}><Save size={15} aria-hidden="true" />仅保存参考答案</button>
              <button type="button" className="btn btn-quiet" onClick={loadReferenceOnly} disabled={pending !== null}>重新加载</button>
            </div>
            {current.score_history?.length ? <div className="score-mini-chart"><span className="lab-meta">历史得分：</span>{current.score_history.map((point, index) => <span key={`${point.created_at}-${index}`} className="score-chip">{point.score ?? "-"}</span>)}</div> : null}
          </>
        )}
      </CoachPanel>

      {result && (
        <CoachPanel title="评分反馈" status={<StatusBadge tone="success">已完成</StatusBadge>}>
          <div className="quiz-result-score">{String(result.ai_score ?? "-")} 分</div>
          <p className="prose">{String(result.feedback ?? "")}</p>
          {(result.gaps_vs_reference as string[] | undefined)?.length ? <><h4>与参考答案的差距</h4><ul className="prose">{(result.gaps_vs_reference as string[]).map((gap) => <li key={gap}>{gap}</li>)}</ul></> : null}
          {result.improvement_tip ? <p className="mock-report-rewrite">{String(result.improvement_tip)}</p> : null}
          {(result.explanation as { key_points?: string[] } | undefined)?.key_points?.length ? <><h4>题库参考要点</h4><ul className="prose">{(result.explanation as { key_points: string[] }).key_points.map((point) => <li key={point}>{point}</li>)}</ul></> : null}
        </CoachPanel>
      )}

      <CoachPanel title="间隔复习" status={<StatusBadge tone={dueItems.length ? "warning" : "neutral"}>{dueItems.length} 道</StatusBadge>}>
        {dueItems.length === 0 ? <p className="empty-hint">当前没有到期复习题</p> : dueItems.map((item) => (
          <article key={item.question.id} className="review-item">
            <p>{item.question.question}</p>
            <div className="review-quality-grid">
              {[[0, "忘了"], [2, "难"], [3, "一般"], [4, "好"], [5, "熟"]].map(([quality, label]) => (
                <button key={quality} type="button" className="btn btn-quiet" disabled={pending !== null} onClick={() => gradeReview(item.question.id, Number(quality))}>{label}</button>
              ))}
            </div>
          </article>
        ))}
      </CoachPanel>
    </div>
  );

  return (
    <div>
      <PageHeader eyebrow="INTERVIEW DRILL" title="题库训练" description="完成一次结构化作答，再用参考答案和评分反馈持续校准。" />
      <Workbench primary={primary} aside={aside} asideLabel="训练教练" />
    </div>
  );
}
