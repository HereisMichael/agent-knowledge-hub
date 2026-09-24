---
source_id: llm101-lora-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# LoRA 代码填空

## 练习 1：LoRA 旁路前向（Level 2）

请补全 `__init__` 中的矩阵初始化和 `forward` 中的前向计算。

```python
import math
import torch
import torch.nn as nn

class LoRALinear(nn.Module):
    """LoRA: h = base(x) + (alpha / r) · B A x"""
    def __init__(self, base: nn.Linear, r: int = 16, alpha: int = 32):
        super().__init__()
        self.base = base
        self.r = r
        self.alpha = alpha
        self.scaling = alpha / r

        d_out, d_in = base.weight.shape
        self.lora_A = nn.Parameter(torch.empty(r, d_in))
        self.lora_B = nn.Parameter(torch.empty(d_out, r))

        # 冻结原权重
        self.base.weight.requires_grad = False
        if self.base.bias is not None:
            self.base.bias.requires_grad = False

        # TODO: 初始化 lora_A（Kaiming uniform，a=sqrt(5)）和 lora_B（全零）
        # 目的：训练初始时 Δ W = B A = 0，不改变预训练行为
        _____  # lora_A: Kaiming uniform 初始化
        _____  # lora_B: 零初始化

    def forward(self, x):
        # TODO: 在 base(x) 上叠加 (alpha / r) · B A x
        h = self.base(x)
        delta = _____    # 提示：x @ lora_A.T @ lora_B.T，再乘 self.scaling
        return h + delta
```




---

## 练习 2：LoRA 的 merge 与 unmerge（Level 2）

推理阶段可将 LoRA 合并回原始权重，避免额外乘法开销。请补全 `merge` 和 `unmerge`。

```python
class LoRALinear(nn.Module):
    def __init__(self, base, r=16, alpha=32):
        super().__init__()
        self.base = base
        self.r = r
        self.alpha = alpha
        self.scaling = alpha / r
        self.merged = False

        d_out, d_in = base.weight.shape
        self.lora_A = nn.Parameter(torch.empty(r, d_in))
        self.lora_B = nn.Parameter(torch.zeros(d_out, r))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))

        self.base.weight.requires_grad = False
        if self.base.bias is not None:
            self.base.bias.requires_grad = False

    def merge(self):
        """将 LoRA 增量合并到原始权重"""
        if not self.merged:
            # TODO: 计算 ΔW = (alpha / r) · B A，并加到 base.weight 上
            # 注意 nn.Linear.weight 形状为 [d_out, d_in]
            delta_W = _____
            self.base.weight.data += _____
            self.merged = True

    def unmerge(self):
        """撤销 merge"""
        if self.merged:
            delta_W = _____
            self.base.weight.data -= _____
            self.merged = False

    def forward(self, x):
        if self.merged:
            return self.base(x)
        h = self.base(x)
        delta = (x @ self.lora_A.T @ self.lora_B.T) * self.scaling
        return h + delta
```



---

## 练习 3：完整 LoRALinear 模块（Level 3）

请独立实现一个完整的 `LoRALinear`：冻结原权重、Kaiming + 零初始化、forward 含旁路、支持 merge/unmerge。

```python
class LoRALinear(nn.Module):
    """
    base 行为:
      未合并: h = base(x) + (alpha/r) · B A x
      已合并: h = (W + (alpha/r) · B A)x + bias
    """
    def __init__(self, base: nn.Linear, r: int = 16, alpha: int = 32):
        super().__init__()
        # TODO: 初始化、冻结、注册 lora_A / lora_B
        _____

    def forward(self, x):
        # TODO
        _____

    def merge(self):
        # TODO
        _____

    def unmerge(self):
        # TODO
        _____


# ====== 测试 ======
torch.manual_seed(42)
linear = nn.Linear(512, 256)
x = torch.randn(2, 10, 512)

lora = LoRALinear(linear, r=8, alpha=16)

with torch.no_grad():
    y_ref = linear(x)
    y_lora = lora(x)
    assert torch.allclose(y_ref, y_lora, atol=1e-5)   # B=0，旁路输出为 0

lora.merge()
with torch.no_grad():
    assert torch.allclose(y_ref, lora(x), atol=1e-5)  # 初始化时 ΔW = 0

lora.unmerge()
with torch.no_grad():
    assert torch.allclose(y_ref, lora(x), atol=1e-5)
print("通过")
```




---

## 练习 4：给预训练模型注入 LoRA（Level 3）

实现 `inject_lora`：递归遍历模型，把 `target_modules` 指定名称的 `nn.Linear` 替换为 `LoRALinear`。

```python
class TransformerBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, dim, bias=False)
        self.v_proj = nn.Linear(dim, dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
        self.ffn = nn.Sequential(
            nn.Linear(dim, dim * 4),
            nn.GELU(),
            nn.Linear(dim * 4, dim),
        )


def inject_lora(model, target_modules, r=16, alpha=32):
    """
    递归遍历 model，把 target_modules 中的 nn.Linear 替换为 LoRALinear。

    target_modules: list[str]，如 ["q_proj", "k_proj", "v_proj", "o_proj"]
    """
    for name, module in model.named_children():
        if isinstance(module, nn.Linear) and _____:
            # TODO: 用 LoRALinear 包装并替换
            _____
        else:
            # TODO: 递归
            _____
    return model
```

## 参考来源

[docs/exercises/lora-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/lora-fill.md)
