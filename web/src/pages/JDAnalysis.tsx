import { useEffect, useMemo, useState } from "react";
import { Download, FileSearch, Save, Trash2 } from "lucide-react";
import { parseJD, type ParsedJD } from "../jd/parse";
import { SAMPLE_JDS } from "../jd/samples";
import { deleteJD, downloadJDReport, listJDs, saveJD, skillCountsByCategory, type JDRecord } from "../jd/storage";
import { CATEGORY_LABELS, CATEGORY_ORDER, type SkillCategory } from "../jd/taxonomy";
import { CoachPanel } from "../components/training/CoachPanel";
import { Workbench } from "../components/training/Workbench";
import { FeedbackState } from "../components/ui/FeedbackState";
import { MetricTile } from "../components/ui/MetricTile";
import { PageHeader } from "../components/ui/PageHeader";
import { Panel } from "../components/ui/Panel";
import { StatusBadge } from "../components/ui/StatusBadge";

export function JDAnalysisPage() {
  const [records, setRecords] = useState<JDRecord[]>([]);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<ParsedJD>();
  const [savedRecord, setSavedRecord] = useState<JDRecord>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { setRecords(listJDs()); }, []);

  const counts = useMemo(() => parsed ? skillCountsByCategory(parsed.skills) : undefined, [parsed]);
  const grouped = useMemo(() => {
    const map = new Map<SkillCategory, NonNullable<ParsedJD["skills"]>>();
    parsed?.skills.forEach((skill) => map.set(skill.category, [...(map.get(skill.category) ?? []), skill]));
    return map;
  }, [parsed]);

  function loadSample(sampleId: string) {
    const sample = SAMPLE_JDS.find((item) => item.id === sampleId);
    if (!sample) return;
    setTitle(sample.label);
    setText(sample.text);
    setParsed(undefined);
    setSavedRecord(undefined);
    setError("");
    setMessage("示例 JD 已载入，可以直接分析");
  }

  function analyze() {
    const rawText = text.trim();
    setMessage("");
    setSavedRecord(undefined);
    if (rawText.length < 20) {
      setError("JD 文本过短，请粘贴完整岗位描述（至少 20 字）。");
      setParsed(undefined);
      return;
    }
    const result = parseJD(rawText, title);
    if (!result.responsibilities.length && !result.skills.length) {
      setError("未能识别岗位职责或技能，请检查是否包含职责与任职要求。");
      setParsed(undefined);
      return;
    }
    setParsed(result);
    setError("");
  }

  function saveAnalysis() {
    if (!parsed || savedRecord) return;
    const record = saveJD({ title: parsed.title, rawText: text.trim(), responsibilities: parsed.responsibilities, skills: parsed.skills });
    setRecords((current) => [record, ...current.filter((item) => item.id !== record.id)]);
    setSavedRecord(record);
    setMessage("分析记录已保存");
  }

  function openRecord(record: JDRecord) {
    setTitle(record.title);
    setText(record.rawText);
    setParsed({ title: record.title, responsibilities: record.responsibilities, skills: record.skills });
    setSavedRecord(record);
    setError("");
    setMessage("已打开历史分析");
  }

  function removeRecord(record: JDRecord) {
    deleteJD(record.id);
    setRecords((current) => current.filter((item) => item.id !== record.id));
    if (savedRecord?.id === record.id) {
      setSavedRecord(undefined);
      setParsed(undefined);
    }
    setMessage("历史记录已删除");
  }

  const primary = (
    <div className="training-stack">
      <Panel eyebrow="JD INPUT" title="岗位描述">
        <div className="field"><label htmlFor="jd-title">岗位名称（可选）</label><input id="jd-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="不填则从 JD 首行推断" /></div>
        <div className="field"><label htmlFor="jd-text">岗位 JD 文本</label><textarea id="jd-text" rows={12} value={text} onChange={(event) => { setText(event.target.value); setError(""); setParsed(undefined); setSavedRecord(undefined); }} placeholder="粘贴完整岗位描述，建议包含岗位职责和任职要求…" /></div>
        {error && <div className="inline-message" data-tone="danger" role="alert">{error}</div>}
        {message && <div className="inline-message" role="status" aria-live="polite">{message}</div>}
        <button type="button" className="btn btn-primary" onClick={analyze}><FileSearch size={16} aria-hidden="true" />分析 JD</button>
      </Panel>

      {!parsed ? <FeedbackState kind="empty" title="等待 JD 分析" description="分析结果会在这里显示职责、技能分类与数量概览。" /> : (
        <section className="jd-result" aria-label="JD 分析结果">
          <Panel eyebrow="ANALYSIS RESULT" title={parsed.title} actions={<StatusBadge tone={savedRecord ? "success" : "info"}>{savedRecord ? "已保存" : "待保存"}</StatusBadge>}>
            <div className="jd-result-metrics"><MetricTile label="岗位职责" value={parsed.responsibilities.length} detail="识别条目" tone="info" /><MetricTile label="技能关键词" value={parsed.skills.length} detail="已归类技能" tone="success" /><MetricTile label="技能类别" value={CATEGORY_ORDER.filter((category) => (counts?.[category] ?? 0) > 0).length} detail="有匹配的类别" /></div>
            <div className="jd-result-actions">
              {!savedRecord && <button type="button" className="btn btn-primary" onClick={saveAnalysis}><Save size={16} aria-hidden="true" />保存分析</button>}
              {savedRecord && <button type="button" className="btn btn-quiet" onClick={() => downloadJDReport(savedRecord)}><Download size={16} aria-hidden="true" />导出报告</button>}
            </div>
          </Panel>
          <Panel title={`岗位职责（${parsed.responsibilities.length}）`}>
            {parsed.responsibilities.length ? <ol className="jd-responsibilities">{parsed.responsibilities.map((responsibility) => <li key={responsibility}>{responsibility}</li>)}</ol> : <p className="empty-hint">未识别到明确职责条目</p>}
          </Panel>
          <Panel title={`岗位所需技能（${parsed.skills.length}）`}>
            {parsed.skills.length ? <div className="jd-skill-groups">{CATEGORY_ORDER.filter((category) => grouped.has(category)).map((category) => <section key={category}><h3>{CATEGORY_LABELS[category]}（{grouped.get(category)!.length}）</h3><div>{grouped.get(category)!.map((skill) => <span key={skill.skill}>{skill.skill}</span>)}</div></section>)}</div> : <p className="empty-hint">未识别到技能关键词</p>}
          </Panel>
        </section>
      )}
    </div>
  );

  const aside = (
    <div className="training-stack">
      <CoachPanel title="快速示例"><div className="jd-samples">{SAMPLE_JDS.map((sample) => <button key={sample.id} type="button" className="btn btn-quiet" onClick={() => loadSample(sample.id)}>{sample.label}</button>)}</div></CoachPanel>
      <CoachPanel title="分析历史" status={<StatusBadge tone={records.length ? "info" : "neutral"}>{records.length} 条</StatusBadge>}>
        {records.length ? <div className="jd-history-list">{records.map((record) => <article key={record.id} className="jd-history-item"><button type="button" className="jd-history-item__open" onClick={() => openRecord(record)}><strong>{record.title}</strong><span>职责 {record.responsibilities.length} · 技能 {record.skills.length}</span><small>{new Date(record.createdAt).toLocaleString("zh-CN")}</small></button><button type="button" className="btn btn-icon" aria-label={`删除 ${record.title}`} onClick={() => removeRecord(record)}><Trash2 size={15} aria-hidden="true" /></button></article>)}</div> : <p className="empty-hint">还没有保存的分析记录</p>}
      </CoachPanel>
    </div>
  );

  return <div><PageHeader eyebrow="ROLE INTELLIGENCE" title="岗位 JD 分析" description="在浏览器中解析职责和技能分类，再按需保存为可下载的岗位分析记录。" /><Workbench primary={primary} aside={aside} asideLabel="分析历史" /></div>;
}
