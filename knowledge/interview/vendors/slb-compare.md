---
source_id: interview-vendor-slb-001
corpus: interview
topic: interview
type: concept
version: 2026.05
---

# 负载均衡产品对照

| 能力 | 阿里云 | 腾讯云 | AWS |
|------|--------|--------|-----|
| 七层 LB | ALB | CLB(七层) | ALB |
| 四层 LB | NLB/SLB | CLB | NLB |
| 全球加速 | GA | GAAP | Global Accelerator |

面试时先问 **HTTP vs TCP、健康检查、会话保持、QUIC** 需求，再映射产品。


## 参考来源

- https://aws.amazon.com/elasticloadbalancing/
- https://www.alibabacloud.com/product/slb
