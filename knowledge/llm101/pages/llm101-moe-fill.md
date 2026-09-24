---
source_id: llm101-moe-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# MoE 代码填空

## 练习 1: Top-K 路由（Level 2）

### 背景

MoE 的核心是门控路由：给定一个 token 的特征向量，路由网络输出每个专家的权重，然后选择 Top-K 个专家进行计算。非 Top-K 专家不参与计算，这就是"稀疏"的含义。

路由流程：
1. 门控网络计算 logits: `gate(x)` -> `[num_experts]`
2. Softmax 得到概率分布
3. Top-K 选择 K 个专家
4. 对选中的 K 个专家的权重重新归一化

### 任务

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class Expert(nn.Module):
    def __init__(self, dim=512):
        super().__init__()
        self.w = nn.Linear(dim, dim)
    def forward(self, x):
        return self.w(x)

class SparseMoE(nn.Module):
    def __init__(self, dim=512, num_experts=8, topk=2):
        super().__init__()
        self.dim = dim
        self.num_experts = num_experts
        self.topk = topk
        self.experts = nn.ModuleList(
            [Expert(dim=dim) for _ in range(num_experts)]
        )
        self.gate = nn.Linear(dim, num_experts)

    def route(self, x):
        """
        x: [bsz, seq_len, dim]
        返回:
            topk_weight: [bsz, seq_len, topk]  归一化权重
            topk_idx:    [bsz, seq_len, topk]  专家 ID
        """
        # ===== 填空 1: 计算门控 logits 并做 softmax =====
        logits = _____           # 提示: self.gate(x)
        weight = _____           # 提示: F.softmax, 在最后一维

        # ===== 填空 2: 选出 Top-K =====
        topk_weight, topk_idx = _____  # 提示: torch.topk

        # ===== 填空 3: 对选中的 K 个权重重新归一化 =====
        topk_weight = _____  # 提示: 除以 sum, 保证和为 1

        return topk_weight, topk_idx
```

### 提示

- `torch.topk(tensor, k=K, dim=-1)` 返回 `(values, indices)`
- 归一化：`v / v.sum(dim=-1, keepdim=True)`


---

## 练习 2: 稀疏 MoE Forward — dispatch-compute-combine（Level 3）

### 背景

高效的 MoE forward 分为三个阶段：

1. **Dispatch（分发）**: 根据路由结果，将 token 分组到各专家。对每个专家，找出哪些 token 选择了它。
2. **Compute（计算）**: 每个专家只对分配给它的 token 做 forward，而非所有 token。
3. **Combine（聚合）**: 将各专家的输出按路由权重加权求和，得到最终输出。

这种实现避免了对未被选中的专家做无效计算。

### 任务

```python
class SparseMoEEfficient(nn.Module):
    def __init__(self, dim=512, num_experts=8, topk=2):
        super().__init__()
        self.dim = dim
        self.num_experts = num_experts
        self.topk = topk
        self.experts = nn.ModuleList(
            [Expert(dim=dim) for _ in range(num_experts)]
        )
        self.gate = nn.Linear(dim, num_experts)

    def forward(self, x):
        """
        x: [bsz, seq_len, dim]
        """
        bsz, seq_len, dim = x.shape
        N = bsz * seq_len
        x_flat = x.view(N, dim)  # 展平为 [N, dim]

        # 0. Gate
        gates = self.gate(x_flat)
        weight = F.softmax(gates, dim=-1)
        v, idx = torch.topk(weight, dim=-1, k=self.topk)
        v = v / v.sum(dim=-1, keepdim=True)

        # ===== 填空 1: Dispatch — 找出每个专家对应的 token =====
        token_to_expert = [None] * self.num_experts
        for i in range(self.num_experts):
            # torch.where(idx == i) 返回 (token_indices, topk_position)
            token_ids = torch.where(idx == i)
            # ===== 填空: 判断该专家是否被选中 =====
            if _____:  # 提示: 检查 token_ids[0] 是否为空
                continue
            token_to_expert[i] = token_ids

        # ===== 填空 2: Compute — 每个专家只计算被分配的 token =====
        expert_outputs = [None] * self.num_experts
        for i in range(self.num_experts):
            if token_to_expert[i] is not None:
                cur_token_ids = token_to_expert[i][0]  # 被选中的 token 下标
                dispatch_x = _____  # 提示: 从 x_flat 中取出对应 token
                expert_outputs[i] = _____  # 提示: 用第 i 个专家计算

        # ===== 填空 3: Combine — 按权重加权聚合 =====
        y = torch.zeros_like(x_flat)
        for i in range(self.num_experts):
            if expert_outputs[i] is not None:
                cur_token_ids = token_to_expert[i][0]
                cur_topk_pos = token_to_expert[i][1]
                # ===== 填空: 取出对应的路由权重 =====
                cur_weight = _____  # 提示: v[cur_token_ids, cur_topk_pos]
                # ===== 填空: 加权累加到输出 =====
                y[cur_token_ids, :] += _____  # 提示: weight * expert_output

        return y.reshape(bsz, seq_len, dim)
```

### 提示

- `torch.where(idx == i)` 返回一个 tuple：`(行索引, 列索引)`，行索引就是 token id
- `len(token_ids[0]) == 0` 表示没有 token 选择了该专家
- 权重需要 `unsqueeze(-1)` 才能与 `[N_i, dim]` 的专家输出广播相乘


---

## 练习 3: 负载均衡损失（Level 3）

### 背景

稀疏 MoE 训练中容易出现"专家坍塌"问题：路由网络倾向于总是选择同几个专家，导致大部分专家得不到训练。Switch Transformer 提出了 auxiliary load balancing loss 来缓解这一问题。

负载均衡损失的核心思想：
- 计算每个专家被选中的频率 $f_i$（即选择该专家的 token 比例）
- 计算每个专家的平均路由概率 $P_i$
- 损失 = $N \cdot \sum_{i=1}^{N} f_i \cdot P_i$，其中 $N$ 是专家数

理想情况下，所有专家被均匀选择，$f_i = 1/N$，$P_i = 1/N$。

### 任务

```python
def load_balancing_loss(
    gate_logits: torch.Tensor,   # [N, num_experts] 门控原始 logits
    topk_idx: torch.Tensor,      # [N, topk] 每个 token 选择的专家 ID
    num_experts: int,
):
    """
    Switch Transformer 风格的负载均衡损失
    N = bsz * seq_len (总 token 数)

    返回: 标量 loss
    """
    N = gate_logits.shape[0]

    # ===== 填空 1: 计算每个专家的路由概率均值 P_i =====
    # gate_probs: [N, num_experts]
    gate_probs = _____  # 提示: softmax(gate_logits)
    # P: [num_experts]，每个专家在所有 token 上的平均概率
    P = _____  # 提示: 在 token 维度求均值

    # ===== 填空 2: 计算每个专家被选中的频率 f_i =====
    # 构造 one-hot: [N, num_experts]
    # topk_idx 中每个 token 有 topk 个专家被选中
    expert_mask = torch.zeros(N, num_experts, device=gate_logits.device)
    for k in range(topk_idx.shape[1]):
        # ===== 填空: 对每个 topk 位置，标记被选中的专家 =====
        _____  # 提示: scatter_ 或手动索引

    # f: [num_experts]，每个专家被选择的 token 比例
    f = _____  # 提示: expert_mask 在 token 维度求均值

    # ===== 填空 3: 计算 auxiliary loss =====
    # loss = num_experts * sum(f_i * P_i)
    loss = _____

    return loss
```

### 提示

- `F.softmax(gate_logits, dim=-1)` 得到路由概率
- `P = gate_probs.mean(dim=0)` 得到每个专家的平均路由概率
- `expert_mask.scatter_(1, topk_idx[:, k:k+1], 1.0)` 可将选中的专家位置标 1
- `f = expert_mask.mean(dim=0)` 得到频率
- 最终 loss = `num_experts * (f * P).sum()`


---

## 参考来源

[docs/exercises/moe-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/moe-fill.md)
