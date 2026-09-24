import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { exerciseGet, exercisesList, exerciseProgress, exerciseSubmit, type ExerciseItem } from "../api";
import { ExercisesPage } from "./Exercises";


vi.mock("../api", () => ({
  exerciseGet: vi.fn(), exercisesList: vi.fn(), exerciseProgress: vi.fn(), exerciseSubmit: vi.fn(),
}));


const item: ExerciseItem = {
  id: "llm101-demo-01", set_id: "llm101-demo", title: "概念题",
  kind: "single_choice", level: 1, topics: ["attention"],
  prompt_markdown: "## 概念题\n选择正确答案。", options: { A: "错误", B: "正确" }, blanks: [],
  answer_mode: "choice_exact", source_anchor: { path: "docs/exercises/demo.md", line: 9 },
};


describe("ExercisesPage", () => {
  beforeEach(() => {
    vi.mocked(exercisesList).mockResolvedValue({ items: [item], total: 1 });
    vi.mocked(exerciseGet).mockResolvedValue(item);
    vi.mocked(exerciseProgress).mockResolvedValue({ total_attempts: 0, completed_items: 0, items: [] });
    vi.mocked(exerciseSubmit).mockResolvedValue({
      attempt_id: "attempt-1", status: "graded", score: 100,
      feedback: { correct: true, message: "回答正确" },
      progress: { total_attempts: 1, completed_items: 1, items: [] },
      reference_markdown: "SECRET EXPLANATION",
    });
  });

  it("shows the answer only after a learner submits", async () => {
    const user = userEvent.setup();
    render(<ExercisesPage />);
    await user.click(await screen.findByRole("button", { name: /概念题/ }));
    expect(screen.queryByText("SECRET EXPLANATION")).not.toBeInTheDocument();
    await user.click(await screen.findByRole("radio", { name: /正确/ }));
    await user.click(screen.getByRole("button", { name: "提交答案" }));
    expect(await screen.findByText("SECRET EXPLANATION")).toBeVisible();
    expect(vi.mocked(exerciseSubmit)).toHaveBeenCalledWith("llm101-demo-01", { choice: "B" }, true);
  });

  it("opens the originating exercise when navigating from a Lab", async () => {
    render(<ExercisesPage targetExerciseId="llm101-demo-01" />);
    expect(await within(screen.getByRole("main", { name: "练习工作区" })).findByText("选择正确答案。")).toBeVisible();
    expect(exerciseGet).toHaveBeenCalledWith("llm101-demo-01");
  });

  it("typesets formulas in the question title and revealed reference", async () => {
    const user = userEvent.setup();
    vi.mocked(exercisesList).mockResolvedValue({ items: [{ ...item, title: "为什么除以 $\\sqrt{d_k}$？" }], total: 1 });
    vi.mocked(exerciseGet).mockResolvedValue({ ...item, title: "为什么除以 $\\sqrt{d_k}$？" });
    vi.mocked(exerciseSubmit).mockResolvedValue({
      attempt_id: "attempt-math", status: "graded", score: 100,
      feedback: { correct: true, message: "回答正确" },
      progress: { total_attempts: 1, completed_items: 1, items: [] },
      reference_markdown: "因为 $$P=\\sigma(x)$$",
    });
    const { container } = render(<ExercisesPage targetExerciseId="llm101-demo-01" />);

    await screen.findByText("为什么除以", { exact: false });
    expect(container.querySelector(".exercise-detail__header h2 .katex")).not.toBeNull();
    expect(container.querySelector(".exercise-list-item strong .katex")).not.toBeNull();
    await user.click(container.querySelector('input[value="B"]')!);
    await user.click(screen.getByText("提交答案"));
    expect(await screen.findByText("回答正确")).toBeVisible();
    expect(container.querySelector(".exercise-result__reference .katex")).not.toBeNull();
  });
});
