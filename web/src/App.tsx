import { lazy, Suspense, useCallback, useEffect, useState, type ReactNode } from "react";
import {
  getCurrentUser,
  health,
  logout,
  type UserIdentity,
} from "./api";
import { AppShell } from "./components/shell/AppShell";
import type { ApiState } from "./components/shell/TopStatusBar";
import { TabPanel } from "./components/TabPanel";
import type { PageId } from "./navigation";
import { AuthPage } from "./pages/Auth";
import { bindLocalUserDataOwner, clearLocalUserData } from "./privacy/localData";

const DashboardPage = lazy(() => import("./pages/Dashboard").then((module) => ({ default: module.DashboardPage })));
const LearnPage = lazy(() => import("./pages/Learn").then((module) => ({ default: module.LearnPage })));
const QuizPage = lazy(() => import("./pages/Quiz").then((module) => ({ default: module.QuizPage })));
const ExercisesPage = lazy(() => import("./pages/Exercises").then((module) => ({ default: module.ExercisesPage })));
const QuestionBankPage = lazy(() => import("./pages/QuestionBank").then((module) => ({ default: module.QuestionBankPage })));
const MockPage = lazy(() => import("./pages/Mock").then((module) => ({ default: module.MockPage })));
const LabsPage = lazy(() => import("./pages/Labs").then((module) => ({ default: module.LabsPage })));
const SkillAssessmentPage = lazy(() => import("./pages/SkillAssessment").then((module) => ({ default: module.SkillAssessmentPage })));
const ProgressPage = lazy(() => import("./pages/Progress").then((module) => ({ default: module.ProgressPage })));
const JDAnalysisPage = lazy(() => import("./pages/JDAnalysis").then((module) => ({ default: module.JDAnalysisPage })));
const SettingsPage = lazy(() => import("./pages/Settings").then((module) => ({ default: module.SettingsPage })));
const ContentReviewPage = lazy(() => import("./pages/ContentReview").then((module) => ({ default: module.ContentReviewPage })));

const LAST_PAGE_KEY = "akh_last_page_v1";

function PageBoundary({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Suspense fallback={<div className="page-skeleton" role="status" aria-label={`正在加载${label}`}><span /><span /><span /></div>}>
      {children}
    </Suspense>
  );
}

export default function App() {
  const [identity, setIdentity] = useState<UserIdentity | null>(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [authUnavailable, setAuthUnavailable] = useState(false);
  const [page, setPage] = useState<PageId>("dashboard");
  const [targetExerciseId, setTargetExerciseId] = useState("");
  const [visited, setVisited] = useState<Set<PageId>>(() => new Set(["dashboard"]));
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [meta, setMeta] = useState({ questions: 0, demo: false });

  const checkHealth = useCallback(async () => {
    setApiState("checking");
    try {
      const response = await health();
      setMeta({ questions: response.questions ?? 0, demo: !!response.demo_mode });
      setApiState("online");
    } catch {
      setApiState("offline");
    }
  }, []);

  const acceptIdentity = useCallback((user: UserIdentity) => {
    bindLocalUserDataOwner(user.id);
    setIdentity(user);
    setAuthUnavailable(false);
  }, []);

  const checkSession = useCallback(() => {
    let active = true;
    setAuthChecking(true);
    getCurrentUser()
      .then((response) => {
        if (active) acceptIdentity(response.user);
      })
      .catch((error) => {
        if (active) {
          if ((error as { status?: unknown })?.status === 401) {
            clearLocalUserData();
            setAuthUnavailable(false);
          } else {
            setAuthUnavailable(true);
          }
          setIdentity(null);
        }
      })
      .finally(() => {
        if (active) setAuthChecking(false);
      });
    return () => {
      active = false;
    };
  }, [acceptIdentity]);

  useEffect(() => checkSession(), [checkSession]);

  useEffect(() => {
    if (identity) void checkHealth();
  }, [checkHealth, identity]);

  const navigate = useCallback((next: PageId) => {
    setVisited((current) => {
      if (current.has(next)) return current;
      const updated = new Set(current);
      updated.add(next);
      return updated;
    });
    if (next !== "dashboard") {
      try {
        localStorage.setItem(LAST_PAGE_KEY, next);
      } catch {
        // Navigation remains usable when browser storage is unavailable.
      }
    }
    setPage(next);
  }, []);

  const openExercise = useCallback((id: string) => {
    setTargetExerciseId(id);
    navigate("exercises");
  }, [navigate]);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } finally {
      clearLocalUserData();
      setIdentity(null);
      setApiState("checking");
      setMeta({ questions: 0, demo: false });
    }
  }, []);

  if (authChecking) {
    return (
      <main className="auth-gate auth-gate--loading" aria-busy="true">
        <div className="page-skeleton" role="status" aria-label="正在确认登录状态">
          <span /><span /><span />
        </div>
      </main>
    );
  }

  if (!identity) {
    if (authUnavailable) {
      return (
        <main className="auth-gate auth-gate--loading">
          <section className="auth-gate__panel" aria-labelledby="offline-auth-title">
            <p className="auth-gate__eyebrow">CONNECTION PAUSED</p>
            <h1 id="offline-auth-title">暂时无法确认登录状态</h1>
            <p>服务当前不可用。为保护这台设备上的个人练习记录，恢复连接前不会开放其他账号登录。</p>
            <button className="btn btn-primary" type="button" onClick={() => checkSession()}>
              重新连接
            </button>
          </section>
        </main>
      );
    }
    return <AuthPage onAuthenticated={acceptIdentity} />;
  }

  return (
    <AppShell
      page={page}
      apiState={apiState}
      questionCount={meta.questions}
      demoMode={meta.demo}
      identity={identity}
      onNavigate={navigate}
      onReconnect={() => void checkHealth()}
      onLogout={() => void signOut()}
    >
      <TabPanel pageId="dashboard" active={page === "dashboard"} mounted={visited.has("dashboard")}>
        <PageBoundary label="今日训练"><DashboardPage onNavigate={navigate} /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="learn" active={page === "learn"} mounted={visited.has("learn")}>
        <PageBoundary label="知识问答"><LearnPage /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="quiz" active={page === "quiz"} mounted={visited.has("quiz")}>
        <PageBoundary label="刷题"><QuizPage /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="exercises" active={page === "exercises"} mounted={visited.has("exercises")}>
        <PageBoundary label="LLM 练习"><ExercisesPage onNavigate={navigate} targetExerciseId={targetExerciseId} /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="bank" active={page === "bank"} mounted={visited.has("bank")}>
        <PageBoundary label="题库"><QuestionBankPage /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="mock" active={page === "mock"} mounted={visited.has("mock")}>
        <PageBoundary label="模拟面试"><MockPage /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="labs" active={page === "labs"} mounted={visited.has("labs")}>
        <PageBoundary label="实操 Lab"><LabsPage onOpenExercise={openExercise} /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="assess" active={page === "assess"} mounted={visited.has("assess")}>
        <PageBoundary label="技能测评"><SkillAssessmentPage /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="progress" active={page === "progress"} mounted={visited.has("progress")}>
        <PageBoundary label="学习进度"><ProgressPage /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="jd" active={page === "jd"} mounted={visited.has("jd")}>
        <PageBoundary label="JD 分析"><JDAnalysisPage /></PageBoundary>
      </TabPanel>
      <TabPanel pageId="settings" active={page === "settings"} mounted={visited.has("settings")}>
        <PageBoundary label="模型设置">
          <SettingsPage
            onAccountDeleted={() => {
              clearLocalUserData();
              setIdentity(null);
              setApiState("checking");
              setMeta({ questions: 0, demo: false });
            }}
          />
        </PageBoundary>
      </TabPanel>
      <TabPanel pageId="review" active={page === "review"} mounted={visited.has("review")}>
        <PageBoundary label="内容审核"><ContentReviewPage /></PageBoundary>
      </TabPanel>
    </AppShell>
  );
}
