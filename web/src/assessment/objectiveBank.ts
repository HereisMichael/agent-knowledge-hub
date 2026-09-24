/**
 * 客观题库（选择 / 多选 / 判断）
 *
 * 每道题都附真实来源（题库题 id 或知识文档 source_id）+ 依据文本，
 * 来自 D:\cursor_project\agent-knowledge-hub_optimized\knowledge\ 知识库
 * 与 knowledge/interview/questions.jsonl 183 题真实条目，无凭空编造。
 */

export type QuestionType = "single" | "multi" | "boolean";

export interface QuestionSource {
  /** 题库题 id（如 aliyun-ai-llm-001）或知识库 source_id（如 harness-five-pillars-001） */
  ref: string;
  /** 简要出处说明 */
  where: string;
  /** 一句依据文本（来自该来源的真实 key_points / 文档内容） */
  evidence: string;
}

export interface ObjectiveQuestion {
  id: string;
  dimId: string;
  type: QuestionType;
  stem: string;
  options?: string[];
  /** 单选/判断：单一索引（0..n-1）；多选：索引数组 */
  correct: number | number[];
  explanation: string;
  source: QuestionSource;
}

export const OBJECTIVE_QUESTIONS: ObjectiveQuestion[] = [
  // ============ 大模型基础（llm）===========
  {
    id: "obj-llm-001",
    dimId: "llm",
    type: "single",
    stem: "Transformer 之所以成为大模型基础架构，核心在于哪个机制？",
    options: [
      "循环神经网络（RNN）的时序连接",
      "Self-Attention：同序列内 Token 互相关注以捕获全局依赖",
      "卷积神经网络（CNN）的局部感受野",
      "基于规则的知识图谱推理",
    ],
    correct: 1,
    explanation: "Self-Attention 让同一序列的 Token 互相加权关注，突破了 RNN 的顺序瓶颈，是大模型捕获长距离依赖的关键。",
    source: {
      ref: "aliyun-ai-llm-001",
      where: "题库 / LLM 基础 / Self-Attention",
      evidence: "Self-Attention：同一序列内的 Token 互相关注，捕获全局依赖，是 Transformer 的核心。",
    },
  },
  {
    id: "obj-llm-002",
    dimId: "llm",
    type: "single",
    stem: "LoRA 微调中 Rank（秩）选择过小会怎样？",
    options: [
      "训练速度显著变慢",
      "表达能力不足，难以拟合任务特异性",
      "显存占用显著增加",
      "梯度爆炸概率增大",
    ],
    correct: 1,
    explanation: "LoRA 用低秩 A·B 分解近似权重增量，r 越小可学习参数量越少，表达能力受限；任务复杂时需调高 r。",
    source: {
      ref: "aliyun-ai-llm-004",
      where: "题库 / LLM 微调 / LoRA 选型",
      evidence: "LoRA 原理：冻结原模型，在注意力层注入 A·B（r 远小于模型维度）。r 越小表达能力越弱。",
    },
  },
  {
    id: "obj-llm-003",
    dimId: "llm",
    type: "multi",
    stem: "下列哪些是处理微调数据分布偏移（catastrophic forgetting）的有效手段？",
    options: [
      "混合原始预训练数据与微调数据一起训练",
      "使用更大学习率加快收敛",
      "渐进式微调 / 课程学习",
      "加大微调数据量到百万级就一定能解决",
    ],
    correct: [0, 2],
    explanation: "混合训练与渐进式微调可缓解灾难性遗忘；学习率过大反而加剧；数据量并非线性解。",
    source: {
      ref: "aliyun-ai-llm-005",
      where: "题库 / LLM 微调 / 数据分布",
      evidence: "分布偏移：微调数据与预训练数据差异大→catastrophic forgetting。缓解：混合训练（原始+微调）、渐进式微调。",
    },
  },
  {
    id: "obj-llm-004",
    dimId: "llm",
    type: "boolean",
    stem: "MoE（Mixture of Experts）模型每次推理都会激活全部专家参数。",
    correct: 0,
    explanation: "MoE 每次只激活部分专家（典型 Top-2），整体参数量大但单次推理算力可控。",
    source: {
      ref: "aliyun-ai-llm-002",
      where: "题库 / LLM 架构 / MoE",
      evidence: "MoE 模型：每次只激活部分专家（如 Top-2），参数总量大但单次推理算力较小。",
    },
  },
  {
    id: "obj-llm-005",
    dimId: "llm",
    type: "boolean",
    stem: "Chinchilla 法则建议训练 Token 数应与模型参数量大致按 20:1 配比。",
    correct: 1,
    explanation: "Chinchilla（DeepMind）研究指出，模型参数与训练 Token 应大致等比扩展，固定算力下平衡点约 20:1。",
    source: {
      ref: "aliyun-ai-llm-006",
      where: "题库 / LLM 训练 / Scaling Law",
      evidence: "Chinchilla 法则：训练 Token 数应与模型参数量大致按 20:1 配比。",
    },
  },

  // ============ 提示工程（prompt）===========
  {
    id: "obj-prompt-001",
    dimId: "prompt",
    type: "single",
    stem: "下列哪项最能描述 Chain-of-Thought（CoT）提示？",
    options: [
      "给模型 2-5 个示例让模型仿照",
      "引导模型「Let's think step by step」逐步推理",
      "多次采样取多数投票结果",
      "随机打乱问题顺序以减少偏差",
    ],
    correct: 1,
    explanation: "CoT 通过显式让模型写出推理步骤提升复杂任务表现，与 Few-shot / Self-consistency 是不同范式。",
    source: {
      ref: "aws-ai-prompt-001",
      where: "题库 / 提示工程 / CoT",
      evidence: "CoT（思维链）：引导模型逐步推理（Let's think step by step），提升复杂推理能力。",
    },
  },
  {
    id: "obj-prompt-002",
    dimId: "prompt",
    type: "multi",
    stem: "设计高质量 System Prompt 通常应包含哪些要素？",
    options: [
      "角色定义、能力边界、行为准则",
      "输出格式约束（JSON / Markdown）",
      "随机生成的问候语以增加亲切感",
      "安全规则与拒绝策略",
    ],
    correct: [0, 1, 3],
    explanation: "角色定义、输出格式、安全规则是核心要素；随机问候语不属于。",
    source: {
      ref: "aws-ai-prompt-002",
      where: "题库 / 提示工程 / System Prompt",
      evidence: "System Prompt 要素：角色定义、输出格式约束、安全规则、上下文注入、迭代优化。",
    },
  },
  {
    id: "obj-prompt-003",
    dimId: "prompt",
    type: "single",
    stem: "Self-consistency 提示策略的核心做法是？",
    options: [
      "同问题多次采样后取多数投票",
      "让模型只输出一个答案以保稳定",
      "把所有示例压缩到一行",
      "在 prompt 中加入随机种子",
    ],
    correct: 0,
    explanation: "Self-consistency 通过多次采样 + 投票提升答案稳定性，常与 CoT 配合。",
    source: {
      ref: "aws-ai-prompt-001",
      where: "题库 / 提示工程 / Self-consistency",
      evidence: "Self-consistency：多次采样取多数投票结果，提升稳定性。",
    },
  },
  {
    id: "obj-prompt-004",
    dimId: "prompt",
    type: "boolean",
    stem: "ReAct 范式适合 Agent 场景下的工具调用。",
    correct: 1,
    explanation: "ReAct（Reason+Act）将推理与行动交替，适合 Agent 中需要工具调用的任务。",
    source: {
      ref: "aws-ai-prompt-001",
      where: "题库 / 提示工程 / ReAct",
      evidence: "ReAct：推理+行动交替进行，适合 Agent 场景的工具调用。",
    },
  },
  {
    id: "obj-prompt-005",
    dimId: "prompt",
    type: "boolean",
    stem: "用 placeholder 作为表单 label 是被广泛认可的最佳实践。",
    correct: 0,
    explanation: "placeholder 不能替代 label——后者承担可访问性语义与对比度保证，是 Form 设计硬规则。",
    source: {
      ref: "design-taste-frontend/SKILL.md",
      where: "design-taste-frontend / Section 4.6",
      evidence: "No placeholder-as-label. Ever.",
    },
  },

  // ============ RAG ============
  {
    id: "obj-rag-001",
    dimId: "rag",
    type: "single",
    stem: "RAG 检索召回率不高的常见优化方向是？",
    options: [
      "增加 chunk size 到 10MB",
      "混合检索（向量 + BM25）+ Rerank 重排",
      "把所有文档合并成一个超长上下文",
      "禁用分块直接全文检索",
    ],
    correct: 1,
    explanation: "混合检索结合语义和关键词信号，Rerank 提升排序质量，是召回优化主流手段。",
    source: {
      ref: "aliyun-ai-rag-001",
      where: "题库 / RAG / 检索优化",
      evidence: "检索优化：混合检索（向量+BM25关键词）、Rerank 重排序、查询改写、Top-K 调大。",
    },
  },
  {
    id: "obj-rag-002",
    dimId: "rag",
    type: "multi",
    stem: "文档分块（Chunking）对不同类型文档的合理做法是？",
    options: [
      "PDF 用 Layout Analysis 提取结构、表格单独处理、OCR 兜底",
      "代码按函数/类级别切分、保留 imports 上下文",
      "表格统一删除以简化索引",
      "Markdown 按标题层级语义分块",
    ],
    correct: [0, 1, 3],
    explanation: "PDF/代码/表格各需特定策略，表格不应被删（否则信息丢失）。",
    source: {
      ref: "aliyun-ai-rag-003",
      where: "题库 / RAG / 分块策略",
      evidence: "PDF 处理：Layout Analysis+表格单独处理+OCR 兜底；代码：按函数/类切分；表格：Markdown/CSV 保留结构。",
    },
  },
  {
    id: "obj-rag-003",
    dimId: "rag",
    type: "boolean",
    stem: "RAG 系统的幻觉防控常用「引用溯源 + NLI 一致性检查」组合。",
    correct: 1,
    explanation: "引用溯源让回答可被逐句验证，NLI 模型判蕴含/矛盾，两者结合是业内常见防控手段。",
    source: {
      ref: "aliyun-ai-rag-004",
      where: "题库 / RAG / 幻觉防控",
      evidence: "检测手段：引用溯源（每条回答标注来源 Chunk）、事实一致性检查（NLI 模型）。",
    },
  },
  {
    id: "obj-rag-004",
    dimId: "rag",
    type: "boolean",
    stem: "Agentic RAG 的核心区别是模型可自主决策是否检索 / 检索什么。",
    correct: 1,
    explanation: "传统 RAG 是固定检索→生成；Agentic RAG 由模型决策路径，可迭代检索。",
    source: {
      ref: "aliyun-ai-rag-005",
      where: "题库 / RAG / Agentic RAG",
      evidence: "核心区别：传统 RAG 固定流程 vs Agentic RAG 由模型决策是否检索/检索什么。",
    },
  },
  {
    id: "obj-rag-005",
    dimId: "rag",
    type: "single",
    stem: "选型场景：客户已有 AnalyticDB 集群并希望结构化+向量混合查询，最合适的向量检索方案是？",
    options: [
      "DashVector 纯向量数据库",
      "Elasticsearch 向量插件",
      "AnalyticDB 向量版（结构化+向量混合 SQL 接口）",
      "Milvus 自建集群",
    ],
    correct: 2,
    explanation: "AnalyticDB 向量版支持 SQL 接口 + 混合查询，匹配「已有 ADB 集群 + 混合查询」场景。",
    source: {
      ref: "aliyun-ai-rag-002",
      where: "题库 / RAG / 向量库选型",
      evidence: "AnalyticDB 向量版：结构化+向量混合查询、SQL 接口，适合已有 ADB 客户。",
    },
  },

  // ============ Agent 编排 ============
  {
    id: "obj-agent-001",
    dimId: "agent",
    type: "single",
    stem: "AI Agent 的核心四要素中，由「模型决策工具调用顺序与是否需要检索」驱动的范式属于？",
    options: ["Workflow 预定义流程", "自主 Agent（如 ReAct/Plan-and-Execute）", "纯 LLM 单轮问答", "硬编码脚本"],
    correct: 1,
    explanation: "自主 Agent 由模型决定路径，适合复杂探索任务；Workflow 适合标准化流程。",
    source: {
      ref: "aliyun-ai-agent-001",
      where: "题库 / Agent / 核心组成",
      evidence: "Workflow：确定性路径、预定义流程；自主 Agent：模型决策路径、ReAct/Plan-and-Execute。",
    },
  },
  {
    id: "obj-agent-002",
    dimId: "agent",
    type: "multi",
    stem: "Supervisor 模式与 Swarm 模式的核心差异是？",
    options: [
      "Supervisor 由中央 Agent 调度控制力强但单点瓶颈",
      "Swarm 去中心化、Agent 间直接通信，协调复杂",
      "两者本质相同只是命名差异",
      "Swarm 一定比 Supervisor Token 消耗更少",
    ],
    correct: [0, 1],
    explanation: "Supervisor 中央调度 vs Swarm 去中心化是核心差异；Token 消耗不一定更少。",
    source: {
      ref: "aliyun-ai-agent-004",
      where: "题库 / Agent / 多 Agent 协作",
      evidence: "Supervisor 模式：中央调度 Agent 分配任务，控制力强但单点瓶颈。Swarm：Agent 之间直接通信，去中心化但协调复杂。",
    },
  },
  {
    id: "obj-agent-003",
    dimId: "agent",
    type: "boolean",
    stem: "Harness 是包在模型外部的工程保障，包含五支柱（Context Assembly / Tool Integrity / Loop Discipline / Policy Enforcement / Context Lifecycle）。",
    correct: 1,
    explanation: "Harness 五支柱正是上述五项，缺一会让整套 Agent 容易失稳。",
    source: {
      ref: "harness-five-pillars-001",
      where: "knowledge/harness/01-five-pillars.md",
      evidence: "Context Assembly / Tool Integrity / Loop Discipline / Policy Enforcement / Context Lifecycle。",
    },
  },
  {
    id: "obj-agent-004",
    dimId: "agent",
    type: "single",
    stem: "OpenClaw Gateway 的核心职责是？",
    options: [
      "作为模型推理加速引擎",
      "作为消息与会话的神经中枢：路由、生命周期、工具事件",
      "替代数据库存储 Embedding",
      "生成 Embedding 向量",
    ],
    correct: 1,
    explanation: "Gateway 是「消息/会话/工具事件」中枢，类比 nervous system 而非推理引擎。",
    source: {
      ref: "openclaw-gateway-001",
      where: "knowledge/openclaw/01-gateway.md",
      evidence: "Gateway 是 OpenClaw 的「唯一中间层」：会话管理、通道适配、工具与事件路由。",
    },
  },
  {
    id: "obj-agent-005",
    dimId: "agent",
    type: "boolean",
    stem: "Skill 在 Agent 生态中是用 SKILL.md 等文件描述的指令/工具封装单元。",
    correct: 1,
    explanation: "Skill 是被 Harness 加载的指令单元，SKILL.md 是其描述格式。",
    source: {
      ref: "glossary-agent-001",
      where: "knowledge/glossary/glossary.md",
      evidence: "Skill：带指令的封装单元，SKILL.md 是其描述格式。",
    },
  },

  // ============ 部署与推理优化 ============
  {
    id: "obj-inf-001",
    dimId: "inference",
    type: "single",
    stem: "vLLM 的核心加速机制中，「分页管理 KV Cache、避免显存碎片」对应的是？",
    options: ["KV Cache 复用", "PagedAttention", "Continuous Batching", "Tensor Parallelism"],
    correct: 1,
    explanation: "PagedAttention 把 KV Cache 像 OS 虚拟内存一样分页管理，显著减少碎片。",
    source: {
      ref: "aliyun-ai-inference-001",
      where: "题库 / 推理优化 / vLLM",
      evidence: "PagedAttention：将 KV Cache 分页管理（借鉴 OS 虚拟内存），减少显存碎片。",
    },
  },
  {
    id: "obj-inf-002",
    dimId: "inference",
    type: "multi",
    stem: "大模型推理成本优化可以在哪几个层级做？",
    options: ["模型层：量化 / 蒸馏 / MoE 稀疏激活", "系统层：KV Cache 优化、Continuous Batching", "业务层：缓存、Prompt 压缩、路由降级", "硬件层：换更贵的 GPU 一定能解决"],
    correct: [0, 1, 2],
    explanation: "前三层都是成本优化抓手；「换更贵 GPU」反而增加成本。",
    source: {
      ref: "aliyun-ai-inference-004",
      where: "题库 / 推理优化 / 成本",
      evidence: "模型层：量化/蒸馏/MoE；系统层：KV Cache/Continuous Batching；业务层：缓存/Prompt 压缩/路由降级。",
    },
  },
  {
    id: "obj-inf-003",
    dimId: "inference",
    type: "boolean",
    stem: "INT8 量化一般会带来显著（>5%）的效果损失。",
    correct: 0,
    explanation: "INT8 通常精度损失 <1%；INT4 才会出现 1-3% 明显损失。",
    source: {
      ref: "aliyun-ai-inference-002",
      where: "题库 / 推理优化 / 量化",
      evidence: "效果影响：INT8 精度损失通常 <1%；INT4 出现 1-3% 损失；2-bit 显著下降。",
    },
  },
  {
    id: "obj-inf-004",
    dimId: "inference",
    type: "single",
    stem: "对 13B-70B 规模的模型推理，通常选用的 GPU 实例是？",
    options: ["T4 / GN7（16GB）", "A100（80GB）", "CPU 通用实例", "Mobile GPU"],
    correct: 1,
    explanation: "A100 80GB 适合 13B-70B 大模型推理；T4/GN7 仅适合 7B 量级。",
    source: {
      ref: "aliyun-ai-inference-003",
      where: "题库 / 推理优化 / GPU 选型",
      evidence: "A100(80GB)：大模型（13B-70B）推理、训练；T4/GN7(16GB) 仅适合 7B 量级。",
    },
  },
  {
    id: "obj-inf-005",
    dimId: "inference",
    type: "boolean",
    stem: "Continuous Batching 通过动态合并不同请求到同一批次，比 Static Batching GPU 利用率更高。",
    correct: 1,
    explanation: "Continuous Batching 在请求完成时立即插入新请求，避免 padding 浪费。",
    source: {
      ref: "aliyun-ai-inference-001",
      where: "题库 / 推理优化 / Batching",
      evidence: "Continuous Batching：动态合并不同请求到 GPU 批次（优于 Static Batching）。",
    },
  },

  // ============ 数据与知识治理 ============
  {
    id: "obj-data-001",
    dimId: "data",
    type: "multi",
    stem: "敏感数据送给大模型前的隐私保护手段通常包括？",
    options: ["PII 检测与替换（姓名/手机号/身份证）", "VPC 内网部署 + PrivateLink 私有连接", "把模型权重上传到公开仓库", "推理日志不保存原文"],
    correct: [0, 1, 3],
    explanation: "脱敏 + 网络隔离 + 日志最小化是标准做法；公开权重会破坏隔离。",
    source: {
      ref: "aliyun-ai-safety-001",
      where: "题库 / 数据安全 / 隐私保护",
      evidence: "网络隔离：VPC 内网部署、PrivateLink 私有连接；数据脱敏：PII 检测与替换；模型隔离；推理日志不保存原文。",
    },
  },
  {
    id: "obj-data-002",
    dimId: "data",
    type: "boolean",
    stem: "知识库构建时，分块后应保留元数据过滤能力以便按时间/来源过滤检索结果。",
    correct: 1,
    explanation: "元数据过滤（时间、来源、标签）是 RAG 检索精准度提升的重要手段。",
    source: {
      ref: "aliyun-ai-rag-001",
      where: "题库 / RAG / 索引优化",
      evidence: "索引优化：Top-K 调大、元数据过滤（metadata filtering）、层级索引。",
    },
  },
  {
    id: "obj-data-003",
    dimId: "data",
    type: "single",
    stem: "等保三级对 AI 应用最直接相关的是？",
    options: ["网络带宽升级", "访问控制、审计日志与数据保护要求", "显卡选型", "字体大小"],
    correct: 1,
    explanation: "等保三级核心是访问控制、审计日志、数据分级保护，与 AI 直接相关的是数据保护与日志审计。",
    source: {
      ref: "aliyun-ai-safety-001",
      where: "题库 / 合规 / 等保",
      evidence: "合规保障：等保三级/SOC2 认证、数据处理协议（DPA）、审计日志。",
    },
  },
  {
    id: "obj-data-004",
    dimId: "data",
    type: "boolean",
    stem: "对 AI 系统的输入/输出做分层 Guardrails 是降低越权与有害输出的有效手段。",
    correct: 1,
    explanation: "Guardrails（规则引擎 → 分类模型 → LLM Judge 分层）是业内公认的多层防御范式。",
    source: {
      ref: "aliyun-ai-safety-002",
      where: "题库 / 数据安全 / Guardrails",
      evidence: "分层策略：规则引擎（快速拦截）→分类模型（语义判断）→LLM Judge（复杂判断）。",
    },
  },
  {
    id: "obj-data-005",
    dimId: "data",
    type: "single",
    stem: "知识库增量更新时，常见的可观测性检查项是？",
    options: ["页面背景色", "新增 chunk 数、Embedding 完成数、检索命中率变化", "字体加载时间", "服务器温度"],
    correct: 1,
    explanation: "增量更新重点观察 chunk/Embedding 数量、命中率漂移等业务指标。",
    source: {
      ref: "aliyun-ai-arch-001",
      where: "题库 / 架构 / 知识库治理",
      evidence: "集成方案：RAG（向量检索+LLM）；增量知识库更新需观察命中率与新增 chunk 数。",
    },
  },

  // ============ 云平台与 MaaS 产品 ============
  {
    id: "obj-cloud-001",
    dimId: "cloud",
    type: "single",
    stem: "阿里云上部署 AI 推理服务，GPU 调度的关键 Kubernetes 插件是？",
    options: ["kube-proxy", "nvidia-device-plugin", "calico", "etcd"],
    correct: 1,
    explanation: "nvidia-device-plugin 让 K8s 识别并调度 NVIDIA GPU 资源（limits: nvidia.com/gpu）。",
    source: {
      ref: "aliyun-ai-cloud-001",
      where: "题库 / 云平台 / GPU 调度",
      evidence: "GPU 调度：nvidia-device-plugin、GPU 资源请求（limits: nvidia.com/gpu: 1）。",
    },
  },
  {
    id: "obj-cloud-002",
    dimId: "cloud",
    type: "multi",
    stem: "AI 应用常用的数据库与各自承担的角色是？",
    options: [
      "向量数据库（DashVector/Milvus）：存储 Embedding、语义检索",
      "关系数据库（PolarDB/RDS）：用户信息、对话历史、业务数据",
      "Redis/Tair：热点问答缓存、会话状态、限流",
      "MongoDB：纯文本展示层",
    ],
    correct: [0, 1, 2],
    explanation: "MongoDB 通常用于非结构化对话日志与 Agent 记忆，不是纯展示层。",
    source: {
      ref: "aliyun-ai-cloud-002",
      where: "题库 / 云平台 / 数据库",
      evidence: "向量库：Embedding；关系库：用户/历史/业务；缓存：热点问答/会话/限流；文档库：Agent 记忆。",
    },
  },
  {
    id: "obj-cloud-003",
    dimId: "cloud",
    type: "boolean",
    stem: "MaaS 平台（如阿里云百炼、AWS Bedrock）的核心价值之一是降低接入门槛、按 token/调用计费。",
    correct: 1,
    explanation: "MaaS = Model-as-a-Service，托管模型 + API + 按量计费是核心。",
    source: {
      ref: "aliyun-ai-cloud-003",
      where: "题库 / 云平台 / MaaS",
      evidence: "MaaS 平台：百炼、AWS Bedrock 等托管模型服务，按 token/调用计费。",
    },
  },
  {
    id: "obj-cloud-004",
    dimId: "cloud",
    type: "single",
    stem: "私有化部署与 MaaS 托管的主要 trade-off 是？",
    options: [
      "私有化更便宜",
      "私有化数据可控但运维成本高；MaaS 灵活但需信任云厂商",
      "两者无差别",
      "MaaS 不能用私有模型",
    ],
    correct: 1,
    explanation: "私有化 vs MaaS 的核心权衡是数据可控性 vs 运维/弹性。",
    source: {
      ref: "aliyun-ai-arch-001",
      where: "题库 / 架构 / 部署模式",
      evidence: "部署架构：私有化（PAI-EAS+vLLM）vs 托管（百炼）。数据安全 vs 运维成本权衡。",
    },
  },
  {
    id: "obj-cloud-005",
    dimId: "cloud",
    type: "boolean",
    stem: "在 GPU 节点池上做模型预热（warm-up）有助于降低首请求延迟。",
    correct: 1,
    explanation: "预热把权重提前加载到显存，避免首请求加载延迟。",
    source: {
      ref: "aliyun-ai-cloud-001",
      where: "题库 / 云平台 / 弹性伸缩",
      evidence: "弹性伸缩：Karpenter GPU 节点扩缩、HPA 按队列深度扩容、模型预热。",
    },
  },

  // ============ 解决方案与售前 ============
  {
    id: "obj-sol-001",
    dimId: "solution",
    type: "multi",
    stem: "面向客户做大模型私有化方案时，核心需要覆盖的架构要素是？",
    options: ["模型选型与规模匹配", "部署架构（PAI-EAS + vLLM 等）", "数据安全（VPC/脱敏/KMS）", "随意选择任意云厂商 GPU"],
    correct: [0, 1, 2],
    explanation: "选型/部署/安全是三要素；GPU 选型应匹配规模与成本，而非「随意」。",
    source: {
      ref: "aliyun-ai-arch-001",
      where: "题库 / 架构 / 私有化部署",
      evidence: "模型选型 + 部署架构 + 数据安全 + 集成方案 + 成本优化。",
    },
  },
  {
    id: "obj-sol-002",
    dimId: "solution",
    type: "single",
    stem: "SA 在客户交流中，需求澄清阶段最关键的是？",
    options: [
      "立即报价",
      "明确业务目标、约束（数据/合规/预算）、现有架构、关键场景",
      "直接演示 Demo",
      "承诺交付时间",
    ],
    correct: 1,
    explanation: "SA 五步法「澄清需求 → 设计方案 → POC → 投标」首步最关键。",
    source: {
      ref: "aliyun-ai-arch-002",
      where: "题库 / 架构 / 解决方案流程",
      evidence: "SA 售前流程：需求澄清 → 方案设计 → POC 验证 → 招投标响应。",
    },
  },
  {
    id: "obj-sol-003",
    dimId: "solution",
    type: "boolean",
    stem: "做 ROI 测算时应区分「模型层 / 系统层 / 业务层」三个成本维度。",
    correct: 1,
    explanation: "三层成本分摊是 SA 评估 TCO 的标准方法。",
    source: {
      ref: "aliyun-ai-inference-004",
      where: "题库 / 推理优化 / 成本",
      evidence: "模型层 / 系统层 / 业务层 + Token 成本 + 阿里云方案：PAI-EAS 弹性预留+Spot+Serverless。",
    },
  },
  {
    id: "obj-sol-004",
    dimId: "solution",
    type: "multi",
    stem: "教育/医疗行业的 AI 落地需特别关注哪些合规要点？",
    options: ["等保三级", "个保法（PIPL）对个人信息的处理要求", "医疗数据分级与脱敏", "无需审计日志"],
    correct: [0, 1, 2],
    explanation: "等保、个保法、医疗数据分级都是强制项；审计日志是合规要求之一。",
    source: {
      ref: "aliyun-ai-safety-001",
      where: "题库 / 数据安全 / 合规",
      evidence: "合规保障：等保三级/SOC2 认证、数据处理协议（DPA）、审计日志；阿里云百炼私有化部署 + PAI-EAS。",
    },
  },
  {
    id: "obj-sol-005",
    dimId: "solution",
    type: "single",
    stem: "POC 验证阶段最应关注？",
    options: [
      "PPT 美观度",
      "在客户真实数据/场景下验证关键指标（延迟、准确率、可解释性）",
      "尽量少沟通保密",
      "跳过合规",
    ],
    correct: 1,
    explanation: "POC 用真实数据/场景验证关键指标，是方案落地的关键依据。",
    source: {
      ref: "aliyun-ai-arch-002",
      where: "题库 / 架构 / POC",
      evidence: "POC 验证：用客户真实数据/场景验证关键指标（延迟/准确率/可解释性），形成可信交付依据。",
    },
  },

  // ============ AI Infra 工程 ============
  {
    id: "obj-ainfra-001",
    dimId: "ai-infra",
    type: "single",
    stem: "Flash Attention 的核心创新是？",
    options: [
      "使用更大的 batch size",
      "将 attention 计算分块在 SRAM 中完成，避免完整 attention 矩阵写回 HBM",
      "用 CPU 代替 GPU 计算 attention",
      "增加更多 attention head",
    ],
    correct: 1,
    explanation: "Flash Attention 的 IO-aware tiling 算法在 SRAM 中分块计算 softmax，避免了 O(n²) 的 HBM 读写。",
    source: {
      ref: "aliyun-ai-inference-007",
      where: "题库 / 推理优化 / Flash Attention",
      evidence: "Flash Attention 核心原理：将 attention 计算分块(tiling)，在 SRAM 中完成 softmax 的 online 计算。",
    },
  },
  {
    id: "obj-ainfra-002",
    dimId: "ai-infra",
    type: "single",
    stem: "大模型推理中 PD 分离（Prefill-Decode Disaggregation）的优势是什么？",
    options: [
      "减少模型参数量",
      "prefill 和 decode 可独立扩缩容，避免 decode 长尾请求阻塞 prefill",
      "完全消除 KV Cache 的需求",
      "不需要 GPU 也能推理",
    ],
    correct: 1,
    explanation: "PD 分离的核心价值：compute-bound 的 prefill 和 memory-bound 的 decode 可独立优化和扩缩容。",
    source: {
      ref: "aliyun-ai-inference-006",
      where: "题库 / 推理优化 / PD 分离",
      evidence: "架构优势：prefill 和 decode 可独立扩缩容、避免 decode 长尾请求阻塞 prefill。",
    },
  },
  {
    id: "obj-ainfra-003",
    dimId: "ai-infra",
    type: "multi",
    stem: "3D 并行（数据并行 DP、张量并行 TP、流水线并行 PP）各自解决什么核心问题？",
    options: [
      "DP 解决数据吞吐问题——多卡同时处理不同 batch",
      "TP 解决单层参数过大问题——将权重矩阵切分到多卡",
      "PP 减少 TP 的通信压力——将不同层放到不同卡上",
      "三者都只解决显存不足的问题",
    ],
    correct: [0, 1, 2],
    explanation: "DP 解决吞吐，TP 解决单层参数过大，PP 减少通信压力。三者互补而非互斥。",
    source: {
      ref: "aliyun-ai-training-001",
      where: "题库 / 训练优化 / 3D 并行",
      evidence: "数据并行每张卡有完整模型副本，处理不同 batch 数据；张量并行将单层权重切分到多卡。",
    },
  },
  {
    id: "obj-ainfra-004",
    dimId: "ai-infra",
    type: "boolean",
    stem: "Ring All-Reduce 在大数据量场景下比 Tree All-Reduce 延迟更低。",
    correct: 0,
    explanation: "Ring 的延迟为 2(N-1)α，与节点数线性增长；Tree 的延迟为 2·log₂(N)·α。大数据量时 Ring 带宽更优，但延迟更高。",
    source: {
      ref: "aliyun-ai-training-003",
      where: "题库 / 训练优化 / All-Reduce",
      evidence: "Ring All-Reduce 带宽最优但延迟随节点数线性增长；Tree 延迟 O(log N) 更低。",
    },
  },
  {
    id: "obj-ainfra-005",
    dimId: "ai-infra",
    type: "single",
    stem: "DeepSeek-V3 的 MLA（Multi-head Latent Attention）核心作用是什么？",
    options: [
      "增加 attention head 数量",
      "将 KV Cache 压缩为低秩潜在向量，显存占用降低 90%+",
      "减少模型层数",
      "用 CPU 替代 GPU 计算 attention",
    ],
    correct: 1,
    explanation: "MLA 将 K 和 V 映射为低秩潜在表示，推理时只需缓存压缩后的低秩向量，大幅节省显存。",
    source: {
      ref: "aliyun-ai-inference-012",
      where: "题库 / 推理优化 / DeepSeek-V3",
      evidence: "MLA 将传统 MHA 的 KV Cache 压缩为低秩潜在向量，显存占用降低 90%+。",
    },
  },
  {
    id: "obj-ainfra-006",
    dimId: "ai-infra",
    type: "boolean",
    stem: "Kernel fusion（算子融合）一定能提升推理性能。",
    correct: 0,
    explanation: "融合后 register 压力过大导致 occupancy 降低、shared memory bank conflict 增加等场景下，性能反而下降。",
    source: {
      ref: "aliyun-ai-inference-013",
      where: "题库 / 推理优化 / Kernel Fusion",
      evidence: "融合后 register 压力过大→occupancy 降低→并行度下降；bank conflict 增加→实际带宽降低。",
    },
  },
  {
    id: "obj-ainfra-007",
    dimId: "ai-infra",
    type: "multi",
    stem: "MoE（Mixture of Experts）大模型在推理部署时面临哪些核心挑战？",
    options: [
      "所有专家权重（如 671B）需要驻留显存，显存需求巨大",
      "热专家负载不均衡——部分 expert 被频繁选择成为瓶颈",
      "小规模部署时需将冷专家 offload 到 CPU/SSD 但增加延迟",
      "MoE 推理不需要 GPU",
    ],
    correct: [0, 1, 2],
    explanation: "MoE 推理三大挑战：全量权重驻留显存、专家负载不均衡、小规模 offload 延迟增加。",
    source: {
      ref: "aliyun-ai-inference-012",
      where: "题库 / 推理优化 / DeepSeek-V3",
      evidence: "MoE 显存挑战：所有专家权重需驻留显存；负载均衡：热专家过载导致瓶颈。",
    },
  },
  {
    id: "obj-ainfra-008",
    dimId: "ai-infra",
    type: "single",
    stem: "DiT（Diffusion Transformer）推理与 LLM 推理的核心差异是什么？",
    options: [
      "DiT 不需要 GPU",
      "DiT 是多步迭代去噪（固定步数、每步输入输出同尺寸），LLM 是自回归逐 token 生成（序列长度动态增长）",
      "两者完全一样",
      "DiT 比 LLM 快得多不需要优化",
    ],
    correct: 1,
    explanation: "DiT 每步 compute-bound（固定尺寸大矩阵乘法），LLM decode 是 memory-bound（KV Cache 带宽瓶颈）。",
    source: {
      ref: "aliyun-ai-inference-011",
      where: "题库 / 推理优化 / DiT",
      evidence: "DiT 是多步迭代（如 40-50 步去噪），LLM 是自回归（逐 token 生成）；计算特性完全不同。",
    },
  },
  {
    id: "obj-ainfra-009",
    dimId: "ai-infra",
    type: "boolean",
    stem: "Two-batch overlap 在任何分布式训练场景下都能提升训练效率。",
    correct: 0,
    explanation: "batch size 过小导致计算时间 < 通信时间、大 TP 规模下通信带宽竞争、显存压力过大等场景会成为负优化。",
    source: {
      ref: "aliyun-ai-inference-010",
      where: "题库 / 训练优化 / Two-Batch Overlap",
      evidence: "负优化场景：batch size 太小→计算时间<通信时间；大 TP 规模下 overlap 带宽竞争降低效率。",
    },
  },
  {
    id: "obj-ainfra-010",
    dimId: "ai-infra",
    type: "single",
    stem: "DeepSpeed ZeRO-2 相比 ZeRO-1 的核心区别是什么？",
    options: [
      "ZeRO-2 减少了模型参数量",
      "ZeRO-2 在分片优化器状态的基础上增加了梯度分片",
      "ZeRO-2 不需要 GPU 通信",
      "ZeRO-2 只能在单机使用",
    ],
    correct: 1,
    explanation: "ZeRO-1 只分片优化器状态，ZeRO-2 增加了梯度分片，梯度同步从 All-Reduce 改为 Reduce-Scatter。",
    source: {
      ref: "aliyun-ai-training-002",
      where: "题库 / 训练优化 / DeepSpeed ZeRO",
      evidence: "ZeRO-1 只分片优化器状态；ZeRO-2 分片优化器状态+梯度。",
    },
  },
];

export function questionsByDim(dimId: string): ObjectiveQuestion[] {
  return OBJECTIVE_QUESTIONS.filter((q) => q.dimId === dimId);
}
