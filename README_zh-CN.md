# AI Lightroom

[English](README.md)

AI Lightroom 是一款 Windows 桌面照片编辑器，提供非破坏式传统调色和可选的自然语言 AI 调色方案。AI 只输出可验证的编辑计划，真正像素处理由本地渲染器完成，不会生成式重绘照片。

![AI Lightroom 界面](docs/assets/application-shell.png)

## 功能

- JPG/PNG 导入、拖拽打开、最近文件、缩放、适合窗口、直方图、原图对比、撤销/重做与恢复编辑。
- 实时基础调整、HSL、曲线、色彩分级、局部蒙版、画笔蒙版和非破坏式水印。
- 原始分辨率 JPG/PNG 导出，并尽量保留 EXIF、ICC 与 DPI。
- Gemini、OpenAI、Qwen/DashScope、DeepSeek 文本增量、Custom OpenAI-compatible、JarvisArt Local 和离线 Mock。
- 默认无自动重试；云端调用采用本地每日安全上限。无 API Key 时仍可完整手动修图。

## 快速使用

从 GitHub Release 下载 Windows x64 ZIP，解压后双击 `AI Lightroom.exe`。打开或拖入图片，调节滑块、HSL、曲线、蒙版或水印；`Ctrl+S` 导出。原始照片默认不会被覆盖。

在 **文件 → 设置** 中可选配 AI Provider。AI 输入框中 `Ctrl+Enter` 发送，`Enter` 换行。

## JarvisArt Local

JarvisArt 是独立可选组件，不包含在本仓库或 Release 中。AI Lightroom 仅连接已安装 JarvisArt 的 localhost 服务，发送缩小预览；模型、运行环境和许可证均保持独立。详情见 [JarvisArt Local](docs/JARVISART.md)。

## 自定义兼容 API

选择 **Custom / OpenAI-compatible API**，填写 Provider 名称、Base URL、API Key 和 Model ID。可选填写 Organization / Project 与安全的 JSON 自定义 Headers。是否开启 Vision/Structured Output 由用户按目标服务真实能力声明。详见 [Custom API](docs/CUSTOM_API.md)。

## 隐私与费用

- 本软件不提供、不转发 API Key。
- 云端仅收到缩小 JPEG 预览与编辑状态，原始全分辨率照片留在本机。
- JarvisArt Local、Offline Mock 不消耗云端额度。
- API Key 存在 Windows Credential Manager；不会写进源码、日志或 Release。

## 文档与许可证

完整说明见 [用户指南](docs/USER_GUIDE.md)、[AI Provider](docs/AI_PROVIDERS.md)、[安装](docs/INSTALLATION.md) 与 [故障排除](docs/TROUBLESHOOTING.md)。AI Lightroom 代码采用 [MIT License](LICENSE)；第三方声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本项目不隶属于 Adobe。
