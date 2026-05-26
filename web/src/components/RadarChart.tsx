type Axis = { axis: string; value: number; detail?: string };

const LABELS: Record<string, string> = {
  architecture: "架构",
  product: "产品",
  behavior: "行为",
  solution: "方案",
  agent: "Agent",
  structure: "结构",
  depth: "深度",
  tradeoff: "权衡",
  compliance: "合规",
  communication: "表达",
};

function label(axis: string) {
  return LABELS[axis] ?? axis;
}

export function RadarChart({
  axes,
  max = 100,
  size = 220,
}: {
  axes: Axis[];
  max?: number;
  size?: number;
}) {
  if (!axes.length) return null;
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;
  const n = axes.length;
  const angleStep = (2 * Math.PI) / n;

  const point = (i: number, ratio: number) => {
    const a = -Math.PI / 2 + i * angleStep;
    return [cx + r * ratio * Math.cos(a), cy + r * ratio * Math.sin(a)];
  };

  const gridLevels = [0.25, 0.5, 0.75, 1];
  const dataPoints = axes.map((a, i) => {
    const ratio = Math.min(1, Math.max(0, a.value / max));
    return point(i, ratio);
  });
  const poly = dataPoints.map(([x, y]) => `${x},${y}`).join(" ");

  return (
    <svg
      className="radar-chart"
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      role="img"
      aria-label="进度雷达图"
    >
      {gridLevels.map((lv) => (
        <polygon
          key={lv}
          points={axes
            .map((_, i) => {
              const [x, y] = point(i, lv);
              return `${x},${y}`;
            })
            .join(" ")}
          fill="none"
          stroke="var(--border)"
          strokeWidth="1"
        />
      ))}
      {axes.map((a, i) => {
        const [x, y] = point(i, 1);
        const [lx, ly] = point(i, 1.18);
        return (
          <g key={a.axis}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="var(--border)" strokeWidth="1" />
            <text
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              className="radar-label"
            >
              {label(a.axis)}
            </text>
          </g>
        );
      })}
      <polygon points={poly} fill="var(--accent-subtle)" stroke="var(--accent)" strokeWidth="2" />
      {dataPoints.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3" fill="var(--accent)" />
      ))}
    </svg>
  );
}
