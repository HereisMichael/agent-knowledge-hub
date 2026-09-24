import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { ask, contentFeed } from "../api";
import { CoachPanel } from "../components/training/CoachPanel";
import { Workbench } from "../components/training/Workbench";
import { FeedbackState } from "../components/ui/FeedbackState";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { StatusBadge } from "../components/ui/StatusBadge";

interface Citation { source_id: string; path?: string; excerpt?: string }
interface FeedItem { action: string; title: string; published_at: string }

export function LearnPage() {
  const [corpus, setCorpus] = useState("all");
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [feedLoading, setFeedLoading] = useState(true);
  const [feedError, setFeedError] = useState(false);

  useEffect(() => {
    contentFeed()
      .then((data) => setFeed(data.items || []))
      .catch(() => setFeedError(true))
      .finally(() => setFeedLoading(false));
  }, []);

  async function onAsk() {
    if (!q.trim() || loading) return;
    setLoading(true);
    setError("");
    try {
      const response = await ask(q, corpus);
      setAnswer(response.answer || JSON.stringify(response));
      setCitations(response.citation_details || []);
    } catch {
      setError("知识库检索失败，请检查服务连接后重试。你的问题已保留。");
    } finally {
      setLoading(false);
    }
  }

  const primary = (
    <div className="training-stack">
      <Panel eyebrow="QUERY CONSOLE" title="向知识库提问">
        <div className="training-filter-row">
          <div className="field training-filter-row__select">
            <label htmlFor="corpus">知识库范围</label>
            <select id="corpus" value={corpus} onChange={(event) => setCorpus(event.target.value)}>
              <option value="all">全部</option>
              <option value="tech">技术知识</option>
              <option value="interview">面试攻略</option>
            </select>
          </div>
          <div className="field training-filter-row__input">
            <label htmlFor="question">你的问题</label>
            <textarea
              id="question"
              rows={5}
              placeholder="例如：mbarrier 如何协调异步事务？"
              value={q}
              onChange={(event) => setQ(event.target.value)}
            />
          </div>
        </div>
        <button type="button" className="btn btn-primary" onClick={onAsk} disabled={loading || !q.trim()}>
          <Search size={16} aria-hidden="true" /> {loading ? "检索中…" : "提问"}
        </button>
      </Panel>

      {error && <FeedbackState kind="error" title="检索未完成" description={error} />}
      {loading && !answer && <FeedbackState kind="loading" title="正在生成回答" description="检索相关知识片段并组织可核验的回答。" />}
      {answer ? (
        <section aria-label="回答">
          <Panel eyebrow="GROUNDED ANSWER" title="回答" actions={<StatusBadge tone="success">已完成</StatusBadge>}>
            <p className="prose training-answer">{answer}</p>
          </Panel>
        </section>
      ) : !loading && !error ? (
        <FeedbackState kind="empty" title="等待问题" description="选择知识范围并提交问题，回答会与引用来源分开呈现。" />
      ) : null}
    </div>
  );

  const aside = (
    <div className="training-stack">
      <CoachPanel title="引用来源" status={<StatusBadge tone={citations.length ? "info" : "neutral"}>{citations.length} 条</StatusBadge>}>
        {citations.length === 0 && <p className="empty-hint">提交问题后将显示知识库片段</p>}
        {citations.map((citation) => {
          const excerpt = citation.excerpt ?? "";
          return (
            <article key={citation.source_id} className="citation-item">
              <span className="citation-id">{citation.source_id}</span>
              {citation.path && <p className="citation-path">{citation.path}</p>}
              <p className="citation-excerpt">{excerpt.length > 220 ? `${excerpt.slice(0, 220)}…` : excerpt}</p>
            </article>
          );
        })}
      </CoachPanel>
      <CoachPanel title="最近发布">
        {feedLoading && <p className="empty-hint">正在读取发布记录…</p>}
        {feedError && <p className="inline-message" role="status">发布记录暂不可用</p>}
        {!feedLoading && !feedError && feed.length === 0 && <p className="empty-hint">暂无发布记录</p>}
        {feed.map((item, index) => <div key={`${item.title}-${index}`} className="feed-item"><span className="tag">{item.action}</span><span>{item.title}</span></div>)}
      </CoachPanel>
    </div>
  );

  return (
    <div>
      <PageHeader eyebrow="KNOWLEDGE RETRIEVAL" title="知识问答" description="基于本地知识库回答，并保留可以追溯的引用证据。" />
      <Workbench primary={primary} aside={aside} asideLabel="知识来源" />
    </div>
  );
}
