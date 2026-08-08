# 自定义 OpenAI-compatible API

[English](CUSTOM_API.md)

Custom 仅适用于真实实现了 OpenAI-compatible Chat Completions 接口的服务；它不代表任何 URL 都可以兼容。

在 **文件 → 设置 → AI** 填写：

- Provider 名称
- Base URL（包含兼容版本路径，通常是 `/v1`）
- API Key
- Model ID
- 可选的 Organization / Project
- 可选 Custom Headers（键和值均为字符串的 JSON 对象）
- Vision 与 structured output 能力声明

Custom Headers 不能覆盖认证头；请只在 API Key 输入框填写 Key。连接测试是用户主动触发的一次最小请求，可能消耗服务商额度。

对于本地服务，只有当其模型与端点确实接收图片 URL 时才启用 Vision；否则请关闭 Vision，只进行基于当前编辑状态的文字增量调整。
