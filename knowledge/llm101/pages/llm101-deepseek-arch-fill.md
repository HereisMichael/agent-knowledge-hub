---
source_id: llm101-deepseek-arch-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# DeepSeek 架构填空

## 练习 1: Multi-Latent Attention (MLA) -- KV 压缩（Level 2）

### 背景

MHA 推理时需缓存完整的 K、V，KV Cache 与 $n_\text{heads} \times d_\text{head}$ 成正比。GQA 通过共享 KV head 缓解，但压缩比有限。DeepSeek-V2 提出 MLA：用低秩投影将 KV 压缩到 latent 向量 $\mathbf{c}$。

MLA 核心流程：
1. **下投影**: $\mathbf{c} = W^{DKV} \mathbf{x}$，将 $d_\text{model}$ 压缩到 $d_c$ 维
2. **上投影**: $\mathbf{K} = W^{UK} \mathbf{c}$，$\mathbf{V} = W^{UV} \mathbf{c}$，从 latent 恢复 K/V
3. 推理时只缓存 $\mathbf{c}$（$d_c$ 维），而非完整 K+V（$2 \times n_\text{heads} \times d_\text{head}$ 维）

### 任务

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class MLAttention(nn.Module):
    """Multi-Latent Attention: KV 低秩压缩"""
    def __init__(
        self,
        d_model=2048,
        n_heads=16,
        d_head=128,
        d_c=512,       # latent 维度 (远小于 n_heads * d_head = 2048)
    ):
        super().__init__()
        self.n_heads = n_heads
        self.d_head = d_head
        self.d_c = d_c

        # Q 投影 (标准)
        self.W_q = nn.Linear(d_model, n_heads * d_head, bias=False)

        # ===== 填空 1: KV 下投影 — 将 d_model 压缩到 d_c =====
        self.W_dkv = _____  # 提示: nn.Linear(d_model, d_c)

        # ===== 填空 2: K 上投影 — 从 d_c 恢复到 n_heads * d_head =====
        self.W_uk = _____   # 提示: nn.Linear(d_c, n_heads * d_head)

        # ===== 填空 3: V 上投影 — 从 d_c 恢复到 n_heads * d_head =====
        self.W_uv = _____   # 提示: nn.Linear(d_c, n_heads * d_head)

        self.W_o = nn.Linear(n_heads * d_head, d_model, bias=False)

    def forward(self, x):
        """
        x: [bsz, seq_len, d_model]
        返回: [bsz, seq_len, d_model]
        """
        bsz, seq_len, _ = x.shape

        # Q: 标准投影
        Q = self.W_q(x).view(bsz, seq_len, self.n_heads, self.d_head).transpose(1, 2)

        # ===== 填空 4: KV 下投影得到 latent 向量 c =====
        c = _____  # 提示: self.W_dkv(x), shape [bsz, seq_len, d_c]

        # ===== 填空 5: 从 c 上投影恢复 K 和 V =====
        K = _____  # 提示: self.W_uk(c), 然后 view + transpose 成多头格式
        K = K.view(bsz, seq_len, self.n_heads, self.d_head).transpose(1, 2)
        V = _____  # 提示: self.W_uv(c), 然后 view + transpose
        V = V.view(bsz, seq_len, self.n_heads, self.d_head).transpose(1, 2)

        # 标准 Scaled Dot-Product Attention
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_head)
        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, V)

        out = out.transpose(1, 2).contiguous().view(bsz, seq_len, -1)
        return self.W_o(out), c  # 返回 c 用于缓存
```

### 提示

- `W_dkv` 将 `d_model` 压缩到 `d_c`，推理时只缓存 `c`
- 压缩比 = $\frac{n_\text{heads} \times d_\text{head}}{d_c}$，本例 $\frac{16 \times 128}{512} = 4\times$


---

## 练习 2: MLA -- RoPE 解耦（Level 2-3）

### 背景

RoPE 通过旋转 Q/K 注入位置信息。但在 MLA 中，若对压缩前的 K 施加 RoPE，$\mathbf{c}$ 会包含位置信息，破坏压缩的位置无关性。

DeepSeek-V2 的解决方案是 **RoPE 解耦**：将 Q/K 各拆为两部分：
- **nope 部分**: 不带位置编码，走压缩/恢复流程
- **rope 部分**: 单独投影并施加 RoPE，K 的 rope 部分不经过压缩

最终 attention score = $\mathbf{q}_\text{nope} \mathbf{k}_\text{nope}^T + \mathbf{q}_\text{rope} \mathbf{k}_\text{rope}^T$

### 任务

```python
def apply_rotary_pos_emb(x, cos, sin):
    """
    对 x 的最后一维施加 RoPE 旋转
    命名沿用 HuggingFace `transformers/models/llama/modeling_llama.py` 的 `apply_rotary_pos_emb`
    """
    d = x.shape[-1]
    x1, x2 = x[..., :d//2], x[..., d//2:]
    return torch.cat([x1 * cos - x2 * sin, x2 * cos + x1 * sin], dim=-1)

class MLAWithRoPE(nn.Module):
    def __init__(self, d_model=2048, n_heads=16, d_head=128,
                 d_head_rope=64, d_c=512):
        super().__init__()
        self.n_heads = n_heads
        self.d_head = d_head
        self.d_head_rope = d_head_rope
        self.d_head_nope = d_head - d_head_rope

        self.W_q = nn.Linear(d_model, n_heads * d_head, bias=False)
        self.W_dkv = nn.Linear(d_model, d_c, bias=False)
        self.W_uk = nn.Linear(d_c, n_heads * self.d_head_nope, bias=False)
        self.W_uv = nn.Linear(d_c, n_heads * d_head, bias=False)
        self.W_kr = nn.Linear(d_model, n_heads * d_head_rope, bias=False)  # rope 部分不压缩
        self.W_o = nn.Linear(n_heads * d_head, d_model, bias=False)

    def forward(self, x, cos, sin):
        """x: [bsz, seq_len, d_model], cos/sin: [1, 1, seq_len, d_rope//2]"""
        bsz, seq_len, _ = x.shape
        nh, d_nope, d_rope = self.n_heads, self.d_head_nope, self.d_head_rope

        Q = self.W_q(x).view(bsz, seq_len, nh, self.d_head).transpose(1, 2)

        # ===== 填空 1: 将 Q 拆分为 nope 和 rope 两部分 =====
        q_nope = _____  # 提示: Q[..., :d_nope]
        q_rope = _____  # 提示: Q[..., d_nope:]
        q_rope = apply_rotary_pos_emb(q_rope, cos, sin)

        # K 的 nope 部分: 从压缩向量恢复
        c = self.W_dkv(x)
        k_nope = self.W_uk(c).view(bsz, seq_len, nh, d_nope).transpose(1, 2)

        # ===== 填空 2: K 的 rope 部分 — 单独投影, 不经过压缩 =====
        k_rope = _____  # 提示: self.W_kr(x)
        k_rope = k_rope.view(bsz, seq_len, nh, d_rope).transpose(1, 2)
        k_rope = apply_rotary_pos_emb(k_rope, cos, sin)

        V = self.W_uv(c).view(bsz, seq_len, nh, self.d_head).transpose(1, 2)

        # ===== 填空 3: attention score = nope 部分 + rope 部分 =====
        score_nope = _____  # 提示: torch.matmul(q_nope, k_nope.transpose(-2, -1))
        score_rope = _____  # 提示: torch.matmul(q_rope, k_rope.transpose(-2, -1))
        scores = _____ / math.sqrt(self.d_head)  # 提示: 两部分相加

        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, V)
        out = out.transpose(1, 2).contiguous().view(bsz, seq_len, -1)
        return self.W_o(out), c, k_rope
```

### 提示

- Q 前 `d_nope` 维不带 RoPE，后 `d_rope` 维带 RoPE；K 的 rope 部分直接从 `x` 投影，不经过压缩
- 推理缓存 `c`（$d_c$）+ `k_rope`（$n_\text{heads} \times d_\text{rope}$），仍远小于 MHA


---

## 练习 3: DeepSeekMoE -- 共享专家 + 路由专家（Level 2-3）

### 背景

标准 MoE 中所有专家都通过路由竞争，但许多 token 需要通用知识（语法、常见实体），导致路由专家间存在冗余。DeepSeekMoE 将专家分为两类：
- **共享专家 (Shared Experts)**: 每个 token 都经过，捕捉通用知识
- **路由专家 (Routed Experts)**: Top-K 门控选择，捕捉专业化知识

最终输出 = 共享专家输出 + 路由专家加权输出。

### 任务

```python
class Expert(nn.Module):
    """单个专家: 标准 FFN"""
    def __init__(self, dim, hidden_dim=None):
        super().__init__()
        hidden_dim = hidden_dim or dim * 4
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)))


class DeepSeekMoE(nn.Module):
    def __init__(
        self,
        dim=1024,
        n_shared=2,         # 共享专家数
        n_routed=64,        # 路由专家数
        topk=6,             # 每 token 激活的路由专家数
        expert_hidden=2048, # 每个专家的隐藏层维度 (细粒度, 较小)
    ):
        super().__init__()
        self.n_shared = n_shared
        self.n_routed = n_routed
        self.topk = topk

        # 共享专家
        self.shared_experts = nn.ModuleList(
            [Expert(dim, expert_hidden) for _ in range(n_shared)]
        )
        # 路由专家
        self.routed_experts = nn.ModuleList(
            [Expert(dim, expert_hidden) for _ in range(n_routed)]
        )
        # 门控网络: 只对路由专家做路由
        self.gate = nn.Linear(dim, n_routed, bias=False)

    def forward(self, x):
        """
        x: [bsz, seq_len, dim]
        返回: [bsz, seq_len, dim]
        """
        bsz, seq_len, dim = x.shape
        N = bsz * seq_len
        x_flat = x.view(N, dim)

        # ===== 填空 1: 所有 token 过共享专家, 结果相加 =====
        shared_out = _____  # 提示: 初始化为 torch.zeros_like(x_flat)
        for expert in self.shared_experts:
            shared_out = _____  # 提示: 累加每个共享专家的输出

        # 路由: 对路由专家做 Top-K 选择
        gate_logits = self.gate(x_flat)               # [N, n_routed]
        gate_probs = F.softmax(gate_logits, dim=-1)
        topk_weight, topk_idx = torch.topk(gate_probs, k=self.topk, dim=-1)
        topk_weight = topk_weight / topk_weight.sum(dim=-1, keepdim=True)

        # ===== 填空 2: 路由专家的 dispatch-compute-combine =====
        routed_out = torch.zeros_like(x_flat)
        for i in range(self.n_routed):
            # 找出选择了第 i 个路由专家的 token
            mask = (topk_idx == i)                     # [N, topk] bool
            token_ids, topk_pos = torch.where(mask)
            if len(token_ids) == 0:
                continue
            # ===== 填空: 取出 token, 过专家, 加权累加 =====
            expert_input = _____    # 提示: x_flat[token_ids]
            expert_output = _____   # 提示: self.routed_experts[i](expert_input)
            cur_weight = _____      # 提示: topk_weight[token_ids, topk_pos]
            routed_out[token_ids] += _____  # 提示: cur_weight.unsqueeze(-1) * expert_output

        # ===== 填空 3: 合并共享专家和路由专家的输出 =====
        output = _____  # 提示: shared_out + routed_out

        return output.view(bsz, seq_len, dim)
```

### 提示

- 共享专家直接对所有 token 计算并求和，路由专家走标准 dispatch-compute-combine
- DeepSeek 设计：多路由专家（64）+ 小隐藏层 + 大 Top-K（6），提升专业化程度


---

## 练习 4: 辅助损失 Free 的负载均衡（Level 3）

### 背景

传统 MoE 用辅助损失强制 token 均匀分配给各专家，但损失权重难调节：太大影响性能，太小无法防止专家坍塌。DeepSeek-V3 提出 **辅助损失 Free** 方案：为每个专家维护 bias $b_i$，加到 gate logits 上影响路由选择，然后根据负载动态更新 bias。关键：bias 只影响 Top-K 选择，不参与最终权重计算，因此不影响梯度回传。

### 任务

```python
class AuxLossFreeMoE(nn.Module):
    def __init__(
        self,
        dim=1024,
        num_experts=64,
        topk=6,
        bias_update_speed=0.001,  # bias 更新步长
    ):
        super().__init__()
        self.num_experts = num_experts
        self.topk = topk
        self.bias_update_speed = bias_update_speed

        self.experts = nn.ModuleList(
            [Expert(dim) for _ in range(num_experts)]
        )
        self.gate = nn.Linear(dim, num_experts, bias=False)

        # ===== 填空 1: 为每个专家维护一个 bias, 不参与梯度 =====
        # 提示: 使用 register_buffer, 初始化为全零
        _____  # self.register_buffer('expert_bias', ...)

    def route_with_bias(self, x):
        """
        x: [N, dim]
        返回: topk_weight, topk_idx (权重用原始概率, 选择用加 bias 后的分数)
        """
        gate_logits = self.gate(x)  # [N, num_experts]

        # 原始概率 (用于最终加权)
        gate_probs = F.softmax(gate_logits, dim=-1)

        # ===== 填空 2: 在 gate logits 上加 bias, 用于 Top-K 选择 =====
        biased_logits = _____  # 提示: gate_logits + self.expert_bias

        # 用加了 bias 的 logits 做 Top-K 选择
        _, topk_idx = torch.topk(biased_logits, k=self.topk, dim=-1)

        # 但权重使用原始概率 (不含 bias)
        topk_weight = gate_probs.gather(1, topk_idx)
        topk_weight = topk_weight / topk_weight.sum(dim=-1, keepdim=True)

        return topk_weight, topk_idx

    @torch.no_grad()
    def update_bias(self, topk_idx, N):
        """
        根据实际负载动态更新 bias
        topk_idx: [N, topk]
        N: 总 token 数
        """
        # 统计每个专家被选中的次数
        expert_counts = torch.zeros(self.num_experts, device=topk_idx.device)
        for k in range(self.topk):
            expert_counts.scatter_add_(
                0, topk_idx[:, k],
                torch.ones(N, device=topk_idx.device)
            )

        # 理想的均匀负载
        ideal_count = N * self.topk / self.num_experts

        # ===== 填空 3: 根据负载偏差更新 bias =====
        # 负载过高 -> 降低 bias, 负载过低 -> 提高 bias
        load_diff = _____  # 提示: expert_counts - ideal_count
        self.expert_bias -= _____  # 提示: self.bias_update_speed * load_diff

    def forward(self, x):
        bsz, seq_len, dim = x.shape
        x_flat = x.view(-1, dim)
        N = x_flat.shape[0]

        topk_weight, topk_idx = self.route_with_bias(x_flat)

        # dispatch-compute-combine (同练习 3, 此处省略细节)
        y = torch.zeros_like(x_flat)
        for i in range(self.num_experts):
            tok, pos = torch.where(topk_idx == i)
            if len(tok) == 0: continue
            y[tok] += topk_weight[tok, pos].unsqueeze(-1) * self.experts[i](x_flat[tok])

        if self.training:
            self.update_bias(topk_idx, N)
        return y.view(bsz, seq_len, dim)
```

### 提示

- `register_buffer` 使 bias 随模型保存但不参与梯度
- 更新规则：`bias -= speed * (actual - ideal)`，简单负反馈控制


---

## 练习 5: KV Cache 大小计算综合题（Level 1-2）

### 背景

KV Cache 是 LLM 推理的核心显存消耗，直接决定最大 batch size 和序列长度。考虑以下三种配置（均为单层）：

| 参数 | 值 |
|------|-----|
| $d_\text{model}$ | 4096 |
| $n_\text{heads}$ (Q heads) | 32 |
| $d_\text{head}$ | 128 |
| 数据类型 | float16 (2 bytes) |

三种注意力方案：
- **MHA**: 每个 head 独立存储 K 和 V
- **GQA**: $n_\text{kv\_heads} = 8$，即每 4 个 Q head 共享 1 组 KV
- **MLA**: $d_c = 512$（latent 维度），额外有 $d_\text{rope} = 64$（每头 rope 维度，共 $n_\text{heads}$ 头的 k_rope）

### 任务

```python
def kv_cache_analysis():
    # 模型参数
    n_heads, d_head = 32, 128
    n_kv_heads_gqa = 8       # GQA 的 KV head 数
    d_c, d_rope = 512, 64    # MLA latent 维度 / 每头 rope 维度
    bpw = 2                  # bytes per weight (float16)
    n_layers = 60

    # ===== 填空 1: 每 token 每层 KV Cache 维度 =====
    dims_mha = _____  # 提示: n_heads * d_head * 2
    dims_gqa = _____  # 提示: n_kv_heads_gqa * d_head * 2
    dims_mla = _____  # 提示: d_c + n_heads * d_rope

    for name, d in [("MHA", dims_mha), ("GQA", dims_gqa), ("MLA", dims_mla)]:
        print(f"{name}: {d} dims = {d * bpw} bytes/token/layer")

    # ===== 填空 2: 总 KV Cache (batch=32, seq=4096) =====
    bs, seq = 32, 4096
    cache_mha = _____  # 提示: bs * seq * n_layers * dims_mha * bpw
    cache_gqa = _____
    cache_mla = _____
    GB = 1024 ** 3
    for name, c in [("MHA", cache_mha), ("GQA", cache_gqa), ("MLA", cache_mla)]:
        print(f"{name}: {c / GB:.2f} GB")

    # ===== 填空 3: 压缩比 =====
    ratio_gqa = _____  # 提示: dims_mha / dims_gqa
    ratio_mla = _____  # 提示: dims_mha / dims_mla
    print(f"GQA vs MHA: {ratio_gqa:.1f}x,  MLA vs MHA: {ratio_mla:.1f}x")

    # 40GB 显存预算下最大序列长度 (bs=1)
    budget = 40 * GB
    for name, d in [("MHA", dims_mha), ("GQA", dims_gqa), ("MLA", dims_mla)]:
        print(f"{name} max_seq (bs=1): {budget // (n_layers * d * bpw):,}")

kv_cache_analysis()
```

### 提示

- MHA: $n_\text{heads} \times d_\text{head} \times 2$; GQA: $n_\text{kv\_heads} \times d_\text{head} \times 2$; MLA: $d_c + n_\text{heads} \times d_\text{rope}$
- 总显存 = batch $\times$ seq $\times$ layers $\times$ dims $\times$ bytes


---

## 参考来源

[docs/exercises/deepseek-arch-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/deepseek-arch-fill.md)
