# Windows Installer Guide

[简体中文](INSTALLER_zh-CN.md)

AI Lightroom is released as a per-user Windows installer and a portable ZIP. Both contain the same app. Neither package includes API keys, photos, local models, caches, or watermark assets.

## Recommended: installer

Download `AI-Lightroom-<version>-Setup.exe` from GitHub Releases.

1. Run the installer and choose an installation directory. The default is under the current user's local programs directory and does not require administrator access.
2. The wizard can create a desktop shortcut with the current AI Lightroom icon.
3. Launch from Start, the shortcut, or the installation directory.
4. To remove it, use **Windows Settings → Apps → Installed apps**, or the installed uninstaller.

Installing or uninstalling never removes photos. API keys live separately in Windows Credential Manager; delete them in app settings if required by your own security policy.

## Portable ZIP

Download `AI-Lightroom-<version>-windows-x64.zip`, extract it fully to a writable folder, then run `AI Lightroom.exe`. Do not run it from the compressed-archive viewer. To remove the portable copy, first ensure you do not need exports or user watermark assets, then delete only the extracted application folder—not your photo folders.

## SmartScreen and integrity

The public installer is not commercially code-signed yet. SmartScreen may show an unknown-publisher notice on first use. Download only from the official GitHub Release and check repository, version, and attachment name. If a hash, source, or signature appears unexpected, do not run the file.

## Build an installer from source

The project uses Inno Setup for per-user installation:

```powershell
.\scripts\build_windows.ps1
.\scripts\build_installer.ps1 -Version 1.0.2
```

The result is `releases\AI-Lightroom-1.0.2-Setup.exe`. Build scripts refuse to include `.env`, Windows credentials, user photos, or JarvisArt model weights.
