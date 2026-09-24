import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  quizGetReference,
  quizNext,
  quizPutReference,
  quizReviewDue,
  quizReviewGrade,
  quizSubmit,
} from "../api";
import { QuizPage } from "./Quiz";

vi.mock("../api", () => ({
  quizGetReference: vi.fn(),
  quizNext: vi.fn(),
  quizPutReference: vi.fn(),
  quizReviewDue: vi.fn(),
  quizReviewGrade: vi.fn(),
  quizSubmit: vi.fn(),
}));

const question = {
  question: { id: "q-1", question: "解释 GPU bank conflict", vendor: "general", category: "architecture" },
  saved_reference: "共享内存按 bank 组织。",
};

describe("QuizPage", () => {
  beforeEach(() => {
    vi.mocked(quizReviewDue).mockResolvedValue({ items: [] });
    vi.mocked(quizGetReference).mockResolvedValue({});
    vi.mocked(quizPutReference).mockResolvedValue({ ok: true });
    vi.mocked(quizReviewGrade).mockResolvedValue({ ok: true });
    vi.mocked(quizSubmit).mockResolvedValue({ ai_score: 80, feedback: "结构清晰" });
  });

  it("offers the shared AI Infra source and saves a reference with inline feedback", async () => {
    const user = userEvent.setup();
    vi.mocked(quizNext).mockResolvedValue(question);
    render(<QuizPage />);

    expect(screen.getByRole("option", { name: "通用 / AI Infra" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("题目来源"), "general");
    await user.click(screen.getByRole("button", { name: "下一题" }));
    await user.click(await screen.findByRole("button", { name: "仅保存参考答案" }));

    expect(await screen.findByText("参考答案已保存")).toBeVisible();
  });

  it("keeps the action recoverable after loading a question fails", async () => {
    const user = userEvent.setup();
    vi.mocked(quizNext).mockRejectedValue(new Error("offline"));
    render(<QuizPage />);

    await user.click(screen.getByRole("button", { name: "下一题" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("题目加载失败");
    expect(screen.getByRole("button", { name: "下一题" })).toBeEnabled();
  });
});
