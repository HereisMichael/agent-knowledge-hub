import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { loadOpenQuestions } from "../assessment/openBank";
import { latestTwo, listAssessments, overallTrend } from "../assessment/storage";
import { SkillAssessmentPage } from "./SkillAssessment";

vi.mock("../assessment/openBank", async (loadOriginal) => {
  const original = await loadOriginal<typeof import("../assessment/openBank")>();
  return { ...original, loadOpenQuestions: vi.fn() };
});
vi.mock("../assessment/storage", async (loadOriginal) => {
  const original = await loadOriginal<typeof import("../assessment/storage")>();
  return { ...original, latestTwo: vi.fn(), listAssessments: vi.fn(), overallTrend: vi.fn() };
});

describe("SkillAssessmentPage", () => {
  beforeEach(() => {
    vi.mocked(listAssessments).mockReturnValue([]);
    vi.mocked(latestTwo).mockReturnValue({});
    vi.mocked(overallTrend).mockReturnValue([]);
    vi.mocked(loadOpenQuestions).mockResolvedValue([{ id: "open-1", dimId: "llm", type: "open", stem: "解释 KV Cache", keyPoints: ["复用"], rubric: { depth: 100 }, source: { ref: "q-1", where: "题库" } }]);
  });

  it("marks the active phase and preserves an open answer across rerenders", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<SkillAssessmentPage />);
    await user.click(screen.getByRole("button", { name: "开始首次测评" }));
    await user.click(screen.getByRole("button", { name: /大模型基础/ }));
    await user.click(screen.getByRole("button", { name: "开始作答" }));

    expect(screen.getByText("作答中", { selector: ".ui-signal-line__label" }).closest("li")).toHaveAttribute("aria-current", "step");
    const answer = await screen.findByLabelText("解释 KV Cache");
    await user.type(answer, "复用历史键值张量，减少重复计算");
    rerender(<SkillAssessmentPage />);
    expect(screen.getByLabelText("解释 KV Cache")).toHaveValue("复用历史键值张量，减少重复计算");
  });
});
