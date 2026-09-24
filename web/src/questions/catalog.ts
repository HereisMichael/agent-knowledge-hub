export type QuestionSource = "general" | "aliyun" | "tencent" | "aws";

export const QUESTION_SOURCES = ["general", "aliyun", "tencent", "aws"] as const;

export const CLOUD_INTERVIEW_SOURCES = ["aliyun", "tencent", "aws"] as const;

export const QUESTION_SOURCE_LABELS: Readonly<Record<QuestionSource, string>> = {
  general: "通用 / AI Infra",
  aliyun: "阿里云",
  tencent: "腾讯云",
  aws: "AWS",
};
