import { beforeEach, describe, expect, it, vi } from "vitest";
import { health, progressRadar, quizReviewDue, quizStats } from "../api";
import { latestTwo } from "../assessment/storage";
import { buildDashboardModel, loadDashboardSources, type DashboardSources } from "./model";

vi.mock("../api", () => ({
  health: vi.fn(),
  quizStats: vi.fn(),
  quizReviewDue: vi.fn(),
  progressRadar: vi.fn(),
}));

vi.mock("../assessment/storage", () => ({ latestTwo: vi.fn() }));

const emptySources = (): DashboardSources => ({ failedSources: [] });

describe("dashboard model", () => {
  beforeEach(() => {
    vi.mocked(latestTwo).mockReturnValue({});
  });

  it("recommends a first assessment when no learning history exists", () => {
    const model = buildDashboardModel(emptySources());

    expect(model.tasks.some((task) => task.label === "完成首次技能测评" && task.target === "assess")).toBe(true);
  });

  it("puts due review first", () => {
    const model = buildDashboardModel({
      ...emptySources(),
      due: { items: [{ question: { id: "q-1", question: "GPU memory?" } }] },
      stats: { total_attempts: 8, avg_score: 71, review: { total_cards: 3, due_now: 1 } },
    });

    expect(model.tasks[0]).toMatchObject({ label: "完成间隔复习", target: "quiz", status: "current" });
  });

  it("turns the lowest radar axis into a training reason", () => {
    const model = buildDashboardModel({
      ...emptySources(),
      radar: {
        quiz: { axes: [{ axis: "inference", value: 18 }, { axis: "rag", value: 72 }] },
        mock: { axes: [] },
      },
    });

    expect(model.tasks.some((task) => task.reason.includes("推理优化"))).toBe(true);
  });

  it("keeps unavailable metrics explicit after partial failure", () => {
    const model = buildDashboardModel({ failedSources: ["health", "stats"] });

    expect(model.metrics.map((metric) => metric.value)).toContain("—");
    expect(model.partialFailure).toBe(true);
  });

  it("offers a valid training page as the resume target", () => {
    const model = buildDashboardModel({ ...emptySources(), lastPage: "mock" });

    expect(model.resume).toEqual({ label: "继续上次训练", target: "mock" });
    expect(buildDashboardModel({ ...emptySources(), lastPage: "settings" }).resume).toBeUndefined();
  });

  it("loads sources independently when one API rejects", async () => {
    vi.mocked(health).mockRejectedValue(new Error("offline"));
    vi.mocked(quizStats).mockResolvedValue({ total_attempts: 2, avg_score: 66 });
    vi.mocked(quizReviewDue).mockResolvedValue({ items: [] });
    vi.mocked(progressRadar).mockResolvedValue({ quiz: { axes: [] }, mock: { axes: [] } });
    localStorage.setItem("akh_last_page_v1", "quiz");

    const sources = await loadDashboardSources();

    expect(sources.failedSources).toEqual(["health"]);
    expect(sources.stats?.total_attempts).toBe(2);
    expect(sources.lastPage).toBe("quiz");
  });
});
