import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listJDs, saveJD } from "../jd/storage";
import { JDAnalysisPage } from "./JDAnalysis";

vi.mock("../jd/storage", async (loadOriginal) => {
  const original = await loadOriginal<typeof import("../jd/storage")>();
  return { ...original, listJDs: vi.fn(), saveJD: vi.fn(), getJD: vi.fn(), deleteJD: vi.fn(), downloadJDReport: vi.fn() };
});

const history = {
  id: "old-1", title: "已有岗位", rawText: "历史内容", responsibilities: ["历史职责"],
  skills: [{ skill: "AWS", category: "cloud" as const, matchedKeyword: "aws" }], createdAt: "2026-08-01T00:00:00Z",
};

describe("JDAnalysisPage", () => {
  beforeEach(() => {
    vi.mocked(listJDs).mockReturnValue([history]);
    vi.mocked(saveJD).mockImplementation((record) => ({ ...record, id: "new-1", createdAt: "2026-08-29T00:00:00Z" }));
  });

  it("analyzes responsibilities and grouped skills in the primary workspace", async () => {
    const user = userEvent.setup();
    render(<JDAnalysisPage />);
    const main = screen.getByRole("main");
    const aside = screen.getByRole("complementary", { name: "分析历史" });
    expect(within(aside).getByText("已有岗位")).toBeVisible();

    await user.type(within(main).getByLabelText("岗位 JD 文本"), "AI Infra 工程师\n岗位职责\n- 负责推理服务性能优化\n任职要求\n- 熟悉 Python、AWS、Docker 与沟通能力");
    await user.click(within(main).getByRole("button", { name: "分析 JD" }));

    expect(within(main).getByText("负责推理服务性能优化")).toBeVisible();
    expect(within(main).getByRole("heading", { name: /技术栈/ })).toBeVisible();
    expect(within(main).getByRole("button", { name: "保存分析" })).toBeEnabled();
  });

  it("validates empty input without saving", async () => {
    const user = userEvent.setup();
    render(<JDAnalysisPage />);
    await user.click(screen.getByRole("button", { name: "分析 JD" }));

    expect(screen.getByRole("alert")).toHaveTextContent("至少 20 字");
    expect(saveJD).not.toHaveBeenCalled();
  });
});
