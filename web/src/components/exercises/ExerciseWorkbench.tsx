import { useState, type FormEvent } from "react";
import type { ExerciseItem } from "../../api";
import { MathInline, MathMarkdown } from "./MathContent";


function choicePrompt(item: ExerciseItem): string {
  if (item.kind !== "single_choice") return item.prompt_markdown;

  const lines = item.prompt_markdown.split("\n");
  const optionLines = new Map<string, number>();
  let inCodeFence = false;
  lines.forEach((line, index) => {
    if (/^\s*(```|~~~)/.test(line)) inCodeFence = !inCodeFence;
    if (inCodeFence) return;
    const match = line.match(/^\s*(?:-\s*([A-D])\)|\*\*([A-D])\.\*\*)\s+(.+)$/);
    if (!match) return;
    const key = match[1] ?? match[2];
    if (item.options[key]?.trim() === match[3].trim()) optionLines.set(key, index);
  });

  const keys = Object.keys(item.options);
  if (keys.length === 0 || !keys.every((key) => optionLines.has(key))) return item.prompt_markdown;
  const indices = new Set(optionLines.values());

  return lines
    .filter((_, index) => !indices.has(index))
    .join("\n")
    .replace(/^##\s+([^\n]+)\n/, (heading, title: string) => title.trim() === item.title ? "" : heading)
    .replace(/(?:\n\s*)+---\s*$/, "")
    .trim();
}

export function ExerciseWorkbench({ item, onSubmit, busy }: {
  item: ExerciseItem;
  onSubmit: (answers: Record<string, unknown>) => Promise<void>;
  busy: boolean;
}) {
  const [choice, setChoice] = useState("");
  const [blanks, setBlanks] = useState<Record<string, string>>({});
  const [submission, setSubmission] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const answers = item.kind === "single_choice"
      ? { choice }
      : item.kind === "blank_fill"
        ? blanks
        : { submission };
    setError("");
    try {
      await onSubmit(answers);
    } catch {
      setError("答案未能保存，请检查连接后重试。已填写的内容仍在这里。");
    }
  }

  const canSubmit = item.kind === "single_choice"
    ? Boolean(choice)
    : item.kind === "blank_fill"
      ? item.blanks.some((blank) => Boolean(blanks[blank.id]?.trim()))
      : Boolean(submission.trim());

  return (
    <div className="exercise-workbench">
      <MathMarkdown markdown={choicePrompt(item)} className="exercise-workbench__prompt prose" />
      <form className="exercise-workbench__form" onSubmit={(event) => void submit(event)}>
        {item.kind === "single_choice" && (
          <fieldset className="exercise-options">
            <legend>选择一个答案</legend>
            {Object.entries(item.options).map(([key, label]) => (
              <label key={key} className="exercise-option">
                <input type="radio" name={`exercise-${item.id}`} value={key} checked={choice === key} onChange={() => setChoice(key)} />
                <span className="exercise-option__letter">{key}</span>
                <MathInline text={label} className="exercise-option__answer" />
              </label>
            ))}
          </fieldset>
        )}
        {item.kind === "blank_fill" && (
          <div className="exercise-blanks">
            <p className="exercise-hint">对照题面中的填空编号填写。需要代码时可直接输入表达式；不会在服务器执行。</p>
            {item.blanks.map((blank, index) => (
              <div className="field" key={blank.id}>
                <label htmlFor={`${item.id}-${blank.id}`}>填空 {index + 1}</label>
                <input
                  id={`${item.id}-${blank.id}`}
                  value={blanks[blank.id] ?? ""}
                  onChange={(event) => setBlanks((current) => ({ ...current, [blank.id]: event.target.value }))}
                  placeholder="输入你的答案"
                />
              </div>
            ))}
          </div>
        )}
        {item.kind === "implementation_challenge" && (
          <div className="field">
            <label htmlFor={`${item.id}-submission`}>完成记录或产物链接</label>
            <textarea
              id={`${item.id}-submission`}
              rows={5}
              value={submission}
              onChange={(event) => setSubmission(event.target.value)}
              placeholder="记录实现思路、仓库链接或验证结果。代码不会在服务器执行。"
            />
          </div>
        )}
        {error && <p className="inline-message" data-tone="danger" role="alert">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={busy || !canSubmit}>
          {busy ? "保存中…" : "提交答案"}
        </button>
      </form>
    </div>
  );
}
