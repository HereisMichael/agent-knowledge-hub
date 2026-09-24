import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { NAV_SECTIONS, type PageId } from "../../navigation";

export function PrimaryNavigation({
  page,
  collapsed,
  isAdmin,
  onNavigate,
  onToggle,
}: {
  page: PageId;
  collapsed: boolean;
  isAdmin: boolean;
  onNavigate: (page: PageId) => void;
  onToggle: () => void;
}) {
  return (
    <nav className="training-nav" aria-label="主导航">
      <div className="training-nav__sections">
        {NAV_SECTIONS.map((section) => (
          <section className="training-nav__section" key={section.label}>
            <p className="training-nav__label">{collapsed ? "" : section.label}</p>
            <ul>
              {section.items.filter((item) => isAdmin || item.id !== "review").map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className="training-nav__item"
                      data-active={page === item.id}
                      aria-current={page === item.id ? "page" : undefined}
                      aria-label={item.label}
                      title={collapsed ? item.label : undefined}
                      onClick={() => onNavigate(item.id)}
                    >
                      <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                      {!collapsed && <span>{item.label}</span>}
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
      <button
        type="button"
        className="training-nav__collapse"
        aria-label={collapsed ? "展开侧栏" : "收起侧栏"}
        onClick={onToggle}
      >
        {collapsed ? <PanelLeftOpen size={17} aria-hidden="true" /> : <PanelLeftClose size={17} aria-hidden="true" />}
        {!collapsed && <span>收起侧栏</span>}
      </button>
    </nav>
  );
}
