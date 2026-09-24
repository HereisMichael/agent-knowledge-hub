import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { exerciseProgress, progressRadar, quizAnalytics, quizReviewCalendar, quizStats } from "../api";
import { ProgressPage } from "./Progress";

vi.mock("../api", () => ({
  exerciseProgress: vi.fn(), progressRadar: vi.fn(), quizAnalytics: vi.fn(), quizReviewCalendar: vi.fn(), quizStats: vi.fn(),
}));

describe("ProgressPage", () => {
  beforeEach(() => {
    vi.mocked(quizStats).mockResolvedValue({ total_attempts: 12, avg_score: 78, by_vendor: { general: 9, aws: 3 }, review: { total_cards: 4, due_now: 2 } });
    vi.mocked(quizAnalytics).mockResolvedValue({ summary: { total_attempts: 12, questions_practiced: 8, overall_avg: 78, by_category: {}, by_vendor: {} }, questions: [] });
    vi.mocked(quizReviewCalendar).mockResolvedValue({ today: "2026-08-29", overdue_count: 0, total_cards: 4, days: {} });
    vi.mocked(exerciseProgress).mockResolvedValue({ total_attempts: 2, completed_items: 2, items: [], attempts: 2, graded_average: 80, recorded_challenges: 1, by_topic: { RAG: { attempts: 2, graded_average: 80 } }, by_level: { "4": { attempts: 1, graded_average: null } } });
  });

  it("keeps stats visible when radar fails independently", async () => {
    vi.mocked(progressRadar).mockRejectedValue(new Error("radar offline"));
    render(<ProgressPage />);

    expect(await screen.findByText("12")).toBeVisible();
    expect(screen.getByText("通用 / AI Infra")).toBeVisible();
    expect(screen.getByRole("alert", { name: "能力雷达" })).toHaveTextContent("雷达数据加载失败");
  });

  it("shows model engineering attempts separately from interview radar", async () => {
    vi.mocked(progressRadar).mockResolvedValue({ quiz: { axes: [] }, mock: { axes: [] } });
    render(<ProgressPage />);
    expect(await screen.findByRole("heading", { name: "模型工程练习" })).toBeVisible();
    expect(screen.getByText("1 次实现挑战仅记录完成，不参与均分")).toBeVisible();
  });
});
