# AI Lightroom V0.2

AI Lightroom 是一个 Windows 非破坏式桌面修图应用。传统滑块、HSL、曲线、蒙版和 AI 规划共享同一份 `EditorState`；预览和导出始终从原图与当前状态重新渲染，不会反复烧录处理结果。

## 当前功能

- JPG/PNG 打开、缩放、适配画布、直方图、原图按住对比、Undo/Redo、复制/粘贴调整。
- 基础调整、8 色 HSL、RGB/分通道曲线、色彩分级、局部蒙版和画笔。
- 全分辨率 JPG/PNG 导出，保留可用的 EXIF、ICC 和 DPI 元数据。
- PNG/JPG/WEBP 水印库；水印以非破坏式图层显示在预览和导出中。
- 自动恢复同一张照片的编辑状态与历史（保存于应用配置，不在照片旁生成文件）。
- Gemini structured output：严格 `EditingPlan` schema、本地二次 Pydantic 校验、不会以生成式重绘替代像素编辑。
- 离线 Mock Provider：未配置 Key 时可完整验证 AI → 编辑计划 → 渲染流程。
- AI 费用保护：默认每天本地上限 20 次、无自动重试、使用记录和可见 Provider 状态。

## 运行

```powershell
Set-Location D:\AI-Lightroom
.\.venv\Scripts\python.exe -m app.main
```

AI 输入框支持多行文本：`Enter` 换行，`Ctrl+Enter` 发送。

## 配置 AI Provider

默认 Provider 是 Gemini。在“文件 → 设置 → AI”中可选择 Gemini、OpenAI（高质量 AI 模式）或离线 Mock；两个 Key 分别写入 Windows Credential Manager，不会写入项目、日志或 EXE。

OpenAI 模式仅使用 Responses API 的视觉输入和严格 JSON `EditingPlan` 输出，不使用图片生成或编辑接口。默认模型为 `gpt-5.6-terra`，也可在设置中改为你账号可用、支持视觉与 Structured Outputs 的文本模型。

也可创建本地 `.env`：

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6-terra
```

环境变量优先于设置页。设置页可编辑系统提示词、关闭默认的自动复检，以及配置本地费用上限。免费保护模式的 `20 次/天` 仅是本地安全阈值，不代表 Google 的实时配额。

## 开发与测试

```powershell
Set-Location D:\AI-Lightroom
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest -q
```

## Windows 打包

```powershell
Set-Location D:\AI-Lightroom
.\scripts\build_windows.ps1
& '.\dist\AI Lightroom\AI Lightroom.exe' --smoke-test
```

打包输出：`dist\AI Lightroom\AI Lightroom.exe`。API Key、用户照片、水印库和会话数据均不进入 Git 或 EXE。

## 已知限制

- 当前正式输入为 JPG/PNG；RAW、16-bit 和完整 ICC 工作流尚未实现。
- 天空/主体/语义蒙版采用轻量本地算法，复杂边缘不等同于大型分割模型。
- 曲线为分段线性；渲染当前使用 OpenCV/CPU。
- 水印支持锚点位置、大小、不透明度和边距；直接拖动、旋转与阴影尚未实现。
- 本地调用计数保守记录已发起的云端请求；它不是 Google 后台账单或额度查询。
