import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  deleteAccount,
  exportAccountData,
  getSettings,
  testSettings,
  updateSettings,
} from "../api";
import type { LlmProtocol } from "../api";
import { FeedbackState } from "../components/ui/FeedbackState";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { StatusBadge } from "../components/ui/StatusBadge";
import { clearLocalUserData } from "../privacy/localData";

const CACHE_KEY = "llm_settings_cache";
const CACHE_MAX_AGE = 24 * 60 * 60 * 1000;

const PROTOCOL_DETAILS: Record<LlmProtocol, { label: string; baseUrl: string; model: string }> = {
  openai_chat: {
    label: "OpenAI Chat Completions",
    baseUrl: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
  },
  anthropic_messages: {
    label: "Anthropic Messages",
    baseUrl: "https://api.anthropic.com",
    model: "claude-3-5-haiku-latest",
  },
};

const SETTINGS_ERROR_MESSAGES: Record<string, string> = {
  credential_encryption_unavailable: "凭据加密服务暂不可用，设置未保存。请稍后重试。",
  unsupported_llm_protocol: "接口协议不受支持，请选择 OpenAI Chat Completions 或 Anthropic Messages。",
  model_key_required_for_endpoint: "更换模型服务主机时必须重新输入对应的 API Key；切换接口协议时也必须重新输入。系统不会把服务器 Key 或旧配置的 Key 发送到新连接。",
  unsafe_llm_base_url: "该地址不安全。请使用可公开访问的 HTTPS 模型地址，不能使用本机、内网或云元数据地址。",
  demo_mode_active: "当前为 Demo 模式，未向外部模型服务发起请求。",
  model_auth_failed: "模型认证失败，请检查该服务对应的 API Key。",
  model_rate_limited: "模型服务正在限流，请稍后重试。",
  model_request_invalid: "模型名称或请求参数无效，请检查当前配置。",
  model_endpoint_blocked: "模型地址不安全，不能发起连接。",
  model_endpoint_unreachable: "无法连接模型服务，请检查地址和网络连通性。",
  model_request_deadline_exceeded: "模型服务响应超时，请稍后重试或检查服务状态。",
  model_response_too_large: "模型服务返回内容过大，请调整服务端配置后重试。",
  model_response_encoding_unsupported: "模型服务返回了不支持的内容编码。",
  model_capacity_exhausted: "模型服务当前繁忙，请稍后重试。",
  model_response_invalid: "模型服务返回了无效响应，请检查接口协议和模型配置。",
  model_json_invalid: "模型服务没有返回有效的结构化结果，请检查模型配置。",
};

function protocolLabel(protocol: LlmProtocol): string {
  return PROTOCOL_DETAILS[protocol].label;
}
function normalizeProtocol(protocol?: string): LlmProtocol {
  return protocol === "anthropic_messages" ? "anthropic_messages" : "openai_chat";
}


function settingsErrorMessage(code?: string): string {
  return SETTINGS_ERROR_MESSAGES[code || ""] || "设置保存失败，请重试。Key 输入已清除。";
}

interface PublicSettings {
  llm_protocol?: LlmProtocol;
  llm_base_url?: string;
  llm_model?: string;
  llm_api_key_masked?: string;
  has_custom_key?: boolean;
  force_demo?: boolean;
  demo_mode_active?: boolean;
  using_server_env_fallback?: boolean;
}

interface CachedSettings extends PublicSettings {
  timestamp: number;
}

function toCache(settings: PublicSettings): CachedSettings {
  return {
    llm_protocol: settings.llm_protocol,
    llm_base_url: settings.llm_base_url,
    llm_model: settings.llm_model,
    llm_api_key_masked: settings.llm_api_key_masked,
    has_custom_key: settings.has_custom_key,
    force_demo: settings.force_demo,
    demo_mode_active: settings.demo_mode_active,
    using_server_env_fallback: settings.using_server_env_fallback,
    timestamp: Date.now(),
  };
}

function loadCache(): CachedSettings | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CachedSettings>;
    if (typeof parsed.timestamp !== "number" || Date.now() - parsed.timestamp > CACHE_MAX_AGE) {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
    return toCache(parsed);
  } catch {
    localStorage.removeItem(CACHE_KEY);
    return null;
  }
}

function saveCache(settings: PublicSettings) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(toCache(settings)));
  } catch {
    // The page still works when storage is unavailable.
  }
}

export function SettingsPage({
  onAccountDeleted,
}: {
  onAccountDeleted?: () => void;
}) {
  const [baseUrl, setBaseUrl] = useState("");
  const [protocol, setProtocol] = useState<LlmProtocol>("openai_chat");
  const [savedProtocol, setSavedProtocol] = useState<LlmProtocol>("openai_chat");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [forceDemo, setForceDemo] = useState(false);
  const [masked, setMasked] = useState("");
  const [hasCustomKey, setHasCustomKey] = useState(false);
  const [demoActive, setDemoActive] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [privacyMessage, setPrivacyMessage] = useState("");

  const applyPublicSettings = useCallback((settings: PublicSettings, cache = true) => {
    setBaseUrl(settings.llm_base_url || "");
    const nextProtocol = normalizeProtocol(settings.llm_protocol);
    setProtocol(nextProtocol);
    setSavedProtocol(nextProtocol);
    setModel(settings.llm_model || "");
    setMasked(settings.llm_api_key_masked || "");
    setHasCustomKey(!!settings.has_custom_key);
    setForceDemo(!!settings.force_demo);
    setDemoActive(!!settings.demo_mode_active);
    setUsingFallback(!!settings.using_server_env_fallback);
    if (cache) saveCache(settings);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const settings = (await getSettings()) as PublicSettings;
      applyPublicSettings(settings);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [applyPublicSettings]);

  useEffect(() => {
    const cached = loadCache();
    if (cached) applyPublicSettings(cached, false);
    void load();
  }, [applyPublicSettings, load]);

  async function save() {
    setSaving(true);
    setMessage("");
    try {
      const result = (await updateSettings({
        llm_protocol: protocol,
        llm_base_url: baseUrl,
        llm_model: model,
        llm_api_key: apiKey || undefined,
        force_demo: forceDemo,
      })) as PublicSettings;
      applyPublicSettings(result);
      setMessage("设置已保存并立即生效。");
    } catch (error) {
      const code = (error as { code?: string })?.code;
      setMessage(settingsErrorMessage(code));
    } finally {
      setApiKey("");
      setSaving(false);
    }
  }

  async function testConnection() {
    setTesting(true);
    setMessage("");
    try {
      const result = await testSettings() as {
        ok?: boolean;
        code?: string;
        protocol?: LlmProtocol;
        model?: string;
        preview?: string;
      };
      if (result.ok) {
        const provider = protocolLabel(normalizeProtocol(result.protocol));
        const modelName = result.model || model || "默认模型";
        const preview = typeof result.preview === "string" && result.preview.trim()
          ? ` 返回：${result.preview}`
          : "";
        setMessage(`连接成功，已验证 ${provider} / ${modelName}。${preview}`);
      } else {
        setMessage(SETTINGS_ERROR_MESSAGES[result.code || ""] || "连接失败，请检查地址、模型和凭据。");
      }
    } catch (error) {
      const code = (error as { code?: string })?.code;
      setMessage(SETTINGS_ERROR_MESSAGES[code || ""] || "连接失败，请检查地址、模型和凭据。");
    } finally {
      setTesting(false);
    }
  }

  async function downloadAccountData() {
    setExporting(true);
    setPrivacyMessage("");
    try {
      const blob = await exportAccountData();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "agent-knowledge-hub-account-export.json";
      anchor.click();
      URL.revokeObjectURL(url);
      setPrivacyMessage("数据导出已生成并开始下载。");
    } catch {
      setPrivacyMessage("数据导出失败，请稍后重试。");
    } finally {
      setExporting(false);
    }
  }

  async function permanentlyDeleteAccount() {
    setDeleting(true);
    setPrivacyMessage("");
    try {
      await deleteAccount(deletePassword);
      clearLocalUserData();
      setDeletePassword("");
      setDeleteConfirm("");
      onAccountDeleted?.();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "request_failed";
      setPrivacyMessage(
        code === "invalid_password"
          ? "当前密码不正确，账号未删除。"
          : code === "last_admin"
            ? "请先为其他账号保留管理员，再删除当前管理员账号。"
            : "账号删除失败，请稍后重试。",
      );
      setDeletePassword("");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="management-page">
      <PageHeader
        eyebrow="SYSTEM CONFIG"
        title="模型与运行设置"
        description="集中管理模型连接、访问凭据和训练台运行模式。敏感输入不会写入浏览器缓存。"
      />

      {loading ? (
        <FeedbackState kind="loading" title="正在同步设置" description="正在读取服务端的最新运行配置。" />
      ) : loadError ? (
        <FeedbackState
          kind="error"
          title="暂时无法读取设置"
          description="已保留可用的本地公开配置，你可以重试同步。"
          action={<button type="button" className="btn" onClick={() => void load()}>重新同步</button>}
        />
      ) : (
        <div className="management-grid management-grid--settings">
          <Panel title="连接信息" eyebrow="ENDPOINT">
            <div className="management-form-stack">
              <div className="field">
                <label htmlFor="llm-protocol">接口协议</label>
                <select
                  id="llm-protocol"
                  value={protocol}
                  onChange={(event) => setProtocol(event.target.value as LlmProtocol)}
                >
                  <option value="openai_chat">OpenAI Chat Completions</option>
                  <option value="anthropic_messages">Anthropic Messages</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="llm-base">API Base URL</label>
                <input id="llm-base" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder={PROTOCOL_DETAILS[protocol].baseUrl} />
                <p className="management-note">仅接受可公开访问的 HTTPS 地址；模型 Key 只会通过 TLS 发送给绑定的主机，更换主机时需重新输入 Key。</p>
              </div>
              <div className="field">
                <label htmlFor="llm-model">模型名称</label>
                <input id="llm-model" value={model} onChange={(event) => setModel(event.target.value)} placeholder={PROTOCOL_DETAILS[protocol].model} />
              </div>
            </div>
            {hasCustomKey && protocol !== savedProtocol && (
              <p className="management-note">切换接口协议后必须重新输入新的 API Key；服务端会在保存时校验并保持最终安全边界。</p>
            )}
          </Panel>

          <Panel title="访问凭据" eyebrow="CREDENTIALS" actions={<StatusBadge tone={hasCustomKey ? "success" : "neutral"}>{hasCustomKey ? "已配置" : "未配置"}</StatusBadge>}>
            <div className="field">
              <label htmlFor="llm-key">API Key</label>
              <input
                id="llm-key"
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder={masked ? `已保存 ${masked}，留空则不修改` : "输入新的 API Key"}
                autoComplete="new-password"
                spellCheck={false}
              />
            </div>
            <p className="management-note">输入内容只用于本次保存请求；提交完成后会立即从页面清除。留空将保留已配置的凭据。</p>
          </Panel>

          <Panel title="运行模式" eyebrow="RUNTIME" actions={<StatusBadge tone={demoActive ? "warning" : "success"}>{demoActive ? "Demo 模式" : "AI 模式"}</StatusBadge>}>
            <label className="management-toggle">
              <input type="checkbox" checked={forceDemo} onChange={(event) => setForceDemo(event.target.checked)} />
              <span><strong>强制 Demo 模式</strong><small>不发起外部模型请求，使用本地规则评分。</small></span>
            </label>
            {usingFallback && !demoActive && <p className="management-note">当前使用服务器环境变量提供的凭据。</p>}
          </Panel>

          <Panel title="我的数据" eyebrow="PRIVACY" className="management-span-two">
            <div className="management-action-list">
              <div>
                <strong>下载账号数据</strong>
                <span>导出服务端个人资料、训练记录和公开设置元数据，不包含密码、会话令牌或模型 Key。本机保存的技能测评和 JD 记录不在导出中，删号时会一并清除。</span>
                <button type="button" className="btn" onClick={() => void downloadAccountData()} disabled={exporting}>
                  {exporting ? "正在生成…" : "下载我的数据"}
                </button>
              </div>
            </div>
            <div className="management-confirm">
              <strong>永久删除账号</strong>
              <p>这会删除你的练习、模拟面试、复习记录和模型设置，且无法撤销。请先下载需要保留的数据。</p>
              <div className="management-form-stack">

                <div className="field">
                  <label htmlFor="delete-password">当前密码</label>
                  <input
                    id="delete-password"
                    type="password"
                    autoComplete="current-password"
                    value={deletePassword}
                    onChange={(event) => setDeletePassword(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="delete-confirm">删除确认</label>
                  <input
                    id="delete-confirm"
                    value={deleteConfirm}
                    onChange={(event) => setDeleteConfirm(event.target.value)}
                    placeholder="输入：删除我的账号"
                  />
                </div>
                <button
                  type="button"
                  className="btn btn-danger"
                  disabled={deleting || !deletePassword || deleteConfirm !== "删除我的账号"}
                  onClick={() => void permanentlyDeleteAccount()}
                >
                  {deleting ? "正在删除…" : "永久删除账号"}
                </button>
              </div>
            </div>
            {privacyMessage && <p className="management-message" role="status" aria-live="polite">{privacyMessage}</p>}
          </Panel>

          <div className="management-actions">
            <button type="button" className="btn btn-primary" onClick={() => void save()} disabled={saving}>{saving ? "保存中…" : "保存设置"}</button>
            <button type="button" className="btn" onClick={() => void testConnection()} disabled={testing}>{testing ? "测试中…" : "测试连接"}</button>
            {message && <p className="management-message" role="status" aria-live="polite">{message}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
