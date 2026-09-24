import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FeedbackState } from "./FeedbackState";
import { MetricTile } from "./MetricTile";
import { PageHeader } from "./PageHeader";
import { Panel } from "./Panel";
import { SignalLine } from "./SignalLine";
import { StatusBadge } from "./StatusBadge";

describe("UI primitives", () => {
  it("exposes one page heading and its description", () => {
    render(<PageHeader eyebrow="MISSION 01" title="今日训练" description="完成三个任务" />);

    expect(screen.getByRole("heading", { level: 1, name: "今日训练" })).toBeVisible();
    expect(screen.getByText("MISSION 01")).toBeVisible();
    expect(screen.getByText("完成三个任务")).toBeVisible();
  });

  it("announces an error and keeps recovery accessible", () => {
    render(
      <FeedbackState
        kind="error"
        title="服务未连接"
        description="检查后端服务"
        action={<button type="button">重新连接</button>}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("服务未连接");
    expect(screen.getByRole("button", { name: "重新连接" })).toBeEnabled();
  });

  it("marks loading without presenting it as an error", () => {
    render(<FeedbackState kind="loading" title="正在加载" description="读取训练信号" />);

    expect(screen.getByText("正在加载").closest("section")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not encode badge meaning with color alone", () => {
    render(<StatusBadge tone="success">API 已连接</StatusBadge>);

    expect(screen.getByText("API 已连接")).toHaveAttribute("data-tone", "success");
  });

  it("renders panels and metrics with stable semantics", () => {
    render(
      <Panel title="能力信号" eyebrow="SKILL SIGNAL" actions={<button type="button">查看</button>}>
        <MetricTile label="正式题库" value={183} detail="37 道 AI Infra" tone="info" />
      </Panel>,
    );

    expect(screen.getByRole("heading", { name: "能力信号" })).toBeVisible();
    expect(screen.getByText("183")).toHaveAttribute("data-tone", "info");
  });

  it("marks exactly the current signal step", () => {
    render(
      <SignalLine
        steps={[
          { id: "one", label: "GPU 架构", detail: "当前任务", status: "current" },
          { id: "two", label: "FlashAttention", detail: "待开始", status: "pending" },
        ]}
      />,
    );

    expect(screen.getByText("GPU 架构").closest("li")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("FlashAttention").closest("li")).not.toHaveAttribute("aria-current");
  });
});
