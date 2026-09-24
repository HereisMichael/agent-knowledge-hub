---
source_id: llm101-attention-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# Attention 代码填空

## 练习 1：Scaled Dot-Product Attention

```python
import torch
import torch.nn.functional as F
import math

def scaled_dot_product_attention(Q, K, V, mask=None):
    """
    计算 Scaled Dot-Product Attention
    
    参数:
        Q: Query  (batch_size, n_heads, seq_len, d_k)
        K: Key    (batch_size, n_heads, seq_len, d_k)
        V: Value  (batch_size, n_heads, seq_len, d_v)
        mask: 可选的掩码 (batch_size, 1, 1, seq_len) 或 (batch_size, 1, seq_len, seq_len)
    
    返回:
        output: 注意力输出 (batch_size, n_heads, seq_len, d_v)
        attn_weights: 注意力权重 (batch_size, n_heads, seq_len, seq_len)
    """
    d_k = Q.size(-1)
    
    # 空白1: 计算缩放点积注意力分数
    # 提示: Q 和 K 的转置做矩阵乘法，然后除以缩放因子
    scores = _____
    
    if mask is not None:
        # 空白2: 将 mask 为 0 的位置填充为负无穷
        # 提示: 使用 masked_fill，mask == 0 的地方填 -inf
        scores = _____
    
    # 空白3: 对 scores 的最后一个维度做 softmax，得到注意力权重
    attn_weights = _____
    
    output = torch.matmul(attn_weights, V)
    return output, attn_weights
```

**提示:**
- 空白1：回忆公式 $\frac{QK^T}{\sqrt{d_k}}$，注意 K 需要转置最后两个维度
- 空白2：`masked_fill` 的第一个参数是布尔条件，第二个参数是填充值
- 空白3：softmax 的 dim 参数决定沿哪个维度归一化


---

## 练习 2：MultiHeadAttention.__init__

```python
import torch
import torch.nn as nn

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        """
        参数:
            d_model: 模型隐藏维度 (例如 512)
            n_heads: 注意力头数 (例如 8)
        """
        super().__init__()
        assert d_model % n_heads == 0, "d_model 必须能被 n_heads 整除"
        
        self.d_model = d_model
        self.n_heads = n_heads
        
        # 空白1: 计算每个头的维度
        self.d_k = _____
        
        # 空白2: 定义 Q、K、V 的线性投影层
        # 提示: 输入维度是 d_model，输出维度也是 d_model（包含所有头）
        self.W_q = _____
        self.W_k = _____
        self.W_v = _____
        
        # 空白3: 定义输出投影层（将拼接后的多头结果映射回 d_model）
        self.W_o = _____
    
    # forward 方法见练习 3
```

**提示:**
- 空白1：总维度平均分配到每个头
- 空白2：`nn.Linear` 的输入和输出维度分别是什么？
- 空白3：多头拼接后的维度是多少？


---

## 练习 3：MultiHeadAttention.forward

```python
def forward(self, Q, K, V, mask=None):
    """
    参数:
        Q, K, V: (batch_size, seq_len, d_model)
        mask: 可选掩码
    
    返回:
        output: (batch_size, seq_len, d_model)
    """
    batch_size = Q.size(0)
    
    # 步骤1: 线性投影
    Q = self.W_q(Q)  # (batch_size, seq_len, d_model)
    K = self.W_k(K)
    V = self.W_v(V)
    
    # 步骤2: 拆分为多头
    # 空白1: 将 (batch_size, seq_len, d_model) 变形为 (batch_size, n_heads, seq_len, d_k)
    # 提示: 先 view/reshape 再 transpose
    Q = _____
    K = _____
    V = _____
    
    # 步骤3: 计算注意力（使用练习1的函数）
    attn_output, attn_weights = scaled_dot_product_attention(Q, K, V, mask)
    # attn_output: (batch_size, n_heads, seq_len, d_k)
    
    # 步骤4: 拼接多头结果
    # 空白2: 将 (batch_size, n_heads, seq_len, d_k) 变回 (batch_size, seq_len, d_model)
    # 提示: 先 transpose 再 contiguous 再 view/reshape
    attn_output = _____
    
    # 步骤5: 输出投影
    # 空白3: 通过输出投影层
    output = _____
    
    return output
```

**提示:**
- 空白1：`view(batch_size, -1, self.n_heads, self.d_k)` 然后 `transpose(1, 2)`
- 空白2：是空白1的逆操作
- 空白3：一个简单的线性变换


---

## 参考来源

[docs/exercises/attention-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/attention-fill.md)
