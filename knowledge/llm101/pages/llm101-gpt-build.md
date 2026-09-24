---
source_id: llm101-gpt-build
corpus: llm101
type: exercise
topic: build
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# GPT 实现挑战

# GPT 实现挑战 (Level 4)

> **难度:** 困难 | **前置知识:** Transformer 全部内容、PyTorch 熟练使用 | **预计时间:** 3-5 小时

## 挑战目标

从零实现一个可训练、可推理的 mini-GPT 模型。不使用 `nn.TransformerDecoderLayer` 等高层封装，所有核心组件手写。

完成后，你的模型应该能在一个小数据集（如莎士比亚全集 / 唐诗三百首）上训练，并生成连贯的文本。

---

## 热身练习

在挑战完整模型之前，先完成以下三个小练习，确保你掌握了核心组件。

### 热身 1：手写 GELU 激活函数

GELU 的数学定义为 $\text{GELU}(x) = x \cdot \Phi(x)$，其中 $\Phi(x)$ 是标准正态分布的 CDF。

GPT-2 使用的是 tanh 近似版本：

$$\text{GELU}(x) \approx x \cdot \frac{1}{2}\left[1 + \tanh\left(\sqrt{\frac{2}{\pi}}(x + 0.044715 x^3)\right)\right]$$

```python
import torch
import math

def gelu(x):
    """
    实现 GELU 激活函数（tanh 近似版本）
    提示: 使用 torch.tanh, torch.pow, math.sqrt, torch.pi
    """
    # TODO: 你的实现
    pass

# 测试
x = torch.tensor([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0])
result = gelu(x)
expected = torch.tensor([-0.0454, -0.1588, -0.1543, 0.0000, 0.3457, 0.8412, 1.9546])
assert torch.allclose(result, expected, atol=1e-4), \
    f"GELU 输出不正确!\n得到: {result}\n期望: {expected}"
print("GELU 测试通过!")
```

### 热身 2：构造因果掩码

因果掩码是 Decoder-Only 模型的核心——确保每个 token 只能看到自己和之前的 token。

```python
import torch
import torch.nn.functional as F

def create_causal_mask(seq_len, neg_inf=-1e5):
    """
    构造 additive 因果掩码

    返回: (seq_len, seq_len) 的矩阵
          下三角（含对角线）= 0，上三角 = neg_inf

    提示: 使用 torch.tril 和 torch.ones
    """
    # TODO: 你的实现
    pass

# 测试
mask = create_causal_mask(4)
print(mask)
# 期望输出:
# tensor([[     0., -100000., -100000., -100000.],
#         [     0.,      0., -100000., -100000.],
#         [     0.,      0.,      0., -100000.],
#         [     0.,      0.,      0.,      0.]])

# 验证 softmax 后的效果
scores = torch.zeros(4, 4)  # 假设注意力分数全为 0
masked_scores = scores + mask
probs = F.softmax(masked_scores, dim=-1)
print(probs)
# 期望: 位置 0 只看自己（概率 1.0），位置 3 均匀看所有（各 0.25）
assert torch.allclose(probs[0], torch.tensor([1.0, 0.0, 0.0, 0.0]), atol=1e-4)
assert torch.allclose(probs[3], torch.tensor([0.25, 0.25, 0.25, 0.25]), atol=1e-4)
print("因果掩码测试通过!")
```

### 热身 3：实现 KV Cache 更新

KV Cache 的核心操作是：每生成一个新 token 时，将其 K、V 追加到缓存中。

```python
import torch

def update_kv_cache(kv_cache, new_k, new_v):
    """
    更新 KV Cache

    参数:
        kv_cache: None（首次调用）或 [cached_k, cached_v]
                  cached_k/v shape: (batch, cached_len, dim)
        new_k: 新 token 的 Key (batch, new_len, dim)
        new_v: 新 token 的 Value (batch, new_len, dim)

    返回:
        updated_cache: [full_k, full_v]
        full_k: (batch, total_len, dim)
        full_v: (batch, total_len, dim)

    提示: 首次调用直接存储，后续用 torch.cat 拼接
    """
    # TODO: 你的实现
    pass

# 测试
batch, dim = 2, 4

# 第一步：prefill，输入 3 个 token
k1 = torch.randn(batch, 3, dim)
v1 = torch.randn(batch, 3, dim)
cache = update_kv_cache(None, k1, v1)
assert cache[0].shape == (2, 3, 4), f"Prefill 后 K shape 错误: {cache[0].shape}"

# 第二步：decode，输入 1 个新 token
k2 = torch.randn(batch, 1, dim)
v2 = torch.randn(batch, 1, dim)
cache = update_kv_cache(cache, k2, v2)
assert cache[0].shape == (2, 4, 4), f"Decode 后 K shape 错误: {cache[0].shape}"

# 第三步：再生成一个 token
k3 = torch.randn(batch, 1, dim)
v3 = torch.randn(batch, 1, dim)
cache = update_kv_cache(cache, k3, v3)
assert cache[0].shape == (2, 5, 4), f"第二次 Decode 后 K shape 错误: {cache[0].shape}"

# 验证拼接正确性
assert torch.equal(cache[0][:, :3, :], k1)
assert torch.equal(cache[0][:, 3:4, :], k2)
assert torch.equal(cache[0][:, 4:5, :], k3)
print("KV Cache 测试通过!")
```

---

## 需求规格

### 模型配置

```python
config = {
    "vocab_size": 50257,       # GPT-2 词表大小（或自定义）
    "max_seq_len": 256,        # 最大序列长度
    "d_model": 384,            # 隐藏维度
    "n_heads": 6,              # 注意力头数
    "n_layers": 6,             # Transformer 层数
    "d_ff": 1536,              # FFN 中间维度 (4 * d_model)
    "dropout": 0.1,            # Dropout 概率
}
```

### 必须实现的组件

1. **Token Embedding + Position Embedding**
2. **Causal Self-Attention**（带因果掩码）
3. **Feed-Forward Network**（带 GELU 激活）
4. **Layer Normalization**（Pre-Norm 架构）
5. **残差连接**
6. **语言模型头**（输出 logits over vocabulary）
7. **文本生成**（Top-k / Top-p 采样）

## 类骨架

以下是建议的类结构。你需要补全所有 `TODO` 部分。

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class GPTConfig:
    """模型配置"""
    def __init__(self, **kwargs):
        self.vocab_size = kwargs.get("vocab_size", 50257)
        self.max_seq_len = kwargs.get("max_seq_len", 256)
        self.d_model = kwargs.get("d_model", 384)
        self.n_heads = kwargs.get("n_heads", 6)
        self.n_layers = kwargs.get("n_layers", 6)
        self.d_ff = kwargs.get("d_ff", 1536)
        self.dropout = kwargs.get("dropout", 0.1)


class CausalSelfAttention(nn.Module):
    """因果自注意力层"""

    def __init__(self, config: GPTConfig):
        super().__init__()
        assert config.d_model % config.n_heads == 0

        # TODO: 定义 Q、K、V 投影层（可以用一个合并的线性层）
        # 提示: 参考 nn.Linear(d_model, d_model * 3)，一次性投影 QKV
        # TODO: 定义输出投影层
        # TODO: 注册因果掩码 buffer（下三角矩阵）
        # 提示: self.register_buffer('mask', torch.tril(...))
        # TODO: 定义 dropout

        self.n_heads = config.n_heads
        self.d_k = config.d_model // config.n_heads

    def forward(self, x):
        """
        参数: x (batch_size, seq_len, d_model)
        返回: (batch_size, seq_len, d_model)
        """
        B, T, C = x.size()

        # TODO: 计算 Q, K, V（用合并投影后 split）
        # TODO: reshape 为多头: (B, T, C) → (B, n_heads, T, d_k)
        # TODO: 计算注意力分数 S = Q @ K^T / sqrt(d_k)
        # TODO: 应用因果掩码（只截取 [:T, :T] 部分）
        # TODO: softmax + dropout
        # TODO: 加权求和 Z = P @ V
        # TODO: 合并多头 (B, n_heads, T, d_k) → (B, T, C)，输出投影

        pass


class FeedForward(nn.Module):
    """前馈网络 (FFN)"""

    def __init__(self, config: GPTConfig):
        super().__init__()

        # TODO: 两层线性变换 + GELU 激活 + Dropout
        # 结构: d_model → d_ff → d_model
        # 提示: nn.Linear(d_model, d_ff), nn.GELU(), nn.Linear(d_ff, d_model), nn.Dropout

        pass

    def forward(self, x):
        # TODO
        pass


class TransformerBlock(nn.Module):
    """一个 Transformer Decoder 块 (Pre-Norm 架构)"""

    def __init__(self, config: GPTConfig):
        super().__init__()

        # TODO: 定义 ln1, attn, ln2, ffn
        # 提示: 用 nn.LayerNorm(d_model) 或手写 LayerNorm

        pass

    def forward(self, x):
        """
        Pre-Norm 架构:
            x = x + Attention(LayerNorm(x))
            x = x + FFN(LayerNorm(x))
        注意: 残差连接不经过 LayerNorm!
        """
        # TODO
        pass


class MiniGPT(nn.Module):
    """完整的 GPT 模型"""

    def __init__(self, config: GPTConfig):
        super().__init__()
        self.config = config

        # TODO: Token Embedding (nn.Embedding)
        # TODO: Position Embedding (nn.Embedding，可学习的)
        # TODO: Dropout
        # TODO: N 个 TransformerBlock (nn.ModuleList)
        # TODO: 最终的 LayerNorm（Pre-Norm 架构必须有!）
        # TODO: 语言模型头 (nn.Linear，映射到 vocab_size)
        # 进阶: LM head 可以与 Token Embedding 共享权重 (weight tying)

        pass

    def forward(self, idx, targets=None):
        """
        参数:
            idx: token indices (batch_size, seq_len)
            targets: 目标 token indices (batch_size, seq_len)，训练时提供

        返回:
            logits: (batch_size, seq_len, vocab_size)
            loss: 交叉熵损失（仅在提供 targets 时返回）
        """
        B, T = idx.size()
        assert T <= self.config.max_seq_len

        # TODO: Token Embedding + Position Embedding + Dropout
        # 提示: pos = torch.arange(T, device=idx.device)
        # TODO: 依次通过所有 TransformerBlock
        # TODO: 最终 LayerNorm
        # TODO: 语言模型头 → logits

        # TODO: 如果提供了 targets，计算交叉熵损失
        # 提示: logits 和 targets 需要 reshape
        # logits: (B*T, vocab_size), targets: (B*T,)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                targets.view(-1)
            )

        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens, temperature=1.0, top_k=None):
        """
        自回归文本生成

        参数:
            idx: 初始 token indices (batch_size, seq_len)
            max_new_tokens: 生成的最大 token 数
            temperature: 采样温度 (>1 更随机, <1 更确定)
            top_k: Top-k 采样的 k 值 (None 表示不使用)
        """
        for _ in range(max_new_tokens):
            # TODO: 截取最后 max_seq_len 个 token（防止超长）
            # TODO: 前向传播获取 logits
            # TODO: 取最后一个位置的 logits: logits[:, -1, :]
            # TODO: 除以 temperature
            # TODO: 可选 Top-k 过滤（将 top-k 之外的 logits 设为 -inf）
            # TODO: softmax → 概率 → torch.multinomial 采样
            # TODO: 拼接新 token
            pass

        return idx
```

## 训练脚本骨架

模型实现完成后，你还需要编写训练循环：

```python
# 伪代码框架
def train():
    # 1. 准备数据
    #    - 加载文本，用 tokenizer 编码
    #    - 切分为固定长度的训练样本
    #    - 构造 DataLoader

    # 2. 初始化模型和优化器
    #    - model = MiniGPT(config)
    #    - optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    #    AdamW 核心: w = w - lr * (m_hat / (sqrt(v_hat) + eps) + wd * w)

    # 3. 训练循环
    #    for epoch in range(n_epochs):
    #        for batch in dataloader:
    #            logits, loss = model(batch_x, batch_y)
    #            loss.backward()
    #            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    #            optimizer.step()
    #            optimizer.zero_grad()

    # 4. 生成测试
    #    model.eval()
    #    prompt = tokenizer.encode("从前有座山")
    #    generated = model.generate(prompt, max_new_tokens=200)
    #    print(tokenizer.decode(generated))
```

## 评估标准

### 基础要求（必须达成）

| 检查项 | 要求 |
|--------|------|
| 模型可实例化 | `MiniGPT(config)` 无报错 |
| 前向传播 | 输出 shape 正确 `(B, T, vocab_size)` |
| 损失计算 | 交叉熵损失可正常计算和反向传播 |
| 参数量合理 | ~25M 参数（给定默认 config） |
| 训练可收敛 | loss 在训练过程中持续下降 |
| 可生成文本 | `generate()` 能输出文本（哪怕质量不高） |

### 进阶要求（挑战自我）

| 检查项 | 要求 |
|--------|------|
| Weight Tying | Token Embedding 和 LM Head 共享权重 |
| 权重初始化 | 使用合理的初始化方案（如 Xavier / 正态分布缩放） |
| 学习率调度 | 使用 Cosine Annealing 或 Warmup + Decay |
| 梯度裁剪 | 使用 `clip_grad_norm_` |
| Top-k + Top-p | generate 方法同时支持 Top-k 和 Top-p 采样 |
| KV Cache | 推理时缓存 K、V 避免重复计算 |
| 生成质量 | 训练 1-2 小时后能生成基本通顺的文本 |

### 高阶挑战（选做）

- 替换位置编码为 RoPE（参考 [Llama 实现挑战](llama-build.md) 的 RoPE 部分）
- 替换 LayerNorm 为 RMSNorm
- 替换 GELU 为 SwiGLU
- 实现 GQA（Grouped-Query Attention）
- 用 Flash Attention 替代手写注意力

## 常见陷阱

在实现过程中，以下问题最容易踩坑：

1. **因果掩码的 shape 不对**：掩码应该是 `(1, 1, T, T)` 的下三角矩阵，注意在前向传播时只截取当前序列长度的部分
2. **损失计算时忘记 shift**：GPT 的训练目标是"给定前 n 个 token 预测第 n+1 个"，所以 logits 和 targets 需要错位一个位置
3. **Position Embedding 的索引**：应该是 `torch.arange(T)`，不要写成 token indices
4. **dropout 在推理时要关闭**：`model.eval()` 会自动处理，但要确认 `nn.Dropout` 而非手动 dropout
5. **数值溢出**：注意力分数在 softmax 前可能很大，确保用了缩放（除以 $\sqrt{d_k}$）

## 参考时间分配

| 阶段 | 内容 | 建议时间 |
|------|------|---------|
| 0 | 完成三个热身练习 | 30 分钟 |
| 1 | 实现 `CausalSelfAttention` | 45 分钟 |
| 2 | 实现 `FeedForward` + `TransformerBlock` | 30 分钟 |
| 3 | 实现 `MiniGPT`（forward + loss） | 45 分钟 |
| 4 | 实现 `generate` 方法 | 30 分钟 |
| 5 | 训练脚本 + 调试 | 60-90 分钟 |
| 6 | 进阶功能（可选） | 60+ 分钟 |

---

## 参考来源

[docs/exercises/gpt-build.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/gpt-build.md)
