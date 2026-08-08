# AI Lightroom

AI Lightroom 是一个 Windows 非破坏式桌面照片编辑器。传统滑块、HSL、曲线、局部蒙版和 AI 规划共用同一个 `EditorState`；预览和导出始终从原图与当前状态重新渲染，不会反复烧录处理结果。

## 当前功能

- JPG / PNG 打开、缩放、适合窗口和全分辨率导出
- 曝光、明暗、白平衡、饱和度、清晰度、纹理、去朦胧、锐化和暗角
- 八色 HSL、RGB 与分通道曲线、阴影/中间调/高光色彩分级
- Undo / Redo / Reset 和可点击历史记录
- 线性、径向、明度、颜色范围、天空、主体、常见语义区域和画笔蒙版
- 严格可验证的 AI Editing DSL；AI 只能调用软件真实支持的操作
- Gemini 多模态 Provider 与离线 Mock Provider
- 后续自然语言命令基于当前状态继续修改；简单的“淡一点”不会重复上传预览
- 设置页、后台 AI/导出任务、Windows 凭据管理器存储 API Key

## 直接运行

```powershell
.\.venv\Scripts\python.exe -m app.main
```

没有 Gemini API Key 时，AI 面板自动使用离线 Mock，核心流程仍可完整体验。

## 配置 Gemini

推荐在应用的“文件 → 设置”中填写 API Key。Key 保存到 Windows 凭据管理器，不进入项目目录。

也可以复制 `.env.example` 为 `.env` 并填写：

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
```

模型名可随时在设置页或 `.env` 中更换，不写死在编辑引擎里。`.env` 已被 Git 忽略。

## 开发环境

需要 Python 3.11–3.13。首次重建环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

运行测试：

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest
```

## Windows 打包

```powershell
.\scripts\build_windows.ps1
```

输出位于 `dist\AI Lightroom\AI Lightroom.exe`。API Key 和用户照片不会打入 EXE。

## 当前限制

- 第一版只支持 JPG / PNG；RAW、16 位完整管线和相机配置文件仍待扩展。
- 天空、主体和语义蒙版使用轻量本地算法，速度和安装体积优先，复杂边缘不等同于大型分割模型。
- 曲线为确定性的分段线性曲线；尚未提供 Lightroom 目录管理和批量同步。
- GPU 已检测但第一版渲染器使用 OpenCV / CPU；AI 请求由云端 Gemini 或离线 Mock 负责规划。
