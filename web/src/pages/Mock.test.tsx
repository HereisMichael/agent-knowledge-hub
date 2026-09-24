import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockCreate, mockFinish, mockMessage } from "../api";
import { MockPage } from "./Mock";

vi.mock("../api", () => ({
  mockCreate: vi.fn(), mockFinish: vi.fn(), mockMessage: vi.fn(),
  mockReportPdfUrl: vi.fn(() => "/report.pdf"),
}));

const timing = {
  stage: "intro", stage_label: "开场", duration_sec: 300, elapsed_sec: 20, remaining_sec: 280,
  stage_index: 0, total_stages: 2,
  stages: [{ id: "intro", label: "开场", duration_sec: 300 }, { id: "deep", label: "技术深挖", duration_sec: 600 }],
};

describe("MockPage", () => {
  beforeEach(() => {
    vi.mocked(mockCreate).mockResolvedValue({ id: "s-1", transcript: [{ role: "interviewer", content: "请做自我介绍" }], stage_timing: timing });
    vi.mocked(mockFinish).mockResolvedValue({ transcript: [], report: null });
  });

  it("shows structured stages and an accessible transcript", async () => {
    const user = userEvent.setup();
    render(<MockPage />);

    await user.selectOptions(screen.getByLabelText("模式"), "structured");
    await user.click(screen.getByRole("button", { name: "开始面试" }));

    expect(await screen.findByRole("log", { name: "面试对话" })).toHaveTextContent("请做自我介绍");
    expect(screen.getByText("开场", { selector: ".ui-signal-line__label" }).closest("li")).toHaveAttribute("aria-current", "step");
  });

  it("retains a typed answer when sending fails", async () => {
    const user = userEvent.setup();
    vi.mocked(mockMessage).mockRejectedValue(new Error("offline"));
    render(<MockPage />);
    await user.click(screen.getByRole("button", { name: "开始面试" }));
    const input = await screen.findByLabelText("你的回答");
    await user.type(input, "我的完整回答");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("发送失败");
    expect(input).toHaveValue("我的完整回答");
  });
});
