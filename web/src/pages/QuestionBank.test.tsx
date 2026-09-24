import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchAllQuestions } from "../api";
import { QuestionBankPage } from "./QuestionBank";

vi.mock("../api", () => ({ fetchAllQuestions: vi.fn() }));

const questions = [
  {
    id: "infra-1", vendor: "general", category: "ai_infra", subcategory: "GPU", difficulty: 3,
    question: "mbarrier 的原理是什么？", key_points: ["arrival count"], tags: ["hopper"],
  },
  {
    id: "aws-1", vendor: "aws", category: "architecture", subcategory: "HA", difficulty: 2,
    question: "AWS 多可用区如何设计？", key_points: ["Multi-AZ"], tags: ["resilience"],
  },
];

describe("QuestionBankPage", () => {
  beforeEach(() => {
    vi.mocked(fetchAllQuestions).mockResolvedValue({ questions });
  });

  it("searches question metadata and clears filters", async () => {
    const user = userEvent.setup();
    render(<QuestionBankPage />);

    expect(await screen.findByText("AWS 多可用区如何设计？")).toBeVisible();
    await user.type(screen.getByRole("searchbox", { name: "搜索题目" }), "mbarrier");
    expect(screen.getByText("mbarrier 的原理是什么？")).toBeVisible();
    expect(screen.queryByText("AWS 多可用区如何设计？")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "清除筛选" }));
    expect(screen.getByText("AWS 多可用区如何设计？")).toBeVisible();
  });

  it("shows shared source counts and filters to general questions", async () => {
    const user = userEvent.setup();
    render(<QuestionBankPage />);

    const general = await screen.findByRole("button", { name: "通用 / AI Infra 1" });
    await user.click(general);
    expect(screen.getByText("mbarrier 的原理是什么？")).toBeVisible();
    expect(screen.queryByText("AWS 多可用区如何设计？")).not.toBeInTheDocument();
  });
});
