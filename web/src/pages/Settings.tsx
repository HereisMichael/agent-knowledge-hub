import { useEffect, useState } from "react";
import { getSettings, testSettings, updateSettings } from "../api";

const CACHE_KEY = "llm_settings_cache";

interface CachedSettings {
  llm_base_url?: string;
  llm_model?: string;
  llm_api_key_masked?: string;
  force_demo?: boolean;
  demo_mode_active?: boolean;
  using_server_env_fallback?: boolean;
  timestamp: number;
}

function loadCache(): CachedSettings | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    // 缓存 24 小时有效
    if (Date.now() - data.timestamp > 24 * 60 * 60 * 1000) {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

function saveCache(settings: CachedSettings) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ ...settings, timestamp: Date.now() }));
  } catch {
    // 忽略存储错误
  }
}

export function SettingsPage() {
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [forceDemo, setForceDemo] = useState(false);
  const [masked, setMasked] = useState("");
  const [demoActive, setDemoActive] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const s = await getSettings();
      setBaseUrl(s.llm_base_url || "");
      setModel(s.llm_model || "");
      setMasked(s.llm_api_key_masked || "");
      setForceDemo(!!s.force_demo);
      setDemoActive(!!s.demo_mode_active);
      setUsingFallback(!!s.using_server_env_fallback);
      // 保存到本地缓存
      saveCache({
        llm_base_url: s.llm_base_url,
        llm_model: s.llm_model,
        llm_api_key_masked: s.llm_api_key_masked,
        force_demo: s.force_demo,
        demo_mode_active: s.demo_mode_active,
        using_server_env_fallback: s.using_server_env_fallback,
        timestamp: Date.now(),
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // 先从缓存快速加载
    const cached = loadCache();
    if (cached) {
      setBaseUrl(cached.llm_base_url || "");
      setModel(cached.llm_model || "");
      setMasked(cached.llm_api_key_masked || "");
      setForceDemo(!!cached.force_demo);
      setDemoActive(!!cached.demo_mode_active);
      setUsingFallback(!!cached.using_server_env_fallback);
      setLoading(false);
    }
    // 然后从服务器刷新
    load();
  }, []);

  async function save() {
    setSaving(true);
    try {
      const result = await updateSettings({
        llm_base_url: baseUrl,
        llm_model: model,
        llm_api_key: apiKey || undefined,
        force_demo: forceDemo,
      });
      setApiKey("");
      setMsg("✓ 设置已保存并立即生效");
      // 更新缓存
      saveCache({
        llm_base_url: result.llm_base_url,
        llm_model: result.llm_model,
        llm_api_key_masked: result.llm_api_key_masked,
        force_demo: result.force_demo,
        demo_mode_active: result.demo_mode_active,
        using_server_env_fallback: result.using_server_env_fallback,
        timestamp: Date.now(),
      });
      // 刷新状态
      load();
    } finally {
      setSaving(false);
    }
  }

  async function test() {
    const r = await testSettings();
    setMsg(r.ok ? `连接成功（${r.model}）` : `连接失败：${r.message}`);
  }

  if (loading) {
    return (
      <div className="panel">
        <p className="empty-hint">加载中…</p>
      </div>
    );
  }

  return (
    <div className="panel settings-panel">
      <div style={{ marginBottom: "1rem" }}>
        <p className="empty-hint">
          配置阅卷与模拟面试使用的模型。密钥保存在本机数据库，不会提交到 GitHub。
        </p>
        <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <span
            className={`status-pill${demoActive ? "" : " ok"}`}
            style={{ fontSize: "0.8rem", padding: "2px 8px" }}
          >
            {demoActive ? "Demo 模式（规则评分）" : `AI 模式 · ${model || "未配置"}`}
          </span>
          {usingFallback && !demoActive && (
            <span
              style={{
                fontSize: "0.8rem",
                padding: "2px 8px",
                background: "#fff3cd",
                borderRadius: "4px",
                color: "#856404",
              }}
            >
              使用服务器环境变量
            </span>
          )}
        </div>
      </div>

      <div className="field">
        <label htmlFor="llm-base">API Base URL</label>
        <input
          id="llm-base"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://api.openai.com/v1"
        />
      </div>
      <div className="field">
        <label htmlFor="llm-model">模型名称</label>
        <input
          id="llm-model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="gpt-4o-mini"
        />
      </div>
      <div className="field">
        <label htmlFor="llm-key">API Key</label>
        <input
          id="llm-key"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={masked ? `已保存 ${masked}，留空则不修改` : "sk-..."}
          autoComplete="off"
        />
      </div>
      <div className="field field-checkbox">
        <label>
          <input
            type="checkbox"
            checked={forceDemo}
            onChange={(e) => setForceDemo(e.target.checked)}
          />
          强制 Demo 模式（不使用 API）
        </label>
      </div>

      <div className="toolbar">
        <button
          type="button"
          className="btn btn-primary"
          onClick={save}
          disabled={saving}
        >
          {saving ? "保存中…" : "保存设置"}
        </button>
        <button type="button" className="btn" onClick={test}>
          测试连接
        </button>
      </div>
      {msg && <p className="settings-msg">{msg}</p>}
    </div>
  );
}
