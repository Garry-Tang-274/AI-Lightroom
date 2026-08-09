# AI Lightroom

**English · 简体中文** — This primary README is intentionally bilingual. A Chinese-only reading mirror is also available at [README_zh-CN.md](README_zh-CN.md).

**中英双语** — 本主 README 采用逐节中英对照；如需只阅读中文，也可使用 [README_zh-CN.md](README_zh-CN.md)。

<p align="center">
  <img src="assets/app.png" width="128" alt="AI Lightroom app icon / AI Lightroom 应用图标">
</p>

AI Lightroom is a Windows desktop photo editor for non-destructive traditional adjustments and optional natural-language AI colour-grading plans. The local renderer applies supported parameters, HSL, curves, masks, and watermarks; it does not redraw or generate a replacement photograph.

AI Lightroom 是一款 Windows 桌面照片编辑器，提供非破坏性的传统调色与可选的自然语言 AI 调色方案。本地渲染器只应用支持的参数、HSL、曲线、蒙版和水印；不会重绘或生成一张替代照片。

![AI Lightroom interface / AI Lightroom 界面](docs/assets/application-shell.png)

## Features / 功能

- JPG/PNG import, drag-and-drop, recent files, zoom, fit, 100%, histogram, before/after, undo/redo, and crash-recovery sessions.<br>
  支持 JPG/PNG 导入、拖入打开、最近文件、缩放、适合窗口、100%、直方图、原图对比、撤回/重做和崩溃恢复会话。
- Real-time Basic adjustments, HSL, RGB/channel curves, colour grading, masks, brush masks, and non-destructive watermark layers.<br>
  提供实时基础参数、HSL、RGB/通道曲线、色彩分级、蒙版、画笔蒙版和非破坏性水印图层。
- Full-resolution JPG/PNG export with available EXIF, ICC, and DPI metadata.<br>
  以全分辨率导出 JPG/PNG，并尽量保留可用的 EXIF、ICC 与 DPI 元数据。
- One shared `EditingPlan` and `EditorState` for manual controls and every AI provider.<br>
  手动控件和所有 AI Provider 共用同一套 `EditingPlan` 与 `EditorState`。
- Provider registry: JarvisArt Local GGUF, Gemini, OpenAI, Qwen/DashScope, DeepSeek text adjustments, Custom OpenAI-compatible API, and Offline Mock.<br>
  Provider 注册表包括 JarvisArt Local GGUF、Gemini、OpenAI、Qwen/DashScope、DeepSeek 文本增量、Custom OpenAI-compatible API 与 Offline Mock。
- Cloud safeguards: no automatic retry, one cloud request per user action by default, and a local daily safety limit.<br>
  云端安全措施：默认不自动重试、一次用户操作最多发起一次云端请求，并提供本地每日安全上限。

## Installation / 安装

Download the Windows x64 installer or ZIP from the GitHub Releases page. The installer is the easiest option; for the ZIP, extract the **whole** archive and run `AI Lightroom.exe`. No AI account is required for manual editing.

从 GitHub Releases 下载 Windows x64 安装包或 ZIP。安装包最省事；使用 ZIP 时必须完整解压后再运行 `AI Lightroom.exe`。仅使用手动编辑不需要 AI 账号。

For source setup, see [Installation / 安装与源码运行](docs/INSTALLATION.md) and [Building / Windows 打包](docs/BUILDING.md). Beginner guides are available in [English](docs/GETTING_STARTED.md) and [简体中文](docs/GETTING_STARTED_zh-CN.md).

源码环境请参阅[Installation / 安装与源码运行](docs/INSTALLATION.md)和[Building / Windows 打包](docs/BUILDING.md)。新手完整指南提供[英文版](docs/GETTING_STARTED.md)和[简体中文版](docs/GETTING_STARTED_zh-CN.md)。

## Quick start / 快速开始

1. Open or drag a JPG/PNG into the app.<br>
   打开或拖入一张 JPG/PNG 照片。
2. Adjust sliders, HSL, curves, masks, or watermarks. Double-click a slider to reset it; enter exact values in its value field.<br>
   调整滑块、HSL、曲线、蒙版或水印。双击滑块可重置；可在数值框内输入精确值。
3. Export with `Ctrl+S` or `Ctrl+Shift+S`. Original files are never overwritten by default.<br>
   使用 `Ctrl+S` 或 `Ctrl+Shift+S` 导出。默认绝不会覆盖原始文件。
4. Optionally configure an AI provider in **File → Settings** and use `Ctrl+Enter` to send an AI prompt.<br>
   可在**文件 → 设置**配置 AI Provider，并用 `Ctrl+Enter` 发送 AI 提示词。

## Preview quality / 预览质量

Use the **Low preview / High preview** button in the toolbar, or **File → Settings → Performance & Export**, to choose the working-preview size. High quality rebuilds a larger local preview; when a visual request is needed, the AI receives a JPEG preview using the independently configured AI image-quality setting.

使用工具栏的**低清预览 / 高清预览**按钮，或进入**文件 → 设置 → 性能与导出**选择工作预览尺寸。高清会重建更大的本地预览；需要视觉分析时，AI 会收到按独立“AI 图像质量”设置生成的 JPEG 预览。

- **Automatic / 自动** (default / 默认): cloud providers use low quality to limit transfer and cost; **JarvisArt Local GGUF** uses high quality because it runs locally.<br>
  云端 Provider 使用低清以控制传输量和费用；**JarvisArt Local GGUF** 在本机运行，默认使用高清。
- **Low / 低清**: default maximum edge is 1536 px.<br>
  默认最长边为 1536 px。
- **High / 高清**: default maximum edge is 3072 px; both limits are editable in Settings.<br>
  默认最长边为 3072 px；两个限制都可在设置中修改。
- Incremental text-only requests may intentionally omit an image. This preserves the existing state-aware cost safeguard.<br>
  纯文字增量请求可能有意不再发送图片，以保留基于编辑状态的费用保护机制。

## AI providers / AI Provider

AI Lightroom does not proxy photos or API keys through a project server. Each cloud provider uses the account and key configured by the user.

AI Lightroom 不会通过项目服务器代理照片或 API Key。每个云端 Provider 均使用用户自行配置的账号和密钥。

| Provider / 服务 | Vision / 视觉能力 | Cost & privacy / 费用与隐私 | Notes / 说明 |
| --- | --- | --- | --- |
| JarvisArt Local GGUF | Yes / 是 | Local, no API fee / 本地，无 API 费用 | User-supplied local GGUF bridge; high preview by default. / 用户自备本地 GGUF bridge，默认高清预览。见 [JarvisArt](docs/JARVISART.md)。 |
| Google Gemini | Yes / 是 | Cloud preview, provider quota/cost / 云端预览，服务商额度/费用 | User-configured model ID. / 用户配置模型 ID。 |
| OpenAI | Yes / 是 | Cloud preview, provider cost / 云端预览，服务商费用 | User-configured model ID. / 用户配置模型 ID。 |
| Qwen / DashScope | Yes / 是 | Cloud preview, provider quota/cost / 云端预览，服务商额度/费用 | Default endpoint can be changed. / 可更改默认 endpoint。 |
| DeepSeek | No / 否 | Text + edit state only / 仅文本与编辑状态 | For incremental text edits, not first-pass image analysis. / 用于增量文字调整，不用于首次看图分析。 |
| Custom OpenAI-compatible | User declared / 用户声明 | User configured / 用户配置 | Base URL, key, model, optional organization and safe custom headers. / Base URL、密钥、模型、可选组织与安全自定义 header。 |
| Offline Mock / JarvisArt Mock | Fixture / 固定样例 | Local, free / 本地免费 | Development-only; it cannot inspect a photograph and is blocked from real editing. / 仅供开发；无法看图，且被禁止用于真实编辑。 |

### JarvisArt Local / JarvisArt 本地运行

JarvisArt Local GGUF is an optional, user-supplied localhost runtime and is not included in this repository or release. AI Lightroom connects only to its local bridge and sends a temporary local preview over loopback. It defaults to the high-quality size; this can be changed in Settings. The GGUF, llama.cpp runtime, and any model license remain separate. See [JarvisArt Local / JarvisArt 本地说明](docs/JARVISART.md).

JarvisArt Local GGUF 是可选、由用户自备的 localhost 运行时，不随本仓库或 Release 分发。AI Lightroom 只连接其本地 bridge，并通过 loopback 发送临时本地预览。默认使用高清尺寸，可在设置中修改。GGUF、llama.cpp 运行时及模型许可证均保持独立。详见 [JarvisArt Local / JarvisArt 本地说明](docs/JARVISART_zh-CN.md)。

#### Example: a restrained cinematic aerial grade / 示例：克制的电影感航拍调色

<p align="center">
  <img src="docs/assets/jarvisart-local-before-after.jpg" width="800" alt="JarvisArt Local before and after aerial road grade: original above, edited result below / JarvisArt Local 航拍道路前后对比：上方原图，下方调整结果">
</p>

Top: original. Bottom: the locally applied result. The request was: “Give this image a cool, hard-edged, low-saturation cinematic look. Darken it slightly overall, strengthen terrain texture and road separation, keep the white subject clear, and avoid excessive HDR.”

上方为原图，下方为本地应用后的结果。使用的提示词是：“把这张照片调成冷峻、硬朗、低饱和的电影感。整体稍微压暗，加强地表纹理和道路层次，白色主体保持清晰，不要过度 HDR。”

This is a useful example of a specific photographic direction with a preservation constraint, rather than a generic “make it better” request. The full prompt, interface reference, and interpretation are in [JarvisArt Local](docs/JARVISART.md).

这展示了如何同时给出明确的摄影方向和保护条件，而不是笼统地要求“修得更好”。完整提示词、界面示意和结果解读见 [JarvisArt Local](docs/JARVISART_zh-CN.md)。

### Custom API / 自定义 API

Choose **Custom / OpenAI-compatible API** in Settings and supply a Provider Name, Base URL, API Key, and Model ID. Vision and structured output switches are declarations by the user; only enable capabilities the target service actually supports. The app rejects custom `Authorization` headers so API keys remain in Windows Credential Manager. See [Custom API](docs/CUSTOM_API.md).

在设置中选择 **Custom / OpenAI-compatible API**，并填写 Provider Name、Base URL、API Key 和 Model ID。Vision 与 structured output 开关是用户声明；只启用目标服务真实支持的能力。应用拒绝自定义 `Authorization` header，使 API Key 保持在 Windows Credential Manager 中。见[自定义 API](docs/CUSTOM_API_zh-CN.md)。

## Privacy and cost / 隐私与费用

- The editor works with no API key.<br>
  不配置 API Key 也可完整使用编辑器。
- Cloud calls send only a configured capped JPEG preview and edit state, never the original full-resolution image.<br>
  云端调用只发送受尺寸限制的 JPEG 预览和编辑状态，绝不发送原始全分辨率照片。
- Real local JarvisArt and Offline Mock do not use the cloud budget manager. Mock is a blocked development fixture, not an image-analysis option.<br>
  真实本地 JarvisArt 与 Offline Mock 不使用云端预算管理器。Mock 是被阻止的开发固定样例，不是图像分析选项。
- API keys are stored separately in Windows Credential Manager (environment variables can override them), never in project configuration, logs, release packages, or source control.<br>
  API Key 单独存储在 Windows Credential Manager 中（可由环境变量覆盖），绝不写入项目配置、日志、发布包或版本控制。
- A cancelled cloud request may already have reached the provider and may count as one call.<br>
  被取消的云端请求可能已经到达服务商，仍可能计为一次调用。

## Keyboard shortcuts / 键盘快捷键

| Shortcut / 快捷键 | Action / 操作 |
| --- | --- |
| `Ctrl+O` | Open image / 打开图像 |
| `Ctrl+S` / `Ctrl+Shift+S` | Export / Export as / 导出 / 另存为 |
| `Ctrl+Z` | Undo / 撤回 |
| `Ctrl+Y` or `Ctrl+Shift+Z` | Redo / 重做 |
| `\` or hold **Original** | Before/after / 原图对比 |
| `F` / `1` | Fit / 100% / 适合窗口 / 100% |
| Mouse wheel / 鼠标滚轮 | Zoom image; sliders ignore the wheel / 缩放图像；滑块不响应滚轮 |
| `Ctrl+Enter` | Send AI request / 发送 AI 请求 |
| `Enter` | New line in AI prompt / 在 AI 提示词中换行 |

## Documentation / 文档

- [Getting started / 新手指南](docs/GETTING_STARTED.md) · [中文新手完整指南](docs/GETTING_STARTED_zh-CN.md)
- [Installer guide / 安装包说明](docs/INSTALLER.md) · [中文安装包说明](docs/INSTALLER_zh-CN.md)
- [User guide / 使用指南](docs/USER_GUIDE.md) · [中文使用指南](docs/USER_GUIDE_zh-CN.md)
- [AI providers / AI Provider](docs/AI_PROVIDERS.md) · [AI Provider 中文说明](docs/AI_PROVIDERS_zh-CN.md)
- [JarvisArt Local / JarvisArt 本地说明](docs/JARVISART.md) · [中文部署与连接说明](docs/JARVISART_zh-CN.md)
- [Custom API / 自定义 API](docs/CUSTOM_API.md) · [自定义 API 中文说明](docs/CUSTOM_API_zh-CN.md)
- [Provider development / Provider 开发](docs/PROVIDER_DEVELOPMENT.md) · [Provider 开发中文说明](docs/PROVIDER_DEVELOPMENT_zh-CN.md)
- [Architecture / 架构](docs/ARCHITECTURE.md) · [中文架构说明](docs/ARCHITECTURE_zh-CN.md)
- [Troubleshooting / 故障排除](docs/TROUBLESHOOTING.md) · [故障排除中文说明](docs/TROUBLESHOOTING_zh-CN.md)
- [Changelog / 更新日志](CHANGELOG.md) · [中文更新日志](CHANGELOG_zh-CN.md)
- [Contributing / 贡献指南](CONTRIBUTING.md) · [中文贡献指南](CONTRIBUTING_zh-CN.md)
- [Security / 安全政策](SECURITY.md) · [中文安全政策](SECURITY_zh-CN.md)
- [Code of Conduct / 行为准则](CODE_OF_CONDUCT.md) · [中文行为准则](CODE_OF_CONDUCT_zh-CN.md)

## Roadmap and limitations / 路线图与限制

This release supports JPG/PNG, not a RAW workflow. Local semantic masks are conservative OpenCV analysis rather than a large segmentation model. JarvisArt's current localhost bridge returns global Lightroom parameters; unsupported native Lightroom operations remain visible and are never silently applied. See the [CHANGELOG](CHANGELOG.md) for the release scope.

当前版本支持 JPG/PNG，而非 RAW 工作流。局部语义蒙版采用保守的 OpenCV 分析，不是大型分割模型。JarvisArt 当前 localhost bridge 返回全局 Lightroom 参数；尚不支持的原生 Lightroom 操作会明确显示，绝不会被悄悄伪装为已应用。发布范围见 [CHANGELOG](CHANGELOG.md)。

## License and credits / 许可证与致谢

AI Lightroom source code is released under the [MIT License (authoritative English text)](LICENSE); a [Chinese reference translation](LICENSE_zh-CN.md) is provided for convenience. Third-party notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). JarvisArt and its model are separate optional components governed by their own license; this project does not redistribute either one. AI Lightroom is not affiliated with or endorsed by Adobe.

AI Lightroom 源代码采用 [MIT License（具法律效力的英文原文）](LICENSE)，并提供便于阅读的[中文参考译文](LICENSE_zh-CN.md)。第三方说明见 [THIRD_PARTY_NOTICES_zh-CN.md](THIRD_PARTY_NOTICES_zh-CN.md)。JarvisArt 及其模型是受自身许可证约束的独立可选组件，本项目不重新分发其中任何一个。AI Lightroom 与 Adobe 没有隶属或认可关系。
