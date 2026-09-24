import { ChevronDown } from "lucide-react";
import { QUESTION_SOURCE_LABELS, type QuestionSource } from "../../questions/catalog";

export interface QuestionBankItem {
  id: string;
  vendor: string;
  category: string;
  subcategory?: string;
  difficulty: number;
  question: string;
  key_points: string[];
  reference_answer?: string;
  follow_ups?: string[];
  tags?: string[];
}

function difficultyLabel(value: number): string {
  const normalized = Math.max(0, Math.min(5, Math.round(value)));
  return `${normalized}/5`;
}

export function QuestionCard({
  question,
  expanded,
  onToggle,
}: {
  question: QuestionBankItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const detailsId = `question-details-${question.id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  return (
    <article className="bank-question-card" data-expanded={expanded}>
      <button type="button" className="bank-question-card__trigger" aria-expanded={expanded} aria-controls={detailsId} onClick={onToggle}>
        <span className="bank-question-card__meta" aria-hidden="true">
          <span>{QUESTION_SOURCE_LABELS[question.vendor as QuestionSource] ?? question.vendor}</span>
          <span>{question.category}</span>
          {question.subcategory && <span>{question.subcategory}</span>}
          <span className="bank-question-card__difficulty">难度 {difficultyLabel(question.difficulty)}</span>
        </span>
        <span className="bank-question-card__question">{question.question}</span>
        <ChevronDown className="bank-question-card__chevron" size={19} aria-hidden="true" />
      </button>
      {expanded && (
        <div className="bank-question-card__details" id={detailsId}>
          {question.reference_answer && <section><h3>参考答案</h3><p className="prose">{question.reference_answer}</p></section>}
          <section><h3>参考答案要点</h3>{question.key_points.length ? <ul>{question.key_points.map((point) => <li key={point}>{point}</li>)}</ul> : <p className="empty-hint">暂无要点</p>}</section>
          {question.follow_ups?.length ? <section><h3>追问问题</h3><ul>{question.follow_ups.map((followUp) => <li key={followUp}>{followUp}</li>)}</ul></section> : null}
          {question.tags?.length ? <section><h3>标签</h3><div className="bank-question-card__tags">{question.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></section> : null}
        </div>
      )}
    </article>
  );
}
