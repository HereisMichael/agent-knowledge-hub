import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { labComplete, labsList, labsRecommend } from "../api";
import { LabsPage } from "./Labs";

vi.mock("../api", () => ({ labComplete: vi.fn(), labsList: vi.fn(), labsRecommend: vi.fn() }));

const lab = { id: "lab-1", title: "实现 FlashAttention", effort_hours: 3, weakness_tags: ["ai-infra"], steps: ["完成 tiling", "验证精度"], source_exercise_id: "llm101-demo-01" };

describe("LabsPage", () => {
  beforeEach(() => {
    vi.mocked(labsList).mockResolvedValue({ labs: [lab] });
    vi.mocked(labsRecommend).mockResolvedValue({ labs: [lab] });
    vi.mocked(labComplete).mockResolvedValue({ ok: true });
  });

  it("keeps recommendation visible when the catalog fails independently", async () => {
    vi.mocked(labsList).mockRejectedValue(new Error("catalog offline"));
    render(<LabsPage />);

    expect(await screen.findByRole("heading", { name: "实现 FlashAttention" })).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("Lab 目录加载失败");
  });

  it("saves notes for the selected Lab with inline feedback", async () => {
    const user = userEvent.setup();
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    render(<LabsPage />);

    const notes = await screen.findByLabelText("实现 FlashAttention 完成笔记");
    await user.type(notes, "精度误差小于阈值");
    await user.click(screen.getByRole("button", { name: "完成 实现 FlashAttention" }));

    expect(labComplete).toHaveBeenCalledWith("lab-1", "精度误差小于阈值");
    expect(await screen.findByText("完成记录已保存")).toBeVisible();
    expect(alertSpy).not.toHaveBeenCalled();
    alertSpy.mockRestore();
  });

  it("links a generated lab back to its originating exercise", async () => {
    const openExercise = vi.fn();
    const user = userEvent.setup();
    render(<LabsPage onOpenExercise={openExercise} />);
    const links = await screen.findAllByRole("link", { name: "查看来源练习" });
    expect(links[0]).toHaveAttribute("href", "#exercise=llm101-demo-01");
    await user.click(links[0]);
    expect(openExercise).toHaveBeenCalledWith("llm101-demo-01");
  });
});
