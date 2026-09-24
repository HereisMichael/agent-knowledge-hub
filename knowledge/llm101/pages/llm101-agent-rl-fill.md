---
source_id: llm101-agent-rl-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# Agent-RL 代码填空

## 练习 1：格式奖励（Format Reward, Level 2）

R1-Zero 的核心 trick 之一：用一个**纯 0/1 奖励**强制模型必须输出 `<think>...</think><answer>...</answer>` 这样的结构。结构对了拿 1 分，错了拿 0 分。完全不打分内容质量——但模型为了拿到这 1 分，会自己学会把推理过程写到 `<think>` 里。

```python
import re

def format_reward(completion: str) -> float:
    """
    检查 completion 是否严格符合 R1 的格式要求：
    - 以 <think> 开头（允许前面有空白）
    - 包含一对完整的 <think>...</think>
    - 紧跟一对 <answer>...</answer>
    - 中间允许任意空白
    
    返回 1.0（合格）或 0.0（不合格）。
    """
    # TODO 1: 写出匹配 <think>X</think>...<answer>Y</answer> 的正则
    #         X, Y 都允许任意字符（含换行），用非贪婪 .*?
    pattern = _____

    # TODO 2: 用 re.match（不是 search）+ re.DOTALL 来检查
    #         为什么用 match 不用 search？因为只允许开头匹配
    match = _____

    return 1.0 if match else 0.0


# ====== 测试 ======
ok = "<think>Let me compute 2+3</think><answer>5</answer>"
bad1 = "The answer is 5"                             # 完全没标签
bad2 = "<answer>5</answer><think>oops</think>"      # 顺序反了
bad3 = "<think>halfway"                              # 缺闭合标签
bad4 = "  <think>x</think>\n\n<answer>y</answer>"   # 前后空白：应该接受？

for c in [ok, bad1, bad2, bad3, bad4]:
    print(f"{format_reward(c):.1f}  | {c[:40]!r}")
```



---

## 练习 2：可验证奖励（Verifiable Reward, Level 2）

数学题的奖励是 R1 / RLVR 范式的另一支柱：给定标准答案，从模型输出里抠出最后那个数，做**符号等价**判断（`1/2 == 0.5`、`\frac{1}{2} == 0.5`）。这就是 RLVR（Reinforcement Learning with Verifiable Reward）的 V。

```python
import re
from fractions import Fraction

def extract_boxed_answer(text: str) -> str | None:
    """从形如 '...所以答案是 \\boxed{42}' 的文本里抠出 '42'。"""
    # TODO 1: 找最后一个 \boxed{...}，返回大括号内的字符串
    #         为什么要"最后一个"？因为模型可能在思考过程中也写过 \boxed
    matches = _____
    return matches[-1] if matches else None


def normalize_to_fraction(s: str) -> Fraction | None:
    """把 '1/2'、'0.5'、'\\frac{1}{2}' 统一成 Fraction(1, 2)。"""
    s = s.strip().replace(r"\frac{", "").replace("}{", "/").replace("}", "")
    try:
        # TODO 2: 优先尝试 Fraction(s)（处理 "1/2"），失败再尝试 float
        return _____
    except (ValueError, ZeroDivisionError):
        return None


def accuracy_reward(completion: str, gold: str) -> float:
    """
    返回 1.0 / 0.0：
    - 1.0：completion 中最后一个 \boxed{} 的值在数值上等于 gold
    - 0.0：抠不出来 / 不相等
    """
    pred_str = extract_boxed_answer(completion)
    if pred_str is None:
        return 0.0
    pred = normalize_to_fraction(pred_str)
    gold_v = normalize_to_fraction(gold)

    # TODO 3: 都成功才比较；任意一个失败返回 0
    if _____:
        return 0.0
    return 1.0 if pred == gold_v else 0.0


# ====== 测试 ======
cases = [
    ("思考...所以\\boxed{0.5}", "1/2",     1.0),  # 跨表示等价
    ("\\boxed{\\frac{1}{2}}",   "0.5",     1.0),  # latex frac vs decimal
    ("\\boxed{2}\n\\boxed{3}",  "3",       1.0),  # 取最后一个
    ("没有答案",                "5",       0.0),  # 抠不出
    ("\\boxed{abc}",           "5",       0.0),  # 抠到了但不是数
]
for comp, gold, expected in cases:
    r = accuracy_reward(comp, gold)
    print(f"{r:.1f}  expected={expected:.1f}  | {comp[:30]!r}")
```



---

## 练习 3：多轮轨迹的 Loss Mask（Level 2-3）

Agent rollout 与单轮聊天的最大不同：**轨迹包含交错的 user / assistant / tool 角色**。loss 只能算在 assistant 生成的 token 上——user / tool / system 的 token 是"observation"，模型不该被它们的内容惩罚或鼓励。

数据结构（一条轨迹）：
```python
trajectory = [
    {"role": "system",    "content": "You are a math agent."},
    {"role": "user",      "content": "What is 23 * 17?"},
    {"role": "assistant", "content": "Let me use the calculator. <call>mul(23,17)</call>"},
    {"role": "tool",      "content": "391"},
    {"role": "assistant", "content": "23 * 17 = 391"},
]
```

```python
def build_loss_mask(token_ids: list[int],
                   role_spans: list[tuple[str, int, int]]) -> list[int]:
    """
    根据 role_spans (role, start, end) 列表构造 loss mask。
    
    role_spans: 每条 (role, start, end) 表示 token_ids[start:end] 属于 role。
                role ∈ {"system", "user", "assistant", "tool"}
    
    返回长度等于 len(token_ids) 的 0/1 列表：
    - 1：该 token 计入 loss（assistant 生成的 token）
    - 0：mask 掉（system / user / tool 提供的 observation）
    """
    mask = [0] * len(token_ids)
    for role, start, end in role_spans:
        # TODO 1: 只有 assistant 段需要被训练
        if _____:
            for i in range(start, end):
                mask[i] = 1
    return mask


def shift_mask_for_clm(mask: list[int]) -> list[int]:
    """
    Causal LM 的 loss 形式是 logits[t] 预测 token[t+1]。
    所以 token[t] 是否计入 loss，取决于 mask[t+1]。
    
    返回 shifted_mask，长度 len(mask) - 1。
    """
    # TODO 2: shift left by 1（丢掉最后一个，因为没有"下一个 token"可预测）
    return _____


# ====== 测试 ======
# 一条轨迹被 tokenize 成 12 个 token：
# [sys=0..2] [usr=2..5] [asst=5..8] [tool=8..10] [asst=10..12]
spans = [
    ("system",    0, 2),
    ("user",      2, 5),
    ("assistant", 5, 8),
    ("tool",      8, 10),
    ("assistant", 10, 12),
]
ids = list(range(12))
m = build_loss_mask(ids, spans)
print("raw mask:    ", m)
# 期望: [0,0, 0,0,0, 1,1,1, 0,0, 1,1]

shifted = shift_mask_for_clm(m)
print("shifted mask:", shifted)
# 期望: [0, 0,0,0, 1,1,1, 0,0, 1,1] (长度 11)
# 解读：第 4 个 token (index 4, 最后一个 user token) 的 logits 预测第 5 个 (第一个 asst)，
#       这个 loss 要算！所以 shifted[4] = mask[5] = 1
print("loss tokens:", sum(shifted), "/ 11")
```



---

## 练习 4：异步 Rollout 队列（Level 3）

Agent-RL 的最大工程瓶颈：**rollout 慢**。一次 rollout 要跑多轮，每轮要等 LLM 生成 + 等环境响应。如果 rollout 与 training 串行（rollout 完一组才训一步），GPU 利用率会跌到 30%。

解决方案：**异步队列**。Rollout worker 不停产生轨迹塞进队列；Trainer 从队列里捞一个 batch 就训一步。两者解耦，GPU 满载。

```python
import asyncio
import random
from collections import deque

class AsyncRolloutBuffer:
    """
    最小异步 rollout buffer。
    - rollout worker 调 put() 持续塞轨迹
    - trainer 调 get_batch() 阻塞等到攒够 batch_size 条
    - 用 max_age 防止 trainer 拿到过老的（off-policy 严重的）轨迹
    """
    def __init__(self, batch_size: int, max_capacity: int):
        self.batch_size = batch_size
        # TODO 1: 用 deque 加 maxlen=max_capacity，自动丢弃最老的轨迹
        self.buf = _____
        self.cond = asyncio.Condition()

    async def put(self, traj: dict):
        """rollout worker 调用：放进一条轨迹，唤醒 trainer。"""
        async with self.cond:
            self.buf.append(traj)
            # TODO 2: 唤醒所有在 wait 的 trainer 协程
            _____

    async def get_batch(self) -> list[dict]:
        """trainer 调用：阻塞直到有 batch_size 条数据可用。"""
        async with self.cond:
            # TODO 3: 等待条件满足。注意 wait_for 比裸 wait 更安全（防虚假唤醒）
            await self.cond.wait_for(lambda: _____)
            # 取出 batch_size 条最新的
            batch = [self.buf.popleft() for _ in range(self.batch_size)]
            return batch


# ====== 测试：模拟 rollout 与 trainer 协程并发 ======
async def rollout_worker(buf: AsyncRolloutBuffer, n: int):
    for i in range(n):
        await asyncio.sleep(random.uniform(0.01, 0.05))  # 模拟生成耗时
        await buf.put({"traj_id": i, "reward": random.random()})
        print(f"  [rollout] put traj {i}")

async def trainer_loop(buf: AsyncRolloutBuffer, n_steps: int):
    for step in range(n_steps):
        batch = await buf.get_batch()
        ids = [t["traj_id"] for t in batch]
        print(f"[trainer] step {step}: trained on {ids}")

async def main():
    buf = AsyncRolloutBuffer(batch_size=4, max_capacity=16)
    await asyncio.gather(
        rollout_worker(buf, n=12),
        trainer_loop(buf, n_steps=3),
    )

# asyncio.run(main())
```



---

## 练习 5：Composite Reward 组装（Level 3）

实战里没有人只用一个奖励。生产 reward 通常长这样：

$$
r(x, y) = w_{\text{fmt}} \cdot r_{\text{fmt}} + w_{\text{acc}} \cdot r_{\text{acc}} + w_{\text{len}} \cdot r_{\text{len}} - w_{\text{rep}} \cdot r_{\text{rep}}
$$

每个 component 是独立函数（练习 1-2 是其中两个），主训练脚本负责加权组装。这道题填一个 reward composer。

```python
from typing import Callable

def cosine_length_reward(completion: str, gold: str, max_len: int = 512) -> float:
    """
    长度 cosine scaling：答错时短的扣分多，答对时短的得分多。
    L = len(completion); ratio = L / max_len ∈ [0, 1]
    
    答对 (acc=1.0): r = 1.0 - 0.5 * (1 - cos(π * ratio))   长 → 1.0,  短 → 0.0
                                                           （惩罚没思考就答对——可能是猜的）
    答错 (acc=0.0): r = -1.0 + 0.5 * (1 - cos(π * ratio))  长 → -1.0, 短 → 0.0
                                                           （惩罚长篇错答——浪费 token）
    """
    import math
    acc = accuracy_reward(completion, gold)  # 复用练习 2
    ratio = min(len(completion) / max_len, 1.0)
    cos_factor = 0.5 * (1 - math.cos(math.pi * ratio))

    # TODO 1: 按 acc 0/1 走两条公式
    if acc > 0.5:
        return _____
    else:
        return _____


def make_reward_fn(weights: dict[str, float],
                   funcs: dict[str, Callable]) -> Callable:
    """
    工厂函数：把多个奖励按权重组合成一个。
    
    weights: 名字 → 权重
    funcs:   名字 → 单个 reward function (返回标量)
    
    返回一个新函数 R(completion, gold) → 加权总分。
    """
    # TODO 2: 检查 weights 和 funcs 的 key 完全对应
    assert _____, "weights and funcs must have identical keys"

    def composite(completion: str, gold: str) -> dict:
        scores = {name: f(completion, gold) for name, f in funcs.items()}
        # TODO 3: 加权求和（注意这里返回 dict，方便日志记录每个分量）
        scores["total"] = _____
        return scores
    return composite


# ====== 测试 ======
funcs = {
    "fmt":     lambda c, g: format_reward(c),       # 练习 1
    "acc":     lambda c, g: accuracy_reward(c, g),  # 练习 2
    "cos_len": cosine_length_reward,
}
weights = {"fmt": 0.1, "acc": 1.0, "cos_len": 0.2}

R = make_reward_fn(weights, funcs)

c = "<think>23*17 = 23*17 = 391</think><answer>\\boxed{391}</answer>"
print(R(c, "391"))
# 期望：fmt=1.0, acc=1.0, cos_len≈0 (短文本对答错才扣，对答对接近 0), total≈1.1
```



---

## 练习 6：Trajectory → Token Reward 分配（Level 3）

Agent rollout 的轨迹奖励是**序列级别**的（"答对了 +1，答错了 0"）。但 PPO/GRPO 需要**每个 token 都有 advantage**才能算 loss。如何把一个标量 reward 分配到 T 个 token 上？

四种主流策略：

1. **Last-token only**：reward 全加到最后一个 assistant token。简单、稀疏、信号弱。
2. **Distribute uniform**：均摊到所有 assistant token。容易让模型刷长度。
3. **Distribute by KL**：按 ref / policy 的 KL 分布权重。SimPO/某些 R1 变体使用。
4. **Token-level critic**：单独训一个 value model。这就是经典 PPO，重。

```python
import torch

def assign_reward_last_token(seq_reward: float,
                              loss_mask: torch.Tensor) -> torch.Tensor:
    """
    策略 1：把 reward 全加到 mask=1 的最后一个位置。
    
    loss_mask: shape [T], 0/1 tensor
    返回:      shape [T], reward tensor
    """
    out = torch.zeros_like(loss_mask, dtype=torch.float32)
    # TODO 1: 找到 mask=1 的最后一个位置
    #         提示：mask.nonzero() 返回所有非零位置的下标
    nz = _____
    if len(nz) > 0:
        last_idx = nz[-1].item()
        out[last_idx] = seq_reward
    return out


def assign_reward_uniform(seq_reward: float,
                          loss_mask: torch.Tensor) -> torch.Tensor:
    """
    策略 2：均摊到所有 mask=1 的位置。
    """
    out = torch.zeros_like(loss_mask, dtype=torch.float32)
    n = loss_mask.sum().item()
    if n == 0:
        return out
    # TODO 2: 给所有 mask=1 的位置赋值 seq_reward / n
    out[_____] = seq_reward / n
    return out


def assign_reward_kl_weighted(seq_reward: float,
                               loss_mask: torch.Tensor,
                               kl_per_token: torch.Tensor) -> torch.Tensor:
    """
    策略 3：按 KL 加权分配。
    KL 大的 token = 模型自信偏离 ref policy，应该承担更多 reward (or punishment)。
    
    kl_per_token: shape [T], 每个 token 的 |KL(policy || ref)|
    """
    out = torch.zeros_like(loss_mask, dtype=torch.float32)
    # TODO 3: 取 mask=1 位置的 KL，归一化成权重，再乘以 seq_reward
    masked_kl = kl_per_token * loss_mask
    total = masked_kl.sum()
    if total < 1e-8:
        # KL 太小退化为 uniform
        return assign_reward_uniform(seq_reward, loss_mask)
    weights = _____
    return seq_reward * weights


# ====== 测试 ======
mask = torch.tensor([0, 0, 1, 1, 0, 1, 1, 1, 0])  # 5 个 assistant token
kl   = torch.tensor([0., 0., 0.1, 0.5, 0., 2.0, 0.1, 0.3, 0.])

print("last:    ", assign_reward_last_token(1.0, mask))
# 期望: [0,0,0,0,0,0,0,1,0]

print("uniform: ", assign_reward_uniform(1.0, mask))
# 期望: 5 个 mask=1 位置各为 0.2

print("kl_weighted:", assign_reward_kl_weighted(1.0, mask, kl))
# 期望: 第 5 位（kl=2.0）拿大头，约 0.667
```



---

## 参考来源

[docs/exercises/agent-rl-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/agent-rl-fill.md)
