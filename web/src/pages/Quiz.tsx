import { useEffect, useState } from "react";
import { quizNext, quizReviewDue, quizReviewGrade, quizSubmit } from "../api";

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

export function QuizPage() {
  const [vendor, setVendor] = useState("aliyun");
  const [category, setCategory] = useState("");
  const [current, setCurrent] = useState<{
    question: { id: string; question: string; vendor: string; category: string };
  } | null>(null);
  const [answer, setAnswer] = useState("");
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
  }

  async function submit() {
    if (!current) return;
    const res = await quizSubmit({
      question_id: current.question.id,
      answer_text: answer,
      use_ai: true,
    });
    setResult(res);
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
              <p className="lab-meta">回忆后自评掌握程度</p>
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

      {!current && (
        <p className="empty-hint">选择厂商与分类后点击「下一题」开始练习</p>
      )}

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
            <label htmlFor="quiz-answer">你的答案</label>
            <textarea
              id="quiz-answer"
              rows={7}
              placeholder="STAR、架构分层、产品选型、合规与 SLA…"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
          </div>
          <button type="button" className="btn btn-primary" onClick={submit}>
            提交并评分
          </button>
        </>
      )}

      {result && (
        <div className="report-block">
          <p className="score">{String(result.ai_score ?? "—")} 分</p>
          <p className="prose" style={{ maxWidth: "none" }}>
            {String(result.feedback ?? "")}
          </p>
          <h3 className="panel-header" style={{ marginTop: "1.25rem" }}>
            参考答案要点
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
