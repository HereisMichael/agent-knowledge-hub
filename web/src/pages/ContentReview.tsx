import { useState } from "react";
import {
  adminApprove,
  adminIngest,
  adminPending,
  adminPublishLogs,
  adminReject,
  adminRollback,
  adminRunUpdate,
} from "../api";

type Item = {
  id: string;
  title: string;
  item_type: string;
  quality_score?: number;
};

export function ContentReviewPage() {
  const [adminKey, setAdminKey] = useState(localStorage.getItem("adminKey") || "");
  const [items, setItems] = useState<Item[]>([]);
  const [msg, setMsg] = useState("");
  const [logs, setLogs] = useState<{ id: string; item_id: string; published_at: string; rolled_back: number }[]>([]);

  async function load() {
    localStorage.setItem("adminKey", adminKey);
    const d = await adminPending(adminKey);
    setItems(d.items || []);
  }

  async function approve(id: string) {
    await adminApprove(adminKey, id);
    setMsg(`已发布：${id}`);
    load();
  }

  async function reject(id: string) {
    await adminReject(adminKey, id, "需修订");
    setMsg(`已驳回：${id}`);
    load();
  }

  async function runUpdate() {
    const r = await adminRunUpdate(adminKey);
    setMsg(r.summary || "更新任务已执行");
    load();
  }

  async function loadLogs() {
    const d = await adminPublishLogs(adminKey);
    setLogs(d.logs || []);
  }

  async function rollback(logId: string) {
    const r = await adminRollback(adminKey, logId);
    setMsg(`已回滚 ${(r.restored as string[])?.length ?? 0} 个文件`);
    loadLogs();
  }

  async function runIngest(full: boolean) {
    const r = await adminIngest(adminKey, full);
    setMsg(
      `${r.mode === "full" ? "全量" : "增量"}索引：${r.chunks_indexed} chunks，` +
        `处理 ${r.files_processed} 文件，跳过 ${r.files_skipped}，删除 ${r.files_removed}`
    );
  }

  return (
    <div className="panel">
      <p className="empty-hint" style={{ marginBottom: "1rem" }}>
        需与 backend `.env` 中 `ADMIN_API_KEY` 一致
      </p>
      <div className="field">
        <label htmlFor="admin-key">管理员密钥</label>
        <input
          id="admin-key"
          type="password"
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
          autoComplete="off"
        />
      </div>
      <div className="toolbar">
        <button type="button" className="btn btn-primary" onClick={load}>
          刷新待审
        </button>
        <button type="button" className="btn" onClick={runUpdate}>
          触发每日更新
        </button>
        <button type="button" className="btn btn-ghost" onClick={loadLogs}>
          发布记录
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => runIngest(false)}>
          增量索引
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => runIngest(true)}>
          全量重建索引
        </button>
      </div>
      {logs.length > 0 && (
        <div className="panel" style={{ marginTop: "1rem" }}>
          <h3 className="panel-header">可回滚发布</h3>
          {logs.filter((l) => !l.rolled_back).map((l) => (
            <div key={l.id} className="toolbar" style={{ justifyContent: "space-between" }}>
              <span className="lab-meta">
                {l.published_at.slice(0, 19)} · {l.item_id.slice(0, 8)}
              </span>
              <button type="button" className="btn btn-ghost" onClick={() => rollback(l.id)}>
                一键回滚
              </button>
            </div>
          ))}
        </div>
      )}
      {msg && <p className="prose" style={{ color: "var(--success)" }}>{msg}</p>}
      {items.length === 0 && <p className="empty-hint">无待审内容</p>}
      {items.map((it) => (
        <article key={it.id} className="lab-card">
          <h4 className="lab-title">{it.title}</h4>
          <p className="lab-meta">
            <span className="tag">{it.item_type}</span>
            {it.quality_score != null && <span>质检 {it.quality_score}</span>}
          </p>
          <div className="toolbar" style={{ marginBottom: 0 }}>
            <button type="button" className="btn btn-primary" onClick={() => approve(it.id)}>
              批准发布
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => reject(it.id)}>
              驳回
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
