export interface RatingLevel {
  value: number;
  label: string;
}

// 5 级自评量表（0-4），维度分归一化时以 4 为满分
export const RATING_LEVELS: RatingLevel[] = [
  { value: 0, label: "不了解" },
  { value: 1, label: "了解概念" },
  { value: 2, label: "指导下会用" },
  { value: 3, label: "独立熟练" },
  { value: 4, label: "精通可带人" },
];

export const RATING_MAX = 4;

export interface MaasDimension {
  id: string;
  label: string;
  summary: string;
  /** 对应题库 category，用于「抽题自测」；为空表示题库暂无该维直接题目 */
  quizCategories: string[];
  /** 自评测评项 */
  criteria: string[];
}

// MaaS（Model-as-a-Service）解决方案专家视角的 8 维能力模型
export const MAAS_DIMENSIONS: MaasDimension[] = [
  {
    id: "llm",
    label: "大模型基础",
    summary: "模型原理、能力边界与选型判断",
    quizCategories: ["llm"],
    criteria: [
      "理解 Transformer、参数规模、上下文窗口与 tokenizer 原理",
      "能判断微调 / RAG / 提示工程的适用边界与选型",
      "了解主流开闭源模型的能力差异与成本特征",
    ],
  },
  {
    id: "prompt",
    label: "提示工程",
    summary: "提示设计、结构化输出与提示评测",
    quizCategories: ["prompt"],
    criteria: [
      "掌握 Few-shot / CoT / ReAct 等提示范式",
      "能设计稳定的结构化输出（JSON/Schema 约束）",
      "会做提示评测与 badcase 驱动的迭代优化",
    ],
  },
  {
    id: "rag",
    label: "RAG 检索增强",
    summary: "检索、切片、召回优化与引用溯源",
    quizCategories: ["rag"],
    criteria: [
      "理解向量检索、混合检索与 Rerank 重排",
      "能设计分块策略并优化召回率与准确率",
      "掌握引用溯源与幻觉检测 / 防控手段",
    ],
  },
  {
    id: "agent",
    label: "Agent 编排",
    summary: "多智能体、工具调用与记忆规划",
    quizCategories: ["agent"],
    criteria: [
      "理解 Planning / Memory / Tool Use 与编排框架",
      "能设计多 Agent 协作（Supervisor / Swarm）",
      "掌握工具调用、记忆管理与上下文工程",
    ],
  },
  {
    id: "inference",
    label: "部署与推理优化",
    summary: "私有化部署、量化与算力成本",
    quizCategories: ["inference"],
    criteria: [
      "掌握私有化部署与推理框架选型",
      "理解量化、并发吞吐与延迟优化手段",
      "能做 GPU 算力规划与推理成本测算",
    ],
  },
  {
    id: "data",
    label: "数据与知识治理",
    summary: "数据清洗、知识库构建与安全分级",
    quizCategories: [],
    criteria: [
      "能构建与增量维护高质量知识库",
      "掌握数据清洗、脱敏与分级安全策略",
      "了解数据合规（个保法 / 等保）落地要点",
    ],
  },
  {
    id: "cloud",
    label: "云平台与 MaaS 产品",
    summary: "MaaS 平台、API 集成与计费模型",
    quizCategories: ["cloud-ai"],
    criteria: [
      "熟悉百炼 / Bedrock 等 MaaS 平台产品体系",
      "能完成模型 API 集成与多云选型",
      "理解 MaaS 计费模型与 TCO 测算",
    ],
  },
  {
    id: "solution",
    label: "解决方案与售前",
    summary: "需求澄清、方案设计与行业落地",
    quizCategories: ["ai-arch", "ai-scenario", "ai-safety"],
    criteria: [
      "能完成需求澄清、方案设计与 POC 验证",
      "会做 ROI 测算与招投标技术响应",
      "掌握合规风控与教育 / 医疗等行业落地",
    ],
  },
  {
    id: "ai-infra",
    label: "AI Infra 工程",
    summary: "推理优化、分布式训练、GPU 编程、高性能计算",
    quizCategories: ["inference", "cloud-ai"],
    criteria: [
      "掌握 Flash Attention / PD 分离等推理优化核心技术",
      "理解分布式训练并行策略（DP/TP/PP/SP）与通信原理",
      "熟悉 GPU CUDA 编程、算子融合与性能分析",
    ],
  },
];

export function getDimension(id: string): MaasDimension | undefined {
  return MAAS_DIMENSIONS.find((d) => d.id === id);
}
