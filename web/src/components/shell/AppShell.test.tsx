import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("keeps navigation usable when the API is offline", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    const onReconnect = vi.fn();

    render(
      <AppShell
        page="dashboard"
        apiState="offline"
        questionCount={0}
        demoMode={false}
        identity={{ id: "user-1", email: "owner@example.com", role: "admin" }}
        onNavigate={onNavigate}
        onReconnect={onReconnect}
        onLogout={vi.fn()}
      >
        <h1>今日训练内容</h1>
      </AppShell>,
    );

    expect(screen.getByRole("status")).toHaveTextContent("服务未连接");
    await user.click(screen.getByRole("button", { name: "重新连接" }));
    expect(onReconnect).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "题库" }));
    expect(onNavigate).toHaveBeenCalledWith("bank");
    expect(screen.getByRole("heading", { name: "今日训练内容" })).toBeVisible();
  });

  it("offers a global question-bank search entry", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();

    render(
      <AppShell
        page="dashboard"
        apiState="online"
        questionCount={183}
        demoMode
        identity={{ id: "user-1", email: "owner@example.com", role: "admin" }}
        onNavigate={onNavigate}
        onReconnect={vi.fn()}
        onLogout={vi.fn()}
      >
        <div>内容</div>
      </AppShell>,
    );

    expect(screen.getByRole("status")).toHaveTextContent("183 题");
    await user.click(screen.getByRole("button", { name: "搜索题库" }));
    expect(onNavigate).toHaveBeenCalledWith("bank");
  });
});
