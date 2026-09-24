import type { StatusTone } from "./StatusBadge";

export function MetricTile({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  detail?: string;
  tone?: StatusTone;
}) {
  return (
    <article className="ui-metric-tile">
      <p className="ui-metric-tile__label">{label}</p>
      <p className="ui-metric-tile__value" data-tone={tone}>{value}</p>
      {detail && <p className="ui-metric-tile__detail">{detail}</p>}
    </article>
  );
}
