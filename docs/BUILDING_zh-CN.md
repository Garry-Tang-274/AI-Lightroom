# Windows 打包

[English](BUILDING.md)

```powershell
Set-Location AI-Lightroom
.\.venv\Scripts\python.exe -m pytest -q
.\scripts\build_windows.ps1
.\scripts\package_release.ps1 -Version 1.0.2
.\scripts\build_installer.ps1 -Version 1.0.2
```

独立应用输出到 `dist\AI Lightroom`。ZIP 与安装包输出到 `releases\`；构建不会包含 API Key、模型权重、用户配置、照片、水印或 JarvisArt 本地运行时。
