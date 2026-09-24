import type { ExerciseItem } from "../../api";
import { MathInline } from "./MathContent";

const kindLabel = {
  single_choice: "选择题",
  blank_fill: "代码填空",
  implementation_challenge: "实现挑战",
} as const;

export function ExerciseCard({ item, selected, onSelect }: {
  item: ExerciseItem;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={`exercise-list-item${selected ? " exercise-list-item--selected" : ""}`}
      onClick={onSelect}
      aria-current={selected ? "true" : undefined}
    >
      <span className="exercise-list-item__meta">Level {item.level} · {kindLabel[item.kind]}</span>
      <strong><MathInline text={item.title} /></strong>
      <span className="exercise-list-item__topics">{item.topics.filter((topic) => topic !== "fill-in" && topic !== "quiz" && topic !== "build").slice(0, 3).join(" / ")}</span>
    </button>
  );
}
