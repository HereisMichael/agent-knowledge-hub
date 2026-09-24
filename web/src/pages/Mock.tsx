import { useEffect, useState } from "react";
import { Lightbulb, Send, Square } from "lucide-react";
import { mockCreate, mockFinish, mockMessage, mockReportPdfUrl } from "../api";
import { MockReport, type MockReportData } from "../components/MockReport";
import { CoachPanel } from "../components/training/CoachPanel";
import { Workbench } from "../components/training/Workbench";
import { FeedbackState } from "../components/ui/FeedbackState";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { SignalLine } from "../components/ui/SignalLine";
import { StatusBadge } from "../components/ui/StatusBadge";
import { CLOUD_INTERVIEW_SOURCES, QUESTION_SOURCE_LABELS, type QuestionSource } from "../questions/catalog";

type Msg = { role: string; content: string };
type StageTiming = {
  stage: string;
  stage_label: string;
  duration_sec: number;
  elapsed_sec: number;
  remaining_sec: number;
  stage_index: number;
  total_stages: number;
  stages: { id: string; label: string; duration_sec: number }[];
};

function fmt(sec: number) {
  const minutes = Math.floor(sec / 60);
  return `${minutes}:${(sec % 60).toString().padStart(2, "0")}`;
}

export function MockPage() {
  const [mode, setMode] = useState("free");
  const [vendor, setVendor] = useState<(typeof CLOUD_INTERVIEW_SOURCES)[number]>("aliyun");
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [report, setReport] = useState<MockReportData | null>(null);
  const [timing, setTiming] = useState<StageTiming | null>(null);
  const [tick, setTick] = useState(0);
  const [pending, setPending] = useState<"start" | "send" | "hint" | "finish" | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId || mode !== "structured" || !timing || report) return;
    const id = window.setInterval(() => setTick((value) => value + 1), 1000);
    return () => window.clearInterval(id);
  }, [sessionId, mode, timing?.stage, report]);

  const remaining = timing ? Math.max(0, timing.remaining_sec - tick) : null;
  const urgent = remaining != null && remaining < 60;

  async function start() {
    if (pending) return;
    setPending("start");
    setError("");
    try {
      const session = await mockCreate(mode, vendor, "architecture");
      setSessionId(session.id);
      setMessages(session.transcript || []);
      setTiming(session.stage_timing ?? null);
      setTick(0);
      setReport(null);
      setInput("");
    } catch {
      setError("面试会话创建失败，请检查服务连接后重试。");
    } finally {
      setPending(null);
    }
  }

  async function send(wantHint = false) {
    if (!sessionId || !input.trim() || pending) return;
    setPending(wantHint ? "hint" : "send");
    setError("");
    try {
      const response = await mockMessage(sessionId, input, wantHint);
      setMessages(response.transcript || []);
      setTiming(response.stage_timing ?? timing);
      setTick(0);
      setInput("");
    } catch {
      setError(wantHint ? "提示请求失败，你的回答已保留，可以重试。" : "发送失败，你的回答已保留，可以直接重试。");
    } finally {
      setPending(null);
    }
  }

  async function finish() {
    if (!sessionId || pending) return;
    setPending("finish");
    setError("");
    try {
      const session = await mockFinish(sessionId);
      setReport((session.report as MockReportData) || null);
      setMessages(session.transcript || []);
      setTiming(null);
    } catch {
      setError("面试报告生成失败，会话仍然保留，请重试。");
    } finally {
      setPending(null);
    }
  }

  const transcript = (
    <div className="training-stack">
      {error && <div className="inline-message" data-tone="danger" role="alert">{error}</div>}
      <Panel eyebrow="LIVE INTERVIEW" title="面试对话" actions={sessionId ? <StatusBadge tone={report ? "success" : "info"}>{report ? "已结束" : "进行中"}</StatusBadge> : undefined}>
        {messages.length ? (
          <div className="mock-chat-log" role="log" aria-label="面试对话" aria-live="polite">
            {messages.map((message, index) => (
              <article key={`${message.role}-${index}`} className="mock-message" data-role={message.role === "interviewer" ? "interviewer" : "candidate"}>
                <span>{message.role === "interviewer" ? "面试官" : "你"}</span>
                <p>{message.content}</p>
              </article>
            ))}
          </div>
        ) : <FeedbackState kind="empty" title="等待面试开始" description="配置模式与厂商后，面试官会从第一轮问题开始。" />}
        {sessionId && !report && (
          <div className="mock-composer">
            <div className="field">
              <label htmlFor="mock-input">你的回答</label>
              <textarea id="mock-input" rows={5} value={input} onChange={(event) => setInput(event.target.value)} placeholder="输入回答，尽量具体、可量化…" />
            </div>
            <div className="quiz-action-row">
              <button type="button" className="btn btn-primary" onClick={() => send(false)} disabled={pending !== null || !input.trim()}><Send size={16} aria-hidden="true" />{pending === "send" ? "发送中…" : "发送"}</button>
              <button type="button" className="btn btn-quiet" onClick={() => send(true)} disabled={pending !== null || !input.trim()}><Lightbulb size={16} aria-hidden="true" />{pending === "hint" ? "请求中…" : "要提示"}</button>
            </div>
          </div>
        )}
      </Panel>
      {report && <Panel eyebrow="INTERVIEW REPORT" title="面试报告"><MockReport report={report} sessionId={sessionId} pdfUrl={mockReportPdfUrl(sessionId)} /></Panel>}
    </div>
  );

  const controls = (
    <div className="training-stack">
      <CoachPanel title="会话设置" status={<StatusBadge tone={sessionId ? "success" : "neutral"}>{sessionId ? "已连接" : "未开始"}</StatusBadge>}>
        <div className="field"><label htmlFor="mock-mode">模式</label><select id="mock-mode" value={mode} disabled={Boolean(sessionId && !report)} onChange={(event) => setMode(event.target.value)}><option value="free">自由多轮</option><option value="structured">结构化流程</option></select></div>
        <div className="field"><label htmlFor="mock-vendor">厂商</label><select id="mock-vendor" value={vendor} disabled={Boolean(sessionId && !report)} onChange={(event) => setVendor(event.target.value as typeof vendor)}>{CLOUD_INTERVIEW_SOURCES.map((source) => <option key={source} value={source}>{QUESTION_SOURCE_LABELS[source as QuestionSource]}</option>)}</select></div>
        <button type="button" className="btn btn-primary" onClick={start} disabled={pending !== null || Boolean(sessionId && !report)}>{pending === "start" ? "正在创建…" : "开始面试"}</button>
      </CoachPanel>
      {mode === "structured" && timing && sessionId && !report && (
        <CoachPanel title="阶段进度" status={<StatusBadge tone={urgent ? "warning" : "info"}>{fmt(remaining ?? timing.remaining_sec)}</StatusBadge>}>
          <SignalLine steps={timing.stages.map((stage, index) => ({ id: stage.id, label: stage.label, detail: `${fmt(stage.duration_sec)} 计划时长`, status: index < timing.stage_index ? "complete" : index === timing.stage_index ? "current" : "pending" }))} />
          <div className="mock-timer" data-urgent={urgent}><span>{timing.stage_label}</span><strong>{fmt(remaining ?? timing.remaining_sec)}</strong><small>剩余 / {fmt(timing.duration_sec)}</small></div>
          <div className="mock-timer-track"><span style={{ width: `${Math.min(100, ((timing.duration_sec - (remaining ?? 0)) / timing.duration_sec) * 100)}%` }} /></div>
        </CoachPanel>
      )}
      {sessionId && !report && <button type="button" className="btn btn-quiet mock-finish" onClick={finish} disabled={pending !== null}><Square size={15} aria-hidden="true" />{pending === "finish" ? "生成报告中…" : "结束并生成报告"}</button>}
    </div>
  );

  return <div><PageHeader eyebrow="INTERVIEW SIMULATOR" title="模拟面试" description="在可控节奏里完成多轮追问，输入只会在服务确认成功后清空。" /><Workbench primary={transcript} aside={controls} asideLabel="面试控制台" /></div>;
}
