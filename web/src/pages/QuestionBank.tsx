import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { fetchAllQuestions } from "../api";
import { FilterBar } from "../components/questions/FilterBar";
import { QuestionCard, type QuestionBankItem } from "../components/questions/QuestionCard";
import { FeedbackState } from "../components/ui/FeedbackState";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge } from "../components/ui/StatusBadge";
import { QUESTION_SOURCES } from "../questions/catalog";

export function QuestionBankPage() {
  const [questions, setQuestions] = useState<QuestionBankItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState("");
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [expandedId, setExpandedId] = useState<string>();
  const deferredQuery = useDeferredValue(query.trim().toLocaleLowerCase());

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(false);
    fetchAllQuestions()
      .then((data) => active && setQuestions(data.questions || []))
      .catch(() => active && setLoadError(true))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [reloadKey]);

  const sourceCounts = useMemo(() => {
    const counts: Record<string, number> = Object.fromEntries(QUESTION_SOURCES.map((item) => [item, 0]));
    questions.forEach((question) => { counts[question.vendor] = (counts[question.vendor] ?? 0) + 1; });
    return counts;
  }, [questions]);

  const categories = useMemo(() => Array.from(new Set(
    questions.filter((question) => !source || question.vendor === source).map((question) => question.category).filter(Boolean),
  )).sort(), [questions, source]);

  const filtered = useMemo(() => questions.filter((question) => {
    if (source && question.vendor !== source) return false;
    if (category && question.category !== category) return false;
    if (!deferredQuery) return true;
    const searchable = [question.question, question.subcategory, question.category, ...(question.tags ?? [])].filter(Boolean).join(" ").toLocaleLowerCase();
    return searchable.includes(deferredQuery);
  }), [questions, source, category, deferredQuery]);

  function clearFilters() {
    setQuery("");
    setSource("");
    setCategory("");
  }

  if (loading) return <FeedbackState kind="loading" title="正在加载正式题库" description="正在整理题目、分类和来源统计。" />;
  if (loadError) return <FeedbackState kind="error" title="题库加载失败" description="正式题目没有丢失，请检查服务连接后重试。" action={<button type="button" className="btn btn-primary" onClick={() => setReloadKey((key) => key + 1)}>重新载入</button>} />;

  return (
    <div className="question-bank-page">
      <PageHeader
        eyebrow="RESOURCE BROWSER"
        title="正式题库"
        description="搜索 183 道已发布面试题，展开查看参考答案、回答要点和追问路径。"
        actions={<StatusBadge tone="info">{questions.length} 道正式题</StatusBadge>}
      />
      <FilterBar
        query={query}
        source={source}
        category={category}
        sourceCounts={sourceCounts}
        categories={categories}
        onQueryChange={setQuery}
        onSourceChange={(value) => { setSource(value); setCategory(""); }}
        onCategoryChange={setCategory}
        onClear={clearFilters}
      />
      <div className="question-bank-results" aria-live="polite"><strong>{filtered.length}</strong> 道匹配题目</div>
      {filtered.length ? (
        <div className="question-bank-list">
          {filtered.map((question) => <QuestionCard key={question.id} question={question} expanded={expandedId === question.id} onToggle={() => setExpandedId((id) => id === question.id ? undefined : question.id)} />)}
        </div>
      ) : <FeedbackState kind="empty" title="没有匹配题目" description="尝试缩短关键词、切换来源或清除筛选。" action={<button type="button" className="btn btn-quiet" onClick={clearFilters}>清除筛选</button>} />}
    </div>
  );
}
