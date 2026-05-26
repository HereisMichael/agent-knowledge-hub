type Scores = Record<string, number>;

type Lab = { id: string; title?: string; description?: string };

export type MockReportData = {
  scores?: Scores;
  highlights?: string[];
  gaps?: string[];
  answer_rewrite?: string;
  suggested_lab_ids?: string[];
  recommended_labs?: Lab[];
};

const SCORE_LABELS: Record<string, string> = {
  structure: "结构",
  depth: "深度",
  tradeoff: "权衡",
  compliance: "合规",
  communication: "表达",
};

export function MockReport({
  report,
  sessionId,
  pdfUrl,
}: {
  report: MockReportData;
  sessionId: string;
  pdfUrl: string;
}) {
  const scores = report.scores ?? {};
  const scoreEntries = Object.entries(scores);
  const avg =
    scoreEntries.length > 0
      ? Math.round(scoreEntries.reduce((a, [, v]) => a + v, 0) / scoreEntries.length)
      : null;
  const labs = report.recommended_labs ?? [];

  return (
    <div className="mock-report">
      <div className="mock-report-header">
        <div>
          <h3 className="mock-report-title">面试报告</h3>
          <p className="mock-report-meta">会话 {sessionId.slice(0, 8)}</p>
        </div>
        {avg != null && (
          <div className="mock-report-overall" aria-label={`综合约 ${avg} 分`}>
            <span className="mock-report-overall-value">{avg}</span>
            <span className="mock-report-overall-label">综合估分</span>
          </div>
        )}
        <a className="btn btn-ghost" href={pdfUrl} download>
          下载 PDF
        </a>
      </div>

      {scoreEntries.length > 0 && (
        <section className="mock-report-section">
          <h4>维度得分</h4>
          <div className="score-bars">
            {scoreEntries.map(([key, val]) => (
              <div key={key} className="score-bar-row">
                <span className="score-bar-label">{SCORE_LABELS[key] ?? key}</span>
                <div className="score-bar-track">
                  <div
                    className="score-bar-fill"
                    style={{ width: `${Math.min(100, val)}%` }}
                  />
                </div>
                <span className="score-bar-value">{val}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="mock-report-columns">
        {report.highlights && report.highlights.length > 0 && (
          <section className="mock-report-section mock-report-good">
            <h4>亮点</h4>
            <ul>
              {report.highlights.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
          </section>
        )}
        {report.gaps && report.gaps.length > 0 && (
          <section className="mock-report-section mock-report-gap">
            <h4>待加强</h4>
            <ul>
              {report.gaps.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {report.answer_rewrite && (
        <section className="mock-report-section mock-report-rewrite">
          <h4>改写建议</h4>
          <p>{report.answer_rewrite}</p>
        </section>
      )}

      {labs.length > 0 && (
        <section className="mock-report-section">
          <h4>推荐 Lab</h4>
          <ul className="mock-report-labs">
            {labs.map((lab) => (
              <li key={lab.id}>
                <span className="tag">{lab.id}</span>
                {lab.title && <span>{lab.title}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
