import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./Dashboard";

describe("DashboardPage", () => {
  it("starts the highest-priority training task", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();

    render(
      <DashboardPage
        onNavigate={onNavigate}
        loader={async () => ({
          failedSources: [],
          health: { questions: 183, demo_mode: true },
          stats: { total_attempts: 12, avg_score: 74, review: { total_cards: 4, due_now: 2 } },
          due: { items: [{ question: { id: "q-1", question: "解释 mbarrier" } }] },
          radar: { quiz: { axes: [] }, mock: { axes: [] } },
        })}
      />,
    );

    expect(await screen.findByText("183")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "开始今日训练" }));
    expect(onNavigate).toHaveBeenCalledWith("quiz");
  });

  it("keeps partial data visible and identifies degraded sources", async () => {
    render(
      <DashboardPage
        onNavigate={vi.fn()}
        loader={async () => ({ failedSources: ["radar"], health: { questions: 183 } })}
      />,
    );

    expect(await screen.findByText("部分数据暂不可用")).toBeVisible();
    expect(screen.getByText("183")).toBeVisible();
  });
});
