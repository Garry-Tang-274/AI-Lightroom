# AI Lightroom

AI Lightroom 是一个面向 Windows 的非破坏式桌面照片编辑器。它把传统可见参数、局部蒙版和结构化 AI 编辑计划放在同一套编辑状态中。

项目仍在连续开发中。当前桌面壳、JPG/PNG 打开、缩放与专业深色界面已经可运行，编辑引擎、AI、蒙版和导出会在后续里程碑接入。

## 开发运行

```powershell
.\.venv\Scripts\python.exe -m app.main
```

## 测试

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest
```

API Key 不会写入仓库。Gemini 配置格式见 `.env.example`。
