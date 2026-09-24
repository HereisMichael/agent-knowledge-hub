import type { ReactNode } from "react";

export function FeedbackState({
  kind,
  title,
  description,
  action,
}: {
  kind: "loading" | "empty" | "error";
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <section
      className="ui-feedback-state"
      data-kind={kind}
      role={kind === "error" ? "alert" : undefined}
      aria-busy={kind === "loading" ? true : undefined}
    >
      <span className="ui-feedback-state__signal" aria-hidden="true" />
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
        {action && <div className="ui-feedback-state__action">{action}</div>}
      </div>
    </section>
  );
}
