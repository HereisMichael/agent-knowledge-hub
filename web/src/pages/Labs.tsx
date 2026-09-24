import { useEffect, useState } from "react";
import { CheckCircle2, Clock3 } from "lucide-react";
import { labComplete, labsList, labsRecommend } from "../api";
import { CoachPanel } from "../components/training/CoachPanel";
import { Workbench } from "../components/training/Workbench";
import { FeedbackState } from "../components/ui/FeedbackState";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { StatusBadge } from "../components/ui/StatusBadge";

type Lab = { id: string; title: string; effort_hours: number; weakness_tags: string[]; steps: string[]; source_exercise_id?: string };
type LoadState = "loading" | "ready" | "error";

export function LabsPage({ onOpenExercise }: { onOpenExercise?: (id: string) => void }) {
  const [labs, setLabs] = useState<Lab[]>([]);
  const [recommendations, setRecommendations] = useState<Lab[]>([]);
  const [catalogState, setCatalogState] = useState<LoadState>("loading");
  const [recommendationState, setRecommendationState] = useState<LoadState>("loading");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [pendingId, setPendingId] = useState("");
  const [message, setMessage] = useState("");
  const [completionError, setCompletionError] = useState("");

  useEffect(() => {
    let active = true;
    labsList().then((data) => { if (active) { setLabs(data.labs || []); setCatalogState("ready"); } }).catch(() => active && setCatalogState("error"));
    labsRecommend().then((data) => { if (active) { setRecommendations(data.labs || []); setRecommendationState("ready"); } }).catch(() => active && setRecommendationState("error"));
    return () => { active = false; };
  }, []);

  async function complete(lab: Lab) {
    if (pendingId) return;
    setPendingId(lab.id);
    setMessage("");
    setCompletionError("");
    try {
      await labComplete(lab.id, notes[lab.id] ?? "");
      setNotes((current) => ({ ...current, [lab.id]: "" }));
      setMessage("完成记录已保存");
    } catch {
      setCompletionError(`${lab.title} 的完成记录保存失败，笔记已保留。`);
    } finally {
      setPendingId("");
    }
  }

  const catalog = (
    <div className="training-stack">
      {completionError && <div className="inline-message" data-tone="danger" role="alert">{completionError}</div>}
      {message && <div className="inline-message" role="status" aria-live="polite">{message}</div>}
      <Panel eyebrow="LAB CATALOG" title="全部 Lab" actions={catalogState === "ready" ? <StatusBadge tone="info">{labs.length} 项</StatusBadge> : undefined}>
        {catalogState === "loading" && <FeedbackState kind="loading" title="正在加载 Lab 目录" description="读取实操步骤与预计用时。" />}
        {catalogState === "error" && <FeedbackState kind="error" title="Lab 目录加载失败" description="推荐内容仍可独立使用，请稍后刷新页面重试。" />}
        {catalogState === "ready" && labs.length === 0 && <FeedbackState kind="empty" title="暂无 Lab" description="目录当前没有可用的实操项目。" />}
        {catalogState === "ready" && <div className="lab-catalog">{labs.map((lab) => (
          <article key={lab.id} className="training-lab-card">
            <header><div><p className="ui-eyebrow">PRACTICE MODULE</p><h3>{lab.title}</h3></div><span><Clock3 size={14} aria-hidden="true" />约 {lab.effort_hours} 小时</span></header>
            <ol>{lab.steps?.map((step) => <li key={step}>{step}</li>)}</ol>
            {lab.source_exercise_id && <a href={`#exercise=${encodeURIComponent(lab.source_exercise_id)}`} onClick={() => onOpenExercise?.(lab.source_exercise_id!)}>查看来源练习</a>}
            <div className="field"><label htmlFor={`lab-notes-${lab.id}`}>{lab.title} 完成笔记</label><textarea id={`lab-notes-${lab.id}`} rows={3} placeholder="记录结果、误差、性能数据或产物链接" value={notes[lab.id] ?? ""} onChange={(event) => setNotes((current) => ({ ...current, [lab.id]: event.target.value }))} /></div>
            <button type="button" className="btn btn-primary" aria-label={`完成 ${lab.title}`} onClick={() => complete(lab)} disabled={Boolean(pendingId)}><CheckCircle2 size={16} aria-hidden="true" />{pendingId === lab.id ? "保存中…" : "完成打卡"}</button>
          </article>
        ))}</div>}
      </Panel>
    </div>
  );

  const recommended = (
    <CoachPanel title="推荐练习" status={recommendationState === "ready" ? <StatusBadge tone={recommendations.length ? "warning" : "neutral"}>{recommendations.length} 项</StatusBadge> : undefined}>
      {recommendationState === "loading" && <FeedbackState kind="loading" title="正在生成推荐" description="根据薄弱标签匹配最合适的实操项目。" />}
      {recommendationState === "error" && <FeedbackState kind="error" title="推荐加载失败" description="全部 Lab 目录仍可独立使用。" />}
      {recommendationState === "ready" && recommendations.length === 0 && <FeedbackState kind="empty" title="等待能力信号" description="完成刷题或模拟面试后会出现个性化推荐。" />}
      {recommendationState === "ready" && <div className="recommended-labs">{recommendations.map((lab) => (
        <article key={lab.id} className="recommended-lab"><h3>{lab.title}</h3><p>约 {lab.effort_hours} 小时</p><div>{lab.weakness_tags?.map((tag) => <span key={tag}>{tag}</span>)}</div>{lab.source_exercise_id && <a href={`#exercise=${encodeURIComponent(lab.source_exercise_id)}`} onClick={() => onOpenExercise?.(lab.source_exercise_id!)}>查看来源练习</a>}</article>
      ))}</div>}
    </CoachPanel>
  );

  return <div><PageHeader eyebrow="HANDS-ON PRACTICE" title="实操 Lab" description="把知识点变成可验证的实现、数据和复盘记录。" /><Workbench primary={catalog} aside={recommended} asideLabel="Lab 推荐" /></div>;
}
