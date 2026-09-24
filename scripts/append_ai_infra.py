# -*- coding: utf-8 -*-
"""Add AI Infra interview questions from AIInfraGuide comprehensive Q-bank."""
import json

TARGET = r"D:\cursor_project\agent-knowledge-hub_optimized\knowledge\interview\questions.jsonl"

qs = [
    {
        "id": "aliyun-ai-inference-007",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "flash-attention",
        "difficulty": 4,
        "question": "Flash Attention 的核心原理是什么？v2 版本中外层循环为什么选择对 Q 进行遍历？Flash Decoding 的 combine kernel 有什么作用？",
        "key_points": [
            "核心原理：将 attention 计算分块(tiling)，在 SRAM 中完成 softmax 的 online 计算，避免把完整 attention 矩阵写回 HBM",
            "Flash Attention v2 外层循环对 Q 遍历的原因：让每个 thread block 处理一个 Q 行，减少 warp 间通信，提升并行度",
            "Flash Decoding 的 combine kernel：将多个 KV 分块的 partial softmax 结果合并，用于长序列 decode 时减少 KV Cache 重读",
            "前向计算中 softmax 的 online safe 算法：通过 running max 和 running sum 避免数值溢出",
            "性能优势：O(n^2) 显存降到 O(n)，wall-clock 加速 2-4 倍"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "Flash Attention 在处理 GQA/MQA 时有什么特殊优化？",
            "Flash Decoding 的 combine kernel 耗时占比大约是多少？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "inference"],
        "source_note": "AIInfraGuide-综合面经题库-1",
        "reference_answer": (
            "Flash Attention 是当前大模型推理最关键的性能优化技术之一，核心思想是用 IO-aware 算法替代传统的 attention 计算。\n\n"
            "一、核心原理\n"
            "传统 attention：Q×K^T 产生 n×n 的矩阵，必须写回 HBM（高带宽显存），然后从 HBM 读取做 softmax，再写回。"
            "HBM 带宽是瓶颈。\n"
            "Flash Attention：将 Q、K、V 分块加载到 SRAM（片上共享内存），在 SRAM 中完成 attention 计算和 softmax，"
            "利用 SRAM 的低延迟和高带宽，避免中间矩阵写回 HBM。关键是使用了 online safe softmax 算法——"
            "通过维护 running max 和 running sum，可以在不完整看到所有 attention 分数的情况下逐步计算 softmax。\n\n"
            "二、v2 外层循环 Q 的设计\n"
            "Flash Attention v1 外层循环遍历 K/V，内层循环遍历 Q。这导致每个 thread block 需要写回 partial softmax 结果，"
            "然后由另一个 thread block 读取并合并，引入了额外通信。\n"
            "v2 改为外层循环遍历 Q：\n"
            "- 每个 thread block 负责一个 Q 行（或多个 Q 行）\n"
            "- K/V 块在循环中依次加载，同一个 block 内完成所有计算\n"
            "- 减少了 warp 间通信和中间结果的写回\n"
            "- 更好利用了 GPU 的 warp-level 并行度\n\n"
            "三、Flash Decoding\n"
            "在长序列 decode 阶段，虽然每次只生成一个 token，但仍需读取全部 KV Cache。"
            "Flash Decoding 将 KV Cache 分给多个 thread block，各自计算部分 attention，"
            "最后通过 combine kernel 合并——本质是多次调用 Flash Attention + 一次 reduction。"
            "combine kernel 使用在线 softmax 的扩展算法，合并各块的 (max, sum, output) 三元组。"
        ),
    },
    {
        "id": "aliyun-ai-inference-008",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "weight-only-quantization",
        "difficulty": 4,
        "question": "Weight-Only 量化有哪些方案？实现 Weight-Only 量化 CUDA kernel 时如何优化访存？Marlin kernel 的核心设计是什么？",
        "key_points": [
            "Weight-Only vs Weight+Activation 量化：Weight-Only 只量化权重而保持激活值为 FP16，减少显存但对计算帮助有限",
            "主流方案：GPTQ(逐层量化+最优脑外科)、AWQ(激活感知权重缩放)、GGUF(CPU友好格式)",
            "访存优化：利用权重去量化后的 register-level 复用、向量化加载(float4/uint4)、bank conflict 避免",
            "Marlin kernel：针对 INT4 Weight-Only 量化推理的高性能 CUDA kernel，利用 Tensor Core 和 warp-level 协作",
            "Marlin 核心设计：permuted layout(B/128×K/256 tile)、异步流水线(global->shared->register)、repack 权重以适应 GPU 内存对齐"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "Weight-Only 量化相比 Weight+Activation 量化在推理加速上效果如何？",
            "Marlin kernel 对 batch size 有什么要求？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "inference"],
        "source_note": "AIInfraGuide-综合面经题库-2",
        "reference_answer": (
            "Weight-Only 量化是大模型推理部署的常见手段，核心是在保持激活值精度的前提下压缩模型权重。\n\n"
            "一、Weight-Only 量化方案\n"
            "- GPTQ：基于最优脑外科（OBS）理论，逐层对权重进行量化，并使用 Hessian 矩阵补偿量化误差。"
            "适合离线量化后部署\n"
            "- AWQ：观察到部分权重通道对激活的影响更大（高激活通道），对权重进行激活感知的逐通道缩放，"
            "保护关键通道的精度\n"
            "- GGUF/GGML：CPU 友好的量化格式，支持 Q4_0/Q4_1/Q5_0/Q8_0 等多种配置，常用于 llama.cpp 部署\n"
            "- Marlin：专为 INT4 推理优化的高性能 kernel，在 vLLM 中广泛应用\n\n"
            "二、CUDA kernel 访存优化要点\n"
            "- 向量化加载：使用 float4/uint4 一次加载 128bit，减少 load 指令数\n"
            "- 寄存器级复用：权重 degroup 后保存在寄存器中，多次与不同激活值相乘\n"
            "- Shared Memory 布局：避免 bank conflict，使用 swizzle/padding 技术\n"
            "- 异步拷贝：利用 async copy（cp.async）从 global memory 流水线加载到 shared memory\n\n"
            "三、Marlin kernel 核心设计\n"
            "Marlin 是目前最快的 INT4 Weight-Only 推理 kernel：\n"
            "- 特殊的权重 repack 布局：将 INT4 权重重新排列为有利于 Tensor Core 加载的格式(B/128 × K/256 tile)\n"
            "- 两级流水线：global mem → shared mem（异步）→ registers → 去量化 → Tensor Core 计算\n"
            "- Warp 级别协作：多个 warp 共享 shared memory tile，最大化并行度\n"
            "- 支持 GPTQ 和 AWQ 两种量化格式，对 batch size ≥ 16 场景加速显著"
        ),
    },
    {
        "id": "aliyun-ai-inference-009",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "pd-separation-multi-node",
        "difficulty": 4,
        "question": "多机 PD 分离会引入 KV Cache 传输开销，为何仍然有必要进行 PD 分离？Mooncake 的 KV Cache 中心化方案是如何设计的？",
        "key_points": [
            "单机 PD 分离问题：prefill 与 decode 计算特性不同（compute-bound vs memory-bound），混部会导致相互干扰",
            "多机 PD 分离的收益＞KV Cache 传输开销：prefill 节点用高算力 GPU，decode 节点用廉价 GPU，整体 TCO 更低",
            "高速互联降低传输开销：NCCL/RDMA/InfiniBand 可以提供数百 GB/s 的传输带宽，传输耗时可被并行流水线掩盖",
            "Mooncake 设计：以 KV Cache 为中心——将 KV Cache 作为独立服务，prefill 和 decode 都是 KV Cache 的消费者/生产者",
            "KV Cache 池化：多个 prefill/decode 实例共享 KV Cache 池，实现 KV Cache 复用和负载均衡"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "KV Cache 传输的带宽要求通常是多少？",
            "如果 KV Cache 传输延迟太高无法隐藏，还有什么替代方案？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "inference"],
        "source_note": "AIInfraGuide-综合面经题库-1,3",
        "reference_answer": (
            "多机 PD 分离虽然在 KV Cache 传输上引入了额外开销，但它是大规模推理部署的必然选择。\n\n"
            "一、为什么多机 PD 分离仍然必要\n"
            "1. 工作负载特性根本不同：\n"
            "- Prefill 是 compute-bound：一次性处理所有输入 token，需要大量矩阵乘法（GEMM），GPU 算力（FLOPS）是关键\n"
            "- Decode 是 memory-bound：每步只处理 1 个新 token，但需读取全部 KV Cache，显存带宽（HBM Bandwidth）是关键\n"
            "- 两者混在同一 GPU 上，慢速 decode 会阻塞后续 prefill，导致 TTFT 大幅波动\n\n"
            "2. 硬件选型可以精准匹配：\n"
            "- Prefill 节点用高算力 A100/H100（贵但 FLOPS 高）\n"
            "- Decode 节点用显存带宽优先的 A10/L40s（相对便宜，性价比高）\n"
            "- 这种异构部署能降低整体 TCO 30-50%\n\n"
            "3. 网络传输开销可被工程化解：\n"
            "- RDMA/InfiniBand 带宽可达 400GB/s+\n"
            "- KV Cache 传输可以与 decode 第一阶段并行（异步流水线）\n"
            "- 只需要传输一次 KV Cache，后续 decode 步无需再传\n\n"
            "二、Mooncake 的 KV Cache 中心化设计\n"
            "Mooncake 将 KV Cache 从计算节点中解耦：\n"
            "- KV Cache 作为独立的分布式存储服务，运行在专用的存储节点上\n"
            "- Prefill 节点：计算完 KV Cache 后写入存储池\n"
            "- Decode 节点：从存储池读取 KV Cache 进行续接生成\n"
            "- 优势：多个 decode 实例可共享同一份 KV Cache，支持请求迁移和负载均衡\n"
            "- 类比：类似 Redis 作为 Session Store，KV Cache 是「推理 Session」的持久状态"
        ),
    },
    {
        "id": "aliyun-ai-training-001",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "distributed-training",
        "difficulty": 4,
        "question": "在多机多卡大模型训练中，3D 并行（数据并行、张量并行、流水线并行）各自解决什么问题？训练超长序列时应如何设计并行策略？",
        "key_points": [
            "数据并行(DP)：每张卡有完整模型副本，处理不同 batch 数据，梯度同步用 All-Reduce。解决数据吞吐问题",
            "张量并行(TP)：将单层权重切分到多卡，进行分片矩阵乘法。解决单层参数量过大装不下的问题",
            "流水线并行(PP)：将不同层放到不同卡上，batch 切分为 micro-batch 流水线执行。减少 TP 的通信压力",
            "序列并行(SP)：在序列长度维度切分，每卡处理部分序列。解决超长序列训练问题",
            "超长序列策略：优先 Ring Attention(序列并行的一种)，配合 ZeRO-3 省显存，必要时结合 TP 处理超大模型"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "张量并行先按列切分和先按行切分有什么区别？",
            "3D 并行中的通信瓶颈通常在哪里？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "training"],
        "source_note": "AIInfraGuide-综合面经题库-3,5,7",
        "reference_answer": (
            "3D 并行是大模型分布式训练的基石，每种并行策略解决不同层面的瓶颈。\n\n"
            "一、三种并行策略及其作用\n\n"
            "1. 数据并行 (DP)\n"
            "- 原理：每张 GPU 持有完整模型副本，处理不同 batch 数据，前向/反向各自计算，梯度通过 All-Reduce 同步\n"
            "- 解决的问题：数据吞吐——单卡处理 batch 太慢，用多卡并行处理\n"
            "- 局限：每张卡需要装下完整模型+优化器状态，参数量大了就装不下\n\n"
            "2. 张量并行 (TP)\n"
            "- 原理：将单层的权重矩阵按列或行切分到多张卡，通过矩阵乘法的分块性质并行计算\n"
            "  · 列切分：W → [W1, W2]，输入 X 完整，输出 Y = [X·W1, X·W2] 拼接\n"
            "  · 行切分：X → [X1, X2]，W 完整 → 分别计算 → All-Reduce 求和\n"
            "- 解决的问题：单层参数太大，单卡显存放不下（如 175B 模型单个 attention 层就需要几十 GB）\n"
            "- 局限：通信量大，每次前向和反向都需要在卡间同步，通常限制在单机内（NVLink 高速互联）\n\n"
            "3. 流水线并行 (PP)\n"
            "- 原理：将模型按层切分到不同卡上（如 GPU0 放 layers 0-10，GPU1 放 layers 11-20）\n"
            "- 解决的问题：减少 TP 的通信压力，允许跨机部署\n"
            "- 关键技术：将 batch 切分为多个 micro-batch，形成流水线，减少 GPU 空闲时间（bubble）\n\n"
            "二、超长序列训练的并行策略\n"
            "- 核心挑战：序列长度 n 增加时，self-attention 的显存和计算量都按 O(n^2) 增长\n"
            "- 首选：序列并行 (Ring Attention)——在序列维度切分，每张卡只处理 n/k 长度的序列段，"
            "通过 Ring 通信交换 KV 块，实现全序列 attention\n"
            "- 辅助：ZeRO-3 将优化器状态、梯度和参数分片存储，最大化节省显存\n"
            "- 极端场景：结合 Flash Attention + Ring Attention 同时优化计算和通信\n"
            "- 工业界实践：训练 1M+ token 超长序列时，使用 SP=8 + ZeRO-3 的配置"
        ),
    },
    {
        "id": "aliyun-ai-training-002",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "megatron-deepspeed",
        "difficulty": 4,
        "question": "Megatron-LM 的通信优化是如何实现的？DeepSpeed ZeRO Stage 1 与 Stage 2 在通信量上有何差异？",
        "key_points": [
            "Megatron-LM 通信优化：张量并行中通过 reduce-scatter+all-gather 替代 all-reduce，减少通信量",
            "Megatron-LM 的列+行切分组合：一次前向只需要 2 次通信（f 和 g 操作），而非两条线性层的 4 次",
            "DeepSpeed ZeRO-1：只分片优化器状态(optimizer states)，通信量与 DP 相同，每个 step All-Reduce 梯度",
            "DeepSpeed ZeRO-2：分片优化器状态+梯度，梯度同步从 All-Reduce 变为 Reduce-Scatter，通信量不变但更节能",
            "ZeRO-2 论文描述的通信量和代码实现有差距：实际可能引入额外通信（如参数 norm），需结合 FP16/BF16 环境分析"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "ZeRO-3 和 ZeRO-2 的显存节省比例是多少？",
            "Megatron-LM 的 TP 和 PP 如何与 DeepSpeed 的 DP 结合？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "training"],
        "source_note": "AIInfraGuide-综合面经题库-2,3,7",
        "reference_answer": (
            "Megatron-LM 和 DeepSpeed 是大模型分布式训练的两大核心框架，侧重点不同。\n\n"
            "一、Megatron-LM 的通信优化\n\n"
            "Megatron 针对张量并行 (TP) 设计了精巧的通信模式：\n"
            "1. f 操作（前向列切分）：Y = GeLU(X·A)，A 按列切分 → 每卡计算部分结果 → All-Gather 拼接 → 再做 GeLU\n"
            "2. g 操作（前向行切分）：Y = GeLU(X)·B，B 按行切分 → 每卡用完整 X 计算 → Reduce-Scatter 求和\n"
            "3. 关键优化：将 MLP 的两层线性层组合——列切分 A + 行切分 B——使得 GeLU 在中间不需要额外通信。"
            "一次 MLP 层只需要 f+g 两次通信操作，而非 naive 方案的四次\n\n"
            "4. 对于 Attention 层类似：QKV 投影做列切分（f），输出投影做行切分（g）\n\n"
            "二、DeepSpeed ZeRO Stage 1 vs Stage 2 通信量分析\n\n"
            "ZeRO-1（优化器状态分片）：\n"
            "- 每个 GPU 只存 1/N 的优化器状态（如 Adam 的 m、v）\n"
            "- 梯度仍需通过 All-Reduce 在所有 GPU 间同步\n"
            "- 通信量 = 2×(N-1)/N × 参数量（All-Reduce 标准开销）\n\n"
            "ZeRO-2（梯度分片）：\n"
            "- 优化器状态+梯度都分片存储\n"
            "- 梯度同步从 All-Reduce 改为 Reduce-Scatter：每张卡只接收自己负责任的那部分梯度\n"
            "- 论文声称通信量与 ZeRO-1 相同，因为 Reduce-Scatter 和 All-Reduce 的通信量理论上一致\n"
            "- 但工程实践中，ZeRO-2 可能引入额外开销（如参数 norm 计算需要 All-Reduce 平方和），"
            "且在不同并行策略组合下，通信模式会变化\n\n"
            "总结：ZeRO 通过「空间换通信」节省显存，Megatron 通过「精巧编排」减少通信次数。两者通常组合使用。"
        ),
    },
    {
        "id": "aliyun-ai-inference-010",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "two-batch-overlap",
        "difficulty": 3,
        "question": "Two-batch overlap 是什么？在哪些场景下 Two-batch overlap 反而会成为负优化？",
        "key_points": [
            "Two-batch overlap：将两个 mini-batch 的计算和通信重叠执行，用一个 batch 的计算时间掩盖另一个 batch 的通信时间",
            "原理：GPU 计算单元和通信引擎可以并行工作——一个 batch 在做前向/反向计算时，另一个 batch 在做梯度同步",
            "正优化场景：计算时间 > 通信时间时效果最好，能实现通信完全隐藏",
            "负优化场景1：batch size 太小→计算时间 < 通信时间→overlap 无意义且增加调度开销",
            "负优化场景2：大 TP 规模下通信量极大→通信成为瓶颈→overlap 带宽竞争反而降低整体效率"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "如何测量计算时间和通信时间的比例来判断是否适合做 overlap？",
            "分布式训练中还有哪些其他 overlap 优化手段？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "training", "inference"],
        "source_note": "AIInfraGuide-综合面经题库-3",
        "reference_answer": (
            "Two-batch overlap 是分布式训练中的经典通信-计算重叠优化，但有其适用条件。\n\n"
            "一、什么是 Two-batch Overlap\n\n"
            "在数据并行训练中，单 batch 流程是：前向→反向→梯度 All-Reduce→参数更新。GPU 在等 All-Reduce 时是空闲的。\n"
            "Two-batch overlap 的核心思想：维护两个 mini-batch 的流水线——\n"
            "- batch_1 做梯度 All-Reduce（通信引擎工作）的同时，batch_2 做前向/反向计算（计算单元工作）\n"
            "- 理想情况下，通信时间被完全隐藏在计算时间中\n\n"
            "二、何时成为负优化\n\n"
            "1. Batch Size 过小\n"
            "- 当每个 batch 的计算时间（T_compute）< 通信时间（T_comm）时，overlap 无法隐藏延迟\n"
            "- 反而引入额外的 CUDA stream 管理和内存分配开销\n"
            "- 典型场景：小模型（<1B 参数）+ 慢速网络（以太网而非 InfiniBand）\n\n"
            "2. 超大 TP 规模\n"
            "- 张量并行的通信量与模型参数量呈线性关系\n"
            "- 当 TP 度数很大时，通信开销成为主导，overlap 的「计算窗口」不够长\n"
            "- 多个通信流之间还可能竞争 NVLink 带宽，导致相互恶化\n"
            "- 典型场景：8 卡 TP + 不支持 NVSwitch 的硬件\n\n"
            "3. 内存压力\n"
            "- 维护两个 batch 的激活值和梯度需要额外显存\n"
            "- 如果显存已经很紧张（如训练大模型时），overlap 可能导致 OOM\n\n"
            "工程实践：通常只在 DP 规模较大（>=4 卡）且网络较好（NVLink/RDMA）时开启 two-batch overlap。"
        ),
    },
    {
        "id": "aliyun-ai-inference-011",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "dit-inference",
        "difficulty": 4,
        "question": "DiT（Diffusion Transformer）推理框架的设计与 LLM 推理框架有哪些异同？",
        "key_points": [
            "相同点：都需要处理 Transformer 结构、KV Cache 优化、多 GPU 并行、显存管理",
            "核心差异1：DiT 是多步迭代（如 40-50 步去噪），LLM 是自回归（逐 token 生成）",
            "核心差异2：DiT 的序列长度固定（latent 分辨率决定），LLM 序列长度动态增长",
            "核心差异3：DiT 每步处理的 token 数相同、可以复用前一步的中间结果；LLM 每步 token 数+1",
            "工程差异：DiT 优先批量处理多个图/视频 token，LLM 优先低延迟首 token 和 streaming 输出"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "DiT 推理中模型量化是否比 LLM 更敏感？",
            "视频 DiT 推理的显存优化有哪些特殊手段？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "inference"],
        "source_note": "AIInfraGuide-综合面经题库-1",
        "reference_answer": (
            "DiT 和 LLM 虽然都基于 Transformer，但推理模式有本质区别，直接影响工程优化策略。\n\n"
            "一、相同点\n"
            "- 都是 Transformer 架构：Self-Attention + FFN + LayerNorm\n"
            "- 都可以使用 Flash Attention、KV Cache、量化等通用优化\n"
            "- 都需要考虑多 GPU 并行和显存管理\n\n"
            "二、核心差异\n\n"
            "1. 推理范式\n"
            "- LLM：自回归（Auto-Regressive），每步生成 1 个 token，序列长度逐渐增大\n"
            "- DiT：迭代去噪，固定步数（如 40-50 步），每步输入输出尺寸相同\n"
            "- 影响：LLM 的 decode 阶段是 memory-bound（受 KV Cache 显存带宽限制），而 DiT 每步都是 compute-bound（大矩阵乘法）\n\n"
            "2. 序列长度\n"
            "- LLM：动态变化（1 → N），需要动态管理和预分配 KV Cache\n"
            "- DiT：固定长度（由 latent 分辨率决定，如 256×256 → 1024 个 patch tokens），可以预分配所有显存\n"
            "- 影响：DiT 不需要复杂的显存管理（如 PagedAttention 对 DiT 的收益较小），但需要处理大批量（batch of images）\n\n"
            "3. 优化重点\n"
            "- LLM：低延迟（TTFT）和 streaming、KV Cache 压缩、投机采样、PD 分离\n"
            "- DiT：高吞吐（同时处理多张图）、多步 iterative 优化的 cache 复用、CFG（classifier-free guidance）的 batch 加倍问题\n"
            "- 影响：DiT 更依赖大 batch 推理 + FP8 加速，因为每步计算量远大于 LLM decode\n\n"
            "三、工业界实践\n"
            "- 视频 DiT（如 Sora 类）：序列长度极大（数万 token），需要 Ring Attention 或序列并行\n"
            "- 图像 DiT（如 Flux）：可批量处理多张图，利用 CUDA Graph 减少 launch overhead"
        ),
    },
    {
        "id": "aliyun-ai-inference-012",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "deepseek-v3",
        "difficulty": 4,
        "question": "DeepSeek-V3 有哪些关键的推理优化点？其 MoE 架构在推理部署时面临哪些挑战？",
        "key_points": [
            "DeepSeek-V3 核心架构：MoE(671B total/37B activated per token) + Multi-head Latent Attention(MLA) + DeepSeekMoE",
            "MLA优化：将传统 MHA 的 KV Cache 压缩为低秩潜在向量，显存占用降低 90%+，但对 decode 的计算量影响需评估",
            "MoE 推理挑战1：所有专家权重（671B）需要驻留显存或快速从 CPU/SSD 加载，显存需求大",
            "MoE 推理挑战2：专家负载不均衡——某些 expert 被频繁选择，热 expert 的 GPU 成为瓶颈",
            "DeepSeek 的解决方案：细粒度专家分割 + 共享专家 + 辅助损失路由平衡 + FP8 训练推理 + Multi-Token Prediction"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "MLA 的 KV Cache 压缩对推理延迟有什么影响？",
            "DeepSeek-V3 的 MoE 推理能否在单卡上部署？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "inference"],
        "source_note": "AIInfraGuide-综合面经题库-3",
        "reference_answer": (
            "DeepSeek-V3 是目前最前沿的 MoE 大模型之一，其推理优化在业界有重要参考价值。\n\n"
            "一、DeepSeek-V3 的关键推理优化\n\n"
            "1. Multi-head Latent Attention (MLA)\n"
            "- 核心创新：不直接存储完整的 KV Cache（每 token d_h × n_layers × 2），而是将 K 和 V 映射为低秩潜在表示\n"
            "- 推理时只需缓存低秩潜在向量（≤ 1/10 传统 KV Cache），显存节省 > 90%\n"
            "- 代价：decode 时需从潜在向量重建 K 和 V，增加少量计算，但总体 memory-bound 场景下收益巨大\n\n"
            "2. DeepSeekMoE 架构\n"
            "- 256 个专家中，每次激活 8 个（Top-8 routing）\n"
            "- 细粒度专家分割：将标准 FFN 拆分为更小的专家，每个专家参数量更小\n"
            "- 共享专家：部分专家始终激活，处理通用知识，减少路由偏差\n"
            "- 辅助损失：通过 load-balancing loss 避免某些专家被过度选择\n\n"
            "3. FP8 训练和推理\n"
            "- DeepSeek-V3 在训练阶段就使用 FP8 精度，推理天然兼容\n"
            "- FP8 相对于 FP16 显存减半，吞吐翻倍\n\n"
            "4. Multi-Token Prediction (MTP)\n"
            "- 一次推理预测多个未来 token\n"
            "- 在推理部署场景中可降低整体延迟（每次预测多个 token）\n\n"
            "二、MoE 推理部署的核心挑战\n"
            "1. 显存挑战：671B 参数全部需要驻留显存（最好是所有专家）\n"
            "2. 负载均衡：热专家过载导致某些 GPU 成为瓶颈\n"
            "3. 全量 vs 部分加载：小规模部署可将冷专家 offload 到 CPU/SSD，但增加延迟\n"
            "4. 批处理效率：不同 batch 的 token 路由到不同专家，降低 batch 内计算效率"
        ),
    },
    {
        "id": "aliyun-ai-training-003",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "all-reduce",
        "difficulty": 3,
        "question": "All-Reduce 的通信开销如何计算？NCCL 中包含哪些通信原语？Ring All-Reduce 和 Tree All-Reduce 各有什么优劣？",
        "key_points": [
            "All-Reduce 通信量：α (latency) + β × data_size (bandwidth term)，Ring 算法延迟为 2(N-1)α，带宽为 2(N-1)/N × data",
            "NCCL 核心原语：All-Reduce、All-Gather、Reduce-Scatter、Broadcast、Reduce、All-to-All、Send/Recv",
            "Ring All-Reduce：通过环形连接，使用 Reduce-Scatter + All-Gather 两步，带宽最优(数据量接近 2×data)但延迟随节点数线性增长",
            "Tree All-Reduce：使用二叉树拓扑，延迟 O(log N) 更低，但带宽利用率(数据量 2×logN×data 总传输)更高",
            "选型建议：大消息用 Ring（带宽优），小消息用 Tree（延迟优），NCCL 自动根据数据大小选择"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "在 8 节点 × 8 卡的集群中，All-Reduce 一次参数量更新需要几次通信？",
            "NVSHMEM 的 Put/Get 模型和 NCCL 的 collective 模型各适合什么场景？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "training"],
        "source_note": "AIInfraGuide-综合面经题库-5,3",
        "reference_answer": (
            "All-Reduce 是分布式训练中最核心的通信操作，理解其开销对估算训练效率至关重要。\n\n"
            "一、All-Reduce 通信开销计算\n\n"
            "通信开销建模：T = α（启动延迟）+ β × M（传输时间）\n"
            "其中 α 是每次通信的固定延迟（us 级），β 是每字节传输时间（带宽的倒数），M 是数据大小\n\n"
            "Ring All-Reduce 的开销：\n"
            "- 分为两步：Reduce-Scatter（每步传 M/N 数据，共 N-1 步）→ All-Gather（同样 N-1 步）\n"
            "- 总延迟：2(N-1) × α\n"
            "- 总数据量：2(N-1)/N × M ≈ 2M（当 N 较大时）\n"
            "- 带宽效率接近最优（每节点只发出 2×M/N 数据，只接收同样多）\n\n"
            "Tree All-Reduce 的开销：\n"
            "- 使用二叉树：先 Reduce 到根节点（向上传播），再 Broadcast 到所有节点（向下传播）\n"
            "- 延迟：2 × log2(N) × α（远低于 Ring 的 2(N-1) × α）\n"
            "- 总传输量：2 × (N-1) × M（所有中间节点的数据累加）\n"
            "- 带宽利用率较低，数据经过多个节点时需多次传输\n\n"
            "二、NCCL 核心通信原语\n"
            "- All-Reduce：所有节点求和，结果广播给所有节点（梯度同步）\n"
            "- All-Gather：每节点贡献一块数据，所有节点收集完整数据（张量并行的 f 操作）\n"
            "- Reduce-Scatter：求和后将结果分片分发（ZeRO-2 的梯度同步）\n"
            "- Broadcast：一个节点广播数据到所有节点（参数分发）\n"
            "- Reduce：所有节点求和，结果只给一个节点\n"
            "- All-to-All：每节点向所有其他节点发送不同数据（MoE 的 expert dispatch）\n\n"
            "三、NCCL 的自适应选择\n"
            "NCCL 内部会根据数据大小和拓扑自动选择算法：\n"
            "- 小数据（<256KB）：用 Tree 算法，延迟优先\n"
            "- 大数据（>=256KB）：用 Ring 算法，带宽优先\n"
            "- 最新 NCCL 还支持 CollNet（基于交换机的 in-network reduction）和 NVLS（NVLink Sharp）"
        ),
    },
    {
        "id": "aliyun-ai-inference-013",
        "vendor": "aliyun",
        "category": "inference",
        "subcategory": "kernel-fusion",
        "difficulty": 3,
        "question": "在进行大模型推理的 kernel fusion 时，通常采用哪种方式实现？什么情况下算子融合后性能反而下降？",
        "key_points": [
            "kernel fusion 方式1：手写 CUDA kernel——将多个操作融合为单一 kernel，最大化数据复用但不灵活",
            "kernel fusion 方式2：编译优化——通过 Triton/MLIR/XLA 等编译器自动融合，灵活但可能有次优情况",
            "方式3：使用 CuTe DSL 实现细粒度融合——控制 shared memory 和 register 的数据流",
            "性能下降场景1：融合后 register 压力过大→occupancy 降低→并行度下降",
            "性能下降场景2：不同操作的访存模式冲突→shared memory bank conflict 增加→实际带宽降低"
        ],
        "rubric": {"structure": 20, "depth": 30, "tradeoff": 25, "compliance": 15, "communication": 10},
        "follow_ups": [
            "Triton 和手写 CUDA 在算子融合方面各有什么优劣？",
            "在 Hopper 架构上 kernel fusion 有什么新特性可以应用？"
        ],
        "related_source_ids": [],
        "tags": ["sa", "aliyun", "ai", "inference"],
        "source_note": "AIInfraGuide-综合面经题库-4",
        "reference_answer": (
            "Kernel fusion 是推理优化中的核心技术，但不是银弹——融合不当会适得其反。\n\n"
            "一、Kernel Fusion 的实现方式\n\n"
            "1. 手写 CUDA Kernel\n"
            "- 优点：对数据流和硬件资源的完全控制，可以实现最优的数据复用\n"
            "- 典型应用：RMSNorm + Linear + SiLU 融合、Attention 中的 QK^T + softmax + V 融合\n"
            "- 缺点：开发成本高，需要在不同模型间重复适配\n\n"
            "2. Triton 编译优化\n"
            "- Triton 的 tiling 模型天然支持融合：将相邻的 element-wise 操作写入同一 kernel 的同一个 tile 循环\n"
            "- 优点：Python 接口，自动优化 block size 和 tiling 策略\n"
            "- 局限：对于不规则的计算模式（如 gather/scatter），性能可能不如手写 CUDA\n\n"
            "3. 编译器自动融合（XLA/TVM/MLIR）\n"
            "- 在计算图层面识别可融合的算子组合\n"
            "- 结合内存规划（buffer liveness analysis）最小化中间结果显存\n\n"
            "二、融合后性能下降的典型原因\n\n"
            "1. Register 压力过大\n"
            "- 融合操作越多，每个 thread 需要的寄存器越多\n"
            "- 当 register 需求超过 SM 的限制时，编译器会将部分数据 spill 到 local memory（L1 Cache），"
            "导致等效带宽降至 HBM 速度\n"
            "- 表现：occupancy（活跃 warp 数）大幅下降，GPU 算力得不到充分发挥\n\n"
            "2. Shared Memory Bank Conflict\n"
            "- 不同算子对 shared memory 的访问模式不同（如行 vs 列访问）\n"
            "- 融合后可能导致 bank conflict 增加，实际有效带宽下降\n"
            "- 需要手动添加 padding 或使用 swizzle 技术\n\n"
            "3. 调度开销\n"
            "- 如果融合后的 kernel 内部有太多条件分支（如不同的操作序列），warp divergence 会大幅增加\n"
            "- GPU 的 SIMT 模型下，不同线程走不同分支会串行执行\n\n"
            "最佳实践：优先融合 element-wise 操作（如 LayerNorm + Residual），审慎融合有复杂内存访问模式的操作。"
        ),
    },
]

def main():
    with open(TARGET, "a", encoding="utf-8") as f:
        for q in qs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"OK: appended {len(qs)} questions")

if __name__ == "__main__":
    main()
