---
source_id: llm101-transformer-quiz
corpus: llm101
type: exercise
topic: quiz
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# Transformer 概念题

## 第 1 题：为什么除以 $\sqrt{d_k}$？

在 Scaled Dot-Product Attention 的公式 $\text{Attention}(Q,K,V) = \text{softmax}(\frac{QK^T}{\sqrt{d_k}})V$ 中，为什么要除以 $\sqrt{d_k}$？

**A.** 为了让注意力权重的和等于 1

**B.** 为了防止点积值过大导致 softmax 进入梯度饱和区

**C.** 为了让 Q 和 K 的维度匹配

**D.** 为了节省计算量，降低浮点运算精度要求


---

## 第 2 题：Multi-Head vs Single-Head 的优势

Multi-Head Attention 相比 Single-Head Attention 的核心优势是什么？

**A.** 计算量更小，因为每个头的维度更低

**B.** 允许模型同时关注不同子空间中的不同位置的信息

**C.** 能处理更长的序列

**D.** 不需要位置编码就能捕捉位置信息


---

## 第 3 题：位置编码的必要性

为什么 Transformer 必须使用位置编码？

**A.** 为了让模型区分不同的 token

**B.** 为了减少注意力计算的复杂度

**C.** 因为 Self-Attention 对输入序列的顺序是置换不变的

**D.** 为了让模型能够处理变长序列


---

## 第 4 题：残差连接的作用

Transformer 中的残差连接（Residual Connection）主要解决什么问题？

**A.** 减少模型的参数量

**B.** 提高模型的推理速度

**C.** 缓解深层网络中的梯度消失问题，使梯度能够直接回传

**D.** 让模型能够学习非线性变换


---

## 第 5 题：Encoder vs Decoder 的关键区别

在原始 Transformer 中，Encoder 和 Decoder 最关键的结构区别是什么？

**A.** Encoder 使用 Multi-Head Attention，Decoder 使用 Single-Head Attention

**B.** Decoder 中的 Self-Attention 使用因果掩码（Causal Mask），防止看到未来位置

**C.** Encoder 有残差连接但 Decoder 没有

**D.** Encoder 处理固定长度的输入，Decoder 处理可变长度的输出


---

## 第 6 题：LayerNorm vs BatchNorm

Transformer 为什么使用 LayerNorm 而非 BatchNorm？

**A.** LayerNorm 的计算速度更快

**B.** LayerNorm 在每个样本内部独立归一化，不依赖 batch 中其他样本，更适合变长序列

**C.** BatchNorm 无法应用于 Transformer 的结构

**D.** LayerNorm 不需要可学习的参数


---

## 参考来源

[docs/exercises/transformer-quiz.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/transformer-quiz.md)
