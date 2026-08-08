# Windows 安装包说明

AI Lightroom 同时提供安装包与 ZIP 绿色版。两者包含相同的应用功能；API Key、用户照片、模型、缓存和水印均不包含在发布文件中。

## 推荐：使用安装包

下载 Release 中名称类似 `AI-Lightroom-<版本>-Setup.exe` 的文件：

1. 双击运行，选择安装位置。默认安装到当前 Windows 用户的本地程序目录，不要求管理员权限。
2. 安装向导可创建桌面快捷方式；图标为 AI Lightroom 的应用图标。
3. 安装完成后从开始菜单、桌面快捷方式或安装目录启动。
4. 卸载时在 **设置 → 应用 → 已安装的应用** 中找到 AI Lightroom，或运行安装目录中的卸载程序。

安装和卸载都不会删除你的照片。API Key 由 Windows Credential Manager 保存；如需完全清除，请在应用设置中删除 Key，并按你的 Windows 安全策略清理凭据。

## ZIP 绿色版

下载 `AI-Lightroom-<版本>-windows-x64.zip` 后：

1. 选择一个有写入权限的位置，例如“文档”或独立的软件文件夹。
2. 完整解压 ZIP；不能从压缩包内直接运行 EXE。
3. 双击 `AI Lightroom.exe`。

绿色版不写入系统程序目录。想卸载时，先确认没有需要保留的导出照片或用户水印，再删除解压文件夹即可；不要删除你的原始照片目录。

## SmartScreen 与校验

当前公开安装包尚未使用商业代码签名证书，因此第一次运行时 Windows 可能显示 SmartScreen 提示。只应从本项目 GitHub Release 下载，确认仓库地址、版本号和 Release 附件名称。发现签名、哈希或来源异常时，不要继续运行。

## 给开发者重新生成安装包

项目使用 Inno Setup 生成按用户安装的安装包：

```powershell
.\scripts\build_windows.ps1
.\scripts\build_installer.ps1 -Version 1.0.2
```

生成文件位于 `releases\AI-Lightroom-1.0.2-Setup.exe`。脚本会检查是否先有可用的 PyInstaller 输出；不会把 `.env`、Windows 凭据、用户照片或 JarvisArt 模型收入安装包。
