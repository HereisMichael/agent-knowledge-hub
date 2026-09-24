import type { ReactNode } from "react";

export function Workbench({
  primary,
  aside,
  asideLabel,
}: {
  primary: ReactNode;
  aside: ReactNode;
  asideLabel: string;
}) {
  return (
    <div className="training-workbench">
      <main className="training-workbench__primary">{primary}</main>
      <aside className="training-workbench__aside" aria-label={asideLabel}>{aside}</aside>
    </div>
  );
}
