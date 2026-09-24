import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getCurrentUser, health, logout } from "./api";
import App from "./App";

const moduleLoads = vi.hoisted(() => ({ learn: 0 }));

vi.mock("./api", () => ({
  getCurrentUser: vi.fn(),
  health: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  registerAccount: vi.fn(),
}));
vi.mock("./pages/Dashboard", () => ({ DashboardPage: () => <h1>今日训练测试页</h1> }));
vi.mock("./pages/Learn", () => {
  moduleLoads.learn += 1;
  return { LearnPage: () => <><h1>知识问答测试页</h1><label htmlFor="draft-note">练习草稿</label><input id="draft-note" /></> };
});
vi.mock("./pages/Quiz", () => ({ QuizPage: () => <h1>刷题测试页</h1> }));
vi.mock("./pages/QuestionBank", () => ({ QuestionBankPage: () => <h1>题库测试页</h1> }));
vi.mock("./pages/Mock", () => ({ MockPage: () => <h1>模拟面试测试页</h1> }));
vi.mock("./pages/Labs", () => ({ LabsPage: () => <h1>Lab 测试页</h1> }));
vi.mock("./pages/SkillAssessment", () => ({ SkillAssessmentPage: () => <h1>测评测试页</h1> }));
vi.mock("./pages/Progress", () => ({ ProgressPage: () => <h1>进度测试页</h1> }));
vi.mock("./pages/JDAnalysis", () => ({ JDAnalysisPage: () => <h1>JD 测试页</h1> }));
vi.mock("./pages/Settings", () => ({ SettingsPage: () => <h1>设置测试页</h1> }));
vi.mock("./pages/ContentReview", () => ({ ContentReviewPage: () => <h1>审核测试页</h1> }));

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCurrentUser).mockResolvedValue({
      user: { id: "user-1", email: "owner@example.com", role: "admin" },
    });
    vi.mocked(health).mockRejectedValue(new Error("offline"));
    vi.mocked(logout).mockResolvedValue(undefined);
  });

  it("shows the invitation sign-in gate when the session is missing", async () => {
    vi.mocked(getCurrentUser).mockRejectedValue({
      status: 401,
      code: "authentication_required",
    });
    localStorage.setItem("akh_jd_records_v1", "previous account JD");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "登录训练平台" })).toBeVisible();
    expect(health).not.toHaveBeenCalled();
    expect(localStorage.getItem("akh_jd_records_v1")).toBeNull();
  });

  it("preserves local personal data and hides login during a temporary API failure", async () => {
    vi.mocked(getCurrentUser).mockRejectedValue(new Error("network unavailable"));
    localStorage.setItem("akh_jd_records_v1", "offline JD");
    localStorage.setItem("akh_maas_assessments_v2", "offline answers");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "暂时无法确认登录状态" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "登录训练平台" })).not.toBeInTheDocument();
    expect(localStorage.getItem("akh_jd_records_v1")).toBe("offline JD");
    expect(localStorage.getItem("akh_maas_assessments_v2")).toBe("offline answers");
  });

  it("clears another account's local data before showing a recovered session", async () => {
    const user = userEvent.setup();
    localStorage.setItem("akh_local_owner_v1", "user-a");
    localStorage.setItem("akh_jd_records_v1", "user A private JD");
    vi.mocked(getCurrentUser)
      .mockRejectedValueOnce(new Error("network unavailable"))
      .mockResolvedValueOnce({
        user: { id: "user-b", email: "b@example.com", role: "member" },
      });

    render(<App />);
    await user.click(await screen.findByRole("button", { name: "重新连接" }));

    expect(await screen.findByRole("heading", { name: "今日训练测试页" })).toBeVisible();
    expect(localStorage.getItem("akh_jd_records_v1")).toBeNull();
    expect(localStorage.getItem("akh_local_owner_v1")).toBe("user-b");
  });

  it("does not expose content governance navigation to a member", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({
      user: { id: "user-2", email: "member@example.com", role: "member" },
    });

    render(<App />);

    expect(await screen.findByRole("heading", { name: "今日训练测试页" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "内容审核" })).not.toBeInTheDocument();
  });

  it("loads pages on demand, preserves visited state and keeps offline navigation usable", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByRole("heading", { name: "今日训练测试页" })).toBeVisible();
    expect(await screen.findByRole("status")).toHaveTextContent("服务未连接");
    expect(moduleLoads.learn).toBe(0);

    await user.click(screen.getByRole("button", { name: "知识问答" }));
    expect(await screen.findByRole("heading", { name: "知识问答测试页" })).toBeVisible();
    expect(moduleLoads.learn).toBe(1);
    await user.type(screen.getByLabelText("练习草稿"), "保留这段内容");

    await user.click(screen.getByRole("button", { name: "今日训练" }));
    await user.click(screen.getByRole("button", { name: "知识问答" }));
    expect(screen.getByLabelText("练习草稿")).toHaveValue("保留这段内容");

    await user.click(screen.getByRole("button", { name: "打开更多导航" }));
    expect(screen.getByRole("dialog", { name: "更多导航" })).toBeVisible();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "更多导航" })).not.toBeInTheDocument());
  });

  it("clears local personal data when signing out", async () => {
    const user = userEvent.setup();
    localStorage.setItem("akh_maas_assessments_v2", "private answers");
    localStorage.setItem("akh_jd_records_v1", "private JD");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "今日训练测试页" })).toBeVisible();

    await user.click(screen.getByRole("button", { name: "退出登录" }));

    expect(await screen.findByRole("heading", { name: "登录训练平台" })).toBeVisible();
    expect(localStorage.getItem("akh_maas_assessments_v2")).toBeNull();
    expect(localStorage.getItem("akh_jd_records_v1")).toBeNull();
  });
});
