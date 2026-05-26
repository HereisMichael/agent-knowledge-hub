import { useEffect, useState } from "react";
import { health } from "./api";
import { ContentReviewPage } from "./pages/ContentReview";
import { LabsPage } from "./pages/Labs";
import { LearnPage } from "./pages/Learn";
import { MockPage } from "./pages/Mock";
import { ProgressPage } from "./pages/Progress";
import { QuizPage } from "./pages/Quiz";

type Tab = "learn" | "quiz" | "mock" | "labs" | "progress" | "review";

const TABS: { id: Tab; label: string; title: string }[] = [
  { id: "learn", label: "学习", title: "知识问答" },
  { id: "quiz", label: "刷题", title: "SA 题库" },
  { id: "mock", label: "模拟面试", title: "模拟面试" },
  { id: "labs", label: "实操 Lab", title: "实操 Lab" },
  { id: "progress", label: "进度", title: "学习进度" },
  { id: "review", label: "内容审核", title: "内容审核" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("learn");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [meta, setMeta] = useState({ questions: 0, demo: false });

  useEffect(() => {
    health()
      .then((h) => {
        setApiOk(true);
        setMeta({ questions: h.questions ?? 0, demo: !!h.demo_mode });
      })
      .catch(() => setApiOk(false));
  }, []);

  const current = TABS.find((t) => t.id === tab)!;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1 className="brand-title">Knowledge Hub</h1>
          <p className="brand-sub">
            Agent 技术 · 云 SA 面试
          </p>
        </div>
        <nav aria-label="主导航">
          <ul className="nav-list">
            {TABS.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  className={`nav-item${tab === t.id ? " active" : ""}`}
                  onClick={() => setTab(t.id)}
                >
                  {t.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <h2 className="page-title">{current.title}</h2>
          <div
            className={`status-pill${apiOk === true ? " ok" : apiOk === false ? " err" : ""}`}
            title={apiOk === false ? "请启动 backend :8001" : undefined}
          >
            <span className="status-dot" aria-hidden />
            {apiOk === null && "连接中…"}
            {apiOk === true && (
              <>
                已连接 · {meta.questions} 题
                {meta.demo ? " · Demo" : ""}
              </>
            )}
            {apiOk === false && "API 未连接"}
          </div>
        </header>

        <div className="content">
          {tab === "learn" && <LearnPage />}
          {tab === "quiz" && <QuizPage />}
          {tab === "mock" && <MockPage />}
          {tab === "labs" && <LabsPage />}
          {tab === "progress" && <ProgressPage />}
          {tab === "review" && <ContentReviewPage />}
        </div>
      </div>
    </div>
  );
}
