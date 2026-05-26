import { useEffect, useState } from "react";
import { ask, contentFeed } from "../api";

export function LearnPage() {
  const [corpus, setCorpus] = useState("all");
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<
    { source_id: string; path?: string; excerpt?: string }[]
  >([]);
  const [feed, setFeed] = useState<{ action: string; title: string; published_at: string }[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    contentFeed().then((d) => setFeed(d.items || [])).catch(() => {});
  }, []);

  async function onAsk() {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const res = await ask(q, corpus);
      setAnswer(res.answer || JSON.stringify(res));
      setCitations(res.citation_details || []);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="split">
      <section>
        <div className="panel">
          <div className="field">
            <label htmlFor="corpus">知识库范围</label>
            <select id="corpus" value={corpus} onChange={(e) => setCorpus(e.target.value)}>
              <option value="all">全部</option>
              <option value="tech">技术（OpenClaw / Hermes / Harness）</option>
              <option value="interview">面试攻略</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="question">你的问题</label>
            <textarea
              id="question"
              rows={4}
              placeholder="例如：OpenClaw Gateway 做什么？Harness 五支柱是什么？"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <button type="button" className="btn btn-primary" onClick={onAsk} disabled={loading}>
            {loading ? "检索中…" : "提问"}
          </button>
        </div>

        {answer && (
          <div className="panel">
            <h3 className="panel-header">回答</h3>
            <p className="prose">{answer}</p>
          </div>
        )}
      </section>

      <aside className="stack">
        <div className="panel">
          <h3 className="panel-header">引用来源</h3>
          {citations.length === 0 && <p className="empty-hint">提交问题后将显示知识库片段</p>}
          {citations.map((c) => (
            <div key={c.source_id} className="citation-item">
              <span className="citation-id">{c.source_id}</span>
              <p className="citation-excerpt">{c.excerpt?.slice(0, 220)}…</p>
            </div>
          ))}
        </div>

        <div className="panel">
          <h3 className="panel-header">最近发布</h3>
          {feed.length === 0 && <p className="empty-hint">暂无发布记录</p>}
          {feed.map((f, i) => (
            <div key={i} className="feed-item">
              <span className="tag">{f.action}</span>
              <span>{f.title}</span>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
