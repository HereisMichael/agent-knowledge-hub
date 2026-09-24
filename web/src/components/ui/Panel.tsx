import type { ReactNode } from "react";

export function Panel({
  title,
  eyebrow,
  actions,
  children,
  className = "",
}: {
  title?: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`ui-panel ${className}`.trim()}>
      {(eyebrow || title || actions) && (
        <header className="ui-panel__header">
          <div>
            {eyebrow && <p className="ui-eyebrow">{eyebrow}</p>}
            {title && <h2 className="ui-panel__title">{title}</h2>}
          </div>
          {actions && <div className="ui-panel__actions">{actions}</div>}
        </header>
      )}
      <div className="ui-panel__body">{children}</div>
    </section>
  );
}
