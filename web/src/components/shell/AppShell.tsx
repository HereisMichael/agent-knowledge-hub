import { Gauge, LibraryBig, ListChecks, Menu, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import type { UserIdentity } from "../../api";
import { NAV_SECTIONS, type PageId } from "../../navigation";
import { PrimaryNavigation } from "./PrimaryNavigation";
import { TopStatusBar, type ApiState } from "./TopStatusBar";

export function AppShell({
  page,
  apiState,
  questionCount,
  demoMode,
  identity,
  onNavigate,
  onReconnect,
  onLogout,
  children,
}: {
  page: PageId;
  apiState: ApiState;
  questionCount: number;
  demoMode: boolean;
  identity: UserIdentity;
  onNavigate: (page: PageId) => void;
  onReconnect: () => void;
  onLogout: () => void;
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    if (!moreOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMoreOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [moreOpen]);

  const navigate = (next: PageId) => {
    setMoreOpen(false);
    onNavigate(next);
  };

  return (
    <div className="training-shell" data-collapsed={collapsed}>
      <aside className="training-shell__sidebar">
        <div className="training-brand">
          <span className="training-brand__mark" aria-hidden="true">K</span>
          {!collapsed && (
            <div><strong>Knowledge Hub</strong><span>AI ENGINEERING CONSOLE</span></div>
          )}
        </div>
        <PrimaryNavigation
          page={page}
          collapsed={collapsed}
          isAdmin={identity.role === "admin"}
          onNavigate={navigate}
          onToggle={() => setCollapsed((value) => !value)}
        />
      </aside>

      <div className="training-shell__workspace">
        <TopStatusBar
          page={page}
          apiState={apiState}
          questionCount={questionCount}
          demoMode={demoMode}
          identity={identity}
          onNavigate={navigate}
          onReconnect={onReconnect}
          onLogout={onLogout}
        />
        <main className="training-shell__content">{children}</main>
      </div>

      <nav className="training-mobile-nav" aria-label="移动导航">
        <button type="button" aria-label="打开今日训练（移动导航）" data-active={page === "dashboard"} onClick={() => navigate("dashboard")}><Gauge aria-hidden="true" /><span>今日</span></button>
        <button type="button" aria-label="打开刷题（移动导航）" data-active={page === "quiz"} onClick={() => navigate("quiz")}><ListChecks aria-hidden="true" /><span>刷题</span></button>
        <button type="button" aria-label="打开题库（移动导航）" data-active={page === "bank"} onClick={() => navigate("bank")}><LibraryBig aria-hidden="true" /><span>题库</span></button>
        <button type="button" aria-label="打开更多导航" aria-expanded={moreOpen} aria-controls="training-mobile-more" onClick={() => setMoreOpen((value) => !value)}>{moreOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}<span>更多</span></button>
      </nav>

      {moreOpen && (
        <div id="training-mobile-more" className="training-mobile-more" role="dialog" aria-label="更多导航">
          {NAV_SECTIONS.slice(1)
            .flatMap((section) => section.items)
            .filter((item) => identity.role === "admin" || item.id !== "review")
            .map((item) => (
            <button key={item.id} type="button" onClick={() => navigate(item.id)}>{item.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}
