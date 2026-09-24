---
source_id: llm101-quantization-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# 量化技术填空

## 练习 1: Absmax 对称量化（Level 2）

### 背景

Absmax 量化是最简单的量化方式：用张量中绝对值的最大值计算 scale，将浮点数映射到 $[-127, 127]$ 的 INT8 范围。因为以零为中心对称映射，所以称为"对称量化"。

核心公式：

$$s = \frac{\max(|x|)}{127}, \quad q = \text{round}\left(\frac{x}{s}\right), \quad \hat{x} = q \cdot s$$

### 任务

```python
import numpy as np

def absmax_quantize(x):
    """
    Absmax 对称量化到 INT8 [-127, 127]
    
    参数:
        x: np.ndarray, 浮点权重
    返回:
        q: np.ndarray, int8 量化值
        scale: float, 缩放因子
    """
    # ===== 填空 1: 计算 scale =====
    # scale = 绝对值最大值 / 127
    scale = _____

    # ===== 填空 2: 量化 =====
    # q = round(x / scale), 并裁剪到 [-127, 127]
    q = _____

    return q.astype(np.int8), scale


def absmax_dequantize(q, scale):
    """反量化: x_hat = q * scale"""
    # ===== 填空 3: 反量化 =====
    x_hat = _____
    return x_hat
```

### 提示

- `np.abs(x).max()` 计算绝对值最大值
- `np.round(...)` 做四舍五入
- `np.clip(arr, -127, 127)` 裁剪到范围内
- 反量化只需将整数乘以 scale


---

## 练习 2: Zero-Point 非对称量化（Level 2）

### 背景

Absmax 量化假设数据以零为中心，但实际权重/激活往往分布不对称（如 ReLU 后全为正值）。Zero-Point 量化引入偏移量 $z$，将 $[\min(x), \max(x)]$ 映射到 $[0, 255]$ 的 UINT8 范围。

核心公式：

$$s = \frac{\max(x) - \min(x)}{255}, \quad z = \text{round}\left(-\frac{\min(x)}{s}\right)$$

$$q = \text{round}\left(\frac{x}{s}\right) + z, \quad \hat{x} = s \cdot (q - z)$$

### 任务

```python
import numpy as np

def zeropoint_quantize(x):
    """
    Zero-Point 非对称量化到 UINT8 [0, 255]
    
    参数:
        x: np.ndarray, 浮点权重
    返回:
        q: np.ndarray, uint8 量化值
        scale: float, 缩放因子
        zero_point: int, 零点偏移
    """
    x_min, x_max = x.min(), x.max()

    # ===== 填空 1: 计算 scale =====
    scale = _____

    # ===== 填空 2: 计算 zero_point =====
    zero_point = _____

    # ===== 填空 3: 量化 =====
    # q = round(x / scale) + zero_point, 裁剪到 [0, 255]
    q = _____

    return q.astype(np.uint8), scale, int(zero_point)


def zeropoint_dequantize(q, scale, zero_point):
    """反量化: x_hat = scale * (q - zero_point)"""
    # ===== 填空 4: 反量化 =====
    x_hat = _____
    return x_hat
```

### 提示

- Scale 用的是数据的全范围 `(max - min)` 除以量化范围 255
- Zero-point 的含义：浮点零在量化空间中对应的整数值
- `np.clip(arr, 0, 255)` 裁剪到 UINT8 范围
- 反量化时先减去 zero_point 再乘以 scale


---

## 练习 3: Per-Channel vs Per-Tensor 量化（Level 2-3）

### 背景

Per-Tensor 量化用一个 scale 处理整个权重矩阵，而 Per-Channel 量化为每个输出通道（即权重矩阵的每一行）计算独立的 scale。当权重矩阵的不同通道数值范围差异很大时（存在 outlier channel），Per-Channel 量化可以显著降低误差。

$$\text{Per-Tensor}: \quad s = \frac{\max(|W|)}{127}$$

$$\text{Per-Channel}: \quad s_i = \frac{\max(|W[i, :]|)}{127}, \quad i = 0, 1, \ldots, C_{\text{out}} - 1$$

### 任务

```python
import numpy as np

def pertensor_absmax_quantize(W):
    """
    Per-Tensor Absmax 量化
    W: [out_channels, in_channels]
    """
    scale = np.abs(W).max() / 127
    q = np.clip(np.round(W / scale), -127, 127).astype(np.int8)
    return q, scale

def pertensor_dequantize(q, scale):
    return q.astype(np.float32) * scale


def perchannel_absmax_quantize(W):
    """
    Per-Channel Absmax 量化
    W: [out_channels, in_channels]
    每一行用独立的 scale
    
    返回:
        q: [out_channels, in_channels], int8
        scales: [out_channels], 每个通道的 scale
    """
    # ===== 填空 1: 对每一行计算 absmax =====
    # 结果形状应为 [out_channels]
    absmax_per_row = _____

    # ===== 填空 2: 计算每行的 scale =====
    # 形状 [out_channels], 注意防止除零
    scales = _____

    # ===== 填空 3: 量化（注意 scale 的广播） =====
    # 需要将 scales 扩展为 [out_channels, 1] 以便广播
    q = _____

    return q.astype(np.int8), scales


def perchannel_dequantize(q, scales):
    """Per-Channel 反量化"""
    # ===== 填空 4: 反量化（注意 scale 的广播） =====
    x_hat = _____
    return x_hat
```

### 提示

- `np.abs(W).max(axis=1)` 对每一行取绝对值最大值，结果形状 `[out_channels]`
- 广播时需要 reshape：`scales[:, np.newaxis]` 变成 `[out_channels, 1]`
- 防止除零可用 `np.maximum(absmax, 1e-8)`


---

## 练习 4: GPTQ 核心 -- 逐列量化与误差补偿（Level 3）

### 背景

GPTQ（Accurate Post-Training Quantization for Generative Pre-trained Transformers）的核心思想：逐列量化权重矩阵，每量化一列后，将量化误差补偿到尚未量化的列。这样后续列可以"纠正"前面列引入的误差，使整体量化误差最小化。

完整的 GPTQ 使用 Hessian 矩阵（$H = 2X^TX$）来决定误差分配权重。本练习使用简化版：将误差均匀分配到剩余列。

简化 GPTQ 流程（对权重矩阵 $W$ 的每一列 $j$）：
1. 量化第 $j$ 列：$\hat{W}_{:,j} = \text{quantize}(W_{:,j})$
2. 计算误差：$\delta_j = W_{:,j} - \hat{W}_{:,j}$
3. 将误差均匀分配到剩余列 $k > j$：$W_{:,k} \mathrel{+}= \frac{\delta_j}{n_{\text{remaining}}}$

### 任务

```python
import numpy as np

def quantize_column(col, n_bits=8):
    """对单列做 Absmax 量化并返回量化后的值"""
    qmax = 2 ** (n_bits - 1) - 1  # 127 for 8-bit
    scale = np.maximum(np.abs(col).max(), 1e-8) / qmax
    q = np.clip(np.round(col / scale), -qmax, qmax)
    return q * scale  # 返回反量化后的值


def naive_quantize(W, n_bits=8):
    """朴素量化: 逐列独立量化, 无误差补偿"""
    W_hat = np.zeros_like(W)
    for j in range(W.shape[1]):
        W_hat[:, j] = quantize_column(W[:, j], n_bits)
    return W_hat


def gptq_simplified(W, n_bits=8):
    """
    简化版 GPTQ: 逐列量化 + 均匀误差补偿
    
    W: [out_channels, in_channels]
    返回: W_hat, 量化后的权重矩阵
    """
    W = W.copy()  # 不修改原始矩阵
    n_cols = W.shape[1]
    W_hat = np.zeros_like(W)

    for j in range(n_cols):
        # ===== 填空 1: 量化当前列 =====
        W_hat[:, j] = _____

        # ===== 填空 2: 计算量化误差 =====
        error = _____

        # ===== 填空 3: 将误差均匀补偿到剩余未量化的列 =====
        n_remaining = n_cols - j - 1
        if n_remaining > 0:
            _____

    return W_hat
```

### 提示

- `quantize_column(W[:, j], n_bits)` 对第 $j$ 列量化
- 误差 = 原始值 - 量化值：`W[:, j] - W_hat[:, j]`
- 补偿：`W[:, j+1:] += error[:, np.newaxis] / n_remaining`
- 注意 `error` 形状是 `[out_channels]`，需要扩展维度才能加到 `W[:, j+1:]` 上


---

## 练习 5: SmoothQuant -- 激活平滑（Level 3）

### 背景

LLM 推理中，激活（activation）往往包含 outlier（少数通道的值远大于其他通道），这使得激活量化非常困难。SmoothQuant 的核心思想：通过数学等价变换，将激活的量化难度转移到权重上。

对于线性层 $Y = XW$，SmoothQuant 引入 per-channel 的平滑因子 $s$：

$$Y = XW = (X \text{diag}(s)^{-1}) \cdot (\text{diag}(s) W) = \hat{X} \hat{W}$$

其中 $\hat{X} = X / s$（激活除以 $s$，减小 outlier），$\hat{W} = s \cdot W$（权重乘以 $s$，吸收难度）。

平滑因子的计算：

$$s_j = \frac{\max(|X_{:,j}|)^{\alpha}}{\max(|W_{j,:}|)^{1-\alpha}}$$

其中 $\alpha \in [0, 1]$ 控制难度在激活和权重之间的分配比例，通常取 $\alpha = 0.5$。

### 任务

```python
import numpy as np

def compute_smooth_factor(X, W, alpha=0.5):
    """
    计算 SmoothQuant 的平滑因子
    
    X: [n_tokens, dim]  校准数据的激活值
    W: [dim, out_dim]   权重矩阵
    alpha: float, 平滑强度 (0=全部转移到权重, 1=保持激活不变)
    
    返回:
        s: [dim], per-channel 平滑因子
    """
    # ===== 填空 1: 计算激活每个通道的最大绝对值 =====
    # act_scales[j] = max(|X[:, j]|), 形状 [dim]
    act_scales = _____

    # ===== 填空 2: 计算权重每个输入通道的最大绝对值 =====
    # weight_scales[j] = max(|W[j, :]|), 形状 [dim]
    weight_scales = _____

    # ===== 填空 3: 计算平滑因子 =====
    # s = act_scales^alpha / weight_scales^(1-alpha)
    s = _____

    return s


def apply_smoothing(X, W, s):
    """
    应用平滑变换
    
    返回:
        X_smooth: X / s  (按列除)
        W_smooth: diag(s) @ W  (按行乘)
    """
    # ===== 填空 4: 平滑激活 =====
    X_smooth = _____

    # ===== 填空 5: 平滑权重 =====
    W_smooth = _____

    return X_smooth, W_smooth
```

### 提示

- `np.abs(X).max(axis=0)` 对每列取最大绝对值，形状 `[dim]`
- `np.abs(W).max(axis=1)` 对每行取最大绝对值，形状 `[dim]`
- 幂运算：`arr ** alpha`
- 平滑激活：`X / s[np.newaxis, :]`（广播到每行）
- 平滑权重：`s[:, np.newaxis] * W`（广播到每列）


---

## 参考来源

[docs/exercises/quantization-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/quantization-fill.md)
