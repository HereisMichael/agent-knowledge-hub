import type { ReactNode } from "react";

export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";

export function StatusBadge({ tone, children }: { tone: StatusTone; children: ReactNode }) {
  return (
    <span className="ui-status-badge" data-tone={tone}>
      <span className="ui-status-badge__dot" aria-hidden="true" />
      {children}
    </span>
  );
}
