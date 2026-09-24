import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  BookOpenText,
  Bot,
  ClipboardCheck,
  Code2,
  FileSearch,
  FlaskConical,
  Gauge,
  LibraryBig,
  ListChecks,
  Settings,
  ShieldCheck,
} from "lucide-react";

export type PageId =
  | "dashboard"
  | "learn"
  | "quiz"
  | "exercises"
  | "bank"
  | "mock"
  | "labs"
  | "assess"
  | "progress"
  | "jd"
  | "settings"
  | "review";

export interface PageDefinition {
  id: PageId;
  label: string;
  title: string;
  icon: LucideIcon;
}

export interface NavigationSection {
  label: string;
  items: readonly PageDefinition[];
}

export const PAGE_DEFINITIONS: readonly PageDefinition[] = [
  { id: "dashboard", label: "今日训练", title: "今日训练", icon: Gauge },
  { id: "learn", label: "知识问答", title: "知识问答", icon: BookOpenText },
  { id: "quiz", label: "刷题", title: "SA 题库训练", icon: ListChecks },
  { id: "exercises", label: "LLM 练习", title: "LLM 练习", icon: Code2 },
  { id: "bank", label: "题库", title: "题库总览", icon: LibraryBig },
  { id: "mock", label: "模拟面试", title: "模拟面试", icon: Bot },
  { id: "labs", label: "实操 Lab", title: "实操 Lab", icon: FlaskConical },
  { id: "assess", label: "技能测评", title: "MaaS 技能测评", icon: ClipboardCheck },
  { id: "progress", label: "学习进度", title: "学习进度", icon: BarChart3 },
  { id: "jd", label: "JD 分析", title: "岗位 JD 分析", icon: FileSearch },
  { id: "settings", label: "模型设置", title: "模型设置", icon: Settings },
  { id: "review", label: "内容审核", title: "内容审核", icon: ShieldCheck },
];

const pageById = new Map(PAGE_DEFINITIONS.map((page) => [page.id, page]));

function pages(ids: readonly PageId[]): readonly PageDefinition[] {
  return ids.map((id) => {
    const page = pageById.get(id);
    if (!page) throw new Error(`Unknown page: ${id}`);
    return page;
  });
}

export const NAV_SECTIONS: readonly NavigationSection[] = [
  { label: "首页", items: pages(["dashboard"]) },
  { label: "学习训练", items: pages(["learn", "quiz", "exercises", "bank", "mock", "labs"]) },
  { label: "能力分析", items: pages(["assess", "progress"]) },
  { label: "求职工具", items: pages(["jd"]) },
  { label: "系统管理", items: pages(["settings", "review"]) },
];

export function getPageDefinition(id: PageId): PageDefinition {
  const page = pageById.get(id);
  if (!page) throw new Error(`Unknown page: ${id}`);
  return page;
}

export function isPageId(value: string): value is PageId {
  return pageById.has(value as PageId);
}
