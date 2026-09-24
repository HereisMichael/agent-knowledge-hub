---
source_id: llm101-dpo-grpo-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# DPO/GRPO 填空

**题目 1**：在 Bradley-Terry 偏好模型中，给定两个回答 $y_w$（优选）和 $y_l$（劣选），人类偏好 $y_w$ 的概率建模为：

$$P(y_w \succ y_l) = \sigma(r(y_w) - r(y_l))$$

其中 $\sigma$ 是 sigmoid 函数。如果 $r(y_w) = 2.0$，$r(y_l) = -1.0$，那么 $P(y_w \succ y_l)$ 最接近：

- A) 0.50
- B) 0.73
- C) 0.95
- D) 0.99


---

**题目 2**：DPO 的核心创新在于：

- A) 使用一个单独训练的 Reward Model 来打分
- B) 将 reward 隐式表达为策略与参考策略的 log ratio，跳过了 Reward Model 的显式训练
- C) 使用 PPO 算法来优化策略
- D) 对 reward 进行 group 内归一化


---

**题目 3**：GRPO 与 PPO 的最大区别是：

- A) GRPO 使用了 clipping 机制
- B) GRPO 不需要 Critic（Value Function），而是用 group 内的 reward 归一化来估计 advantage
- C) GRPO 使用了 KL penalty
- D) GRPO 的学习率更大


---

## 练习 2：DPO Loss 实现（Level 2）

实现 TRL `DPOTrainer` 风格的**序列级** DPO loss。输入是策略与参考模型对 chosen/rejected 序列分别求和后的 log probability。

> 实现风格参考：[TRL DPOTrainer.dpo_loss](https://github.com/huggingface/trl/blob/main/trl/trainer/dpo_trainer.py)（sigmoid 损失类型，TRL 默认设置）。

```python
import torch
import torch.nn.functional as F


def dpo_loss(policy_chosen_logp, policy_rejected_logp,
             ref_chosen_logp,    ref_rejected_logp,
             beta=0.1):
    """
    序列级 DPO loss（sigmoid 损失类型）。

    参数（每个都是 [batch_size] 的标量序列级 log p）:
        policy_chosen_logp:    log π_θ(y_w | x)
        policy_rejected_logp:  log π_θ(y_l | x)
        ref_chosen_logp:       log π_ref(y_w | x)
        ref_rejected_logp:     log π_ref(y_l | x)
        beta:                  温度，典型 0.1
    返回:
        loss: 标量，batch 平均 DPO loss
    """
    # TODO 1: chosen 序列上的隐式 reward = π_θ 与 π_ref 的 log 差
    chosen_implicit_r = _____

    # TODO 2: rejected 序列上的隐式 reward
    rejected_implicit_r = _____

    # TODO 3: 用 beta 缩放 (chosen reward − rejected reward)，得到对比 margin
    margin = _____

    # TODO 4: 对 margin 取负 log-sigmoid，batch 内求平均
    loss = _____
    return loss


# ====== 测试 ======
# 直接给出已经在 completion 区间求和后的序列级 log p（数值就是 log π(y|x) 的真实量级）
policy_chosen_logp   = torch.tensor([-23.41,  -9.85, -17.62, -12.07])
policy_rejected_logp = torch.tensor([-25.30,  -8.71, -16.94, -13.85])
ref_chosen_logp      = torch.tensor([-22.96, -10.12, -17.40, -12.45])
ref_rejected_logp    = torch.tensor([-23.88,  -9.04, -16.71, -12.30])

loss = dpo_loss(policy_chosen_logp, policy_rejected_logp,
                ref_chosen_logp,    ref_rejected_logp, beta=0.1)
print(f"DPO Loss: {loss.item():.4f}")
```




---

## 练习 3：GRPO Advantage 计算（Level 2）

GRPO 对同一 prompt 采一组（group）候选回答，用组内 reward 的 z-score 当 advantage，从而省掉 PPO 里的 critic 网络。

> 参考：[TRL GRPOTrainer 文档](https://huggingface.co/docs/trl/main/en/grpo_trainer)、DeepSeekMath / DeepSeek-R1 论文。

```python
import torch


def compute_grpo_advantages(group_rewards, eps=1e-4):
    """
    GRPO group-relative advantage（组内 z-score 归一化）。

    参数:
        group_rewards: 1D tensor 或 list，同一 prompt 下采到的 G 个 reward
                       reward 可以是连续值（RM 打分）或 0/1（规则可判）。
        eps:           防止全组 reward 相同时除零

    返回:
        advantages: tensor，与输入同形状

    公式:
        A_i = (r_i − mean(r_group)) / (std(r_group) + eps)
    """
    group_rewards = torch.as_tensor(group_rewards, dtype=torch.float)

    # TODO: 用组内均值与标准差对 reward 做 z-score 归一化
    advantages = _____
    return advantages


# ====== 测试用例 ======
# Case 1: 连续 reward（典型 RM 打分），advantage 应有正有负
A = compute_grpo_advantages([0.83, 0.41, 0.95, 0.27, 0.62, 0.09, 0.51, 0.78])
print(f"连续 reward (G=8): {A}")

# Case 2: 全组 reward 相同 -> advantage 全 ≈ 0，该组无训练信号
A = compute_grpo_advantages([0.5] * 8)
print(f"全相同: {A}")

# Case 3: 单个高分异常值，稀有正例 advantage 显著大于其他
A = compute_grpo_advantages([0.10, 0.12, 0.85, 0.08, 0.15, 0.11, 0.09, 0.13])
print(f"稀有正例 (G=8): {A}")

# Case 4: 数学题 pass/fail 风格，G=128 中 3 道做对
rewards_128 = torch.zeros(128)
rewards_128[[7, 53, 91]] = 1.0
A = compute_grpo_advantages(rewards_128)
print(f"3/128 通过, 通过样本 advantage = {A[7].item():.2f}")
print(f"3/128 通过, 失败样本 advantage = {A[0].item():.2f}")
```




---

## 练习 4：GRPO Loss 完整实现（Level 3）

实现完整的 GRPO loss，包括 clipped policy ratio、advantage 加权和 KL penalty。

```python
import torch
import torch.nn.functional as F

def approx_kl(log_p, log_q):
    """
    计算近似 KL 散度（非对称）。
    
    公式: KL = exp(q/p) - (q - p) - 1
    即: q/p - log(q/p) - 1
    """
    return log_q.exp() / log_p.exp() \
           - (log_q - log_p) - 1


def grpo_loss(pi_logprob, pi_old_logprob, pi_ref_logprob,
              advantage, input_len):
    """
    计算 GRPO loss。
    
    参数:
        pi_logprob:     当前策略的 token log prob, [group_size, seq_len]
        pi_old_logprob: 采样时策略的 token log prob, [group_size, seq_len]
        pi_ref_logprob: 参考策略的 token log prob, [group_size, seq_len]
        advantage:      group-relative advantage, [group_size]
        input_len:      prompt 长度（只在回答部分计算 loss）
    
    返回:
        loss: 标量
    """
    epsilon = 0.2  # clipping 范围
    beta = 0.01    # KL penalty 系数

    bs, seq_len = pi_logprob.shape

    # TODO 1: 将 advantage 扩展维度以便广播 [group_size] -> [group_size, 1]
    advantage = _____

    # TODO 2: 计算 importance sampling ratio: exp(log_pi - log_pi_old)
    ratio = _____

    # TODO 3: clip ratio 到 [1-epsilon, 1+epsilon]
    ratio_clip = _____

    # TODO 4: 计算 clipped policy gradient（取 min，保守更新）
    policy_gradient = _____

    # TODO 5: 计算 KL penalty
    kl = _____

    # 只在回答部分（跳过 prompt）计算 loss
    response_loss = (policy_gradient - beta * kl)[:, input_len:]
    loss = -response_loss.mean()
    return loss


# ====== 测试代码 ======
torch.manual_seed(42)
group_size = 4
seq_len = 8
vocab_size = 50

# 模拟 logits
pi_logits = torch.randn(group_size, seq_len, vocab_size)
pi_old_logits = torch.randn(group_size, seq_len, vocab_size)
pi_ref_logits = torch.randn(group_size, seq_len, vocab_size)

# 模拟 token ids
token_ids = torch.randint(0, vocab_size, (group_size, seq_len))

# 计算 log prob
pi_logprob = torch.gather(
    F.log_softmax(pi_logits, dim=-1), dim=-1,
    index=token_ids.unsqueeze(-1)
).squeeze(-1)

pi_old_logprob = torch.gather(
    F.log_softmax(pi_old_logits, dim=-1), dim=-1,
    index=token_ids.unsqueeze(-1)
).squeeze(-1)

pi_ref_logprob = torch.gather(
    F.log_softmax(pi_ref_logits, dim=-1), dim=-1,
    index=token_ids.unsqueeze(-1)
).squeeze(-1)

# 模拟 advantage（沿用练习 3 的 z-score 函数）
advantage = compute_grpo_advantages([0.7, 0.2, 0.4, 0.85])
input_len = 3

loss = grpo_loss(pi_logprob, pi_old_logprob, pi_ref_logprob,
                 advantage, input_len)
print(f"GRPO Loss: {loss.item():.4f}")
```




---

## 练习 5：Reward Model 的 forward（Level 3）

实现一个简单的 Reward Model，它在预训练语言模型的基础上加一个 value head，输出标量 reward。

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class RewardModel(nn.Module):
    """
    Reward Model: 在语言模型基础上添加 value head，
    对每个序列输出一个标量 reward。
    
    结构:
        input -> backbone(LM) -> hidden_states -> value_head -> scalar reward
    
    训练目标:
        对于 (chosen, rejected) 对，最大化 r(chosen) - r(rejected) 的概率
    """
    def __init__(self, backbone, hidden_dim):
        super().__init__()
        # TODO 1: 保存 backbone 并冻结其参数
        self.backbone = _____
        for param in self.backbone.parameters():
            _____

        # TODO 2: 定义 value head (Linear: hidden_dim -> 1)
        self.value_head = _____

    def forward(self, input_ids):
        """
        参数:
            input_ids: [batch_size, seq_len]
        返回:
            rewards: [batch_size]，每个序列的标量 reward
        """
        # TODO 3: 获取 backbone 的 hidden states（取最后一层）
        with torch.no_grad():
            hidden_states = _____  # [bs, seq_len, hidden_dim]

        # TODO 4: 取最后一个 token 的 hidden state 作为序列表示
        last_hidden = _____  # [bs, hidden_dim]

        # TODO 5: 通过 value head 得到标量 reward
        reward = _____  # [bs, 1] -> [bs]
        return reward

    def compute_preference_loss(self, reward_chosen, reward_rejected):
        """
        Bradley-Terry 偏好 loss:
            loss = -log(sigmoid(r_chosen - r_rejected))
        
        参数:
            reward_chosen:   [batch_size]
            reward_rejected: [batch_size]
        返回:
            loss: 标量
        """
        # TODO 6: 计算 Bradley-Terry loss
        loss = _____
        return loss


# ====== 测试代码 ======
class SimpleBackbone(nn.Module):
    """模拟一个简单的语言模型 backbone"""
    def __init__(self, vocab_size, hidden_dim, seq_len):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, hidden_dim)
        self.linear = nn.Linear(hidden_dim, hidden_dim)

    def forward(self, input_ids):
        h = self.embed(input_ids)
        h = F.gelu(self.linear(h))
        return h

torch.manual_seed(42)
vocab_size, hidden_dim, seq_len = 100, 64, 10

backbone = SimpleBackbone(vocab_size, hidden_dim, seq_len)
reward_model = RewardModel(backbone, hidden_dim)

chosen_ids = torch.randint(0, vocab_size, (4, seq_len))
rejected_ids = torch.randint(0, vocab_size, (4, seq_len))

r_chosen = reward_model(chosen_ids)
r_rejected = reward_model(rejected_ids)

print(f"Chosen rewards: {r_chosen}")
print(f"Rejected rewards: {r_rejected}")

loss = reward_model.compute_preference_loss(r_chosen, r_rejected)
print(f"Preference loss: {loss.item():.4f}")

# 验证 value_head 可训练，backbone 冻结
trainable = sum(p.numel() for p in reward_model.parameters() if p.requires_grad)
total = sum(p.numel() for p in reward_model.parameters())
print(f"可训练参数: {trainable}, 总参数: {total}")
```




---

## 练习 6：端到端 toy GRPO 训练（Level 3）

把前几题的零件拼起来，跑一个真能收敛的最小 GRPO。任务：在 10 token 词表上，让 policy 学会"从 `<bos>` 出发只输出 `a`"。reward 由规则定义，模型用 `n_layer=1, n_embd=16` 的 tiny GPT-2，CPU 上 30 秒收敛。

```python
import copy, torch, torch.nn.functional as F
from transformers import GPT2Config, GPT2LMHeadModel

torch.manual_seed(0)
VOCAB = list("abcdefghi") + ["<bos>"]
V = len(VOCAB)
stoi = {c: i for i, c in enumerate(VOCAB)}
TARGET = stoi["a"]
prompt_id = torch.tensor([[stoi["<bos>"]]])

cfg = GPT2Config(vocab_size=V, n_positions=4,
                 n_embd=16, n_layer=1, n_head=2)
policy = GPT2LMHeadModel(cfg)
ref = copy.deepcopy(policy).eval()
old = copy.deepcopy(policy).eval()
for p in ref.parameters(): p.requires_grad_(False)

def reward_fn(token_id: int) -> float:
    return 1.0 if token_id == TARGET else 0.0


def sample_group(model, G=32):
    """从 prompt 出发，用 old policy 各自采 1 个 token，返回 (samples, old_lp, rewards)."""
    with torch.no_grad():
        # TODO 1: 取 prompt 最后一个位置的 logits, [1, V]
        logits = _____
        probs = logits.softmax(-1)
        # TODO 2: 从 probs 多次采样 G 个 token, 形状 [G]
        samples = _____
        # TODO 3: 计算这些 token 在 old policy 下的 log prob, [G]
        old_lp = _____
    rewards = torch.tensor([reward_fn(t.item()) for t in samples])
    return samples, old_lp, rewards


def grpo_advantage(rewards):
    """组内 z-score 归一化（GRPO 的核心）。"""
    # TODO 4: 用 mean / (std + 1e-8) 做 z-score
    return _____


def grpo_step(samples, old_lp, advantages, clip=0.2, kl_coef=0.04):
    """clipped surrogate + K3 KL penalty。"""
    logits = policy(prompt_id).logits[0, -1]      # [V]
    new_lp_full = F.log_softmax(logits, dim=-1)   # [V]
    new_lp = new_lp_full[samples]                 # [G]

    with torch.no_grad():
        ref_lp_full = F.log_softmax(
            ref(prompt_id).logits[0, -1], dim=-1)
    ref_lp = ref_lp_full[samples]                 # [G]

    # TODO 5: importance ratio = exp(new_lp - old_lp)
    ratio = _____
    # TODO 6: clipped surrogate（注意 PG 是最大化，loss 取负号）
    unclipped = ratio * advantages
    clipped = torch.clamp(ratio, 1 - clip, 1 + clip) * advantages
    pg = _____  # 提示：min(unclipped, clipped)

    # TODO 7: K3 KL: exp(log_r) - log_r - 1，其中 log_r = ref_lp - new_lp
    log_r = ref_lp - new_lp
    kl = _____

    return -(pg - kl_coef * kl).mean()


# ====== 训练循环 ======
opt = torch.optim.Adam(policy.parameters(), lr=3e-3)
for it in range(40):
    samples, old_lp, rewards = sample_group(old, G=32)
    adv = grpo_advantage(rewards)
    for _ in range(2):  # inner update
        loss = grpo_step(samples, old_lp, adv)
        opt.zero_grad(); loss.backward(); opt.step()
    # TODO 8: 把更新后的 policy 同步到 old（GRPO 的 on-policy 边界）
    _____
    if it % 10 == 0:
        with torch.no_grad():
            p_a = policy(prompt_id).logits[0, -1].softmax(-1)[TARGET]
        print(f"iter {it:>2}  loss={loss.item():+.3f}  P(a)={p_a:.3f}")
```




---

## 参考来源

[docs/exercises/dpo-grpo-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/dpo-grpo-fill.md)
