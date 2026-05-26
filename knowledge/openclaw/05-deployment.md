---
source_id: openclaw-deploy-001
corpus: tech
topic: openclaw
type: concept
version: 2026.05
---

# 部署与安全边界

## 部署选项

- 本机 macOS/Linux；Windows 建议 WSL2
- VPS 常开：适合 Telegram 远程触发
- `openclaw onboard` 向导配置 Gateway、渠道、Skills

## 数据边界

- BYOM：可接 Ollama 离线模型
- 密钥存本地配置，勿提交仓库
- 无默认遥测；企业场景仍需自审工具权限

## SA 面试场景

客户问「能否私有化 IM 助手」：答 OpenClaw 类架构 = 自建 Gateway + 内网 LLM + 审计。


## 参考来源

- https://docs.openclaw.ai/start/wizard
