# Building

```powershell
Set-Location AI-Lightroom
.\.venv\Scripts\python.exe -m pytest -q
.\scripts\build_windows.ps1
.\scripts\package_release.ps1 -Version 1.0.1
.\scripts\build_installer.ps1 -Version 1.0.1
```

The resulting standalone application is under `dist\AI Lightroom`. The release ZIP is written under `releases\` and does not contain API keys, model weights, user configurations, or JarvisArt.
