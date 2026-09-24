import { SKILL_TAXONOMY, type SkillCategory } from "./taxonomy";

export interface ExtractedSkill {
  skill: string;
  category: SkillCategory;
  matchedKeyword: string;
}

export interface ParsedJD {
  title: string;
  responsibilities: string[];
  skills: ExtractedSkill[];
}

const RESPONSIBILITY_HEADERS = [
  "岗位职责",
  "工作职责",
  "职责描述",
  "职位职责",
  "job responsibilities",
  "responsibilities",
  "what you will do",
];

const REQUIREMENT_HEADERS = [
  "任职要求",
  "岗位要求",
  "任职资格",
  "职位要求",
  "job requirements",
  "qualifications",
  "requirements",
  "we are looking for",
];

const BULLET_PREFIX = /^[\s]*([-*•]|\d+[.、)）])\s*/;

function normalize(s: string): string {
  return s.trim().toLowerCase();
}

function matchHeader(line: string, headers: string[]): boolean {
  const n = normalize(line);
  return headers.some((h) => n === h || n.startsWith(h) || n.startsWith(h + ":") || n.startsWith(h + "："));
}

function splitSections(text: string): { resp: string[]; req: string[] } {
  const lines = text.split(/\r?\n/);
  let mode: "pre" | "resp" | "req" = "pre";
  const resp: string[] = [];
  const req: string[] = [];

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;

    if (matchHeader(line, RESPONSIBILITY_HEADERS)) {
      mode = "resp";
      continue;
    }
    if (matchHeader(line, REQUIREMENT_HEADERS)) {
      mode = "req";
      continue;
    }

    if (mode === "resp") resp.push(line);
    else if (mode === "req") req.push(line);
  }

  // 没识别出小标题时，整段按"职责/要求"经验式切分：含"要求/资格/学历/经验"关键词的行归 req
  if (resp.length === 0 && req.length === 0) {
    const reqHint = /要求|资格|学历|本科|硕士|经验|年以上|熟练|精通|熟悉|了解/;
    for (const line of lines) {
      const t = line.trim();
      if (!t) continue;
      if (reqHint.test(t)) req.push(t);
      else resp.push(t);
    }
  }

  return { resp, req };
}

function stripBullet(line: string): string {
  return line.replace(BULLET_PREFIX, "").trim();
}

function extractResponsibilities(respLines: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const line of respLines) {
    const text = stripBullet(line);
    if (text && !seen.has(text.toLowerCase())) {
      seen.add(text.toLowerCase());
      out.push(text);
    }
  }
  return out;
}

function extractSkills(reqLines: string[]): ExtractedSkill[] {
  const lowerToEntry: { lower: string; keyword: string; category: SkillCategory }[] = [];
  for (const e of SKILL_TAXONOMY) {
    lowerToEntry.push({ lower: e.keyword.toLowerCase(), keyword: e.keyword, category: e.category });
    for (const a of e.aliases ?? []) {
      lowerToEntry.push({ lower: a.toLowerCase(), keyword: e.keyword, category: e.category });
    }
  }
  // 长串优先匹配，避免 "go" 吃掉 "google"
  lowerToEntry.sort((a, b) => b.lower.length - a.lower.length);

  const fullText = reqLines.join("\n").toLowerCase();
  const matched = new Map<string, ExtractedSkill>();

  for (const { lower, keyword, category } of lowerToEntry) {
    if (fullText.includes(lower)) {
      if (!matched.has(keyword)) {
        matched.set(keyword, { skill: keyword, category, matchedKeyword: lower });
      }
    }
  }

  return Array.from(matched.values());
}

function guessTitle(text: string, fallback: string): string {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  // 首行若不像小标题就当标题
  const first = lines[0] ?? "";
  const looksHeader =
    matchHeader(first, RESPONSIBILITY_HEADERS) || matchHeader(first, REQUIREMENT_HEADERS);
  if (first && !looksHeader && first.length <= 40) return first.replace(/^#+\s*/, "");
  // 找含"岗位/职位/工程师/架构师/经理"的行
  const titleHint = /(岗位|职位|工程师|架构师|经理|总监|专员|顾问|售前|solution|architect|engineer|manager)/i;
  const hit = lines.find((l) => titleHint.test(l) && l.length <= 40);
  if (hit) return hit.replace(/^#+\s*/, "");
  return fallback;
}

export function parseJD(rawText: string, titleHint?: string): ParsedJD {
  const { resp, req } = splitSections(rawText);
  const responsibilities = extractResponsibilities(resp);
  const skills = extractSkills(req);
  const title = titleHint?.trim() || guessTitle(rawText, "未命名岗位");
  return { title, responsibilities, skills };
}
