import { ArrowUpRight } from "lucide-react";
import type { DashboardTask } from "../../dashboard/model";
import type { PageId } from "../../navigation";

export function TrainingTaskCard({
  task,
  index,
  onStart,
}: {
  task: DashboardTask;
  index: number;
  onStart: (page: PageId) => void;
}) {
  return (
    <article className="training-task" data-status={task.status}>
      <span className="training-task__index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
      <div className="training-task__copy">
        <h3>{task.label}</h3>
        <p>{task.reason}</p>
      </div>
      <button type="button" className="btn btn-quiet training-task__action" onClick={() => onStart(task.target)}>
        进入 <ArrowUpRight size={15} aria-hidden="true" />
      </button>
    </article>
  );
}
