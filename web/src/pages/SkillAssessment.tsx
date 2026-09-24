import { useEffect, useMemo, useState } from "react";
import { gradeAssessmentAnswer } from "../api";
import { RadarChart } from "../components/RadarChart";
import { CoachPanel } from "../components/training/CoachPanel";
import { Workbench } from "../components/training/Workbench";
import { PageHeader } from "../components/ui/PageHeader";
import { SignalLine } from "../components/ui/SignalLine";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { MAAS_DIMENSIONS, getDimension, type MaasDimension } from "../assessment/dimensions";
import { OBJECTIVE_QUESTIONS, type ObjectiveQuestion, questionsByDim } from "../assessment/objectiveBank";
import { loadOpenQuestions, type OpenQuestion } from "../assessment/openBank";
import {
  buildOpenGradingRequest,
  computeDimensionScores,
  gradeObjective,
  type UserAnswer,
} from "../assessment/grade";
import {
  deleteAssessment,
  dimensionDeltas,
  latestTwo,
  listAssessments,
  overallTrend,
  saveAssessment,
  type AssessmentRecord,
  type RatingsInput,
} from "../assessment/storage";

type View = "overview" | "select" | "assess" | "review";

const OBJECTIVE_INDEX = new Map<string, ObjectiveQuestion>(
  OBJECTIVE_QUESTIONS.map((q) => [q.id, q]),
);

function testedDimIds(record: AssessmentRecord): string[] {
  return record.dimIds ?? MAAS_DIMENSIONS.map((d) => d.id);
}

function questionCountForDim(dimId: string, openQuestions: OpenQuestion[]) {
  return {
    objective: questionsByDim(dimId).length,
    open: openQuestionsByDim(openQuestions, dimId).length,
  };
}

export function SkillAssessmentPage() {
  const [view, setView] = useState<View>("overview");
  const [records, setRecords] = useState<AssessmentRecord[]>([]);
  const [openQuestions, setOpenQuestions] = useState<OpenQuestion[]>([]);
  const [openLoading, setOpenLoading] = useState(false);
  const [reviewedRecord, setReviewedRecord] = useState<AssessmentRecord | null>(null);
  const [selectedDimIds, setSelectedDimIds] = useState<string[]>([]);

  function refresh() {
    setRecords(listAssessments());
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if ((view === "select" || view === "assess") && openQuestions.length === 0) {
      setOpenLoading(true);
      loadOpenQuestions()
        .then(setOpenQuestions)
        .finally(() => setOpenLoading(false));
    }
  }, [view, openQuestions.length]);

  function handleSubmitted(record: AssessmentRecord) {
    refresh();
    setReviewedRecord(record);
    setView("review");
  }

  if (view === "select") {
    return (
      <AssessmentShell view={view} selectedDimIds={selectedDimIds}>
        <SelectDimensionsView
          openQuestions={openQuestions}
          openLoading={openLoading}
          selectedDimIds={selectedDimIds}
          onChange={setSelectedDimIds}
          onStart={() => setView("assess")}
          onCancel={() => setView("overview")}
        />
      </AssessmentShell>
    );
  }

  if (view === "assess" && selectedDimIds.length > 0) {
    return (
      <AssessmentShell view={view} selectedDimIds={selectedDimIds}>
        <AssessView
          selectedDimIds={selectedDimIds}
          openQuestions={openQuestions}
          openLoading={openLoading}
          onSubmitted={handleSubmitted}
          onCancel={() => setView("select")}
        />
      </AssessmentShell>
    );
  }

  if (view === "review" && reviewedRecord) {
    return (
      <AssessmentShell view={view} selectedDimIds={testedDimIds(reviewedRecord)}>
        <ReviewView
          record={reviewedRecord}
          onBack={() => {
            setReviewedRecord(null);
            setView("overview");
          }}
        />
      </AssessmentShell>
    );
  }

  return (
    <AssessmentShell view={view} selectedDimIds={selectedDimIds}>
      <OverviewView
        records={records}
        onNew={() => {
          setSelectedDimIds([]);
          setView("select");
        }}
        onReview={(r) => {
          setReviewedRecord(r);
          setView("review");
        }}
        onDelete={(id) => {
          deleteAssessment(id);
          refresh();
        }}
      />
    </AssessmentShell>
  );
}

const ASSESSMENT_PHASES: { id: View; label: string }[] = [
  { id: "overview", label: "准备" },
  { id: "select", label: "选择范围" },
  { id: "assess", label: "作答中" },
  { id: "review", label: "结果" },
];

function AssessmentShell({ view, selectedDimIds, children }: { view: View; selectedDimIds: string[]; children: React.ReactNode }) {
  const activeIndex = ASSESSMENT_PHASES.findIndex((phase) => phase.id === view);
  const selectedDimensions = selectedDimIds.map((id) => getDimension(id)).filter((dim): dim is MaasDimension => Boolean(dim));
  const aside = (
    <div className="training-stack">
      <CoachPanel title="测评进度" status={<StatusBadge tone={view === "review" ? "success" : "info"}>{activeIndex + 1}/4</StatusBadge>}>
        <SignalLine steps={ASSESSMENT_PHASES.map((phase, index) => ({ id: phase.id, label: phase.label, status: index < activeIndex ? "complete" : index === activeIndex ? "current" : "pending" }))} />
      </CoachPanel>
      <CoachPanel title="测评范围">
        {selectedDimensions.length ? <ul className="assessment-context-list">{selectedDimensions.map((dimension) => <li key={dimension.id}><strong>{dimension.label}</strong><span>{dimension.summary}</span></li>)}</ul> : <p className="empty-hint">下一步选择一个或多个能力维度。</p>}
      </CoachPanel>
    </div>
  );
  return (
    <div className="assessment-page">
      <PageHeader eyebrow="CAPABILITY ASSESSMENT" title="MaaS 技能测评" description="客观题与开放题共同形成能力基线，原有评分和本地历史格式保持不变。" />
      <Workbench primary={<div className="assessment-workspace">{children}</div>} aside={aside} asideLabel="测评上下文" />
    </div>
  );
}

function OverviewView({
  records,
  onNew,
  onReview,
  onDelete,
}: {
  records: AssessmentRecord[];
  onNew: () => void;
  onReview: (r: AssessmentRecord) => void;
  onDelete: (id: string) => void;
}) {
  const { latest, previous } = useMemo(() => latestTwo(), [records]);
  const deltas = useMemo(
    () => (latest ? dimensionDeltas(latest, previous) : {}),
    [latest, previous],
  );
  const trend = useMemo(() => overallTrend(), [records]);

  if (!latest) {
    return (
      <div>
        <div className="toolbar">
          <h3 className="panel-header" style={{ margin: 0 }}>
            MaaS 技能测评
          </h3>
        </div>
        <div className="panel empty-state">
          <p className="empty-hint">
            从 MaaS 解决方案专家视角，按 8 个能力维度测评。可单选一个模块快速练习，也可多选组合。
            包含选择题、多选题、判断题与开放/架构设计题（开放题可语音输入，由大模型判分），生成能力雷达并持续追踪进步。
          </p>
          <button type="button" className="btn btn-primary" onClick={onNew}>
            开始首次测评
          </button>
        </div>
      </div>
    );
  }

  const overallDelta = previous ? latest.overall - previous.overall : null;
  const dims = testedDimIds(latest);
  const radarAxes = dims.map((id) => ({
    axis: getDimension(id)?.label ?? id,
    value: latest.scores[id] ?? 0,
  }));

  return (
    <div>
      <div className="toolbar">
        <h3 className="panel-header" style={{ margin: 0 }}>
          能力总览
        </h3>
        <button type="button" className="btn btn-primary" onClick={onNew}>
          开始新测评
        </button>
      </div>

      <div className="stat-grid">
        <div className="stat">
          <div className="stat-value">{latest.overall}</div>
          <div className="stat-label">综合得分</div>
        </div>
        <div className="stat">
          <div className="stat-value">
            <DeltaText delta={overallDelta} />
          </div>
          <div className="stat-label">较上次</div>
        </div>
        <div className="stat">
          <div className="stat-value">{records.length}</div>
          <div className="stat-label">测评次数</div>
        </div>
        <div className="stat">
          <div className="stat-value">{dims.length}</div>
          <div className="stat-label">测评维度</div>
        </div>
      </div>

      <div className="panel radar-panel">
        <h3 className="panel-header">能力雷达（{dims.length} 维）</h3>
        <div className="assess-radar-wrap">
          <RadarChart axes={radarAxes} max={100} size={280} />
          <ul className="assess-dim-list">
            {dims.map((id) => {
              const d = getDimension(id);
              if (!d) return null;
              return (
              <li key={d.id} className="assess-dim-row">
                <span className="assess-dim-name">{d.label}</span>
                <span className="assess-dim-score">{latest.scores[d.id] ?? 0}</span>
                <span className="assess-dim-delta">
                  <DeltaText delta={deltas[d.id] ?? null} />
                </span>
              </li>
              );
            })}
          </ul>
        </div>
      </div>

      <div className="panel">
        <h3 className="panel-header">测评历史（{trend.length}）</h3>
        <ul className="assess-history">
          {records.map((r) => (
            <li key={r.id} className="assess-history-row">
              <span className="assess-history-date">
                {new Date(r.createdAt).toLocaleString("zh-CN")}
              </span>
              <span className="assess-history-score">{r.overall} 分</span>
              <span className="assess-history-delta">
                <AnswerCount answers={r.answers} dimIds={r.dimIds} />
              </span>
              <button
                type="button"
                className="filter-btn"
                onClick={() => onReview(r)}
              >
                查看详情
              </button>
              <button
                type="button"
                className="btn btn-ghost assess-history-del"
                onClick={() => onDelete(r.id)}
              >
                删除
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function AnswerCount({ answers, dimIds }: { answers: UserAnswer[]; dimIds?: string[] }) {
  const open = answers.filter((a) => a.grading).length;
  const dims = dimIds?.length ?? MAAS_DIMENSIONS.length;
  return <span>{dims} 维 · {answers.length} 题 · 大模型判 {open} 题</span>;
}

function DeltaText({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="delta-neutral">首次</span>;
  if (delta > 0) return <span className="delta-up">+{delta}</span>;
  if (delta < 0) return <span className="delta-down">{delta}</span>;
  return <span className="delta-neutral">0</span>;
}

function SelectDimensionsView({
  openQuestions,
  openLoading,
  selectedDimIds,
  onChange,
  onStart,
  onCancel,
}: {
  openQuestions: OpenQuestion[];
  openLoading: boolean;
  selectedDimIds: string[];
  onChange: (ids: string[]) => void;
  onStart: () => void;
  onCancel: () => void;
}) {
  const selectedSet = useMemo(() => new Set(selectedDimIds), [selectedDimIds]);

  const totalQuestions = useMemo(
    () =>
      selectedDimIds.reduce((n, id) => {
        const c = questionCountForDim(id, openQuestions);
        return n + c.objective + c.open;
      }, 0),
    [selectedDimIds, openQuestions],
  );

  function toggle(id: string) {
    onChange(
      selectedSet.has(id) ? selectedDimIds.filter((d) => d !== id) : [...selectedDimIds, id],
    );
  }

  return (
    <div>
      <div className="toolbar">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          ← 返回
        </button>
        <h3 className="panel-header" style={{ margin: 0 }}>
          选择测评维度
        </h3>
        <button
          type="button"
          className="btn btn-primary"
          style={{ marginLeft: "auto" }}
          disabled={selectedDimIds.length === 0}
          onClick={onStart}
        >
          开始作答
        </button>
      </div>

      <div className="panel">
        <p className="empty-hint" style={{ marginTop: 0 }}>
          可单选一个模块快速练习，也可多选组合。仅加载所选维度的题目，开放题仍由大模型判分。
        </p>
        <div className="assess-dim-pick-actions">
          <button
            type="button"
            className="filter-btn"
            onClick={() => onChange(MAAS_DIMENSIONS.map((d) => d.id))}
          >
            全选
          </button>
          <button type="button" className="filter-btn" onClick={() => onChange([])}>
            清空
          </button>
          <span className="empty-hint">
            已选 {selectedDimIds.length} 维
            {openLoading ? " · 开放题加载中…" : ` · 共 ${totalQuestions} 题`}
          </span>
        </div>

        <div className="assess-dim-pick-grid">
          {MAAS_DIMENSIONS.map((dim) => {
            const counts = questionCountForDim(dim.id, openQuestions);
            const selected = selectedSet.has(dim.id);
            return (
              <button
                key={dim.id}
                type="button"
                className={`assess-dim-pick${selected ? " selected" : ""}`}
                onClick={() => toggle(dim.id)}
                aria-pressed={selected}
              >
                <div className="assess-dim-pick-header">
                  <span className={`assess-dim-pick-check${selected ? " on" : ""}`} aria-hidden>
                    {selected ? "✓" : ""}
                  </span>
                  <strong>{dim.label}</strong>
                </div>
                <span className="empty-hint">{dim.summary}</span>
                <span className="assess-dim-pick-count">
                  {counts.objective} 客观
                  {openLoading ? " · 开放…" : ` · ${counts.open} 开放`}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function AssessView({
  selectedDimIds,
  openQuestions,
  openLoading,
  onSubmitted,
  onCancel,
}: {
  selectedDimIds: string[];
  openQuestions: OpenQuestion[];
  openLoading: boolean;
  onSubmitted: (r: AssessmentRecord) => void;
  onCancel: () => void;
}) {
  const [answers, setAnswers] = useState<UserAnswer[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const setAnswer = (a: UserAnswer) => {
    setAnswers((prev) => {
      const i = prev.findIndex((p) => p.questionId === a.questionId);
      if (i === -1) return [...prev, a];
      const next = [...prev];
      next[i] = a;
      return next;
    });
  };

  const activeDims = useMemo(
    () => MAAS_DIMENSIONS.filter((d) => selectedDimIds.includes(d.id)),
    [selectedDimIds],
  );

  const dimLabel =
    activeDims.length === 1
      ? activeDims[0].label
      : activeDims.length === MAAS_DIMENSIONS.length
        ? "全部 8 维"
        : `${activeDims.length} 个维度`;

  const totalQuestions = activeDims.reduce(
    (n, d) => n + questionsByDim(d.id).length + openQuestionsByDim(openQuestions, d.id).length,
    0,
  );
  const answered = answers.filter((a) => isAnswered(a)).length;

  async function handleSubmit() {
    if (!confirm(`已答 ${answered}/${totalQuestions} 题。未作答的客观题按错计，开放题按 0 分计。提交？`))
      return;
    setSubmitting(true);
    try {
      // 触发所有未判分的开放题判分
      const graded = await Promise.all(
        answers.map(async (a) => {
          if (a.kind !== "open" && a.kind !== "architecture") return a;
          if (a.grading) return a;
          if (typeof a.value !== "string" || a.value.trim().length < 5) {
            return { ...a, grading: { aiScore: 0, matched: [], missing: [], feedback: "未作答", demo: true } };
          }
          const q = openQuestions.find((oq) => oq.id === a.questionId);
          if (!q) return a;
          try {
            const res = await gradeAssessmentAnswer(buildOpenGradingRequest(q, a.value));
            return {
              ...a,
              grading: {
                aiScore: res.ai_score,
                matched: res.matched_points,
                missing: res.missing_points,
                feedback: res.feedback,
                demo: res.demo,
              },
            };
          } catch (e) {
            return {
              ...a,
              grading: { aiScore: 0, matched: [], missing: [], feedback: `判分失败: ${String(e)}`, demo: true },
            };
          }
        }),
      );

      const dimResults = computeDimensionScores(graded, OBJECTIVE_INDEX);
      const scores: Record<string, number> = {};
      for (const r of dimResults) {
        if (!selectedDimIds.includes(r.dimId)) continue;
        scores[r.dimId] = r.score;
      }
      const overall =
        selectedDimIds.length === 0
          ? 0
          : Math.round(
              selectedDimIds.reduce((s, id) => s + (scores[id] ?? 0), 0) / selectedDimIds.length,
            );

      const ratings: RatingsInput = {};
      for (const d of activeDims) ratings[d.id] = [0];

      const record = saveAssessment({
        ratings,
        scores,
        overall,
        answers: graded,
        dimIds: selectedDimIds,
      });
      onSubmitted(record);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="toolbar">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          ← 返回
        </button>
        <h3 className="panel-header" style={{ margin: 0 }}>
          新建测评 · {dimLabel} · {answered}/{totalQuestions} 题已答
        </h3>
        <button
          type="button"
          className="btn btn-primary"
          style={{ marginLeft: "auto" }}
          disabled={submitting}
          onClick={handleSubmit}
        >
          {submitting ? "大模型判分中…" : "提交测评"}
        </button>
      </div>

      {activeDims.map((dim) => (
        <DimensionBlock
          key={dim.id}
          dim={dim}
          answers={answers}
          openQuestions={openQuestionsByDim(openQuestions, dim.id)}
          openLoading={openLoading}
          onAnswer={setAnswer}
        />
      ))}
    </div>
  );
}

function openQuestionsByDim(all: OpenQuestion[], dimId: string) {
  return all.filter((q) => q.dimId === dimId);
}

function isAnswered(a: UserAnswer): boolean {
  if (a.kind === "open" || a.kind === "architecture") {
    return typeof a.value === "string" && a.value.trim().length > 0;
  }
  if (a.kind === "multi") return Array.isArray(a.value) && (a.value as number[]).length > 0;
  return typeof a.value === "number";
}

function DimensionBlock({
  dim,
  answers,
  openQuestions,
  openLoading,
  onAnswer,
}: {
  dim: MaasDimension;
  answers: UserAnswer[];
  openQuestions: OpenQuestion[];
  openLoading: boolean;
  onAnswer: (a: UserAnswer) => void;
}) {
  const objList = questionsByDim(dim.id);

  return (
    <div className="panel">
      <div className="assess-dim-header">
        <div>
          <h3 className="panel-header" style={{ margin: 0 }}>
            {dim.label}
          </h3>
          <p className="empty-hint">{dim.summary}</p>
        </div>
        <span className="empty-hint">
          {objList.length} 客观 · {openQuestions.length} 开放
        </span>
      </div>

      {objList.map((q) => (
        <ObjectiveRow key={q.id} q={q} answer={answers.find((a) => a.questionId === q.id)} onAnswer={onAnswer} />
      ))}

      {openLoading && (
        <p className="empty-hint" style={{ marginTop: "1rem" }}>
          正在加载开放题…
        </p>
      )}
      {openQuestions.map((q) => (
        <OpenRow key={q.id} q={q} answer={answers.find((a) => a.questionId === q.id)} onAnswer={onAnswer} />
      ))}
      {!openLoading && openQuestions.length === 0 && (
        <p className="empty-hint" style={{ marginTop: "0.75rem" }}>
          本维度暂无开放题（题库无对应题），仅作客观题作答。
        </p>
      )}
    </div>
  );
}

function ObjectiveRow({
  q,
  answer,
  onAnswer,
}: {
  q: ObjectiveQuestion;
  answer?: UserAnswer;
  onAnswer: (a: UserAnswer) => void;
}) {
  const typeLabel: Record<string, string> = { single: "单选", multi: "多选", boolean: "判断" };

  function pick(idx: number) {
    if (q.type === "multi") {
      const cur = (Array.isArray(answer?.value) ? (answer!.value as number[]) : []) as number[];
      const next = cur.includes(idx) ? cur.filter((v) => v !== idx) : [...cur, idx];
      onAnswer({ questionId: q.id, dimId: q.dimId, kind: q.type, value: next });
    } else {
      onAnswer({ questionId: q.id, dimId: q.dimId, kind: q.type, value: idx });
    }
  }

  return (
    <div className="assess-q">
      <div className="assess-q-stem">
        <span className="assess-q-tag">{typeLabel[q.type]}</span>
        <span>{q.stem}</span>
      </div>
      <div className="assess-opts">
        {q.type === "boolean"
          ? // 判断题：数据约定 1=正确 / 0=错误
            [
              { label: "正确", val: 1 },
              { label: "错误", val: 0 },
            ].map(({ label, val }) => (
              <button
                key={val}
                type="button"
                className={`assess-opt${answer?.value === val ? " selected" : ""}`}
                onClick={() => pick(val)}
              >
                <span className="assess-opt-mark">{val === 1 ? "✓" : "✗"}</span>
                <span>{label}</span>
              </button>
            ))
          : q.options?.map((opt, idx) => {
              const selected =
                q.type === "multi"
                  ? Array.isArray(answer?.value) && (answer!.value as number[]).includes(idx)
                  : answer?.value === idx;
              return (
                <button
                  key={idx}
                  type="button"
                  className={`assess-opt${selected ? " selected" : ""}`}
                  onClick={() => pick(idx)}
                >
                  <span className="assess-opt-mark">{String.fromCharCode(65 + idx)}</span>
                  <span>{opt}</span>
                </button>
              );
            })}
      </div>
      <SourceLine source={q.source} />
    </div>
  );
}

function SourceLine({ source }: { source: { ref: string; where: string; evidence?: string } }) {
  return (
    <p className="assess-source">
      <span className="assess-source-tag">来源</span>
      <code>{source.ref}</code>
      <span className="assess-source-where">· {source.where}</span>
    </p>
  );
}

function OpenRow({
  q,
  answer,
  onAnswer,
}: {
  q: OpenQuestion;
  answer?: UserAnswer;
  onAnswer: (a: UserAnswer) => void;
}) {
  const speech = useSpeechRecognition();
  const value = typeof answer?.value === "string" ? (answer.value as string) : "";
  const grading = answer?.grading;

  function updateText(t: string) {
    onAnswer({
      questionId: q.id,
      dimId: q.dimId,
      kind: q.type,
      value: t,
      ...(grading ? { grading } : {}),
    });
  }

  function appendVoice() {
    if (!speech.transcript) return;
    const next = (value + " " + speech.transcript).trim();
    updateText(next);
    speech.reset();
  }

  return (
    <div className="assess-q open">
      <div className="assess-q-stem">
        <span className="assess-q-tag">{q.type === "architecture" ? "架构设计" : "开放论证"}</span>
        <span>{q.stem}</span>
      </div>
      <textarea
        aria-label={q.stem}
        rows={5}
        value={value}
        onChange={(e) => updateText(e.target.value)}
        placeholder="尽可能列出关键要点、权衡依据与落地步骤。也可使用语音输入转写。"
      />
      <div className="assess-voice">
        {speech.supported ? (
          speech.isListening ? (
            <>
              <button type="button" className="btn btn-ghost" onClick={speech.stop}>
                停止语音
              </button>
              <span className="assess-voice-tip">正在听写…</span>
              {speech.transcript && (
                <button type="button" className="filter-btn" onClick={appendVoice}>
                  加入正文
                </button>
              )}
            </>
          ) : (
            <button type="button" className="btn btn-ghost" onClick={speech.start}>
              🎤 语音输入
            </button>
          )
        ) : (
          <span className="empty-hint">当前浏览器不支持语音识别</span>
        )}
        {speech.error && <span className="assess-voice-err">{speech.error}</span>}
      </div>
      <details className="assess-kp">
        <summary>查看评分要点（{q.keyPoints.length}）</summary>
        <ul>
          {q.keyPoints.map((k, i) => (
            <li key={i}>{k}</li>
          ))}
        </ul>
      </details>
      <SourceLine source={q.source} />
    </div>
  );
}

function ReviewView({ record, onBack }: { record: AssessmentRecord; onBack: () => void }) {
  const dims = testedDimIds(record);
  const dimLabels = dims.map((id) => getDimension(id)?.label ?? id).join("、");

  return (
    <div>
      <div className="toolbar">
        <button type="button" className="btn btn-ghost" onClick={onBack}>
          ← 返回
        </button>
        <h3 className="panel-header" style={{ margin: 0 }}>
          测评详情 · {new Date(record.createdAt).toLocaleString("zh-CN")} · {record.overall} 分
        </h3>
      </div>
      <p className="empty-hint assess-review-scope">
        测评范围：{dimLabels}（{dims.length} 维 · {record.answers.length} 题）
      </p>

      {record.answers.map((a) => (
        <ReviewAnswerRow key={a.questionId} a={a} />
      ))}
    </div>
  );
}

function ReviewAnswerRow({ a }: { a: UserAnswer }) {
  const obj = a.kind !== "open" && a.kind !== "architecture" ? OBJECTIVE_INDEX.get(a.questionId) : null;
  const stem =
    obj?.stem ??
    (() => {
      const t = a.questionId.startsWith("open-") ? a.questionId.replace("open-", "") : a.questionId;
      return `（开放题 · 题库 ${t}）`;
    })();

  let body: React.ReactNode = null;
  if (a.kind === "open" || a.kind === "architecture") {
    body = (
      <>
        <p className="assess-review-answer">{String(a.value ?? "").slice(0, 600) || "（未作答）"}</p>
        {a.grading && (
          <div className="assess-review-grading">
            <span className="assess-score-pill">{a.grading.aiScore} 分</span>
            <span className="assess-score-demo">{a.grading.demo ? "Demo" : "LLM"}</span>
            <p>{a.grading.feedback}</p>
            {a.grading.matched.length > 0 && (
              <p>
                <strong>命中：</strong>
                {a.grading.matched.join("；")}
              </p>
            )}
            {a.grading.missing.length > 0 && (
              <p>
                <strong>缺失：</strong>
                {a.grading.missing.join("；")}
              </p>
            )}
          </div>
        )}
      </>
    );
  } else if (obj) {
    const grade = gradeObjective(obj, a.value as number | number[]);
    body = (
      <div className={`assess-feedback${grade.correct ? " ok" : " bad"}`}>
        <strong>{grade.correct ? "正确" : "未完全正确"}</strong>
        {!grade.correct && <span>{obj.explanation}</span>}
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="assess-q-stem">
        <span className="assess-q-tag">{a.kind === "multi" ? "多选" : a.kind === "single" ? "单选" : a.kind === "boolean" ? "判断" : a.kind}</span>
        <span>{stem}</span>
      </div>
      {body}
    </div>
  );
}
