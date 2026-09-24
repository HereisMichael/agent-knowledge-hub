---
source_id: llm101-scaling-laws-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# Scaling Laws 填空

## 练习 1: Transformer 参数量计算（Level 1-2）

### 背景

一个标准 decoder-only Transformer 的参数来自三部分：**Embedding 层**（$V \times d$）、**Attention**（Q/K/V/O 四个 $d \times d$ 矩阵）、**FFN**（两层线性变换，中间维度 $4d$）。总参数量近似 $N \approx V d + L \times (12 d^2 + 13d)$。

现代大模型（如 LLaMA）使用 GatedMLP（SwiGLU），FFN 有三个投影矩阵而非两个，参数量需相应调整。

### 任务

```python
import numpy as np

def count_transformer_params(
    vocab_size,      # V: 词表大小
    hidden_size,     # d: 隐藏维度
    num_layers,      # L: Transformer 层数
    num_heads,       # h: 注意力头数
    ffn_mult=4,      # FFN 中间维度倍数（标准 Transformer 为 4）
    use_gated_mlp=False,  # 是否使用 GatedMLP (SwiGLU)
    weight_tying=False    # 输入/输出 embedding 是否共享权重
):
    """
    计算 decoder-only Transformer 的参数量。
    不计 bias（现代大模型通常不用 bias）。
    """
    head_dim = hidden_size // num_heads
    ffn_hidden = hidden_size * ffn_mult

    # ===== 填空 1: Embedding 参数量 =====
    # Token embedding: V * d
    embedding_params = _____

    # ===== 填空 2: 单层 Attention 参数量 =====
    # Q, K, V 各一个投影矩阵: d -> d (即 d * d 每个)
    # Output 投影矩阵: d -> d
    # 共 4 个 d*d 的矩阵
    attn_params_per_layer = _____

    # ===== 填空 3: 单层 FFN 参数量 =====
    # 标准 FFN: up (d -> ffn_hidden) + down (ffn_hidden -> d)
    # GatedMLP: gate (d -> ffn_hidden) + up (d -> ffn_hidden) + down (ffn_hidden -> d)
    if use_gated_mlp:
        ffn_params_per_layer = _____  # 3 个矩阵
    else:
        ffn_params_per_layer = _____  # 2 个矩阵

    # ===== 填空 4: LayerNorm 参数量 =====
    # 每层 2 个 LayerNorm (attention 前 + FFN 前)，每个有 d 个 scale 参数
    # (RMSNorm 没有 bias/shift，只有 scale)
    ln_params_per_layer = _____

    # ===== 填空 5: 总参数量 =====
    # 所有层的参数 + embedding + 最终 LayerNorm
    # 如果 weight_tying=False, 输出 head 额外有 d*V 个参数
    total_per_layer = attn_params_per_layer + ffn_params_per_layer + ln_params_per_layer
    total = num_layers * total_per_layer + embedding_params + hidden_size  # 最终 LN

    if not weight_tying:
        output_head_params = _____
        total += output_head_params

    return {
        "embedding": embedding_params,
        "attn_per_layer": attn_params_per_layer,
        "ffn_per_layer": ffn_params_per_layer,
        "ln_per_layer": ln_params_per_layer,
        "total_per_layer": total_per_layer,
        "total": total,
    }
```

### 提示

- Embedding 参数量就是 $V \times d$
- Attention 的 Q/K/V/O 四个投影矩阵各为 $d \times d$，共 $4d^2$
- 标准 FFN 有 2 个矩阵：$d \times 4d$ 和 $4d \times d$，共 $2 \times d \times \text{ffn\_hidden} = 8d^2$
- GatedMLP 多一个 gate 矩阵，共 3 个 $d \times \text{ffn\_hidden}$ 的矩阵
- 输出 head 与 embedding 形状相同：$d \times V$


---

## 练习 2: 训练 FLOPs 估算（Level 2）

### 背景

Kaplan et al. (2020) 给出训练 FLOPs 的经验公式：$C \approx 6ND$（$N$ = 参数量，$D$ = token 数）。系数 6 = 2（前向）+ 4（反向约 2 倍前向），误差通常不超过 10%。

结合 GPU 理论算力（如 A100 BF16 = 312 TFLOPS）和实际利用率 MFU（通常 30%-50%），可以估算训练时间。

### 任务

```python
import numpy as np

def estimate_training_flops(num_params, num_tokens):
    """
    估算训练所需的总 FLOPs。
    
    参数:
        num_params: 模型参数量 N
        num_tokens: 训练 token 数 D
    返回:
        total_flops: 总 FLOPs (C ≈ 6ND)
    """
    # ===== 填空 1: 计算总 FLOPs =====
    total_flops = _____
    return total_flops


def estimate_training_time(
    num_params,
    num_tokens,
    num_gpus,
    gpu_peak_tflops,    # GPU 峰值算力 (TFLOPS, 如 A100 BF16 = 312)
    mfu=0.4             # Model FLOPs Utilization (通常 0.3-0.5)
):
    """
    估算训练时间。
    
    返回:
        training_hours: 训练时间（小时）
    """
    total_flops = estimate_training_flops(num_params, num_tokens)

    # ===== 填空 2: 计算实际每秒可用 FLOPs =====
    # 每块 GPU 的实际吞吐 = 峰值 * MFU
    # 总吞吐 = num_gpus * 实际吞吐
    # 注意单位: gpu_peak_tflops 是 TFLOPS (10^12)
    effective_flops_per_sec = _____

    # ===== 填空 3: 计算训练时间（秒 -> 小时） =====
    training_seconds = _____
    training_hours = _____
    return training_hours


def max_model_size(
    total_gpu_hours,
    num_gpus,
    gpu_peak_tflops,
    mfu=0.4,
    tokens_per_param=20   # Chinchilla 最优比例 D ≈ 20N
):
    """
    给定 GPU 算力预算，计算能训练的最大模型。
    
    利用 C = 6ND 和 D = tokens_per_param * N，
    得到 C = 6 * N * tokens_per_param * N = 6 * tokens_per_param * N^2
    """
    # ===== 填空 4: 计算可用总 FLOPs =====
    total_seconds = total_gpu_hours * 3600
    available_flops = _____

    # ===== 填空 5: 从 C = 6 * tokens_per_param * N^2 反推 N =====
    # N = sqrt(C / (6 * tokens_per_param))
    max_n = _____

    max_d = int(tokens_per_param * max_n)
    return int(max_n), max_d
```

### 提示

- $C = 6ND$ 是最核心的公式
- 实际吞吐 = GPU 数量 $\times$ 单卡峰值 $\times$ MFU
- 注意单位换算：TFLOPS = $10^{12}$ FLOPS，1 小时 = 3600 秒
- 反推模型大小时，将 $D = 20N$ 代入 $C = 6ND$ 得到 $C = 120N^2$，解出 $N = \sqrt{C/120}$


---

## 练习 3: Chinchilla 最优配比（Level 2-3）

### 背景

Chinchilla (Hoffmann et al., 2022) 核心发现：给定计算预算 $C$，$N$ 和 $D$ 应等比例缩放，最优比例约 $D \approx 20N$。70B 的 Chinchilla 在 1.4T token 上训练，性能超过 175B GPT-3（仅 300B token）。

Loss 模型：$L(N, D) = A/N^\alpha + B/D^\beta + L_\infty$，第一项是模型容量不足损失，第二项是数据不足损失。给定 $C = 6ND$，可求使 $L$ 最小的 $N^*$ 和 $D^*$。

### 任务

```python
import numpy as np
from scipy.optimize import minimize_scalar

# Chinchilla 论文中拟合的参数（近似值）
A = 406.4
B = 410.7
alpha = 0.34
beta = 0.28
L_inf = 1.69

def chinchilla_loss(N, D):
    """
    计算 Chinchilla Loss: L(N, D) = A/N^alpha + B/D^beta + L_inf
    """
    # ===== 填空 1: 实现 Chinchilla Loss 公式 =====
    loss = _____
    return loss


def chinchilla_optimal(C):
    """
    给定计算预算 C (FLOPs)，找到最优的 N 和 D。
    约束: C = 6 * N * D
    
    方法: 将 D = C / (6N) 代入 Loss 函数，对 N 求最优。
    """
    def loss_given_N(log_N):
        N = np.exp(log_N)
        # ===== 填空 2: 从 C 和 N 计算 D =====
        D = _____
        if D < 1:
            return 1e10  # 无效区域
        return chinchilla_loss(N, D)

    # 搜索范围: N 从 1M 到 1T
    result = minimize_scalar(
        loss_given_N,
        bounds=(np.log(1e6), np.log(1e12)),
        method='bounded'
    )

    N_opt = np.exp(result.x)
    # ===== 填空 3: 计算对应的最优 D =====
    D_opt = _____

    return int(N_opt), int(D_opt), result.fun


def compare_strategies(C):
    """
    对比三种策略:
    1. 过大模型 (Large N, Small D): 将 80% 计算花在更大的模型上
    2. 小模型多数据 (Small N, Large D): 将 20% 计算花在模型上
    3. Chinchilla 最优
    """
    N_opt, D_opt, loss_opt = chinchilla_optimal(C)

    # ===== 填空 4: 过大模型策略 =====
    # N 是最优值的 4 倍，D 从 C = 6ND 反推
    N_large = 4 * N_opt
    D_large = _____
    loss_large = chinchilla_loss(N_large, D_large)

    # ===== 填空 5: 小模型多数据策略 =====
    # N 是最优值的 1/4，D 从 C = 6ND 反推
    N_small = N_opt // 4
    D_small = _____
    loss_small = chinchilla_loss(N_small, D_small)

    return {
        "过大模型": {"N": N_large, "D": D_large, "loss": loss_large},
        "Chinchilla 最优": {"N": N_opt, "D": D_opt, "loss": loss_opt},
        "小模型多数据": {"N": N_small, "D": D_small, "loss": loss_small},
    }
```

### 提示

- Loss 公式直接对应三项之和：$A / N^\alpha + B / D^\beta + L_\infty$
- 约束条件 $C = 6ND$ 意味着 $D = C / (6N)$
- 过大模型和小模型策略的 $D$ 都通过 $D = C / (6N)$ 从同一总预算 $C$ 推出
- `scipy.optimize.minimize_scalar` 对 $\log N$ 搜索更稳定（避免数值问题）


---

## 练习 4: Loss 预测与幂律拟合（Level 2-3）

### 背景

Scaling Laws 最实用的应用：**用小模型实验预测大模型性能**。在 3-5 个规模的小模型上测量 loss，拟合 $L(N) = a N^{-\alpha} + L_\infty$ 的三个参数，即可预测更大模型的 loss。

拟合用 `scipy.optimize.curve_fit`（非线性最小二乘法）。注意 $L_\infty$ 的估计对外推影响很大。

### 任务

```python
import numpy as np
from scipy.optimize import curve_fit

# 模拟实验数据 (来自不同规模模型的训练结果)
# 这些数据点大致符合公开的 Scaling Laws 实验结果
experiment_data = {
    "N": np.array([1e7, 5e7, 1e8, 5e8, 1e9, 3e9]),    # 参数量
    "L": np.array([3.20, 2.85, 2.65, 2.35, 2.20, 2.05]) # 验证集 loss
}

def scaling_law_func(N, a, alpha, L_inf):
    """
    幂律公式: L(N) = a * N^(-alpha) + L_inf
    """
    # ===== 填空 1: 实现幂律公式 =====
    return _____


def fit_scaling_law(N_data, L_data):
    """
    拟合 Scaling Law 的三个参数: a, alpha, L_inf
    
    使用 scipy.optimize.curve_fit 做非线性最小二乘拟合。
    """
    # ===== 填空 2: 设置初始猜测值 =====
    # a: 控制曲线整体高度，通常在 1-1000 之间
    # alpha: 控制下降速率，通常在 0.05-1 之间
    # L_inf: 不可约损失，通常在 1-2 之间
    p0 = _____  # [a_init, alpha_init, L_inf_init]

    # ===== 填空 3: 调用 curve_fit 拟合 =====
    # curve_fit 返回 (最优参数, 协方差矩阵)
    popt, pcov = _____

    a, alpha, L_inf = popt
    # 计算参数的标准误差
    perr = np.sqrt(np.diag(pcov))

    return {
        "a": a, "alpha": alpha, "L_inf": L_inf,
        "std_errors": {"a": perr[0], "alpha": perr[1], "L_inf": perr[2]},
    }


def predict_loss(fit_result, N_target):
    """
    用拟合结果预测目标规模模型的 loss。
    """
    a = fit_result["a"]
    alpha = fit_result["alpha"]
    L_inf = fit_result["L_inf"]

    # ===== 填空 4: 预测 loss =====
    predicted_loss = _____

    return predicted_loss


def analyze_extrapolation(fit_result, N_data, L_data):
    """
    分析拟合质量和外推可靠性。
    """
    # ===== 填空 5: 计算训练数据上的 R^2 =====
    L_pred = np.array([predict_loss(fit_result, n) for n in N_data])
    ss_res = np.sum((L_data - L_pred) ** 2)
    ss_tot = _____  # 总变异 = sum((L_data - mean(L_data))^2)
    r_squared = _____

    return {
        "r_squared": r_squared,
        "residuals": L_data - L_pred,
        "L_inf": fit_result["L_inf"],
    }
```

### 提示

- 幂律公式：`a * N ** (-alpha) + L_inf`
- `curve_fit(f, xdata, ydata, p0=初始值)` 做非线性最小二乘拟合
- 初始猜测值不需要很精确，但量级要合理：`p0 = [100, 0.1, 1.8]` 是一个可以尝试的起点
- $R^2 = 1 - SS_{res} / SS_{tot}$，其中 $SS_{tot} = \sum(y_i - \bar{y})^2$


---

## 练习 5: 训练预算规划器（Level 3）

### 背景

本练习将前面所有知识整合为实用工具：给定 GPU 资源和预算，自动计算 Chinchilla 最优配置、估算训练时间、预测 loss。

规划器综合考虑：GPU 算力 -> 可用 FLOPs -> 最优 $N$ 和 $D$ -> 预测 loss -> 推荐模型架构（层数、隐藏维度等）。

### 任务

```python
import numpy as np
from scipy.optimize import minimize_scalar

# GPU 规格表
GPU_SPECS = {
    "A100_40G":  {"peak_tflops": 312, "memory_gb": 40, "cost_per_hour": 1.10},
    "A100_80G":  {"peak_tflops": 312, "memory_gb": 80, "cost_per_hour": 1.85},
    "H100_80G":  {"peak_tflops": 989, "memory_gb": 80, "cost_per_hour": 3.50},
    "H200_141G": {"peak_tflops": 989, "memory_gb": 141, "cost_per_hour": 4.50},
}

# Chinchilla 参数
CHINCHILLA = {"A": 406.4, "B": 410.7, "alpha": 0.34, "beta": 0.28, "L_inf": 1.69}


class TrainingBudgetPlanner:
    def __init__(self, gpu_type="A100_80G", num_gpus=8, mfu=0.4):
        assert gpu_type in GPU_SPECS, f"未知 GPU 类型: {gpu_type}"
        self.gpu = GPU_SPECS[gpu_type]
        self.gpu_type = gpu_type
        self.num_gpus = num_gpus
        self.mfu = mfu

    def compute_available_flops(self, budget_hours=None, budget_dollars=None):
        """
        计算给定预算下的可用 FLOPs。
        可以指定 GPU 小时预算或美元预算（二选一）。
        """
        if budget_dollars is not None:
            # ===== 填空 1: 从美元预算计算可用 GPU 小时 =====
            # 总费用 = num_gpus * cost_per_hour * hours
            budget_hours = _____

        # ===== 填空 2: 计算可用 FLOPs =====
        # 可用 FLOPs = GPU 数 * 峰值算力 * MFU * 总训练秒数
        total_seconds = budget_hours * 3600
        available_flops = _____

        return available_flops, budget_hours

    def find_optimal_config(self, available_flops):
        """
        给定可用 FLOPs，找到 Chinchilla 最优的 N 和 D。
        """
        C = available_flops
        p = CHINCHILLA

        def loss_given_log_N(log_N):
            N = np.exp(log_N)
            D = C / (6 * N)
            if D < 1:
                return 1e10
            # ===== 填空 3: 计算 Chinchilla Loss =====
            return _____

        result = minimize_scalar(
            loss_given_log_N,
            bounds=(np.log(1e6), np.log(1e12)),
            method='bounded'
        )

        N_opt = int(np.exp(result.x))
        D_opt = int(C / (6 * N_opt))
        loss_opt = result.fun
        return N_opt, D_opt, loss_opt

    def suggest_architecture(self, target_params):
        """
        根据目标参数量，推荐合理的模型架构。
        
        使用经验法则:
        - hidden_size 选择 128 的倍数（硬件友好）
        - depth-to-width 比例约 layers ≈ 2 * hidden_size / 128
        - FFN 使用 GatedMLP (SwiGLU), 中间维度约 8/3 * hidden_size
        """
        # ===== 填空 4: 估算 hidden_size =====
        # 近似: N ≈ 12 * L * d^2 (忽略 embedding 和小项)
        # 设 L ≈ d / 64 (经验比例), 则 N ≈ 12 * (d/64) * d^2 = 0.1875 * d^3
        # d ≈ (N / 0.1875) ^ (1/3)
        d_raw = _____
        hidden_size = int(round(d_raw / 128)) * 128  # 对齐到 128
        hidden_size = max(hidden_size, 256)

        # ===== 填空 5: 估算层数 =====
        # 层数 ≈ hidden_size / 64 (经验比例)
        num_layers = _____
        num_layers = max(num_layers, 4)

        num_heads = max(hidden_size // 128, 4)  # head_dim = 128
        ffn_hidden = int(hidden_size * 8 / 3)
        ffn_hidden = int(round(ffn_hidden / 256)) * 256  # 对齐到 256

        # 实际参数量估算 (GatedMLP)
        vocab_size = 32000
        params_per_layer = 4 * hidden_size**2 + 3 * hidden_size * ffn_hidden + 2 * hidden_size
        actual_params = num_layers * params_per_layer + 2 * vocab_size * hidden_size + hidden_size

        return {
            "hidden_size": hidden_size,
            "num_layers": num_layers,
            "num_heads": num_heads,
            "ffn_hidden": ffn_hidden,
            "vocab_size": vocab_size,
            "actual_params": actual_params,
        }

    def plan(self, budget_hours=None, budget_dollars=None):
        """
        完整规划流程: 预算 -> FLOPs -> 最优 N,D -> 架构 -> 训练时间
        """
        flops, hours = self.compute_available_flops(budget_hours, budget_dollars)
        N_opt, D_opt, loss_pred = self.find_optimal_config(flops)
        arch = self.suggest_architecture(N_opt)
        cost = hours * self.num_gpus * self.gpu["cost_per_hour"]

        return {
            "budget": {
                "gpu_type": self.gpu_type,
                "num_gpus": self.num_gpus,
                "hours": hours,
                "cost_usd": cost,
            },
            "compute": {
                "available_flops": flops,
                "mfu": self.mfu,
            },
            "optimal": {
                "N": N_opt,
                "D": D_opt,
                "D_over_N": D_opt / N_opt,
                "predicted_loss": loss_pred,
            },
            "architecture": arch,
        }
```

### 提示

- 美元预算转 GPU 小时：`hours = budget_dollars / (num_gpus * cost_per_hour)`
- 可用 FLOPs = GPU 数量 $\times$ 峰值 TFLOPS $\times 10^{12} \times$ MFU $\times$ 总秒数
- Chinchilla Loss 就是练习 3 中的公式：$A/N^\alpha + B/D^\beta + L_\infty$
- 从参数量估算 `hidden_size`：利用 $N \approx 0.1875 d^3$ 反推 $d$
- 层数的经验比例：`num_layers = hidden_size // 64`


---

## 参考来源

[docs/exercises/scaling-laws-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/scaling-laws-fill.md)
