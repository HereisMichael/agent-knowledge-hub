import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  deleteAccount,
  exportAccountData,
  getSettings,
  testSettings,
  updateSettings,
} from "../api";
import { SettingsPage } from "./Settings";

vi.mock("../api", () => ({
  deleteAccount: vi.fn(),
  exportAccountData: vi.fn(),
  getSettings: vi.fn(),
  testSettings: vi.fn(),
  updateSettings: vi.fn(),
}));

const publicSettings = { llm_protocol: "openai_chat" as const, llm_base_url: "https://example.com/v1", llm_model: "demo-model", llm_api_key_masked: "sk-…1234", has_custom_key: true, force_demo: false, demo_mode_active: false, using_server_env_fallback: false };

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.mocked(getSettings).mockResolvedValue(publicSettings);
    localStorage.clear();
    vi.mocked(updateSettings).mockResolvedValue(publicSettings);
    vi.mocked(testSettings).mockResolvedValue({ ok: true, model: "demo-model" });
    vi.mocked(exportAccountData).mockResolvedValue(new Blob(["{}"]));
    vi.mocked(deleteAccount).mockResolvedValue(undefined);
  });

  it("clears a raw key after save and never caches or renders it", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);
    const input = await screen.findByLabelText("API Key");
    await user.type(input, "plain-secret-value");
    await user.click(screen.getByRole("button", { name: "保存设置" }));

    await waitFor(() => expect(input).toHaveValue(""));
    expect(document.body).not.toHaveTextContent("plain-secret-value");
    for (let index = 0; index < localStorage.length; index += 1) {
      expect(localStorage.getItem(localStorage.key(index)!)).not.toContain("plain-secret-value");
    }
  });

  it("saves the explicitly selected Anthropic protocol", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);
    const protocol = await screen.findByLabelText("接口协议");

    await user.selectOptions(protocol, "anthropic_messages");

    expect(screen.getByLabelText("API Base URL")).toHaveAttribute(
      "placeholder",
      "https://api.anthropic.com",
    );
    expect(screen.getByLabelText("模型名称")).toHaveAttribute(
      "placeholder",
      "claude-3-5-haiku-latest",
    );
    expect(screen.getByText(/切换接口协议后必须重新输入/)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "保存设置" }));

    await waitFor(() =>
      expect(updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({ llm_protocol: "anthropic_messages" }),
      ),
    );
  });

  it("只缓存公开协议信息而不缓存 API Key", async () => {
    render(<SettingsPage />);

    await screen.findByLabelText("接口协议");

    await waitFor(() => {
      const cached = JSON.parse(localStorage.getItem("llm_settings_cache") || "{}");
      expect(cached.llm_protocol).toBe("openai_chat");
      expect(cached.llm_api_key).toBeUndefined();
    });
  });

  it("连接成功时显示 Anthropic 协议和模型，并以纯文本展示预览", async () => {
    vi.mocked(testSettings).mockResolvedValueOnce({
      ok: true,
      protocol: "anthropic_messages",
      model: "claude-3-5-haiku-latest",
      preview: '<img src=x onerror="alert(1)">',
    });
    const user = userEvent.setup();
    render(<SettingsPage />);
    await screen.findByLabelText("API Base URL");

    await user.click(screen.getByRole("button", { name: "测试连接" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Anthropic Messages / claude-3-5-haiku-latest",
    );
    expect(screen.getByRole("status")).toHaveTextContent('<img src=x onerror="alert(1)">');
    expect(document.querySelector("img")).toBeNull();
  });

  it("explains why an unsafe model endpoint was rejected", async () => {
    vi.mocked(updateSettings).mockRejectedValueOnce({
      code: "unsafe_llm_base_url",
    });
    const user = userEvent.setup();
    render(<SettingsPage />);
    await screen.findByLabelText("API Base URL");

    await user.click(screen.getByRole("button", { name: "保存设置" }));

    expect(
      await screen.findByText(/不能使用本机、内网或云元数据地址/),
    ).toBeInTheDocument();
  });

  it("requires a new key when the model host changes", async () => {
    vi.mocked(updateSettings).mockRejectedValueOnce({
      code: "model_key_required_for_endpoint",
    });
    const user = userEvent.setup();
    render(<SettingsPage />);
    await screen.findByLabelText("API Base URL");

    await user.click(screen.getByRole("button", { name: "保存设置" }));

    expect(
      await screen.findByText(/更换模型服务主机时必须重新输入/),
    ).toBeInTheDocument();
  });

  it("downloads the authenticated account export", async () => {
    const user = userEvent.setup();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const createObjectURL = vi.fn(() => "blob:account-export");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { value: createObjectURL, configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: revokeObjectURL, configurable: true });
    render(<SettingsPage />);
    await screen.findByLabelText("API Base URL");

    await user.click(screen.getByRole("button", { name: "下载我的数据" }));

    await waitFor(() => expect(exportAccountData).toHaveBeenCalledTimes(1));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:account-export");
    expect(click).toHaveBeenCalledTimes(1);
  });

  it("requires typed confirmation and password before deleting the account", async () => {
    const user = userEvent.setup();
    const onAccountDeleted = vi.fn();
    localStorage.setItem("llm_settings_cache", "public metadata");
    localStorage.setItem("akh_maas_assessments_v2", "private answers");
    localStorage.setItem("akh_jd_records_v1", "private JD");
    localStorage.setItem("akh_last_page_v1", "jd");
    render(<SettingsPage onAccountDeleted={onAccountDeleted} />);
    await screen.findByLabelText("API Base URL");
    const deleteButton = screen.getByRole("button", { name: "永久删除账号" });
    expect(deleteButton).toBeDisabled();

    await user.type(screen.getByLabelText("当前密码"), "member privacy password");
    await user.type(screen.getByLabelText("删除确认"), "删除我的账号");
    await user.click(deleteButton);

    await waitFor(() => {
      expect(deleteAccount).toHaveBeenCalledWith("member privacy password");
    });
    expect(onAccountDeleted).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("当前密码")).toHaveValue("");
    for (const key of [
      "llm_settings_cache",
      "akh_maas_assessments_v2",
      "akh_jd_records_v1",
      "akh_last_page_v1",
    ]) {
      expect(localStorage.getItem(key)).toBeNull();
    }
    expect(screen.getByText(/本机保存的技能测评和 JD 记录不在导出中/)).toBeVisible();
  });
});
