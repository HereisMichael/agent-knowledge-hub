import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ask, contentFeed } from "../api";
import { LearnPage } from "./Learn";

vi.mock("../api", () => ({ ask: vi.fn(), contentFeed: vi.fn() }));

describe("LearnPage", () => {
  beforeEach(() => {
    vi.mocked(contentFeed).mockResolvedValue({ items: [] });
  });

  it("renders the answer and citation in separately labelled regions", async () => {
    const user = userEvent.setup();
    vi.mocked(ask).mockResolvedValue({
      answer: "mbarrier 用于协调异步事务完成。",
      citation_details: [{ source_id: "gpu-notes", excerpt: "异步拷贝完成后唤醒消费者。" }],
    });
    render(<LearnPage />);

    await user.type(screen.getByLabelText("你的问题"), "解释 mbarrier");
    await user.click(screen.getByRole("button", { name: "提问" }));

    expect(await screen.findByRole("region", { name: "回答" })).toHaveTextContent("mbarrier");
    expect(screen.getByRole("complementary", { name: "知识来源" })).toHaveTextContent("gpu-notes");
  });
});
