import { Search } from "lucide-react";
import type { UserIdentity } from "../../api";
import { getPageDefinition, type PageId } from "../../navigation";
import { StatusBadge } from "../ui/StatusBadge";

export type ApiState = "checking" | "online" | "offline";

export function TopStatusBar({
  page,
  apiState,
  questionCount,
  demoMode,
  identity,
  onNavigate,
  onReconnect,
  onLogout,
}: {
  page: PageId;
  apiState: ApiState;
  questionCount: number;
  demoMode: boolean;
  identity: UserIdentity;
  onNavigate: (page: PageId) => void;
  onReconnect: () => void;
  onLogout: () => void;
}) {
  const current = getPageDefinition(page);

  return (
    <header className="training-topbar">
      <div>
        <p className="training-topbar__path">KNOWLEDGE HUB / {current.label}</p>
        <h2>{current.title}</h2>
      </div>
      <div className="training-topbar__actions">
        <button type="button" className="training-topbar__search" aria-label="搜索题库" onClick={() => onNavigate("bank")}>
          <Search size={16} aria-hidden="true" />
          <span>搜索题库</span>
        </button>
        <div className="training-topbar__status" role="status" aria-live="polite">
          {apiState === "checking" && <StatusBadge tone="neutral">连接中</StatusBadge>}
          {apiState === "online" && (
            <StatusBadge tone="success">
              API 在线 · {questionCount} 题{demoMode ? " · Demo" : ""}
            </StatusBadge>
          )}
          {apiState === "offline" && (
            <>
              <StatusBadge tone="danger">服务未连接</StatusBadge>
              <button type="button" className="training-topbar__retry" onClick={onReconnect}>
                重新连接
              </button>
            </>
          )}
        </div>
        <div className="training-topbar__account">
          <span title={identity.email}>{identity.email}</span>
          <button type="button" onClick={onLogout}>退出登录</button>
        </div>
      </div>
    </header>
  );
}
