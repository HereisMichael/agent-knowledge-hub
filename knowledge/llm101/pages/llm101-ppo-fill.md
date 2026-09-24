---
source_id: llm101-ppo-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# PPO 代码填空

## 练习 1：Importance Ratio（Level 2）

PPO 的核心是用 `old policy` 采样 + 多轮 `inner update` 复用样本。每次 inner update 时，用 importance ratio 修正"采样分布与当前策略的差异"。

```python
import torch

def importance_ratio(new_logprobs, old_logprobs, mask):
    """
    计算 token 级 importance ratio。

    参数:
        new_logprobs: 当前 policy 的逐 token log prob, [B, T]
        old_logprobs: 采样时刻 frozen old policy 的 log prob, [B, T]
        mask:         [B, T]，1 表示该 token 在 response 内
    返回:
        ratio:        [B, T]，masked 后的 importance ratio
    """
    # TODO 1: 计算 log ratio = new - old
    log_ratio = _____

    # TODO 2: ratio = exp(log_ratio)，并对 padding 位置置 1（exp(0)=1，不影响后续 mean）
    ratio = _____
    ratio = ratio * mask + (1 - mask)
    return ratio


# ====== 测试 ======
torch.manual_seed(0)
B, T = 2, 6
old = torch.randn(B, T) * 0.1
new = old + torch.randn(B, T) * 0.05
mask = torch.tensor([[1, 1, 1, 1, 0, 0],
                     [1, 1, 1, 0, 0, 0]], dtype=torch.float)
ratio = importance_ratio(new, old, mask)
print(f"ratio range: [{ratio.min():.4f}, {ratio.max():.4f}]")  # 通常都接近 1.0
```



---

## 练习 2：GAE 倒序递推（Level 2）

GAE 的递推关系：$\hat{A}_t = \delta_t + \gamma\lambda\hat{A}_{t+1}$，必须**从最后一个 token 反向**累加。这是 PPO 实现里最容易写反的地方。

```python
import torch

def compute_gae(rewards, values, mask, gamma=1.0, lam=0.95):
    """
    GAE 倒序递推。

    参数:
        rewards: token 级 reward, [B, T]（KL 惩罚已揉进，最后一位还有 RM 标量）
        values:  critic 估计, [B, T]
        mask:    [B, T]
        gamma:   折扣因子（语言任务通常取 1.0）
        lam:     GAE λ
    返回:
        advantages, returns: 都是 [B, T]
    """
    B, T = rewards.shape
    advantages = torch.zeros_like(rewards)
    gae = torch.zeros(B)

    # TODO 1: 倒序遍历 t（从 T-1 到 0）
    for t in _____:
        # TODO 2: next_value：t+1 越界时为 0，否则取 values[:, t+1]
        next_value = _____

        # TODO 3: TD 残差 delta_t = r_t + gamma * V(t+1) - V(t)
        delta = _____

        # TODO 4: GAE 递推 A_t = delta + gamma * lam * A_{t+1}
        gae = _____

        advantages[:, t] = gae

    advantages = advantages * mask
    returns = advantages + values                              # critic 的回归目标
    return advantages.detach(), returns.detach()


# ====== 测试 ======
B, T = 2, 5
rewards = torch.zeros(B, T)
rewards[:, -1] = torch.tensor([1.0, -0.5])                     # RM 分加在最后一位
values = torch.zeros(B, T) + 0.1
mask = torch.ones(B, T)
adv, ret = compute_gae(rewards, values, mask)
print(f"advantages:\n{adv}")
print(f"returns:\n{ret}")
```



---

## 练习 3：Clipped Surrogate Policy Loss（Level 2）

PPO 用 `max(unclipped, clipped)` 作为 loss——这里的"max"是 PPO 论文里最容易记错的细节。

```python
import torch

def policy_surrogate_loss(new_logprobs, old_logprobs, advantages, mask, clip_range=0.2):
    """
    PPO clipped surrogate loss。

    参数:
        new_logprobs: [B, T]
        old_logprobs: [B, T]
        advantages:   [B, T]（来自 compute_gae）
        mask:         [B, T]
        clip_range:   ε，论文常用 0.2
    返回:
        scalar loss（已经过 mask 平均）
    """
    # TODO 1: 计算 ratio = exp(new - old)
    ratio = _____

    # TODO 2: unclipped 项 = -advantages * ratio
    unclipped = _____

    # TODO 3: clipped 项 = -advantages * clamp(ratio, 1 - eps, 1 + eps)
    clipped = _____

    # TODO 4: 取 max（悲观估计：选两者中 loss 更大的一项）
    loss_per_tok = _____

    # mask 平均
    return (loss_per_tok * mask).sum() / mask.sum().clamp(min=1)


# ====== 测试 ======
torch.manual_seed(1)
B, T = 2, 4
old = torch.zeros(B, T)
new = torch.tensor([[0.0, 0.5, -0.5, 1.0],
                    [-0.3, 0.0, 0.3, -0.1]])                  # ratio 越界样本
adv = torch.tensor([[1.0, 1.0, 1.0, 1.0],
                    [-1.0, -1.0, -1.0, -1.0]])
mask = torch.ones(B, T)
loss = policy_surrogate_loss(new, old, adv, mask, clip_range=0.2)
print(f"policy loss = {loss.item():+.4f}")
```



---

## 练习 4：Value Clipped Loss（Level 3）

PPO 的 value loss 不是简单的 MSE——critic 也要 clip，避免一次 inner update 把 `V_θ` 拉飞。这是 PPO 论文 Appendix 里经常被忽略的细节。

```python
import torch

def value_clipped_loss(new_values, old_values, returns, mask, clip_range_value=0.2):
    """
    PPO clipped value loss。

    参数:
        new_values: 当前 critic 输出, [B, T]
        old_values: rollout 时刻冻结的 critic 输出, [B, T]
        returns:    GAE 返回的 returns（advantages + values_old）, [B, T]
        mask:       [B, T]
        clip_range_value: critic 更新的 clip 范围
    返回:
        scalar loss
    """
    # TODO 1: 把 new_values 限制在 old_values ± clip_range_value 内
    v_clipped = _____

    # TODO 2: unclipped 损失 = (new_values - returns) ** 2
    loss_unclipped = _____

    # TODO 3: clipped 损失 = (v_clipped - returns) ** 2
    loss_clipped = _____

    # TODO 4: 取 max（同样是悲观估计）后乘 0.5
    loss_per_tok = _____

    return (loss_per_tok * mask).sum() / mask.sum().clamp(min=1)


# ====== 测试 ======
torch.manual_seed(2)
B, T = 2, 5
old_v = torch.randn(B, T) * 0.5
new_v = old_v + torch.randn(B, T) * 0.3                       # 引入了一些"漂移"
returns = old_v + torch.randn(B, T) * 0.4
mask = torch.ones(B, T)
loss = value_clipped_loss(new_v, old_v, returns, mask, clip_range_value=0.2)
print(f"value loss = {loss.item():.4f}")
```



---

## 练习 5：KL 散度的三种估计（Level 2）

K1（朴素）/ K2（无偏低方差）/ K3（Schulman 推荐）三种 KL 估计——RLHF 中 PPO 用 K1（揉进 reward），GRPO 用 K3（直接进 loss）。详见 [John Schulman 的博客](http://joschu.net/blog/kl-approx.html)。

```python
import torch

def kl_estimators(p_logprobs, q_logprobs):
    """
    给定从 q 采样的 token 序列在 p 和 q 下的 log prob，给出 KL(q || p) 的三种估计。

    定义 r = p / q（比值）；以下表达式都是从 q 采样估计 E_q[KL]：
        K1 = -log r
        K2 = (1/2) * (log r) ** 2
        K3 = (r - 1) - log r

    参数:
        p_logprobs: [B, T]，目标分布 p 在采样 token 上的 log prob
        q_logprobs: [B, T]，采样分布 q 在采样 token 上的 log prob
    返回:
        k1, k2, k3: 三个估计，形状均为 [B, T]
    """
    # TODO 1: log r = p_logprobs - q_logprobs
    log_r = _____

    # TODO 2: K1 = -log_r
    k1 = _____

    # TODO 3: K2 = 0.5 * log_r ** 2
    k2 = _____

    # TODO 4: K3 = exp(log_r) - 1 - log_r （等价于 r - 1 - log r）
    k3 = _____

    return k1, k2, k3


# ====== 测试 ======
torch.manual_seed(3)
B, T = 2, 8
q = torch.randn(B, T) * 0.5
p = q + torch.randn(B, T) * 0.05                              # p 与 q 接近
k1, k2, k3 = kl_estimators(p, q)
print(f"K1 mean = {k1.mean():+.4f}  (could be negative — high variance)")
print(f"K2 mean = {k2.mean():+.4f}  (always >= 0)")
print(f"K3 mean = {k3.mean():+.4f}  (always >= 0, low variance)")
```



---

## 练习 6：把 KL 揉进 Token-Level Reward（Level 3）

PPO 把 RM 的"序列级标量分"和 KL 惩罚的"token 级序列"统一到一条 token reward 张量里——这是 PPO 训练流程里最容易写错的拼装步骤。

```python
import torch

def shape_token_rewards(rm_score, logprobs, ref_logprobs, response_mask, kl_coef=0.05):
    """
    把 RM 序列级分数 + KL 惩罚拼成 token 级 reward。

    参数:
        rm_score:      [B]      RM 给整条 response 的标量分
        logprobs:      [B, T]   policy 当前 token log-prob
        ref_logprobs:  [B, T]   reference 模型的 token log-prob
        response_mask: [B, T]   1 表示该 token 在 response 内
        kl_coef:       float    KL 惩罚系数
    返回:
        token_rewards: [B, T]
    """
    # TODO 1: 每 token 的 KL（K1 估计）= logprobs - ref_logprobs
    kl = _____

    # TODO 2: token_rewards 全程减 kl_coef * kl（每 token 都受 KL 约束）
    token_rewards = _____

    # TODO 3: 找到每条样本的"最后一个 response token"位置
    last_idx = response_mask.sum(dim=-1).long() - 1

    # TODO 4: 把 RM 标量分加到最后一位（仅最后一个 response token）
    batch_idx = torch.arange(rm_score.size(0))
    token_rewards[batch_idx, last_idx] += _____

    # 应用 mask（response 之外置 0）
    return token_rewards * response_mask


# ====== 测试 ======
torch.manual_seed(4)
B, T = 2, 6
rm_score = torch.tensor([1.5, -0.3])                          # 第 1 条好，第 2 条差
logprobs = torch.randn(B, T) * 0.1
ref_logprobs = logprobs - torch.randn(B, T) * 0.05            # 假设 policy 比 ref 略微偏高
response_mask = torch.tensor([[0, 0, 1, 1, 1, 1],
                              [0, 1, 1, 1, 1, 0]], dtype=torch.float)
rewards = shape_token_rewards(rm_score, logprobs, ref_logprobs, response_mask, kl_coef=0.05)
print(f"token_rewards:\n{rewards}")
print(f"\n第 1 条最后一个 response token (位置 5) 应包含 RM 分: {rewards[0, 5]:.3f}  (≈ 1.5 + KL 项)")
print(f"第 2 条最后一个 response token (位置 4) 应包含 RM 分: {rewards[1, 4]:.3f}  (≈ -0.3 + KL 项)")
```



---

## 参考来源

[docs/exercises/ppo-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/ppo-fill.md)
