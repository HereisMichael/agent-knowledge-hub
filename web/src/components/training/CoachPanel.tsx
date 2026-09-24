import type { ReactNode } from "react";
import { Panel } from "../ui/Panel";

export function CoachPanel({
  title,
  status,
  children,
}: {
  title: string;
  status?: ReactNode;
  children: ReactNode;
}) {
  return <Panel className="coach-panel" title={title} actions={status}>{children}</Panel>;
}
