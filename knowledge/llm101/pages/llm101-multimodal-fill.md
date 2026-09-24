---
source_id: llm101-multimodal-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# 多模态代码填空

## 练习 1：Patch Embedding（Level 2）

ViT 把图像切成 patch、再线性投影成 token——这是所有视觉 Transformer（ViT / CLIP / DINO / SAM 的 image encoder）的入口。一个反直觉的事实：**这一步并不需要写双重 for 循环切 patch**，一个 `Conv2d(kernel_size=patch_size, stride=patch_size)` 就把"切 patch + 线性投影"两步合成了一个算子，效率最高。

输入图像 224×224、patch_size=16、embed_dim=768，应当产生 14×14=196 个 token，每个 token 维度 768。

```python
import torch
import torch.nn as nn

class PatchEmbed(nn.Module):
    """ViT 风格的 patch embedding：把 [B, C, H, W] 切 patch + 线性投影成 [B, N, D]。"""

    def __init__(self, img_size: int = 224, patch_size: int = 16,
                 in_channels: int = 3, embed_dim: int = 768):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        # TODO 1: 计算 patch 数 N = (H/P) * (W/P)
        self.num_patches = _____

        # TODO 2: 用一个 Conv2d 同时完成"切 patch"与"线性投影"
        #         kernel_size = stride = patch_size 是关键：
        #         每个 patch 内部的像素被一个 (patch_size, patch_size) 的卷积核线性组合，
        #         相邻 patch 之间没有重叠（stride = kernel）。
        self.proj = _____

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: [B, C, H, W]
        返回: [B, N, D]，N=num_patches，D=embed_dim
        """
        B, C, H, W = x.shape
        assert H == self.img_size and W == self.img_size, \
            f"input size mismatch: got {H}x{W}, expected {self.img_size}"

        # TODO 3: Conv2d 输出形如 [B, D, H/P, W/P]
        #         flatten 后两个维度，再交换成 [B, N, D]
        x = self.proj(x)               # [B, D, H/P, W/P]
        x = x.flatten(2)               # [B, D, N]
        x = _____                      # [B, N, D]
        return x


# ====== 测试 ======
patch_embed = PatchEmbed(img_size=224, patch_size=16, embed_dim=768)
x = torch.randn(2, 3, 224, 224)
y = patch_embed(x)
print(y.shape)             # 期望: torch.Size([2, 196, 768])
print(patch_embed.num_patches)  # 期望: 196

# 参数量验算：Conv2d(3, 768, k=16, s=16) 的权重 = 3*768*16*16 + 768 = 590,592
n_params = sum(p.numel() for p in patch_embed.parameters())
print("params:", n_params)  # 期望: 590592
```



---

## 练习 2：CLIP InfoNCE Loss（Level 2）

CLIP 训练的核心是 **N×N 的对比矩阵**：一个 batch 里有 N 张图、N 段文本（一一配对），用它们的 embedding 算 cosine similarity 得到一个 N×N 矩阵，**对角线是正样本（图 i 配文 i），非对角线全是负样本**。然后在两个方向上各算一次 cross-entropy（image-to-text、text-to-image），取平均。

三个关键点：
- L2 normalize：让点积变成 cosine
- learnable temperature：`logit_scale = exp(τ)`，τ 初始化为 `ln(1/0.07)`，clip 上限避免数值爆炸
- 双向损失：避免单方向坍塌

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class CLIPLoss(nn.Module):
    """CLIP 的对称 InfoNCE 损失。"""

    def __init__(self, init_temperature: float = 0.07):
        super().__init__()
        # TODO 1: 把 temperature 做成 log 空间的可学习参数
        #         为什么用 log？避免 τ 直接被优化成负数（temperature 必须 > 0）
        #         初始值: ln(1/0.07)
        import math
        self.logit_scale = nn.Parameter(_____)

    def forward(self, image_features: torch.Tensor,
                text_features: torch.Tensor) -> dict:
        """
        image_features: [N, D]
        text_features:  [N, D]
        返回 dict：包含 loss / loss_i2t / loss_t2i / accuracy
        """
        # TODO 2: 在最后一维做 L2 normalize
        image_features = _____
        text_features = _____

        # 把 logit_scale 转回线性 + clip 上限避免数值不稳定
        logit_scale = self.logit_scale.exp().clamp(max=100.0)

        # TODO 3: 算 logits 矩阵 [N, N]
        #         logits_i2t[i, j] = image_i 与 text_j 的相似度（乘以 scale）
        logits_i2t = _____
        logits_t2i = logits_i2t.t()

        # TODO 4: ground-truth label：对角线即正样本对
        N = image_features.size(0)
        labels = _____   # [0, 1, 2, ..., N-1]

        # TODO 5: 双向 cross-entropy + 平均
        loss_i2t = F.cross_entropy(logits_i2t, labels)
        loss_t2i = F.cross_entropy(logits_t2i, labels)
        loss = _____

        # 评估：top-1 accuracy（图找对文本）
        with torch.no_grad():
            acc = (logits_i2t.argmax(dim=-1) == labels).float().mean()

        return {"loss": loss, "loss_i2t": loss_i2t,
                "loss_t2i": loss_t2i, "accuracy": acc}


# ====== 测试 ======
torch.manual_seed(42)
loss_fn = CLIPLoss()

# 8 张图、8 段文本，假设 image 与 text encoder 都是 512 维
N, D = 8, 512
img = torch.randn(N, D, requires_grad=True)
txt = torch.randn(N, D, requires_grad=True)

out = loss_fn(img, txt)
print(f"loss     = {out['loss'].item():.4f}")     # 随机初始化下 ~ ln(8) = 2.08
print(f"loss_i2t = {out['loss_i2t'].item():.4f}")
print(f"loss_t2i = {out['loss_t2i'].item():.4f}")
print(f"acc      = {out['accuracy'].item():.4f}")  # 随机情况下 ~ 1/N = 0.125

out["loss"].backward()
print("logit_scale.grad =", loss_fn.logit_scale.grad.item())  # 应该非零
```



---

## 练习 3：LLaVA Visual Projector 工厂（Level 2）

LLaVA 的核心 trick：**冻结 vision encoder（CLIP-ViT）+ 冻结 LLM，只训中间一个小的 projector**，把 vision feature 投到 LLM 的 hidden_size。这个 projector 只占总参数的 < 1%，但决定了视觉信号能不能被 LLM 吃下去。

主流配置三选一：
- `linear`：单个 `nn.Linear(mm_hidden_size, hidden_size)`。LLaVA-v1 默认。
- `mlp2x_gelu`：`Linear → GELU → Linear`。LLaVA-1.5 升级版，多一层非线性。
- `mlp3x_gelu`：`Linear → GELU → Linear → GELU → Linear`。LLaVA-1.6/Next 用过。

要求：写一个**字符串驱动的工厂函数**，输入 `proj_type: str`，输出对应 `nn.Module`。`mlpNx_gelu` 的 N 要从字符串里抠出来，支持任意正整数。

```python
import re
import torch
import torch.nn as nn

def build_visual_projector(proj_type: str,
                           vision_dim: int,
                           llm_dim: int) -> nn.Module:
    """
    根据字符串构建 visual projector。

    proj_type: 
      - "linear":     [vision_dim] → [llm_dim]
      - "identity":   恒等映射（要求 vision_dim == llm_dim）
      - "mlpNx_gelu": N 个 Linear，中间夹 GELU
                      第一层 vision_dim → llm_dim，之后 llm_dim → llm_dim
    vision_dim: vision encoder 输出维度（如 CLIP ViT-L/14 是 1024）
    llm_dim:    LLM 的 hidden_size（如 LLaMA-7B 是 4096）

    返回一个 nn.Module。
    """
    # ---------- 分支 1: linear ----------
    if proj_type == "linear":
        # TODO 1: 单个 Linear
        return _____

    # ---------- 分支 2: identity ----------
    if proj_type == "identity":
        if vision_dim != llm_dim:
            raise ValueError(
                f"identity projector requires vision_dim == llm_dim, "
                f"got {vision_dim} vs {llm_dim}"
            )
        return nn.Identity()

    # ---------- 分支 3: mlpNx_gelu ----------
    # TODO 2: 用正则抽取 N，例如 "mlp2x_gelu" → 2，"mlp3x_gelu" → 3
    #         匹配模式: ^mlp(\d+)x_gelu$
    match = _____
    if match:
        depth = int(match.group(1))
        if depth < 1:
            raise ValueError(f"mlp depth must be >= 1, got {depth}")

        # TODO 3: 拼一个 [Linear, GELU, Linear, GELU, ..., Linear] 序列
        #         第 1 层: vision_dim → llm_dim
        #         之后:   llm_dim → llm_dim，前面加 GELU
        layers = [nn.Linear(vision_dim, llm_dim)]
        for _ in range(1, depth):
            layers.append(nn.GELU())
            layers.append(_____)
        return nn.Sequential(*layers)

    # ---------- 兜底 ----------
    raise ValueError(f"Unknown projector type: {proj_type!r}")


# ====== 测试 ======
# 模拟 CLIP ViT-L/14 → LLaMA-7B
V, L = 1024, 4096
batch_n_tokens = (2, 256)  # 2 个样本，每个 256 个 vision token

x = torch.randn(*batch_n_tokens, V)

for proj_type in ["linear", "mlp2x_gelu", "mlp3x_gelu"]:
    proj = build_visual_projector(proj_type, V, L)
    y = proj(x)
    n_params = sum(p.numel() for p in proj.parameters())
    print(f"{proj_type:12s} | out={tuple(y.shape)} | params={n_params:,}")

# 期望:
# linear       | out=(2, 256, 4096) | params=4,198,400
# mlp2x_gelu   | out=(2, 256, 4096) | params=21,000,192
# mlp3x_gelu   | out=(2, 256, 4096) | params=37,801,984

# 边界测试
identity_proj = build_visual_projector("identity", 4096, 4096)
print("identity:", identity_proj(torch.randn(1, 4, 4096)).shape)

try:
    build_visual_projector("identity", 1024, 4096)
except ValueError as e:
    print("expected error:", e)

try:
    build_visual_projector("mlp0x_gelu", V, L)
except ValueError as e:
    print("expected error:", e)
```



---

## 练习 4：Video Frame Sampler（Level 3）

视频比图像贵 30~120 倍——不可能把每一帧都喂给 vision encoder。Video-LLaVA / VideoChat / LLaVA-Video 等都依赖一个**采样器**：从 T 帧视频里挑 K 帧（K << T）送进模型。三种主流采样策略：

1. **均匀采样（Uniform）**：每隔 T/K 取一帧。最简单、最常用、最容易漏关键帧。
2. **关键帧采样（Keyframe）**：基于相邻帧差选变化大的帧——动作 / 场景切换处。
3. **Query-driven**：给定文本 query，用 CLIP 算每帧与 query 的相似度，取 Top-K。检索类任务最强。

```python
import torch
import torch.nn.functional as F

def sample_uniform(num_frames: int, k: int) -> list[int]:
    """
    均匀采样：从 [0, num_frames) 里取 k 个等距下标。
    要求 k >= 1。如果 k >= num_frames，返回所有帧。
    """
    if k >= num_frames:
        return list(range(num_frames))
    # TODO 1: 用 linspace 在 [0, num_frames-1] 上取 k 个浮点点，再四舍五入到 int
    #         注意去重（极端情况下相邻 index 可能撞）
    idxs = _____
    idxs = sorted(set(idxs))
    return idxs


def sample_keyframe(frames: torch.Tensor, k: int) -> list[int]:
    """
    关键帧采样：基于"相邻帧像素差"挑变化大的帧。
    
    frames: [T, C, H, W]，已归一化到 [0, 1]
    返回 k 个 frame index（升序）
    """
    T = frames.size(0)
    if k >= T:
        return list(range(T))

    # TODO 2: 算相邻帧的 L1 距离: diffs[t] = mean |frames[t+1] - frames[t]|
    #         得到 [T-1] 长度的差分序列
    diffs = _____

    # 第 0 帧总是保留（视频开头），剩下从 diffs 里挑 top-(k-1) 大的
    # diffs[t] 大表示 frames[t+1] 是关键帧（变化点）
    # TODO 3: 用 topk 选 k-1 个最大的 diff 下标，对应的关键帧是 idx+1
    top_diff = _____
    keyframe_idx = (top_diff + 1).tolist()

    return sorted(set([0] + keyframe_idx))[:k]


def sample_query_driven(frame_features: torch.Tensor,
                        query_feature: torch.Tensor,
                        k: int) -> list[int]:
    """
    Query 驱动采样：用预计算好的 CLIP feature 算相似度，取 Top-K。
    
    frame_features: [T, D]，每帧的 CLIP image embedding（已 L2 normalized）
    query_feature:  [D]，query 文本的 CLIP text embedding（已 L2 normalized）
    返回 k 个 frame index（按相似度从高到低）
    """
    T = frame_features.size(0)
    if k >= T:
        return list(range(T))

    # TODO 4: cosine similarity（已经 normalize 过，直接点积）
    sims = _____   # [T]

    # TODO 5: topk 取 k 个相似度最高的帧
    top = _____
    return top.indices.tolist()


# ====== 测试 ======
torch.manual_seed(0)

# 模拟一段 30 帧视频
T, C, H, W = 30, 3, 64, 64
frames = torch.rand(T, C, H, W)

# 故意在第 10 / 20 帧造一个剧烈变化（场景切换）
frames[10:] += 0.5
frames[20:] -= 0.8
frames = frames.clamp(0, 1)

print("uniform   :", sample_uniform(T, 5))
# 期望: [0, 7, 14, 21, 29] 这种等距分布

print("keyframe  :", sample_keyframe(frames, 5))
# 期望: 包含 0, 10, 20 附近的下标（因为我们故意造了变化）

# Query-driven：模拟 CLIP feature
D = 512
frame_feats = F.normalize(torch.randn(T, D), dim=-1)
query = F.normalize(torch.randn(D), dim=-1)

# 故意把第 7 / 15 / 25 帧造成与 query 相似度最高
for i in [7, 15, 25]:
    frame_feats[i] = F.normalize(query + 0.1 * torch.randn(D), dim=-1)

print("query-top3:", sample_query_driven(frame_feats, query, 3))
# 期望: [7, 15, 25]（顺序可能不同，但应该是这三个）
```



---

## 练习 5：Vision Tool Router（Level 3）

Vision Agent（如 OmniParser + GPT-4V、Claude Computer Use）的常见架构：**LLM 做 planner，调用一组视觉工具完成原子任务**。每次输入 (screenshot, user_query)，agent 需要决定调哪个工具：

- `OCR`：抽取屏幕上的文字（"截图里写了什么"）
- `detection`：定位 UI 元素或物体（"找到登录按钮"）
- `caption`：整体图像描述（"这张图在干嘛"）
- `VQA`：开放问答（"图里有几个人"）

朴素做法：让 LLM 看 query 自己决定。但 **LLM 调用一次成本高**——很多场景下用纯关键词路由器就能覆盖 80% 的请求，剩下 20% 再回退给 LLM。这个练习实现一个 **keyword + heuristic 路由器**。

```python
import re
from dataclasses import dataclass, field

@dataclass
class RouteDecision:
    tool: str
    confidence: float       # [0, 1]，1 = 非常确定
    reason: str             # 给 log / debug 用

@dataclass
class VisionToolRouter:
    """关键词驱动的 Vision tool 路由器。"""

    # 每个工具的触发关键词（可被外部 override）
    ocr_keywords: list[str] = field(default_factory=lambda: [
        "文字", "文本", "text", "字", "ocr", "读出", "识别字",
        "写的", "写着", "看清", "看不清",
    ])
    detection_keywords: list[str] = field(default_factory=lambda: [
        "在哪", "位置", "找到", "定位", "click", "按钮", "图标",
        "where", "locate", "find", "bounding box", "bbox",
    ])
    caption_keywords: list[str] = field(default_factory=lambda: [
        "描述", "总结", "概括", "describe", "caption", "summary",
        "整体", "大致", "在干什么", "在做什么",
    ])

    def route(self, user_query: str,
              screenshot_meta: dict | None = None) -> RouteDecision:
        """
        screenshot_meta: 可选，包含 image 的 metadata 帮助决策：
            - "has_text_region": bool   是否检出大段文字（OCR pre-detect）
            - "ui_elements": int        UI 元素数量（高 → 大概率是网页/app）
            - "image_size": (W, H)
        """
        q = user_query.lower().strip()

        # ---------- 规则 1: OCR 关键词命中 ----------
        # TODO 1: 命中 ocr_keywords 任何一个 → 返回 ocr，confidence=0.9
        if _____:
            return RouteDecision(
                tool="ocr", confidence=0.9,
                reason=f"matched ocr keyword in: {q!r}"
            )

        # ---------- 规则 2: detection 关键词 ----------
        if any(kw in q for kw in self.detection_keywords):
            return RouteDecision(
                tool="detection", confidence=0.9,
                reason=f"matched detection keyword in: {q!r}"
            )

        # ---------- 规则 3: caption 关键词 ----------
        if any(kw in q for kw in self.caption_keywords):
            return RouteDecision(
                tool="caption", confidence=0.85,
                reason=f"matched caption keyword in: {q!r}"
            )

        # ---------- 规则 4: 启发式（按 metadata） ----------
        if screenshot_meta:
            # TODO 2: UI 元素 > 5 且 query 含"?"或"什么/哪个/几个" → VQA on UI
            if (screenshot_meta.get("ui_elements", 0) > 5
                    and _____):
                return RouteDecision(
                    tool="vqa", confidence=0.7,
                    reason="ui-rich screen + interrogative query"
                )

            # TODO 3: query 极短（< 5 个字符） + 检出文字区域 → 大概率是想 OCR
            if (len(q) < 5
                    and screenshot_meta.get("has_text_region", False)):
                return RouteDecision(
                    tool="ocr", confidence=0.6,
                    reason="ultra-short query + text-rich screen"
                )

        # ---------- 规则 5: 兜底用 VQA（最通用） ----------
        # TODO 4: VQA 是兜底——所有疑问句都可以回答
        return RouteDecision(
            tool=_____, confidence=0.5,
            reason="fallback to general VQA"
        )


# ====== 测试 ======
router = VisionToolRouter()

cases = [
    ("截图里的文字是什么？", None,                        "ocr"),
    ("登录按钮在哪？",       None,                        "detection"),
    ("总结一下这张图",       None,                        "caption"),
    ("这张图里有几个人？",   None,                        "vqa"),       # 兜底
    ("?",                    {"ui_elements": 10,
                              "has_text_region": True},   "vqa"),       # 启发式 2
    ("好",                   {"has_text_region": True},   "ocr"),       # 启发式 3
    ("这张图怎么样",         None,                        "vqa"),       # 兜底
]

for query, meta, expected in cases:
    d = router.route(query, meta)
    ok = "OK" if d.tool == expected else "MISS"
    print(f"[{ok}] {query!r:35s} → {d.tool:10s} "
          f"(conf={d.confidence:.2f}) | {d.reason}")
```



---

## 参考来源

[docs/exercises/multimodal-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/multimodal-fill.md)
