import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminPending } from "../api";
import { ContentReviewPage } from "./ContentReview";

vi.mock("../api", () => ({
  adminApprove: vi.fn(), adminIngest: vi.fn(), adminPending: vi.fn(), adminPublishLogs: vi.fn(),
  adminReject: vi.fn(), adminRollback: vi.fn(), adminRunUpdate: vi.fn(),
}));

describe("ContentReviewPage", () => {
  beforeEach(() => { vi.mocked(adminPending).mockResolvedValue({ items: [] }); });

  it("uses the signed-in administrator session and removes the legacy key", async () => {
    localStorage.setItem("adminKey", "legacy-secret");
    const user = userEvent.setup();
    render(<ContentReviewPage />);

    expect(screen.queryByLabelText("管理员密钥")).not.toBeInTheDocument();
    await waitFor(() => expect(localStorage.getItem("adminKey")).toBeNull());
    await user.click(screen.getByRole("button", { name: "刷新待审" }));

    expect(adminPending).toHaveBeenCalledWith();
    expect(localStorage.getItem("adminKey")).toBeNull();
  });
});
