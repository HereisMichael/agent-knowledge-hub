import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { login, registerAccount } from "../api";


vi.mock("../api", () => ({
  login: vi.fn(),
  registerAccount: vi.fn(),
}));


it("registers with an invite without storing credentials in the browser", async () => {
  const user = userEvent.setup();
  const onAuthenticated = vi.fn();
  vi.mocked(registerAccount).mockResolvedValue({
    user: { id: "user-1", email: "owner@example.com", role: "admin" },
  });
  const { AuthPage } = await import("./Auth");
  render(<AuthPage onAuthenticated={onAuthenticated} />);

  await user.click(screen.getByRole("button", { name: "使用邀请码注册" }));
  await user.type(screen.getByLabelText("邮箱"), "owner@example.com");
  await user.type(screen.getByLabelText("密码"), "correct horse battery staple");
  await user.type(screen.getByLabelText("邀请码"), "invite-2026-safe");
  await user.click(screen.getByRole("button", { name: "创建账号并进入" }));

  expect(registerAccount).toHaveBeenCalledWith({
    email: "owner@example.com",
    password: "correct horse battery staple",
    invite_code: "invite-2026-safe",
  });
  expect(onAuthenticated).toHaveBeenCalledWith({
    id: "user-1",
    email: "owner@example.com",
    role: "admin",
  });
  expect(JSON.stringify(localStorage)).not.toContain("correct horse");
  expect(JSON.stringify(localStorage)).not.toContain("invite-2026-safe");
  expect(login).not.toHaveBeenCalled();
});
