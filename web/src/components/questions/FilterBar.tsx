import { RotateCcw, Search } from "lucide-react";
import { QUESTION_SOURCES, QUESTION_SOURCE_LABELS, type QuestionSource } from "../../questions/catalog";

export function FilterBar({
  query,
  source,
  category,
  sourceCounts,
  categories,
  onQueryChange,
  onSourceChange,
  onCategoryChange,
  onClear,
}: {
  query: string;
  source: string;
  category: string;
  sourceCounts: Readonly<Record<string, number>>;
  categories: readonly string[];
  onQueryChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onClear: () => void;
}) {
  return (
    <section className="question-filter" aria-label="题库筛选">
      <div className="question-filter__top">
        <div className="question-search field">
          <label htmlFor="question-search">搜索题目</label>
          <div className="question-search__control">
            <Search size={17} aria-hidden="true" />
            <input id="question-search" type="search" value={query} placeholder="搜索题目、子分类或标签" onChange={(event) => onQueryChange(event.target.value)} />
          </div>
        </div>
        <div className="field question-category">
          <label htmlFor="question-category">分类</label>
          <select id="question-category" value={category} onChange={(event) => onCategoryChange(event.target.value)}>
            <option value="">全部分类</option>
            {categories.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </div>
        <button type="button" className="btn btn-quiet question-filter__clear" onClick={onClear}><RotateCcw size={15} aria-hidden="true" />清除筛选</button>
      </div>
      <div className="question-source-list" aria-label="题目来源">
        <button type="button" className="question-source-chip" aria-pressed={!source} onClick={() => onSourceChange("")}>全部 <span>{Object.values(sourceCounts).reduce((sum, count) => sum + count, 0)}</span></button>
        {QUESTION_SOURCES.map((item) => {
          const label = QUESTION_SOURCE_LABELS[item as QuestionSource];
          const count = sourceCounts[item] ?? 0;
          return <button key={item} type="button" className="question-source-chip" aria-label={`${label} ${count}`} aria-pressed={source === item} onClick={() => onSourceChange(item)}>{label} <span aria-hidden="true">{count}</span></button>;
        })}
      </div>
    </section>
  );
}
