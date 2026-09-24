import type { ReactNode } from "react";

export function TabPanel({
  active,
  mounted,
  pageId,
  children,
}: {
  active: boolean;
  mounted: boolean;
  pageId: string;
  children: ReactNode;
}) {
  if (!mounted) return null;
  return (
    <section
      data-testid={`page-${pageId}`}
      className="training-page"
      hidden={!active}
      aria-hidden={!active}
    >
      {children}
    </section>
  );
}
