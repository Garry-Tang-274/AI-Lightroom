# AI Lightroom

[English](README.md)

<p align="center">
  <img src="assets/app.png" width="128" alt="AI Lightroom 应用图标">
</p>

AI Lightroom 是一款 Windows 桌面照片编辑器：传统参数调色与自然语言 AI 调色共用同一套非破坏性编辑状态。AI 只会返回可验证的编辑方案；真正的像素处理由本地渲染器完成，绝不会用生成式模型重绘你的照片。

![AI Lightroom 界面](docs/assets/application-shell.png)

## 先从这里开始

第一次使用、安装包、云端 AI 配置、JarvisArt 模型下载、导出和常见错误，请直接看：

**[中文新手完整指南](docs/GETTING_STARTED_zh-CN.md)**

## 已支持的功能

- JPG / PNG 导入、拖入打开、缩放、适合窗口、直方图、原图对比、撤回/重做与编辑恢复。
- 实时基础参数、HSL、RGB/通道曲线、色彩分级、局部蒙版、画笔蒙版和非破坏性水印。
- 从原始全分辨率照片渲染导出 JPG / PNG，并尽量保留 EXIF、ICC 与 DPI。
- Gemini、OpenAI、Qwen / DashScope、DeepSeek 文本增量、Custom OpenAI-compatible、JarvisArt Local 与离线 Mock。
- API 调用默认无自动重试；云端调用有本地每日安全上限。

## 三种使用方式

| 你想做什么 | 需要什么 | 从哪里开始 |
| --- | --- | --- |
| 纯手动修图 | 无账号、无 API Key | 下载后直接运行即可。 |
| 使用云端 AI 调色 | 对应服务商的 API Key | 在 **文件 → 设置 → AI** 选择 Provider 并测试连接。 |
| 本地运行 JarvisArt | 独立安装的 JarvisArt、模型与本地桥接服务 | 阅读 [JarvisArt 本地部署与连接说明](docs/JARVISART_zh-CN.md)。 |

## 快速操作

1. 从 GitHub Releases 下载 Windows 安装包或 ZIP；安装包最简单，ZIP 必须完整解压后再运行。
2. 打开或拖入 JPG / PNG 照片。右侧滑块、HSL、曲线、蒙版与水印都可直接使用。
3. `Ctrl+S` 导出。默认不会覆盖原始照片。
4. 如需 AI，在 **文件 → 设置** 配置 Provider；AI 输入框中 `Ctrl+Enter` 发送，`Enter` 换行。

## 隐私、费用与许可

- 不配置 API Key 也可以完整手动修图。
- 云端 AI 只接收缩小的 JPEG 预览和当前编辑状态；原始全分辨率照片始终保留在本机。
- API Key 存在 Windows Credential Manager，不写入源码、日志、发布包或 Git。
- JarvisArt 是独立可选组件，模型、运行环境与许可证不随本项目分发。
- AI Lightroom 代码采用 [MIT License](LICENSE)；第三方说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本项目与 Adobe 没有隶属或认可关系。

## 文档

- [中文新手完整指南](docs/GETTING_STARTED_zh-CN.md)
- [安装包说明](docs/INSTALLER_zh-CN.md)
- [JarvisArt 本地部署与连接说明](docs/JARVISART_zh-CN.md)
- [AI Provider 说明](docs/AI_PROVIDERS.md)
- [自定义 OpenAI-compatible API](docs/CUSTOM_API.md)
- [故障排除](docs/TROUBLESHOOTING.md)
