import { useEffect, useState } from "react";
import { mockCreate, mockFinish, mockMessage, mockReportPdfUrl } from "../api";
import { MockReport, type MockReportData } from "../components/MockReport";

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
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function MockPage() {
  const [mode, setMode] = useState("free");
  const [vendor, setVendor] = useState("aliyun");
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [report, setReport] = useState<MockReportData | null>(null);
  const [timing, setTiming] = useState<StageTiming | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!sessionId || mode !== "structured" || !timing) return;
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, [sessionId, mode, timing?.stage]);

  const remaining =
    timing != null
      ? Math.max(0, timing.remaining_sec - tick)
      : null;
  const urgent = remaining != null && remaining < 60;

  async function start() {
    const s = await mockCreate(mode, vendor, "architecture");
    setSessionId(s.id);
    setMessages(s.transcript || []);
    setTiming(s.stage_timing ?? null);
    setTick(0);
    setReport(null);
  }

  async function send(wantHint = false) {
    if (!sessionId || !input.trim()) return;
    const res = await mockMessage(sessionId, input, wantHint);
    setMessages(res.transcript || []);
    setTiming(res.stage_timing ?? timing);
    setTick(0);
    setInput("");
  }

  async function finish() {
    const s = await mockFinish(sessionId);
    setReport((s.report as MockReportData) || null);
    setMessages(s.transcript || []);
    setTiming(null);
  }

  return (
    <div className="panel">
      <div className="toolbar">
        <div className="field">
          <label htmlFor="mock-mode">模式</label>
          <select id="mock-mode" value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="free">自由多轮</option>
            <option value="structured">结构化流程</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="mock-vendor">厂商</label>
          <select id="mock-vendor" value={vendor} onChange={(e) => setVendor(e.target.value)}>
            <option value="aliyun">阿里云</option>
            <option value="tencent">腾讯云</option>
            <option value="aws">AWS</option>
          </select>
        </div>
        <button type="button" className="btn btn-primary" onClick={start}>
          开始面试
        </button>
        {sessionId && (
          <>
            <button type="button" className="btn btn-ghost" onClick={() => send(true)}>
              要提示
            </button>
            <button type="button" className="btn" onClick={finish}>
              结束并生成报告
            </button>
          </>
        )}
      </div>

      {mode === "structured" && timing && sessionId && !report && (
        <div className="mock-timer-block">
          <div className="mock-stage-steps">
            {timing.stages.map((s, i) => (
              <span
                key={s.id}
                className={`mock-stage-pill ${i === timing.stage_index ? "active" : ""} ${i < timing.stage_index ? "done" : ""}`}
              >
                {s.label}
              </span>
            ))}
          </div>
          <div className={`mock-timer ${urgent ? "urgent" : ""}`}>
            <span className="mock-timer-label">{timing.stage_label}</span>
            <span className="mock-timer-value">{fmt(remaining ?? timing.remaining_sec)}</span>
            <span className="mock-timer-hint">剩余 / {fmt(timing.duration_sec)}</span>
          </div>
          <div className="mock-timer-bar">
            <div
              className="mock-timer-fill"
              style={{
                width: `${Math.min(100, ((timing.duration_sec - (remaining ?? 0)) / timing.duration_sec) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div className="chat-log" role="log" aria-live="polite">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`bubble ${m.role === "interviewer" ? "bubble-interviewer" : "bubble-user"}`}
            >
              <span className="bubble-label">
                {m.role === "interviewer" ? "面试官" : "你"}
              </span>
              {m.content}
            </div>
          ))}
        </div>
      )}

      {sessionId && !report && (
        <>
          <div className="field">
            <label htmlFor="mock-input">你的回答</label>
            <textarea
              id="mock-input"
              rows={3}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入回答，尽量具体、可量化…"
            />
          </div>
          <button type="button" className="btn btn-primary" onClick={() => send(false)}>
            发送
          </button>
        </>
      )}

      {!sessionId && messages.length === 0 && (
        <p className="empty-hint">选择模式与厂商后开始，面试官将逐轮追问</p>
      )}

      {report && (
        <div className="report-block">
          <MockReport
            report={report}
            sessionId={sessionId}
            pdfUrl={mockReportPdfUrl(sessionId)}
          />
        </div>
      )}
    </div>
  );
}
