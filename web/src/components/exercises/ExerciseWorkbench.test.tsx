import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ExerciseItem } from "../../api";
import { ExerciseWorkbench } from "./ExerciseWorkbench";


const quiz: ExerciseItem = {
  id: "llm101-quiz-01", set_id: "llm101-quiz", title: "注意力测试",
  kind: "single_choice", level: 1, topics: ["attention"],
  prompt_markdown: "## 问题\n为什么要缩放？\n\n```python\nscore = q @ k\n```",
  options: { A: "降低内存", B: "避免 softmax 饱和" }, blanks: [],
  answer_mode: "choice_exact", source_anchor: { path: "docs/exercises/quiz.md", line: 12 },
};


describe("ExerciseWorkbench", () => {
  it("shows markdown list choices only in the interactive answer group", () => {
    const item: ExerciseItem = {
      ...quiz,
      prompt_markdown: "## 问题\n选择正确答案：\n\n- A) 降低内存\n- B) 避免 softmax 饱和\n\n---",
    };
    const { container } = render(<ExerciseWorkbench item={item} onSubmit={vi.fn()} busy={false} />);

    expect(screen.getAllByText("降低内存")).toHaveLength(1);
    expect(screen.getAllByText("避免 softmax 饱和")).toHaveLength(1);
    expect(container.querySelector(".exercise-workbench__prompt li")).toBeNull();
    expect(screen.getAllByRole("radio")).toHaveLength(2);
  });

  it("shows paragraph-style choices only once and renders inline math", () => {
    const item: ExerciseItem = {
      ...quiz,
      prompt_markdown: "## 问题\n为什么除以 $\\sqrt{d_k}$？\n\n$$P=\\sigma(x)$$\n\n**A.** 降低内存\n\n**B.** 避免 softmax 饱和\n\n---",
    };
    const { container } = render(<ExerciseWorkbench item={item} onSubmit={vi.fn()} busy={false} />);

    expect(screen.getAllByText("降低内存")).toHaveLength(1);
    expect(screen.getAllByText("避免 softmax 饱和")).toHaveLength(1);
    expect(container.querySelectorAll(".katex")).toHaveLength(2);
    expect(container.querySelector(".katex-display")).not.toBeNull();
    expect(screen.getAllByRole("radio")).toHaveLength(2);
  });

  it("keeps long answer text in its own selectable option", async () => {
    const user = userEvent.setup();
    const item: ExerciseItem = {
      ...quiz,
      options: { A: "短答案", B: "这是一个较长的答案，需要完整呈现原理、条件和适用范围，不应截断。" },
      prompt_markdown: "选择正确答案。",
    };
    render(<ExerciseWorkbench item={item} onSubmit={vi.fn()} busy={false} />);

    const longOption = screen.getByRole("radio", { name: /这是一个较长的答案/ });
    expect(longOption.closest("label")).toHaveTextContent(item.options.B);
    await user.click(longOption);
    expect(longOption).toBeChecked();
  });

  it("typesets an answer formula without changing its submitted choice key", async () => {
    const user = userEvent.setup();
    const submit = vi.fn().mockResolvedValue(undefined);
    const item: ExerciseItem = { ...quiz, options: { A: "$\\sqrt{d_k}$", B: "普通文本" } };
    const { container } = render(<ExerciseWorkbench item={item} onSubmit={submit} busy={false} />);

    expect(container.querySelector(".exercise-option__answer .katex")).not.toBeNull();
    await user.click(container.querySelector('input[value="B"]')!);
    await user.click(screen.getByText("提交答案"));
    expect(submit).toHaveBeenCalledWith({ choice: "B" });
  });

  it("renders Markdown and submits a choice without showing a hidden answer", async () => {
    const user = userEvent.setup();
    const submit = vi.fn().mockResolvedValue(undefined);
    render(<ExerciseWorkbench item={quiz} onSubmit={submit} busy={false} />);

    expect(screen.getByRole("heading", { name: "问题" })).toBeVisible();
    expect(screen.getByText("score = q @ k")).toBeVisible();
    expect(screen.queryByText("SECRET EXPLANATION")).not.toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /避免 softmax 饱和/ }));
    await user.click(screen.getByRole("button", { name: "提交答案" }));
    expect(submit).toHaveBeenCalledWith({ choice: "B" });
  });

  it("keeps a typed blank when submission fails", async () => {
    const user = userEvent.setup();
    const submit = vi.fn().mockRejectedValue(new Error("offline"));
    const fill: ExerciseItem = {
      ...quiz, kind: "blank_fill", options: {}, blanks: [{ id: "blank-1" }],
      answer_mode: "manual_review",
    };
    render(<ExerciseWorkbench item={fill} onSubmit={submit} busy={false} />);
    const input = screen.getByRole("textbox", { name: "填空 1" });
    await user.type(input, "chunk_size - overlap");
    await user.click(screen.getByRole("button", { name: "提交答案" }));
    expect(input).toHaveValue("chunk_size - overlap");
  });
});
