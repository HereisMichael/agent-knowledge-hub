import { describe, expect, it } from "vitest";
import { NAV_SECTIONS, PAGE_DEFINITIONS } from "./navigation";

describe("Mission Grid navigation", () => {
  it("groups every page around the user workflow", () => {
    expect(NAV_SECTIONS.map((section) => section.label)).toEqual([
      "首页",
      "学习训练",
      "能力分析",
      "求职工具",
      "系统管理",
    ]);
    expect(NAV_SECTIONS[0].items.map((item) => item.id)).toEqual(["dashboard"]);
    expect(NAV_SECTIONS[1].items.map((item) => item.id)).toEqual([
      "learn",
      "quiz",
      "exercises",
      "bank",
      "mock",
      "labs",
    ]);
    expect(NAV_SECTIONS[2].items.map((item) => item.id)).toEqual(["assess", "progress"]);
    expect(NAV_SECTIONS[3].items.map((item) => item.id)).toEqual(["jd"]);
    expect(NAV_SECTIONS[4].items.map((item) => item.id)).toEqual(["settings", "review"]);
  });

  it("defines every page once and makes Dashboard the default", () => {
    expect(PAGE_DEFINITIONS[0]).toMatchObject({ id: "dashboard", label: "今日训练" });
    const ids = PAGE_DEFINITIONS.map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toHaveLength(12);
  });
});
