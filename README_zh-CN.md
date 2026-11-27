# AI Lightroom

[English](README.md)

<p align="center">
  <img src="assets/app.png" width="128" alt="AI Lightroom 应用图标">
</p>

AI Lightroom 是一款 Windows 桌面照片编辑器：传统参数调色与自然语言 AI 调色共用同一套非破坏性编辑状态。AI 只会返回可验证的编辑方案；真正的像素处理由本地渲染器完成，绝不会用生成式模型重绘你的照片。

![AI Lightroom 界面](docs/assets/application-shell.png)

## 先从这里开始

第一次使用、安装包、云端 AI 配置、JarvisArt 模型下载、导出和常见错误，请直接看：

**[中文新手完整指南](docs/GETTING_STARTED_zh-CN.md)** · [English getting-started guide](docs/GETTING_STARTED.md)

日常使用可先看[手动修图与文字调色示例](docs/EDITING_WORKFLOWS.md)。**v1.2.0 照片组与调色配方**的主要变化见[中英双语发布说明](docs/RELEASE_1_2.md)。

## 已支持的功能

- JPG / PNG 后台载入、多选或拖入照片组、组内导航、缩放、直方图、可拖动左右对比、专注模式，每张照片独立保存编辑与撤回/重做历史。
- 右侧独立的“调色 / AI 助手”页；调色参数按明暗、色彩、HSL、曲线、分级、细节/降噪、效果、光学、几何和校准分组，可折叠并按中英文名称搜索。
- 已改参数高亮、仅看已调整、单项复位、分级融合/平衡，以及可保存并跨启动复用的调色配方。
- 局部蒙版、画笔蒙版和非破坏性水印；渐变与范围参数、自定义水印位置均可手动修改。
- 从原始全分辨率照片以 sRGB 工作色彩空间渲染导出 JPG / PNG，可选保留或去除摄影 EXIF，并保留可用的 DPI。
- Gemini、OpenAI、Qwen / DashScope、DeepSeek 文本增量、Custom OpenAI-compatible、JarvisArt Local GGUF 与离线 Mock。
- API 调用默认无自动重试；云端调用有本地每日安全上限。

## 三种使用方式

| 你想做什么 | 需要什么 | 从哪里开始 |
| --- | --- | --- |
| 纯手动修图 | 无账号、无 API Key | 下载后直接运行即可。 |
| 使用云端 AI 调色 | 对应服务商的 API Key | 在 **文件 → 设置 → AI 服务**选择 Provider 并测试连接。 |
| 本地运行 JarvisArt | 独立安装的 JarvisArt、模型与本地桥接服务 | 阅读 [JarvisArt 本地部署与连接说明](docs/JARVISART_zh-CN.md)。 |

## JarvisArt Local 效果示例

<p align="center">
  <img src="docs/assets/jarvisart-local-before-after.jpg" width="800" alt="JarvisArt Local 航拍照片前后对比：上方原图，下方调整结果">
</p>

上方为原图，下方为本地应用后的结果。使用的提示词是：“把这张照片调成冷峻、硬朗、低饱和的电影感。整体稍微压暗，加强地表纹理和道路层次，白色主体保持清晰，不要过度 HDR。”它展示了如何同时给出明确的视觉方向和保护条件，而不是笼统地要求“修得更好”。完整提示词、界面示意和结果解读见 [JarvisArt 本地部署与连接说明](docs/JARVISART_zh-CN.md)。

## 快速操作

1. 从 GitHub Releases 下载 Windows 安装包或 ZIP；安装包最简单，ZIP 必须完整解压后再运行。
2. 用 `Ctrl+O` 多选 JPG / PNG，或拖入多张照片。画布标题栏箭头及 `Alt+←` / `Alt+→` 切换照片，点照片计数可跳转。在右侧**调色**页搜索参数或勾选**仅看已调整**；左侧有**蒙版**与**水印**。
3. 按 `C` 打开可拖动的左右对比，按 `Ctrl+Tab` 切换专注模式；`Ctrl+S` 导出一份全尺寸成片。程序会拒绝覆盖当前照片组内的任何原图。
4. 如需 AI，在 **文件 → 设置 → AI 服务**配置 Provider；切换右侧 **AI 助手**页，`Ctrl+Enter` 发送，`Enter` 换行。

回访当前组内已编辑的照片，会继续它自己的编辑与历史；首次从持久记录恢复仍会询问。需要复用风格时，点工具栏**配方 → 将当前调色存为配方…**并命名，再切换照片应用。配方保留基础调色、HSL、曲线、分级、细节、效果和校准，不带入光学、几何、蒙版或水印；应用可一次撤销，配方在关闭程序后仍保留。

## 预览质量与 AI 发送质量

工具栏的 **低清预览 / 高清预览** 按钮可以立即切换工作画布；也可在 **文件 → 设置 → 性能与导出** 中选择。

拖动期间临时使用快速预览：默认**平衡**模式最长边为 **1280 px**，**省电**为 **768 px**，**精细交互**为 **1600 px**，可在**设置 → 性能与导出 → 性能模式**选择。松手恢复所选质量，不影响 AI 发送质量和最终全尺寸导出。画布的 100% 指工作预览像素。

- **自动（默认）**：云端 Provider 默认低清，减少上传和费用；**JarvisArt Local GGUF** 默认高清，因为它在本机运行。
- **低清** 默认最长边为 1536 px；**高清** 默认最长边为 3072 px；两个数值都可以修改。
- “发送给 AI 的图像质量”可独立选择“跟随画布 / 始终低清 / 始终高清”。发生视觉分析时，AI 只会收到该大小的 JPEG 预览，不会收到原始全分辨率照片。
- “弱一点”“退一点”这类纯文字增量请求可能不会再传图，这是为了延续已有的费用保护；需要重新看图时请明确说“重新看看”。

## 隐私、费用与许可

- 不配置 API Key 也可以完整手动修图。
- 云端 AI 只接收缩小的 JPEG 预览和当前编辑状态；原始全分辨率照片始终保留在本机。
- AI 面板显示实际处理阶段与耗时，不伪造进度百分比。取消后不应用结果；已发送的云端请求仍可能计费，本地模型也可能仍在运行。失败不会自动重试。
- **设置 → 性能与导出 → 导出 EXIF**默认保留拍摄信息，可能含 GPS。分享前取消此项，新导出的照片将去除摄影 EXIF，包括其中的 GPS。
- API Key 存在 Windows Credential Manager，不写入源码、日志、发布包或 Git。
- JarvisArt Local GGUF 是用户自行安装的本地运行时，模型、llama.cpp 与许可证不随本项目分发。只有 **Local GGUF** 才会进行真实本地推理；**Mock** 是固定开发样例，软件会阻止它用于真实调色。
- AI Lightroom 代码采用 [MIT License](LICENSE)；第三方说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本项目与 Adobe 没有隶属或认可关系。

## 文档

- [使用指南](docs/USER_GUIDE_zh-CN.md) · [1.2 发布说明](docs/RELEASE_1_2.md) · [渲染器配对性能实测](docs/benchmarks/README.md)
- [中文新手完整指南](docs/GETTING_STARTED_zh-CN.md) · [English getting-started guide](docs/GETTING_STARTED.md)
- [安装包说明](docs/INSTALLER_zh-CN.md) · [Installer guide (English)](docs/INSTALLER.md)
- [JarvisArt 本地部署与连接说明](docs/JARVISART_zh-CN.md)
- [AI Provider 说明](docs/AI_PROVIDERS_zh-CN.md) · [English](docs/AI_PROVIDERS.md)
- [自定义 OpenAI-compatible API](docs/CUSTOM_API_zh-CN.md) · [English](docs/CUSTOM_API.md)
- [故障排除](docs/TROUBLESHOOTING_zh-CN.md) · [English](docs/TROUBLESHOOTING.md)
- [安装与源码运行](docs/INSTALLATION_zh-CN.md) · [Windows 打包](docs/BUILDING_zh-CN.md)
- [架构](docs/ARCHITECTURE_zh-CN.md) · [Provider 开发说明](docs/PROVIDER_DEVELOPMENT_zh-CN.md)
