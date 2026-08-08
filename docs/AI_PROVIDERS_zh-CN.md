# AI Provider 说明

[English](AI_PROVIDERS.md)

所有 Provider 都只输出同一套严格 `EditingPlan`；图像渲染器不依赖任何 AI 厂商。

Gemini、OpenAI 和 Qwen 可使用视觉模型。进入 **文件 → 设置 → 性能与导出** 后，可单独选择画布预览与 AI 发送图片的低清/高清质量：云端自动默认低清（默认最长边 1536 px）；用户自行安装的 JarvisArt Local GGUF 自动默认高清（默认最长边 3072 px）。纯文字的增量指令可能不再发图；需要重新判断照片时请明确说“重新看看”。

DeepSeek 当前只处理文字与当前编辑状态，适合“饱和度再低一点”这类增量操作，不应用于首次看图。

连接测试是你主动触发的调用，可能消耗服务商额度。普通请求不自动重试；只要云端请求已经发出，即使后续校验失败，也会计入本地调用记录。

## Key 与配置

Key 的读取优先级是相应环境变量，然后是 Windows Credential Manager。设置不会把 Key 写入 Git 可追踪文件。

| Provider | 环境变量 | 可选 Endpoint 变量 |
| --- | --- | --- |
| Gemini | `GEMINI_API_KEY` | — |
| OpenAI | `OPENAI_API_KEY` | — |
| Qwen | `DASHSCOPE_API_KEY` | `QWEN_BASE_URL` |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL` |
| Custom | `AI_LIGHTROOM_CUSTOM_API_KEY` | `AI_LIGHTROOM_CUSTOM_BASE_URL` |

## Mock 边界

Offline Mock 与 JarvisArt Local 的 Mock Native 都是开发 fixture，不是视觉模型。它们不能读取照片。JarvisArt Mock 会被软件阻止执行，以免固定演示参数被误当成真实 AI 分析。

参见 [Custom API](CUSTOM_API.md) 与 [JarvisArt Local](JARVISART_zh-CN.md)。
