import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { QuestionCard, type QuestionBankItem } from "./QuestionCard";

const question: QuestionBankItem = {
  id: "infra-1",
  vendor: "general",
  category: "ai_infra",
  subcategory: "GPU",
  difficulty: 3,
  question: "mbarrier 的原理是什么？",
  reference_answer: "mbarrier 跟踪异步事务和到达计数。",
  key_points: ["phase bit", "arrival count"],
  follow_ups: ["如何与 TMA 配合？"],
  tags: ["hopper"],
};

describe("QuestionCard", () => {
  it("exposes all answer details from an accessible header button", async () => {
    const user = userEvent.setup();
    render(<QuestionCard question={question} expanded={false} onToggle={() => {}} />);

    const button = screen.getByRole("button", { name: /mbarrier 的原理/ });
    expect(button).toHaveAttribute("aria-expanded", "false");

    render(<QuestionCard question={question} expanded onToggle={() => {}} />);
    const expandedButton = screen.getAllByRole("button", { name: /mbarrier 的原理/ })[1];
    expect(expandedButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/跟踪异步事务/)).toBeVisible();
    expect(screen.getByText("phase bit")).toBeVisible();
    expect(screen.getByText("如何与 TMA 配合？")).toBeVisible();
    await user.click(expandedButton);
  });
});
