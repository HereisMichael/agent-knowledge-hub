import type { ExtractedSkill } from "./parse";
import { CATEGORY_LABELS, CATEGORY_ORDER, type SkillCategory } from "./taxonomy";

const STORAGE_KEY = "akh_jd_records_v1";

export interface JDRecord {
  id: string;
  title: string;
  rawText: string;
  responsibilities: string[];
  skills: ExtractedSkill[];
  createdAt: string;
}

export type NewJDRecord = Omit<JDRecord, "id" | "createdAt">;

function safeRead(): JDRecord[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as JDRecord[]) : [];
  } catch {
    return [];
  }
}

function safeWrite(records: JDRecord[]): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
  } catch {
    /* ignore quota / serialization errors */
  }
}

export function listJDs(): JDRecord[] {
  return safeRead().sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function getJD(id: string): JDRecord | undefined {
  return safeRead().find((r) => r.id === id);
}

export function saveJD(record: NewJDRecord): JDRecord {
  const full: JDRecord = {
    ...record,
    id: `jd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
  };
  const records = safeRead();
  records.push(full);
  safeWrite(records);
  return full;
}

export function deleteJD(id: string): void {
  const records = safeRead().filter((r) => r.id !== id);
  safeWrite(records);
}

export function skillCountsByCategory(skills: ExtractedSkill[]): Record<SkillCategory, number> {
  const counts: Record<SkillCategory, number> = {
    tech: 0,
    cloud: 0,
    domain: 0,
    soft: 0,
    experience: 0,
    education: 0,
  };
  for (const s of skills) counts[s.category] += 1;
  return counts;
}

export function jdToMarkdown(record: JDRecord): string {
  const lines: string[] = [];
  lines.push(`# ${record.title} · JD 分析报告`);
  lines.push("");
  lines.push(`> 生成时间：${new Date(record.createdAt).toLocaleString("zh-CN")}`);
  lines.push("");

  lines.push(`## 岗位职责（${record.responsibilities.length}）`);
  lines.push("");
  if (record.responsibilities.length === 0) {
    lines.push("_未识别到明确的岗位职责条目。_");
  } else {
    for (const r of record.responsibilities) lines.push(`- ${r}`);
  }
  lines.push("");

  lines.push(`## 岗位所需技能（${record.skills.length}）`);
  lines.push("");
  const counts = skillCountsByCategory(record.skills);
  for (const cat of CATEGORY_ORDER) {
    const items = record.skills.filter((s) => s.category === cat);
    if (items.length === 0) continue;
    lines.push(`### ${CATEGORY_LABELS[cat]}（${counts[cat]}）`);
    for (const s of items) lines.push(`- ${s.skill}`);
    lines.push("");
  }

  return lines.join("\n");
}

export function downloadJDReport(record: JDRecord): void {
  if (typeof document === "undefined") return;
  const md = jdToMarkdown(record);
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const safeName = record.title.replace(/[\\/:*?"<>|]/g, "_").slice(0, 40);
  const a = document.createElement("a");
  a.href = url;
  a.download = `JD分析_${safeName}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
