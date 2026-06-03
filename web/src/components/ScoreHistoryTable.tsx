type Row = {
  question_id: string;
  question: string;
  category: string;
  vendor: string;
  attempts: number;
  first_score: number;
  last_score: number;
  best_score: number;
  avg_score: number;
  trend: string;
  has_reference: boolean;
};

const TREND_LABEL: Record<string, string> = {
  up: "↑ 进步",
  down: "↓ 回落",
  stable: "→ 稳定",
  new: "新题",
};

const VENDOR: Record<string, string> = {
  aliyun: "阿里云",
  tencent: "腾讯云",
  aws: "AWS",
};

export function ScoreHistoryTable({ rows }: { rows: Row[] }) {
  if (!rows.length) {
    return <p className="empty-hint">暂无作答记录，请先在「刷题」中练习</p>;
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>题目</th>
            <th>厂商</th>
            <th>分类</th>
            <th>次数</th>
            <th>首次</th>
            <th>最近</th>
            <th>最佳</th>
            <th>均分</th>
            <th>趋势</th>
            <th>参考答案</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.question_id}>
              <td className="cell-question" title={r.question}>
                {r.question}
              </td>
              <td>{VENDOR[r.vendor] ?? r.vendor}</td>
              <td>{r.category}</td>
              <td>{r.attempts}</td>
              <td>{r.first_score}</td>
              <td className={r.last_score >= 70 ? "score-good" : "score-low"}>{r.last_score}</td>
              <td>{r.best_score}</td>
              <td>{r.avg_score}</td>
              <td>
                <span className={`trend trend-${r.trend}`}>{TREND_LABEL[r.trend] ?? r.trend}</span>
              </td>
              <td>{r.has_reference ? "已保存" : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
