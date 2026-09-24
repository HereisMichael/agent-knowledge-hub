import type { ExerciseAttemptResult } from "../../api";
import { MathMarkdown } from "./MathContent";


export function ExerciseResult({ result }: { result: ExerciseAttemptResult }) {
  const title = result.status === "graded"
    ? `得分 ${result.score ?? 0}`
    : result.status === "partially_graded"
      ? `已部分判分 · ${result.score ?? 0}`
      : "作答已保存";
  return (
    <section className="exercise-result" aria-label="作答结果" aria-live="polite">
      <h3>{title}</h3>
      <p>{result.feedback.message || (result.status === "recorded" ? "本题需要对照参考答案自行检查。" : "查看下面的反馈继续练习。")}</p>
      {result.reference_markdown && (
        <div className="exercise-result__reference">
          <h4>参考答案</h4>
          <MathMarkdown markdown={result.reference_markdown} className="prose" />
        </div>
      )}
    </section>
  );
}
