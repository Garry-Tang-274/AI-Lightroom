# 安装与源码运行

[English](INSTALLATION.md)

## Windows 发布版

1. 下载所需版本的 Windows x64 安装包或 ZIP。
2. 安装包直接运行并保留默认的当前用户安装位置；ZIP 必须完整解压到可写入的文件夹。
3. 双击 `AI Lightroom.exe`。

手动修图不需要 API Key，也不需要 JarvisArt。完整的首次使用、模型/本地 GGUF、AI 与导出说明见 [中文新手完整指南](GETTING_STARTED_zh-CN.md)；安装包细节见 [安装包说明](INSTALLER_zh-CN.md)。

## 从源码运行

需要 Windows 与 Python 3.11–3.13：

```powershell
git clone <repository-url>
Set-Location AI-Lightroom
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

只有想用环境变量配置 Provider 时才复制 `.env.example` 为 `.env`；绝不要提交 `.env`。
