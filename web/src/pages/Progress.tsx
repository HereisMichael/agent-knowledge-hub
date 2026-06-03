import { useEffect, useState } from "react";
import { progressRadar, quizAnalytics, quizStats } from "../api";
import { RadarChart } from "../components/RadarChart";
import { ReviewCalendar } from "../components/ReviewCalendar";
import { ScoreHistoryTable } from "../components/ScoreHistoryTable";

const VENDOR_LABEL: Record<string, string> = {
  aliyun: "阿里云",
  tencent: "腾讯云",
  aws: "AWS",
};

type RadarData = {
  quiz: { axes: { axis: string; value: number; detail?: string }[] };
  mock: { axes: { axis: string; value: number }[] };
};

export function ProgressPage() {
  const [stats, setStats] = useState<{
    total_attempts: number;
    avg_score: number;
    by_vendor: Record<string, number>;
    review?: { total_cards: number; due_now: number };
  } | null>(null);
  const [radar, setRadar] = useState<RadarData | null>(null);
  const [analytics, setAnalytics] = useState<{
    summary: {
      total_attempts: number;
      questions_practiced: number;
      overall_avg: number;
      by_category: Record<string, number>;
      by_vendor: Record<string, number>;
    };
    questions: Parameters<typeof ScoreHistoryTable>[0]["rows"];
  } | null>(null);

  useEffect(() => {
    quizStats().then(setStats).catch(() => {});
    progressRadar().then(setRadar).catch(() => {});
    quizAnalytics().then(setAnalytics).catch(() => {});
  }, []);

  if (!stats) {
    return (
      <div className="panel">
        <p className="empty-hint">加载中…</p>
      </div>
    );
  }

  return (
    <>
      <div className="stat-grid">
        <div className="stat">
          <div className="stat-value">{stats.total_attempts}</div>
          <div className="stat-label">作答次数</div>
        </div>
        <div className="stat">
          <div className="stat-value">{stats.avg_score}</div>
          <div className="stat-label">平均得分</div>
        </div>
        {stats.review && (
          <>
            <div className="stat">
              <div className="stat-value">{stats.review.due_now}</div>
              <div className="stat-label">待复习</div>
            </div>
            <div className="stat">
              <div className="stat-value">{stats.review.total_cards}</div>
              <div className="stat-label">复习卡片</div>
            </div>
          </>
        )}
      </div>

      {analytics && (
        <div className="panel">
          <h3 className="panel-header">答题水平（按题目）</h3>
          <p className="empty-hint" style={{ marginBottom: "0.75rem" }}>
            已练 {analytics.summary.questions_practiced} 题 · 总作答{" "}
            {analytics.summary.total_attempts} 次 · 均分 {analytics.summary.overall_avg}
          </p>
          <ScoreHistoryTable rows={analytics.questions} />
        </div>
      )}

      <div className="panel">
        <h3 className="panel-header">复习日历（SM-2）</h3>
        <ReviewCalendar />
      </div>

      {radar && (
        <div className="panel radar-panel">
          <h3 className="panel-header">能力雷达</h3>
          <div className="radar-grid">
            <div className="radar-cell">
              <h4>刷题覆盖（%）</h4>
              <RadarChart axes={radar.quiz.axes} max={100} />
              <ul className="radar-legend">
                {radar.quiz.axes.map((a) => (
                  <li key={a.axis}>
                    <span>{a.axis}</span>
                    <span>
                      {a.value}% {a.detail ? `(${a.detail})` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="radar-cell">
              <h4>模拟面试均分</h4>
              <RadarChart axes={radar.mock.axes} max={100} />
            </div>
          </div>
        </div>
      )}

      <div className="panel">
        <h3 className="panel-header">题库覆盖</h3>
        <ul className="vendor-list">
          {Object.entries(stats.by_vendor || {}).map(([v, n]) => (
            <li key={v}>
              <span>{VENDOR_LABEL[v] ?? v}</span>
              <span>{n} 题</span>
            </li>
          ))}
        </ul>
        <p className="empty-hint" style={{ marginTop: "1.25rem" }}>
          模拟面试报告在「模拟面试」结束后可下载 PDF。
        </p>
      </div>
    </>
  );
}
