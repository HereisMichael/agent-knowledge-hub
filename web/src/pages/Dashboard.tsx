import { useEffect, useState } from "react";
import { ArrowRight, RotateCw } from "lucide-react";
import type { PageId } from "../navigation";
import { buildDashboardModel, loadDashboardSources, type DashboardSources } from "../dashboard/model";
import { FeedbackState } from "../components/ui/FeedbackState";
import { MetricTile } from "../components/ui/MetricTile";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { SignalLine } from "../components/ui/SignalLine";
import { StatusBadge } from "../components/ui/StatusBadge";
import { TrainingTaskCard } from "../components/training/TrainingTaskCard";

export function DashboardPage({
  onNavigate,
  loader = loadDashboardSources,
}: {
  onNavigate: (page: PageId) => void;
  loader?: () => Promise<DashboardSources>;
}) {
  const [sources, setSources] = useState<DashboardSources>();
  const [loadError, setLoadError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoadError(false);
    loader()
      .then((data) => active && setSources(data))
      .catch(() => active && setLoadError(true));
    return () => { active = false; };
  }, [loader, reloadKey]);

  if (loadError) {
    return (
      <FeedbackState
        kind="error"
        title="训练台暂时无法载入"
        description="本地服务可能尚未启动，请稍后重试。"
        action={<button type="button" className="btn btn-primary" onClick={() => setReloadKey((key) => key + 1)}>重新载入</button>}
      />
    );
  }
  if (!sources) {
    return <FeedbackState kind="loading" title="正在组织今日训练" description="正在读取题库、复习队列与能力信号。" />;
  }

  const model = buildDashboardModel(sources);
  const primaryTask = model.tasks[0];
  return (
    <div className="dashboard-page">
      <PageHeader
        eyebrow="MISSION CONTROL"
        title="把薄弱点变成今天的训练队列"
        description="基于正式题库、到期复习和能力记录生成一组可以马上执行的任务。"
        actions={
          <>
            {model.partialFailure && <StatusBadge tone="warning">部分数据暂不可用</StatusBadge>}
            {model.resume && (
              <button type="button" className="btn btn-quiet" onClick={() => onNavigate(model.resume!.target)}>
                {model.resume.label} <ArrowRight size={15} aria-hidden="true" />
              </button>
            )}
          </>
        }
      />

      <section className="dashboard-metrics" aria-label="训练概况">
        {model.metrics.map((metric) => <MetricTile key={metric.label} {...metric} />)}
      </section>

      <section className="dashboard-grid">
        <Panel
          className="dashboard-queue"
          eyebrow="TRAINING QUEUE"
          title="今日任务"
          actions={model.partialFailure ? <button type="button" className="btn btn-icon" aria-label="刷新训练数据" onClick={() => setReloadKey((key) => key + 1)}><RotateCw size={16} /></button> : undefined}
        >
          <div className="training-task-list">
            {model.tasks.map((task, index) => <TrainingTaskCard key={task.id} task={task} index={index} onStart={onNavigate} />)}
          </div>
          {primaryTask && (
            <button type="button" className="btn btn-primary dashboard-start" onClick={() => onNavigate(primaryTask.target)}>
              开始今日训练 <ArrowRight size={17} aria-hidden="true" />
            </button>
          )}
        </Panel>

        <Panel className="dashboard-signals" eyebrow="SKILL SIGNALS" title="能力信号">
          {model.signals.length ? (
            <div className="skill-signal-list">
              {model.signals.map((signal) => (
                <div className="skill-signal" key={signal.id}>
                  <div><span>{signal.label}</span><strong>{Math.round(signal.value)}</strong></div>
                  <span className="skill-signal__track"><span style={{ width: `${Math.max(0, Math.min(100, signal.value))}%` }} /></span>
                </div>
              ))}
            </div>
          ) : (
            <FeedbackState kind="empty" title="等待首个能力信号" description="完成一次技能测评或刷题后，这里会显示需要优先加强的能力。" />
          )}
        </Panel>

        <Panel className="dashboard-route" eyebrow="TODAY ROUTE" title="训练路径">
          <SignalLine steps={model.tasks.map((task) => ({ id: task.id, label: task.label, detail: task.reason, status: task.status }))} />
        </Panel>
      </section>
    </div>
  );
}
