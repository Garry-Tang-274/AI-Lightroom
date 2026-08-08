# Installation

## Windows release

1. Download the Windows x64 installer or ZIP for the desired release.
2. For the installer, run it and keep the default per-user installation directory. For the ZIP, extract the whole archive to a writable folder.
3. Run `AI Lightroom.exe`.

No API key or JarvisArt installation is required for manual editing.

For a Chinese first-run guide, model-download notes, and installer details, see [新手完整指南](GETTING_STARTED_zh-CN.md) and [安装包说明](INSTALLER_zh-CN.md).

## Source

Requires Python 3.11–3.13 on Windows.

```powershell
git clone <repository-url>
Set-Location AI-Lightroom
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

Copy `.env.example` to `.env` only if environment-variable configuration is preferred. Do not commit `.env`.
