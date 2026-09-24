import { describe, expect, it } from "vitest";
import {
  CLOUD_INTERVIEW_SOURCES,
  QUESTION_SOURCES,
  QUESTION_SOURCE_LABELS,
} from "./catalog";

describe("question source catalog", () => {
  it("keeps the published sources in one ordered catalog", () => {
    expect(QUESTION_SOURCES).toEqual(["general", "aliyun", "tencent", "aws"]);
    expect(QUESTION_SOURCE_LABELS.general).toBe("通用 / AI Infra");
    expect(CLOUD_INTERVIEW_SOURCES).toEqual(["aliyun", "tencent", "aws"]);
  });
});
