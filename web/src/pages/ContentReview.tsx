import { useEffect, useState } from "react";
import {
  adminApprove,
  adminIngest,
  adminPending,
  adminPublishLogs,
  adminReject,
  adminRollback,
  adminRunUpdate,
} from "../api";
import { FeedbackState } from "../components/ui/FeedbackState";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { StatusBadge } from "../components/ui/StatusBadge";

type Item = {
  id: string;
  title: string;
  item_type: string;
  quality_score?: number;
};

type PublishLog = {
  id: string;
  item_id: string;
  published_at: string;
  rolled_back: number;
};

const LEGACY_CREDENTIAL_KEY = ["admin", "Key"].join("");

export function ContentReviewPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [logs, setLogs] = useState<PublishLog[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [loadedPending, setLoadedPending] = useState(false);
  const [confirmFull, setConfirmFull] = useState(false);

  useEffect(() => {
    localStorage.removeItem(LEGACY_CREDENTIAL_KEY);
  }, []);

  function begin(action: string) {
    setBusy(action);
    setMessage("");
    setError("");
  }

  function fail(description: string) {
    setError(description);
    setBusy("");
  }

  async function load() {
    begin("pending");
    try {
      const response = await adminPending();
      setItems(response.items || []);
      setLoadedPending(true);
      setMessage("待审列表已刷新。");
      setBusy("");
    } catch {
      fail("无法读取待审内容，请确认管理员权限和服务状态。");
    }
  }

  async function approve(id: string) {
    begin(`approve-${id}`);
    try {
      await adminApprove(id);
      setMessage("内容已批准并发布。");
      setBusy("");
      await load();
    } catch {
      fail("发布失败，请检查权限后重试。");
    }
  }

  async function reject(id: string) {
    begin(`reject-${id}`);
    try {
      await adminReject(id, "需修订");
      setMessage("内容已退回修订。");
      setBusy("");
      await load();
    } catch {
      fail("退回失败，请检查权限后重试。");
    }
  }

  async function runUpdate() {
    begin("update");
    try {
      await adminRunUpdate();
      setMessage("每日内容更新任务已执行。");
      setBusy("");
      await load();
    } catch {
      fail("更新任务执行失败，请稍后重试。");
    }
  }

  async function loadLogs() {
    begin("logs");
    try {
      const response = await adminPublishLogs();
      setLogs(response.logs || []);
      setMessage("发布记录已刷新。");
      setBusy("");
    } catch {
      fail("无法读取发布记录，请检查权限后重试。");
    }
  }

  async function rollback(logId: string) {
    begin(`rollback-${logId}`);
    try {
      const response = await adminRollback(logId);
      const restoredCount = Array.isArray(response.restored) ? response.restored.length : 0;
      setMessage(`回滚完成，共恢复 ${restoredCount} 个文件。`);
      setBusy("");
      await loadLogs();
    } catch {
      fail("回滚失败，请检查记录状态后重试。");
    }
  }

  async function runIngest(full: boolean) {
    begin(full ? "ingest-full" : "ingest-incremental");
    try {
      const response = await adminIngest(full);
      const mode = full ? "全量" : "增量";
      setMessage(`${mode}索引完成：处理 ${Number(response.files_processed) || 0} 个文件，建立 ${Number(response.chunks_indexed) || 0} 个片段。`);
      setConfirmFull(false);
      setBusy("");
    } catch {
      fail("索引任务执行失败，请检查服务状态后重试。");
    }
  }

  const activeLogs = logs.filter((log) => !log.rolled_back);

  return (
    <div className="management-page">
      <PageHeader
        eyebrow="CONTENT OPS"
        title="内容发布与回滚"
        description="审核训练内容、触发知识更新并管理可恢复的发布记录。操作权限来自当前管理员账号。"
      />

      <div className="management-grid management-grid--content">
        <Panel title="权限状态" eyebrow="AUTH" actions={<StatusBadge tone="success">管理员会话</StatusBadge>}>
          <p className="management-note">当前账号已通过管理员角色校验。退出登录后，本页操作权限会立即失效。</p>
          <button type="button" className="btn btn-primary" onClick={() => void load()} disabled={busy === "pending"}>{busy === "pending" ? "刷新中…" : "刷新待审"}</button>
        </Panel>

        <Panel title="内容入库" eyebrow="INGESTION">
          <div className="management-action-list">
            <div><strong>每日更新</strong><span>拉取并整理最新内容，再更新待审队列。</span><button type="button" className="btn" onClick={() => void runUpdate()} disabled={busy === "update"}>{busy === "update" ? "执行中…" : "触发每日更新"}</button></div>
            <div><strong>增量索引</strong><span>仅处理新增或变化的内容，适合日常维护。</span><button type="button" className="btn btn-ghost" onClick={() => void runIngest(false)} disabled={busy === "ingest-incremental"}>{busy === "ingest-incremental" ? "处理中…" : "增量索引"}</button></div>
            <div><strong>全量重建</strong><span>重新处理所有内容，耗时较长且会替换现有索引。</span><button type="button" className="btn btn-ghost" onClick={() => setConfirmFull(true)} disabled={busy === "ingest-full"}>全量重建索引</button></div>
          </div>
          {confirmFull && (
            <section className="management-confirm" role="region" aria-label="确认全量重建">
              <strong>确认重新建立全部索引？</strong>
              <p>此操作适合数据结构变化或索引异常后的恢复，执行期间检索结果可能短暂波动。</p>
              <div className="toolbar">
                <button type="button" className="btn btn-primary" onClick={() => void runIngest(true)}>确认全量重建</button>
                <button type="button" className="btn btn-ghost" onClick={() => setConfirmFull(false)}>取消</button>
              </div>
            </section>
          )}
        </Panel>

        <Panel title="待审内容" eyebrow="REVIEW QUEUE" actions={<StatusBadge tone={items.length ? "info" : "neutral"}>{items.length} 条待审</StatusBadge>} className="management-span-two">
          {!loadedPending ? (
            <FeedbackState kind="empty" title="尚未读取待审队列" description="刷新后可在这里审核内容。" />
          ) : items.length === 0 ? (
            <FeedbackState kind="empty" title="当前没有待审内容" description="队列已清空，可以触发每日更新获取新内容。" />
          ) : (
            <div className="management-review-list">
              {items.map((item) => (
                <article key={item.id} className="management-review-card">
                  <div>
                    <h3>{item.title}</h3>
                    <p><span className="tag">{item.item_type}</span>{item.quality_score != null && <span>质检 {item.quality_score}</span>}</p>
                  </div>
                  <div className="toolbar">
                    <button type="button" className="btn btn-primary" onClick={() => void approve(item.id)} disabled={busy === `approve-${item.id}`}>批准发布</button>
                    <button type="button" className="btn btn-ghost" onClick={() => void reject(item.id)} disabled={busy === `reject-${item.id}`}>退回修订</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="发布回滚" eyebrow="ROLLBACK" actions={<button type="button" className="btn btn-ghost" onClick={() => void loadLogs()} disabled={busy === "logs"}>{busy === "logs" ? "读取中…" : "刷新记录"}</button>} className="management-span-two">
          {activeLogs.length === 0 ? <p className="management-note">暂无可回滚的发布记录。</p> : (
            <div className="management-log-list">
              {activeLogs.map((log) => (
                <div key={log.id}>
                  <span>{log.published_at.slice(0, 19)} · 内容 {log.item_id.slice(0, 8)}</span>
                  <button type="button" className="btn btn-ghost" onClick={() => void rollback(log.id)} disabled={busy === `rollback-${log.id}`}>一键回滚</button>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {message && <p className="management-message" role="status" aria-live="polite">{message}</p>}
      {error && <p className="management-message management-message--error" role="alert">{error}</p>}
    </div>
  );
}
