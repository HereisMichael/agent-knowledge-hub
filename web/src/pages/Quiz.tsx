import { useEffect, useState } from "react";
import {
  quizGetReference,
  quizNext,
  quizPutReference,
  quizReviewDue,
  quizReviewGrade,
  quizSubmit,
} from "../api";

function vendorClass(v: string) {
  if (v === "aliyun") return "tag tag-vendor-aliyun";
  if (v === "tencent") return "tag tag-vendor-tencent";
  if (v === "aws") return "tag tag-vendor-aws";
  return "tag";
}

const VENDOR_LABEL: Record<string, string> = {
  aliyun: "阿里云",
  tencent: "腾讯云",
  aws: "AWS",
};

type ScorePoint = { score: number | null; created_at: string };

export function QuizPage() {
  const [vendor, setVendor] = useState("aliyun");
  const [category, setCategory] = useState("");
  const [current, setCurrent] = useState<{
    question: { id: string; question: string; vendor: string; category: string };
    saved_reference?: string;
    score_history?: ScorePoint[];
  } | null>(null);
  const [answer, setAnswer] = useState("");
  const [reference, setReference] = useState("");
  const [saveRef, setSaveRef] = useState(true);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [dueItems, setDueItems] = useState<
    { card: { question_id: string }; question: { id: string; question: string } }[]
  >([]);

  useEffect(() => {
    quizReviewDue(5).then((d) => setDueItems(d.items || [])).catch(() => {});
  }, [result]);

  async function gradeReview(questionId: string, quality: number) {
    await quizReviewGrade(questionId, quality);
    const d = await quizReviewDue(5);
    setDueItems(d.items || []);
  }

  async function loadNext() {
    setResult(null);
    const data = await quizNext(vendor, category || undefined);
    setCurrent(data);
    setAnswer("");
    setReference(data.saved_reference || "");
  }

  async function loadReferenceOnly() {
    if (!current) return;
    const d = await quizGetReference(current.question.id);
    if (d.reference?.reference_text) setReference(d.reference.reference_text);
  }

  async function saveReferenceOnly() {
    if (!current || !reference.trim()) return;
    await quizPutReference(current.question.id, reference);
    alert("参考答案已保存");
  }

  async function submit() {
    if (!current) return;
    const res = await quizSubmit({
      question_id: current.question.id,
      answer_text: answer,
      reference_answer: reference,
      save_reference: saveRef,
      use_ai: true,
    });
    setResult(res);
    if (res.score_history) {
      setCurrent({ ...current, score_history: res.score_history as ScorePoint[] });
    }
  }

  return (
    <div className="panel">
      <div className="toolbar">
        <div className="field">
          <label htmlFor="quiz-vendor">厂商</label>
          <select id="quiz-vendor" value={vendor} onChange={(e) => setVendor(e.target.value)}>
            <option value="aliyun">阿里云</option>
            <option value="tencent">腾讯云</option>
            <option value="aws">AWS</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="quiz-cat">分类</label>
          <select id="quiz-cat" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">全部</option>
            <option value="architecture">架构</option>
            <option value="product">产品</option>
            <option value="behavior">行为</option>
            <option value="solution">方案</option>
            <option value="agent">Agent</option>
          </select>
        </div>
        <button type="button" className="btn btn-primary" onClick={loadNext}>
          下一题
        </button>
      </div>

      {dueItems.length > 0 && (
        <div className="review-block">
          <h3 className="panel-header">间隔复习（SM-2）</h3>
          {dueItems.map((it) => (
            <article key={it.question.id} className="lab-card">
              <p className="question-body" style={{ fontSize: "0.95rem" }}>
                {it.question.question}
              </p>
              <div className="toolbar" style={{ marginBottom: 0 }}>
                {[0, 2, 3, 4, 5].map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => gradeReview(it.question.id, q)}
                  >
                    {q === 0 ? "忘了" : q === 2 ? "难" : q === 3 ? "一般" : q === 4 ? "好" : "熟"}
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}

      {!current && <p className="empty-hint">选择厂商与分类后点击「下一题」开始练习</p>}

      {current && (
        <>
          <div>
            <span className={vendorClass(current.question.vendor)}>
              {VENDOR_LABEL[current.question.vendor] ?? current.question.vendor}
            </span>
            <span className="tag">{current.question.category}</span>
          </div>
          <p className="question-body">{current.question.question}</p>

          <div className="field">
            <label htmlFor="quiz-reference">我的参考答案（持久化，用于对比评分）</label>
            <textarea
              id="quiz-reference"
              rows={5}
              placeholder="写下你认可的完整答案，模型将据此评估本次作答并追踪进步…"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          </div>
          <div className="toolbar" style={{ marginBottom: "1rem" }}>
            <label className="field-checkbox">
              <input
                type="checkbox"
                checked={saveRef}
                onChange={(e) => setSaveRef(e.target.checked)}
              />
              提交时保存参考答案
            </label>
            <button type="button" className="btn btn-ghost" onClick={saveReferenceOnly}>
              仅保存参考答案
            </button>
            <button type="button" className="btn btn-ghost" onClick={loadReferenceOnly}>
              重新加载已存答案
            </button>
          </div>

          {current.score_history && current.score_history.length > 0 && (
            <div className="score-mini-chart">
              <span className="lab-meta">历史得分：</span>
              {current.score_history.map((h, i) => (
                <span key={i} className="score-chip">
                  {h.score ?? "—"}
                </span>
              ))}
            </div>
          )}

          <div className="field">
            <label htmlFor="quiz-answer">本次作答</label>
            <textarea
              id="quiz-answer"
              rows={6}
              placeholder="本次练习的口头/书面回答…"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
          </div>
          <button type="button" className="btn btn-primary" onClick={submit}>
            提交并对比评分
          </button>
        </>
      )}

      {result && (
        <div className="report-block">
          <p className="score">{String(result.ai_score ?? "—")} 分</p>
          {result.reference_used ? (
            <p className="lab-meta">已根据「我的参考答案」进行对比评分</p>
          ) : (
            <p className="lab-meta">未提供参考答案，按题目要点评分。建议填写参考答案以便追踪质量变化。</p>
          )}
          <p className="prose" style={{ maxWidth: "none" }}>
            {String(result.feedback ?? "")}
          </p>
          {(result.gaps_vs_reference as string[] | undefined)?.length ? (
            <>
              <h4 className="panel-header">与参考答案的差距</h4>
              <ul className="prose" style={{ paddingLeft: "1.25rem" }}>
                {(result.gaps_vs_reference as string[]).map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </>
          ) : null}
          {result.improvement_tip ? (
            <p className="mock-report-rewrite">{String(result.improvement_tip)}</p>
          ) : null}
          <h3 className="panel-header" style={{ marginTop: "1.25rem" }}>
            题库参考要点
          </h3>
          <ul className="prose" style={{ maxWidth: "none", paddingLeft: "1.25rem" }}>
            {(result.explanation as { key_points?: string[] })?.key_points?.map((k) => (
              <li key={k}>{k}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
