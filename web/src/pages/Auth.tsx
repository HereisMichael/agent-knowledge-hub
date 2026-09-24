import { useState, type FormEvent } from "react";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import {
  ApiError,
  login,
  registerAccount,
  type UserIdentity,
} from "../api";


export function AuthPage({
  onAuthenticated,
}: {
  onAuthenticated: (identity: UserIdentity) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const result = mode === "login"
        ? await login({ email, password })
        : await registerAccount({
          email,
          password,
          invite_code: inviteCode,
        });
      setPassword("");
      setInviteCode("");
      onAuthenticated(result.user);
    } catch (reason) {
      const code = reason instanceof ApiError ? reason.code : "request_failed";
      const messageByCode: Record<string, string> = {
        invalid_credentials: "邮箱或密码不正确。",
        invalid_invite: "邀请码无效，请向管理员确认。",
        email_exists: "该邮箱已注册，请直接登录。",
        weak_password: "密码至少需要 12 个字符。",
        invalid_email: "请输入有效邮箱。",
        request_failed: "暂时无法连接服务，请稍后重试。",
      };
      setError(messageByCode[code] || messageByCode.request_failed);
    } finally {
      setPassword("");
      setInviteCode("");
      setSubmitting(false);
    }
  }

  function changeMode(next: "login" | "register") {
    setMode(next);
    setPassword("");
    setInviteCode("");
    setError("");
  }

  return (
    <main className="auth-gate">
      <section className="auth-gate__brief" aria-labelledby="auth-title">
        <div className="auth-gate__brand">
          <span className="training-brand__mark" aria-hidden="true">K</span>
          <div><strong>Knowledge Hub</strong><span>AI INTERVIEW TRAINING</span></div>
        </div>
        <p className="auth-gate__eyebrow">SESSION HANDSHAKE</p>
        <h1 id="auth-title">登录训练平台</h1>
        <p className="auth-gate__lede">
          进入你的 AI Infra 面试训练空间。题库、练习记录和模型设置都按账号独立保存。
        </p>
        <ol className="auth-handshake" aria-label="会话安全步骤">
          <li data-active="true"><span>01</span><div><strong>确认身份</strong><small>邮箱与密码只发送到当前服务</small></div></li>
          <li><span>02</span><div><strong>建立会话</strong><small>浏览器只接收不可读的安全 Cookie</small></div></li>
          <li><span>03</span><div><strong>载入训练台</strong><small>仅访问属于你的进度与设置</small></div></li>
        </ol>
      </section>

      <section className="auth-gate__panel" aria-label={mode === "login" ? "账号登录" : "受邀注册"}>
        <div className="auth-gate__panel-head">
          {mode === "login" ? <LockKeyhole aria-hidden="true" /> : <ShieldCheck aria-hidden="true" />}
          <div>
            <p>{mode === "login" ? "RETURNING MEMBER" : "INVITED MEMBER"}</p>
            <h2>{mode === "login" ? "继续训练" : "创建受邀账号"}</h2>
          </div>
        </div>

        <form className="auth-form" onSubmit={submit}>
          <div className="field">
            <label htmlFor="auth-email">邮箱</label>
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="auth-password">密码</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={12}
              required
            />
          </div>
          {mode === "register" ? (
            <div className="field">
              <label htmlFor="auth-invite">邀请码</label>
              <input
                id="auth-invite"
                type="password"
                value={inviteCode}
                onChange={(event) => setInviteCode(event.target.value)}
                autoComplete="off"
                required
              />
            </div>
          ) : null}
          {error ? <p className="auth-form__error" role="alert">{error}</p> : null}
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting
              ? "正在建立会话…"
              : mode === "login"
                ? "登录并进入"
                : "创建账号并进入"}
          </button>
        </form>

        {mode === "login" ? (
          <button type="button" className="auth-gate__switch" onClick={() => changeMode("register")}>
            使用邀请码注册
          </button>
        ) : (
          <button type="button" className="auth-gate__switch" onClick={() => changeMode("login")}>
            返回账号登录
          </button>
        )}
        <p className="auth-gate__privacy">密码和邀请码不会写入浏览器缓存。</p>
      </section>
    </main>
  );
}
